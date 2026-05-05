"""Rule: never propose an NDA to investor-tagged contacts.

Investors don't sign NDAs at first contact; proposing one signals
inexperience and friction.

Trigger: any of {'NDA', 'non-disclosure', 'non disclosure',
'비밀유지', '비공개협약'} in the OUTBOUND body of a cold_contacts/*.md
where the frontmatter declares the contact is an investor:
- vertical: investor, OR
- tags: [vc] / [investor] / [angel] (any of these)

Negation context exempts the match — e.g., 'no NDA needed',
'without NDA', 'NDA가 필요 없', 'NDA 없이'. The user can write
'investors don't need an NDA' without tripping the rule.

Scope:
- cold_contacts/*.md (body only, skip frontmatter)
- Gmail MCP create_draft body / subject / htmlBody (with no
  frontmatter to gate on, scans only when sent. Reasonable
  conservative default: scan every Gmail draft regardless of
  recipient classification.)

Allowed exceptions:
- File contains the marker `<!-- lint-disable vc-nda -->`
- Reply sections (`## Reply ...`) — recipient may have written 'NDA'.
"""
import re
from pathlib import Path

import yaml

from lint import Violation, is_archive_section_header

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCOPED_PREFIXES = ("cold_contacts/",)

INVESTOR_TAGS = {"vc", "investor", "angel"}

NDA_RE = re.compile(
    r"\b(NDA|non[-\s]?disclosure|비밀유지|비공개협약)\b",
    re.IGNORECASE,
)

# Negation-context regex applied to a window around the match.
NEG_RE = re.compile(
    r"\b(no|without|not\s+need(ed)?|don'?t\s+need|no\s+need\s+for|skip(ping)?)\b"
    r"|필요\s*없"
    r"|없이",
    re.IGNORECASE,
)

def _relpath(file_path: str) -> str:
    if not file_path:
        return ""
    p = str(file_path)
    root = str(PROJECT_ROOT) + "/"
    if p.startswith(root):
        return p[len(root):]
    return p


def _is_in_scope(file_path: str) -> bool:
    rel = _relpath(file_path)
    return any(rel.startswith(prefix) for prefix in SCOPED_PREFIXES)


def _is_investor_contact(text: str) -> bool:
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 4)
    if end == -1:
        return False
    try:
        fm = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return False
    if not isinstance(fm, dict):
        return False

    if str(fm.get("vertical", "")).strip().lower() == "investor":
        return True
    tags = fm.get("tags") or []
    if isinstance(tags, list):
        for t in tags:
            if str(t).strip().lower() in INVESTOR_TAGS:
                return True
    return False


def _is_negated(buf: str, match_start: int, match_end: int) -> bool:
    window = 40
    pre = buf[max(0, match_start - window):match_start]
    post = buf[match_end:match_end + window]
    return bool(NEG_RE.search(pre) or NEG_RE.search(post))


def _scannable_text(text: str, skip_frontmatter: bool) -> tuple[str, list[int]]:
    """Return (joined_buffer, offset_to_lineno_map). Skips frontmatter and reply sections."""
    lines = text.split("\n")
    in_frontmatter = False
    in_archive = False
    buf_parts: list[str] = []
    offset_to_line: list[int] = []

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if skip_frontmatter:
            if i == 1 and stripped == "---":
                in_frontmatter = True
                continue
            if in_frontmatter:
                if stripped == "---":
                    in_frontmatter = False
                continue

        if is_archive_section_header(stripped):
            in_archive = True
            continue
        if in_archive and (stripped.startswith("## ") or stripped.startswith("# ")):
            in_archive = False
        if in_archive:
            continue

        buf_parts.append(line)
        for _ in range(len(line)):
            offset_to_line.append(i)
        offset_to_line.append(i)  # newline glue

    return "\n".join(buf_parts), offset_to_line


def _scan(text: str, source: str, skip_frontmatter: bool, gate_on_investor: bool) -> list[Violation]:
    if "<!-- lint-disable vc-nda -->" in text:
        return []

    if gate_on_investor and not _is_investor_contact(text):
        return []

    buf, offset_to_line = _scannable_text(text, skip_frontmatter)
    if not buf:
        return []

    violations: list[Violation] = []
    for m in NDA_RE.finditer(buf):
        if _is_negated(buf, m.start(), m.end()):
            continue
        line_no = offset_to_line[m.start()] if m.start() < len(offset_to_line) else 0
        violations.append(Violation(
            rule="vc-nda",
            file_path=source,
            line=line_no,
            severity="block",
            message=(
                f"{source}:{line_no} '{m.group(0)}' in outbound to investor "
                f"contact. Investors don't sign NDAs at first contact; "
                f"proposing one signals friction. Either drop the mention or "
                f"reframe as 'no NDA needed'."
            ),
        ))
    return violations


def check(tool_name: str, tool_input: dict) -> list[Violation]:
    violations: list[Violation] = []

    file_path = tool_input.get("file_path", "") or ""
    if file_path and _is_in_scope(file_path):
        rel = _relpath(file_path)
        for field in ("content", "new_string"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan(text, rel, skip_frontmatter=True, gate_on_investor=True))
        for edit in tool_input.get("edits", []) or []:
            ns = edit.get("new_string", "") or ""
            if ns:
                violations.extend(_scan(ns, rel, skip_frontmatter=True, gate_on_investor=True))

    if tool_name == "mcp__claude_ai_Gmail__create_draft":
        # Conservative: scan every draft. Most drafts don't mention NDA, so
        # the false-positive rate is low and the cost of missing one to a
        # VC is high.
        for field in ("subject", "body", "htmlBody"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan(text, f"Gmail.{field}", skip_frontmatter=False, gate_on_investor=False))

    return violations

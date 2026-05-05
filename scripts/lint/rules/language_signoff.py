"""Rule: outbound message body language must match the signoff language.

Korean body + English-only signoff (e.g. "Co-founder & CEO, Acme")
reads as a translated pitch and undermines the message. The inverse
(English body + Korean closer) reads as a paste error.

This rule fires when:
1. The body of the DRAFT section (everything except the last 2 non-blank
   lines) has Hangul ratio ≥ 20%, AND
2. The signoff (last 2 non-blank lines) contains an English-only role
   marker (`Co-founder`, `CEO`, `Founder`, `CTO`, `COO`, `President`),
   AND
3. The signoff has no canonical Korean closer (`드림`, `올림`).

Inverse trigger: body Hangul ratio < 5% AND signoff has a Korean
closer AND signoff has no English role marker.

Scope:
- cold_contacts/*.md (DRAFT sections only — `## Outbound draft pending
  review`)
- drafts/*.md
- Gmail MCP create_draft body / htmlBody

Allowed exceptions:
- File contains the marker `<!-- lint-disable language-signoff -->`.
- Archive sections (`## Sent`, `## Reply`, etc.) — historical content.
"""
import re
from pathlib import Path

from lint import Violation, is_archive_section_header

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCOPED_PREFIXES = ("cold_contacts/", "drafts/")

DRAFT_HEADER_PREFIXES = (
    "## Outbound draft pending review",
    "## Draft",
)

HANGUL_RE = re.compile(r"[가-힯ᄀ-ᇿ㄰-㆏]")
LATIN_RE = re.compile(r"[A-Za-z]")

ENGLISH_SIGNOFF_RE = re.compile(
    r"\b(Co-?founder|CEO|Founder|CTO|COO|President)\b",
)
# Narrow to canonical Korean signoff closers — `드림`, `올림`. Common body
# verbs like `드립니다` and `감사합니다` are NOT signoff markers (they appear
# throughout polite Korean prose).
KOREAN_SIGNOFF_RE = re.compile(r"드림|올림")


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


def _is_draft_header(stripped: str) -> bool:
    return any(stripped.startswith(p) for p in DRAFT_HEADER_PREFIXES)


def _hangul_ratio(text: str) -> float:
    if not text:
        return 0.0
    hangul = len(HANGUL_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    total = hangul + latin
    if total == 0:
        return 0.0
    return hangul / total


def _check_section(section_lines: list[str], header_line: int, source: str) -> list[Violation]:
    """Return violations found in a single draft section's body."""
    if not any(ln.strip() for ln in section_lines):
        return []

    # Split the section into body (everything except last 2 non-blank lines)
    # and signoff (last 2 non-blank lines). Body ratio measures the message
    # text language; signoff ratio measures the signature language.
    non_blank = [ln for ln in section_lines if ln.strip()]
    if len(non_blank) < 2:
        # Too short to have both body and signoff
        return []
    signoff_lines = non_blank[-2:]
    body_lines = non_blank[:-2]
    body_text = "\n".join(body_lines)
    signoff_text = "\n".join(signoff_lines)

    if not body_text.strip():
        return []

    ratio = _hangul_ratio(body_text)

    has_eng_signoff = bool(ENGLISH_SIGNOFF_RE.search(signoff_text))
    has_kor_signoff = bool(KOREAN_SIGNOFF_RE.search(signoff_text))

    violations: list[Violation] = []

    # Korean body + English-only signoff
    if ratio >= 0.20 and has_eng_signoff and not has_kor_signoff:
        violations.append(Violation(
            rule="language-signoff",
            file_path=source,
            line=header_line,
            severity="block",
            message=(
                f"{source}:{header_line} draft body has Korean text "
                f"(Hangul ratio {ratio:.0%}) but the signoff uses "
                f"English-only role markers (Co-founder/CEO/Founder) "
                f"with no Korean closer (드림/올림). Match the signoff "
                f"language to the body."
            ),
        ))

    # English body + Korean signoff
    if ratio < 0.05 and has_kor_signoff and not has_eng_signoff:
        # English body has near-zero Hangul; any Korean closer reads as a
        # mistakenly-pasted signoff fragment.
        violations.append(Violation(
            rule="language-signoff",
            file_path=source,
            line=header_line,
            severity="block",
            message=(
                f"{source}:{header_line} draft body is predominantly "
                f"English but the signoff includes a Korean closer "
                f"(드림/올림/감사합니다). Match the signoff language to "
                f"the body."
            ),
        ))

    return violations


def _scan_text(text: str, source: str, skip_frontmatter: bool = True) -> list[Violation]:
    if "<!-- lint-disable language-signoff -->" in text:
        return []

    lines = text.split("\n")
    in_frontmatter = False
    in_draft = False
    in_archive = False
    draft_header_line = 0
    draft_body: list[str] = []
    violations: list[Violation] = []

    def _flush() -> None:
        nonlocal in_draft, draft_body, draft_header_line
        if in_draft and draft_body:
            violations.extend(_check_section(draft_body, draft_header_line, source))
        in_draft = False
        draft_body = []
        draft_header_line = 0

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

        if _is_draft_header(stripped):
            _flush()
            in_archive = False
            in_draft = True
            draft_header_line = i
            draft_body = []
            continue
        if is_archive_section_header(stripped):
            _flush()
            in_archive = True
            continue
        if stripped.startswith("## ") or stripped.startswith("# "):
            _flush()
            in_archive = False
            continue
        if in_draft and not in_archive:
            draft_body.append(line)

    _flush()
    return violations


def check(tool_name: str, tool_input: dict) -> list[Violation]:
    violations: list[Violation] = []

    file_path = tool_input.get("file_path", "") or ""
    if file_path and _is_in_scope(file_path):
        rel = _relpath(file_path)
        for field in ("content", "new_string"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan_text(text, rel, skip_frontmatter=True))
        for edit in tool_input.get("edits", []) or []:
            ns = edit.get("new_string", "") or ""
            if ns:
                violations.extend(_scan_text(ns, rel, skip_frontmatter=True))

    if tool_name == "mcp__claude_ai_Gmail__create_draft":
        for field in ("body", "htmlBody"):
            text = tool_input.get(field, "") or ""
            if text:
                # Treat the whole Gmail body as a single 'draft section'.
                synthesized = "## Outbound draft pending review (gmail)\n\n" + text
                violations.extend(_scan_text(synthesized, f"Gmail.{field}", skip_frontmatter=False))

    return violations

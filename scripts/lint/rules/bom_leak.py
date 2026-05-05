"""Rule: warn on $-amount BOM mentions in outbound message content.

For hardware projects, BOM cost figures and disparaging synonyms
("commodity BOM", "budget parts", "cheap parts") are internal cost
data that should not appear in routine outreach. Severity is WARN,
not BLOCK, because investor / partnership conversations sometimes
legitimately need to discuss BOM economics. The warning surfaces
every mention so the user can confirm intent before sending.

Detection has two patterns:
  A. PROXIMITY: 'BOM' (case-insensitive, word boundary) within
     PROXIMITY_WINDOW characters of any '$<digits>' pattern. Catches
     constructions like "$N BOM", "$N BOM cost", "BOM is $N".
  B. LITERAL: phrases "commodity BOM", "budget parts", "cheap parts".

Scope:
- cold_contacts/*.md  (outbound sections only, NOT '## Reply ...')
- drafts/*.md
- Gmail MCP create_draft body / subject / htmlBody

Allowed exceptions:
- File contains the marker `<!-- lint-disable bom-leak -->`
- Reply sections: anything under `## Reply`-prefixed headings (the
  recipient may have written 'BOM' or '$N' in their reply, preserved
  verbatim).
- YAML frontmatter (e.g. 'notes' field; internal record).
"""
import re
from pathlib import Path

from lint import Violation, is_archive_section_header

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCOPED_PREFIXES = ("cold_contacts/", "drafts/")

PROXIMITY_WINDOW = 200

BOM_RE = re.compile(r"\bBOM\b", re.IGNORECASE)
DOLLAR_RE = re.compile(r"\$\d+")
LITERAL_RE = re.compile(
    r"\b(commodity\s+BOM|budget\s+parts|cheap\s+parts)\b",
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


def _classify_lines(text: str, skip_frontmatter: bool) -> list[tuple[int, str, bool]]:
    """Return [(line_no, text, scannable)] tuples.

    `scannable` is False for: frontmatter lines (if skip_frontmatter),
    lines inside ## Reply sections, and the heading lines themselves.
    """
    lines = text.split("\n")
    result: list[tuple[int, str, bool]] = []
    in_frontmatter = False
    in_archive = False

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        scannable = True

        if skip_frontmatter:
            if i == 1 and stripped == "---":
                in_frontmatter = True
                scannable = False
                result.append((i, line, scannable))
                continue
            if in_frontmatter:
                if stripped == "---":
                    in_frontmatter = False
                scannable = False
                result.append((i, line, scannable))
                continue

        if is_archive_section_header(stripped):
            in_archive = True
            scannable = False
            result.append((i, line, scannable))
            continue
        if in_archive and (stripped.startswith("## ") or stripped.startswith("# ")):
            in_archive = False
            # The heading line itself is not in archive, but other section
            # headers are also not 'scannable' as content (they're metadata).
            # Heading lines rarely contain BOM/$\d+ pairs anyway.

        if in_archive:
            scannable = False

        result.append((i, line, scannable))

    return result


def _scan(text: str, source: str, skip_frontmatter: bool = True) -> list[Violation]:
    if "<!-- lint-disable bom-leak -->" in text:
        return []

    classified = _classify_lines(text, skip_frontmatter)

    # Build the scannable buffer with offset->line_no map.
    buf_parts: list[str] = []
    offset_to_line: list[int] = []  # offset_to_line[offset] = line_no
    cur = 0
    for line_no, line, scannable in classified:
        if not scannable:
            continue
        buf_parts.append(line)
        for _ in range(len(line)):
            offset_to_line.append(line_no)
        # Newline glue between lines
        offset_to_line.append(line_no)
        cur += len(line) + 1
    buf = "\n".join(buf_parts)

    if not buf:
        return []

    violations: list[Violation] = []
    flagged_offsets: set[int] = set()

    # Pattern A: proximity
    bom_matches = list(BOM_RE.finditer(buf))
    dollar_matches = list(DOLLAR_RE.finditer(buf))
    for bom in bom_matches:
        for d in dollar_matches:
            if abs(bom.start() - d.start()) <= PROXIMITY_WINDOW:
                if bom.start() in flagged_offsets:
                    continue
                flagged_offsets.add(bom.start())
                line_no = (
                    offset_to_line[bom.start()]
                    if bom.start() < len(offset_to_line) else 0
                )
                violations.append(Violation(
                    rule="bom-leak",
                    file_path=source,
                    line=line_no,
                    severity="warn",
                    message=(
                        f"{source}:{line_no} 'BOM' appears within "
                        f"{PROXIMITY_WINDOW} chars of a $-amount "
                        f"('{d.group(0)}'). BOM figures are internal "
                        f"cost data and should not leave the team."
                    ),
                ))
                break

    # Pattern B: literal phrases
    for m in LITERAL_RE.finditer(buf):
        if m.start() in flagged_offsets:
            continue
        flagged_offsets.add(m.start())
        line_no = offset_to_line[m.start()] if m.start() < len(offset_to_line) else 0
        violations.append(Violation(
            rule="bom-leak",
            file_path=source,
            line=line_no,
            severity="warn",
            message=(
                f"{source}:{line_no} forbidden phrase '{m.group(0)}'. "
                f"Use the project's retail / volume-pricing language "
                f"in outreach instead."
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
                violations.extend(_scan(text, rel, skip_frontmatter=True))
        for edit in tool_input.get("edits", []) or []:
            ns = edit.get("new_string", "") or ""
            if ns:
                violations.extend(_scan(ns, rel, skip_frontmatter=True))

    if tool_name == "mcp__claude_ai_Gmail__create_draft":
        for field in ("subject", "body", "htmlBody"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan(text, f"Gmail.{field}", skip_frontmatter=False))

    return violations

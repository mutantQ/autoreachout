"""Rule: no em-dash, en-dash, or double-hyphen in outreach content.

Strict policy: em-dash (U+2014), en-dash (U+2013), ASCII
double-hyphen (--) all banned.

Scope:
- File writes to cold_contacts/*.md
- File writes to drafts/*.md
- reports/OUTREACH_REPORT.md
- Gmail MCP create_draft body, subject, htmlBody

Allowed exceptions:
- YAML frontmatter block (between first pair of ^---$ lines)
- Markdown horizontal rules (^---$, ^***$, ^___$ on their own)
- Blockquote lines (^> ...) — preserves external quoted content verbatim
- Files containing the marker <!-- lint-disable em-dash --> at top of content
- HTML comments <!-- ... --> (single-line and multi-line) are stripped
  before scanning, so lint-disable markers and other comment-internal '--'
  do not false-trigger.
"""
import re
from pathlib import Path

from lint import Violation

FORBIDDEN = re.compile(r"(—|–|(?<!-)--(?!-))")
# — = em-dash, – = en-dash, -- = double-hyphen.
# `(?<!-)--(?!-)` prevents matching the inner pair of `---` (horizontal
# rule, YAML frontmatter delimiter, or backtick-quoted YAML reference).

SCOPED_PREFIXES = (
    "cold_contacts/",
    "drafts/",
)
SCOPED_SUFFIXES = (
    "reports/OUTREACH_REPORT.md",
)
PROJECT_ROOT = Path(__file__).resolve().parents[3]


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
    if not rel:
        return False
    if any(rel.startswith(prefix) for prefix in SCOPED_PREFIXES):
        return True
    if any(rel.endswith(suffix) for suffix in SCOPED_SUFFIXES):
        return True
    return False


def _scan_text(text: str, source: str) -> list[Violation]:
    """Scan text for forbidden dashes; respects structural exceptions."""
    violations: list[Violation] = []

    if "<!-- lint-disable em-dash -->" in text:
        return violations

    # Strip HTML comments before scanning so lint-disable markers and other
    # comment-internal `--` (e.g. `<!-- lint-disable connection-note-length -->`)
    # do not false-trigger. Replace with spaces of equal length to preserve
    # line numbers and approximate column offsets for downstream violations.
    def _blank_html_comment(match: "re.Match[str]") -> str:
        return "".join("\n" if ch == "\n" else " " for ch in match.group(0))

    text = re.sub(r"<!--.*?-->", _blank_html_comment, text, flags=re.DOTALL)

    lines = text.split("\n")
    in_frontmatter = False

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # YAML frontmatter open/close
        if i == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and stripped == "---":
            in_frontmatter = False
            continue
        if in_frontmatter:
            # frontmatter values also checked
            pass

        # Markdown horizontal rule
        if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", line):
            continue

        # Markdown table separator row: e.g. `|---|---|---|` or
        # `| :--- | ---: | --- |`. Contains at least one `|` and
        # consists only of pipes, dashes, colons, and whitespace.
        if "|" in stripped and re.fullmatch(r"[\s|\-:]+", stripped):
            continue

        # Blockquote (external quoted content)
        if stripped.startswith(">"):
            continue

        for m in FORBIDDEN.finditer(line):
            token = m.group(0)
            name = {"—": "em-dash", "–": "en-dash", "--": "double-hyphen"}[token]
            context = stripped[:80]
            violations.append(Violation(
                rule="em-dash",
                file_path=source,
                line=i,
                severity="block",
                message=(
                    f"{source}:{i} forbidden {name} '{token}' at col {m.start()}. "
                    f"Context: \"{context}\". Fix: use comma/period/restructure, not dashes. "
                    f"Override per-file with <!-- lint-disable em-dash -->."
                ),
            ))
    return violations


def check(tool_name: str, tool_input: dict) -> list[Violation]:
    """Inspect the outgoing tool call for forbidden dashes."""
    violations: list[Violation] = []

    file_path = tool_input.get("file_path", "") or ""
    if file_path and _is_in_scope(file_path):
        content = tool_input.get("content", "")
        if content:
            violations.extend(_scan_text(content, _relpath(file_path)))
        new_string = tool_input.get("new_string", "")
        if new_string:
            violations.extend(_scan_text(new_string, _relpath(file_path)))
        for edit in tool_input.get("edits", []) or []:
            ns = edit.get("new_string", "") or ""
            if ns:
                violations.extend(_scan_text(ns, _relpath(file_path)))

    if tool_name == "mcp__claude_ai_Gmail__create_draft":
        for field in ("subject", "body", "htmlBody"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan_text(text, f"Gmail.{field}"))

    return violations

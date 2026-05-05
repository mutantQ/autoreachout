"""Rule: detect LinkedIn quick-reaction picker emojis logged as content.

LinkedIn's DM UI shows a quick-reaction picker (a row of preset emojis,
by default the trio clap / thumbs-up / smiley) above the message input.
When a user pastes a thread verbatim, the picker row appears alongside
real messages and is easy to mislog as reactions sent by the other party.

This rule blocks writes that introduce the picker trio either:
- Inline as content (`👏 👍 😊` on the same line, e.g. logged as "Leo: ...
  *(LinkedIn reactions)*"), OR
- As 3+ consecutive solo-emoji lines (raw paste shape with each emoji on
  its own line, 2+ unique emojis from the picker set).

Allowed exceptions:
- File contains the marker `<!-- lint-disable linkedin-ui-artifacts -->`.
- The inline-trio line ALSO contains a meta-discussion keyword (`picker`,
  `UI artifact`, `not content`, `reaction button`, `not reactions`,
  `buttons preceded`, `preceded the message`).
- YAML frontmatter (between the first pair of `^---$` lines).

Scope:
- outreach/cold_contacts/*.md
- outreach/drafts/*.md
"""
import re
from pathlib import Path

from lint import Violation

PICKER_EMOJIS = ("\U0001F44F", "\U0001F44D", "\U0001F60A")  # clap, thumbs-up, smiley

META_KEYWORDS_RE = re.compile(
    r"\b(picker|UI artifact|UI artifacts|reaction button|reaction buttons|"
    r"buttons preceded|not content|not reactions|not a reaction|"
    r"preceded the message)\b",
    re.IGNORECASE,
)

SCOPED_PREFIXES = (
    "cold_contacts/",
    "drafts/",
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
    return any(rel.startswith(prefix) for prefix in SCOPED_PREFIXES)


def _line_has_full_trio(line: str) -> bool:
    return all(e in line for e in PICKER_EMOJIS)


def _is_meta_explanation(line: str) -> bool:
    return bool(META_KEYWORDS_RE.search(line))


def _is_solo_picker_line(line: str) -> bool:
    s = line.strip().lstrip(">").strip()
    return s in PICKER_EMOJIS


def _stacked_violation(source: str, start_line: int, count: int) -> Violation:
    return Violation(
        rule="linkedin-ui-artifacts",
        file_path=source,
        line=start_line,
        message=(
            f"{source}:{start_line} stacked LinkedIn quick-reaction picker "
            f"emojis ({count} consecutive solo-emoji lines, 2+ unique). "
            f"Likely UI paste, not real reactions. Strip the picker row, "
            f"or use the marker <!-- lint-disable linkedin-ui-artifacts -->."
        ),
    )


def _scan_text(text: str, source: str) -> list[Violation]:
    violations: list[Violation] = []

    if "<!-- lint-disable linkedin-ui-artifacts -->" in text:
        return violations

    lines = text.split("\n")

    # Pass 1: identify frontmatter line indices to skip
    skip_indices: set[int] = set()
    in_frontmatter = False
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if i == 1 and stripped == "---":
            in_frontmatter = True
            skip_indices.add(i)
            continue
        if in_frontmatter and stripped == "---":
            in_frontmatter = False
            skip_indices.add(i)
            continue
        if in_frontmatter:
            skip_indices.add(i)

    # Pass 2: inline trio
    for i, line in enumerate(lines, start=1):
        if i in skip_indices:
            continue
        if _line_has_full_trio(line) and not _is_meta_explanation(line):
            violations.append(Violation(
                rule="linkedin-ui-artifacts",
                file_path=source,
                line=i,
                message=(
                    f"{source}:{i} LinkedIn quick-reaction picker trio "
                    f"appears inline. This is the LinkedIn UI reaction "
                    f"picker row, not real reactions. Strip it from the "
                    f"log, or add a meta keyword ('picker', 'UI artifact', "
                    f"'not reactions') to clarify, or use the marker "
                    f"<!-- lint-disable linkedin-ui-artifacts --> to override."
                ),
            ))

    # Pass 3: stacked solo emojis (3+ consecutive lines, 2+ unique)
    consec_count = 0
    consec_seen: set[str] = set()
    consec_start: int | None = None

    def _flush() -> None:
        if consec_count >= 3 and len(consec_seen) >= 2:
            violations.append(_stacked_violation(source, consec_start or 1, consec_count))

    for i, line in enumerate(lines, start=1):
        if i in skip_indices:
            _flush()
            consec_count = 0
            consec_seen = set()
            consec_start = None
            continue
        if _is_solo_picker_line(line):
            consec_count += 1
            consec_seen.add(line.strip().lstrip(">").strip())
            if consec_start is None:
                consec_start = i
        else:
            _flush()
            consec_count = 0
            consec_seen = set()
            consec_start = None
    _flush()

    return violations


def check(tool_name: str, tool_input: dict) -> list[Violation]:
    violations: list[Violation] = []

    file_path = tool_input.get("file_path", "") or ""
    if file_path and _is_in_scope(file_path):
        for field in ("content", "new_string"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan_text(text, _relpath(file_path)))
        for edit in tool_input.get("edits", []) or []:
            ns = edit.get("new_string", "") or ""
            if ns:
                violations.extend(_scan_text(ns, _relpath(file_path)))

    return violations

"""Rule: timezone-conversion arithmetic must be correct in outbound drafts.

When a draft says "10:00 PST (= 02:00 JST)" but 10:00 PST (= UTC-8)
maps to 03:00 JST (= UTC+9, diff=+17h) the next day, the recipient
and sender carry different mental anchors of the meeting time. The
calendar invite may be stored at the correct UTC offset, but the
prose written into the email body becomes the human anchor and can
override the calendar.

The failure mode is generic across any cross-timezone pair: prose
arithmetic is easy to get wrong by an hour, and the recipient often
trusts the prose over the invite.

Trigger: a paired `H:MM TZ1` … `H:MM TZ2` where:
- both TZ tokens have unambiguous offsets in the table below,
- TZ1 ≠ TZ2,
- the gap between the two times begins with a conversion separator
  (`(`, `=`, `≈`, `→`, `/`) and is ≤30 characters,
- the arithmetic is wrong by more than 1 minute (mod 24 hours).

Scope:
- cold_contacts/*.md (body zones, excluding frontmatter and archive sections)
- vendors/*.md
- drafts/*.md
- Gmail MCP create_draft body / htmlBody

Allowed exceptions:
- File contains marker `<!-- lint-disable timezone-conversion -->`.
- Phrase is in YAML frontmatter.
- Phrase is in archive section (## Sent, ## Reply, ## Follow-up, etc.).
- One or both timezone abbreviations are not in the offsets table
  (e.g., CST, IST, BST — too ambiguous to verify safely).
"""
import re
from pathlib import Path

from lint import Violation, is_archive_section_header

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCOPED_PREFIXES = ("cold_contacts/", "vendors/", "drafts/")

# Unambiguous timezone offsets vs UTC, in hours. Excluded as ambiguous:
# CST (US Central -6 vs China +8), IST (India +5.5 vs Israel +2/+3),
# BST (UK +1 vs Bangladesh +6), AST, SAST, WST.
TZ_OFFSETS = {
    "UTC": 0, "GMT": 0,
    "KST": 9, "JST": 9,
    "CET": 1, "CEST": 2,
    "EST": -5, "EDT": -4,
    "MST": -7, "MDT": -6,
    "PST": -8, "PDT": -7,
    "CDT": -5,
    "AEST": 10, "AEDT": 11,
    "NZST": 12, "NZDT": 13,
}

TIME_TZ_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d{1,2}):(\d{2})\s+([A-Z]{2,5})(?![A-Za-z])",
)

GAP_START_RE = re.compile(r"^\s*[(=≈→/]")


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


def _is_conversion_gap(gap: str) -> bool:
    if len(gap) > 30:
        return False
    return bool(GAP_START_RE.match(gap))


def _check_pair(h1: int, m1: int, tz1: str, h2: int, m2: int, tz2: str) -> bool:
    """True if the conversion is correct within 1 minute (mod 24h)."""
    off1 = TZ_OFFSETS[tz1]
    off2 = TZ_OFFSETS[tz2]
    expected = (h1 * 60 + m1 + (off2 - off1) * 60) % (24 * 60)
    actual = (h2 * 60 + m2) % (24 * 60)
    diff = (expected - actual) % (24 * 60)
    return min(diff, 24 * 60 - diff) <= 1


def _scan_text(text: str, source: str) -> list[Violation]:
    if "<!-- lint-disable timezone-conversion -->" in text:
        return []

    lines = text.split("\n")
    skip_indices: set[int] = set()
    in_frontmatter = False
    in_archive = False
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if i == 1 and stripped == "---":
            in_frontmatter = True
            skip_indices.add(i)
            continue
        if in_frontmatter:
            skip_indices.add(i)
            if stripped == "---":
                in_frontmatter = False
            continue
        if is_archive_section_header(stripped):
            in_archive = True
            skip_indices.add(i)
            continue
        if stripped.startswith("## ") or stripped.startswith("# "):
            in_archive = False
        if in_archive:
            skip_indices.add(i)

    scannable_lines: list[str] = []
    line_num_map: list[int] = []
    for i, line in enumerate(lines, start=1):
        if i in skip_indices:
            continue
        scannable_lines.append(line)
        line_num_map.append(i)

    if not scannable_lines:
        return []
    scannable_text = "\n".join(scannable_lines)

    matches = list(TIME_TZ_RE.finditer(scannable_text))

    groups: list[tuple[str, list[re.Match]]] = []
    for m in matches:
        tz = m.group(3).upper()
        if groups and groups[-1][0] == tz:
            groups[-1][1].append(m)
        else:
            groups.append((tz, [m]))

    violations: list[Violation] = []
    for i in range(len(groups) - 1):
        tz1, matches1 = groups[i]
        tz2, matches2 = groups[i + 1]
        if tz1 == tz2:
            continue
        if tz1 not in TZ_OFFSETS or tz2 not in TZ_OFFSETS:
            continue

        last1 = matches1[-1]
        first2 = matches2[0]
        gap = scannable_text[last1.end():first2.start()]
        if not _is_conversion_gap(gap):
            continue

        for k in range(min(len(matches1), len(matches2))):
            m1 = matches1[k]
            m2 = matches2[k]
            h1 = int(m1.group(1))
            mn1 = int(m1.group(2))
            h2 = int(m2.group(1))
            mn2 = int(m2.group(2))
            if _check_pair(h1, mn1, tz1, h2, mn2, tz2):
                continue
            off1 = TZ_OFFSETS[tz1]
            off2 = TZ_OFFSETS[tz2]
            correct_total = (h1 * 60 + mn1 + (off2 - off1) * 60) % (24 * 60)
            ch, cm = divmod(correct_total, 60)
            line_idx = scannable_text[:m1.start()].count("\n")
            line_num = line_num_map[line_idx]
            violations.append(Violation(
                rule="timezone-conversion",
                file_path=source,
                line=line_num,
                severity="block",
                message=(
                    f"{source}:{line_num} timezone conversion error: "
                    f"{h1:d}:{mn1:02d} {tz1} = {ch:d}:{cm:02d} {tz2}, "
                    f"but text says {h2:d}:{mn2:02d} {tz2}. "
                    f"({tz1}=UTC{off1:+d}, {tz2}=UTC{off2:+d}, "
                    f"diff={off2 - off1:+d}h). Worked-example failure: a "
                    f"meeting was missed by an hour because the prose anchor "
                    f"in a confirmation email overrode the calendar offset."
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
                violations.extend(_scan_text(text, rel))
        for edit in tool_input.get("edits", []) or []:
            ns = edit.get("new_string", "") or ""
            if ns:
                violations.extend(_scan_text(ns, rel))

    if tool_name == "mcp__claude_ai_Gmail__create_draft":
        for field in ("body", "htmlBody"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan_text(text, f"Gmail.{field}"))

    return violations

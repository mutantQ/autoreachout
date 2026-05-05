"""Rule: `## Outbound draft pending` header is reserved for LinkedIn channel.

LinkedIn connection notes have a hard 300-char limit and a specific
channel context. The convention `## Outbound draft pending review` (and
variants) is the LinkedIn-specific draft section header, scanned by
`connection-note-length` for the 300-char budget.

For non-LinkedIn channels (email, KakaoTalk, Discord, etc.), this header
is wrong on two counts: it triggers `connection-note-length` false
positives (since email/KakaoTalk drafts naturally exceed 300 chars), and
it misclassifies which channel will receive the message.

Right headers for non-LinkedIn drafts:
- Email: `## Email draft pending review: <topic>`
- KakaoTalk: `## KakaoTalk DM ... pending review`

Pairs with `connection-note-length` which assumes the LinkedIn convention.

Scope:
- cold_contacts/*.md
- drafts/*.md

Triggers (OR):
- Frontmatter `channel:` field is set and does NOT contain "linkedin"
  (case-insensitive), AND a `## Outbound draft pending` section exists.
- A `## Outbound draft pending` section's body contains an explicit
  non-LinkedIn channel indicator (e.g. `**채널:** Email`,
  `**채널:** KakaoTalk`, `Gmail thread`, `kakaotalk_chat_id`).

Allowed exceptions:
- File contains the marker `<!-- lint-disable outbound-draft-channel-mismatch -->`.
"""
import re
from pathlib import Path

from lint import Violation

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCOPED_PREFIXES = ("cold_contacts/", "drafts/")

DRAFT_HEADER_PREFIX = "## Outbound draft pending"

EMAIL_INDICATOR_RE = re.compile(
    r"(\*\*채널:\*\*\s*Email|\*\*Channel:\*\*\s*Email|Gmail\s+thread)",
    re.IGNORECASE,
)
KAKAO_INDICATOR_RE = re.compile(
    r"(\*\*채널:\*\*\s*KakaoTalk|\*\*Channel:\*\*\s*KakaoTalk|kakaotalk_chat_id)",
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


def _extract_channel(lines: list[str]) -> str | None:
    """Return the value of `channel:` from YAML frontmatter, or None."""
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        s = line.strip()
        if s == "---":
            break
        if s.startswith("channel:"):
            return s[len("channel:"):].strip().strip('"').strip("'")
    return None


def _detect_body_channel(body: str) -> str | None:
    """Return 'email' or 'kakaotalk' if body has an explicit non-LinkedIn signal."""
    if EMAIL_INDICATOR_RE.search(body):
        return "email"
    if KAKAO_INDICATOR_RE.search(body):
        return "kakaotalk"
    return None


def _scan_text(text: str, source: str) -> list[Violation]:
    if "<!-- lint-disable outbound-draft-channel-mismatch -->" in text:
        return []

    lines = text.split("\n")
    channel = _extract_channel(lines)
    frontmatter_blocks = channel is not None and "linkedin" not in channel.lower()

    violations: list[Violation] = []

    current_header: str | None = None
    current_header_line: int = 0
    current_body: list[str] = []

    def _evaluate() -> None:
        nonlocal current_header, current_header_line, current_body
        if current_header is None:
            return
        body_text = "\n".join(current_body)
        body_signal = _detect_body_channel(body_text)

        reasons: list[str] = []
        if frontmatter_blocks:
            reasons.append(f"frontmatter channel='{channel}' has no 'linkedin'")
        if body_signal:
            reasons.append(f"body has explicit {body_signal} indicator")

        if reasons:
            if body_signal == "email":
                suggested = "## Email draft pending review"
            elif body_signal == "kakaotalk":
                suggested = "## KakaoTalk DM pending review"
            else:
                suggested = "a channel-specific prefix (not 'Outbound')"
            violations.append(Violation(
                rule="outbound-draft-channel-mismatch",
                file_path=source,
                line=current_header_line,
                severity="block",
                message=(
                    f"{source}:{current_header_line} '{current_header}' "
                    f"uses the LinkedIn-only '## Outbound draft pending' "
                    f"prefix but {' AND '.join(reasons)}. This prefix "
                    f"triggers the `connection-note-length` 300-char rule "
                    f"and misclassifies the channel. Use {suggested} "
                    f"instead. Override with "
                    f"<!-- lint-disable outbound-draft-channel-mismatch -->."
                ),
            ))

        current_header = None
        current_header_line = 0
        current_body = []

    in_frontmatter = False
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if i == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue

        if stripped.startswith("## "):
            _evaluate()
            if stripped.startswith(DRAFT_HEADER_PREFIX):
                current_header = stripped
                current_header_line = i
                current_body = []
            continue
        if stripped.startswith("# "):
            _evaluate()
            continue
        if current_header is not None:
            current_body.append(line)

    _evaluate()
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

    return violations

"""Rule: no Markdown formatting inside the body zone of outbound drafts.

Email/DM/SMS bodies render Markdown LITERALLY when copy-pasted into
Gmail, 리멤버, KakaoTalk, SMS, etc. The recipient sees the asterisks,
brackets, backticks. The `body_headings` rule already catches `####+`
headings; this rule covers the rest of the Markdown family inside the
body zone:

- `**bold**` and `__bold__`
- `[text](url)` links
- `` `inline code` `` (single-backtick spans)
- triple-backtick code fences

Single-asterisk emphasis (`*x*`) and single-underscore emphasis (`_x_`)
are NOT blocked — they false-positive on multiplication signs, names
with underscores, footnote markers, and similar prose.

Worked-example failures:
- A past draft used `**bold**` after a worker initially used `####`
  headings; both render as literal characters in pasted email.
- A vendor brief and a CA inquiry both contained body-zone
  bold/links that would have rendered literally to recipients.

Scope:
- cold_contacts/*.md
- vendors/*.md

Body zone detection (heuristic):
- Body STARTS at `### Body` (canonical), or, when absent, at the first
  non-meta line after a recognized outbound section header
  (`## Sent (...)`, `## Outbound draft pending review (...)`,
  `## Reply received (...)`, `## Reply sent (...)`,
  `## Follow-up sent (...)`, `## Email sent (...)`,
  `## Confirmation DM sent (...)`, `## SMS sent (...)`,
  `## In-person meeting completed (...)`, etc.). Meta is the run of
  consecutive `**Field:** value` lines and blank lines immediately
  following the section header — they're scaffolding, not body.
- Body ENDS at the next `### ` or `## ` heading, OR at any of the
  recognized "post-body" markers: `### Acceptance check`, `### Reviewer
  attention flags`, `### 사전 준비`, `### 발송 후 체크리스트`,
  `### Send pre-flight checklist`, `### Open actions`, `### Notes`,
  `### Why this exists`, OR EOF.

Outside the body zone, Markdown is allowed (meta scaffolding like
`**Channel:** linkedin`, `**To:** kim@example.com`, the bold in
`### Reviewer attention flags` items, etc. all render only in the
local Markdown viewer and never get sent).

Allowed exceptions:
- File contains the marker `<!-- lint-disable no-markdown-in-body -->`.
- YAML frontmatter (between the first pair of `^---$` lines).
- Code fences themselves: the opening/closing ``` lines trigger, but
  contents inside fences are not re-scanned for inner Markdown.
- Annotation label lines matching '**Label:**' at line start (e.g.,
  **Read:**, **Status:**, **Action:**, **경위:**,
  **Channel:**) are recognized as internal scaffolding within body
  zones and pass the bold-check. The rest of the line (after the
  label) is still scanned for links, inline code, and code fences,
  so `**Read:** see [link](url)` still fires on the link.
"""
import re
from pathlib import Path

from lint import Violation

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCOPED_PREFIXES = ("cold_contacts/", "vendors/")

# Body-start: explicit canonical marker.
BODY_HEADER_RE = re.compile(r"^###\s+Body\s*$", re.IGNORECASE)

# Body-start fallback: outbound section headers whose content is body.
OUTBOUND_SECTION_RE = re.compile(
    r"^##\s+(?:"
    r"Sent\b|"
    r"Outbound\s+draft\s+pending\s+review\b|"
    r"Reply\s+(?:received|sent)\b|"
    r"Follow[-\s]?up\s+sent\b|"
    r"Email\s+(?:sent|scheduled|draft)\b|"
    r"Confirmation\s+DM\s+sent\b|"
    r"SMS\s+sent\b|"
    r"LinkedIn\s+(?:DM|message)\b|"
    r"In[-\s]?person\s+meeting\s+completed\b"
    r")",
    re.IGNORECASE,
)

# Body-end: explicit "post-body" sub-section markers.
POST_BODY_HEADERS = (
    "### Acceptance check",
    "### Reviewer attention flags",
    "### 사전 준비",
    "### 발송 후 체크리스트",
    "### Send pre-flight checklist",
    "### Open actions",
    "### Notes",
    "### Why this exists",
)

META_FIELD_RE = re.compile(r"^\*\*[^*]+:\*\*")  # **Field:** value

# Annotation labels at line start: "**Label:**" optionally followed by
# whitespace + content. Used as internal scaffolding (e.g., **Read:**,
# **Status:**, **경위:**) inside body zones. Lines
# matching this pattern skip the bold-check; their tail (after the
# label) is still scanned for other Markdown patterns.
LABEL_RE = re.compile(r"^\s*\*\*[^*\n]+:\*\*(\s.*)?$")

# Markdown patterns that BLOCK inside the body zone.
BOLD_STAR_RE = re.compile(r"\*\*[^*\n]+\*\*")
BOLD_USCORE_RE = re.compile(r"__[^_\n]+__")
LINK_RE = re.compile(r"\[[^\]\n]+\]\([^)\n]+\)")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
CODE_FENCE_RE = re.compile(r"^\s*```")

BOLD_LABELS = {"bold (**x**)", "bold (__x__)"}

PATTERNS = [
    ("bold (**x**)", BOLD_STAR_RE),
    ("bold (__x__)", BOLD_USCORE_RE),
    ("link [text](url)", LINK_RE),
    ("inline code `x`", INLINE_CODE_RE),
]


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


def _starts_post_body(stripped: str) -> bool:
    return any(stripped.startswith(h) for h in POST_BODY_HEADERS)


def _scan_text(text: str, source: str) -> list[Violation]:
    if "<!-- lint-disable no-markdown-in-body -->" in text:
        return []

    violations: list[Violation] = []
    lines = text.split("\n")
    in_frontmatter = False
    in_body = False
    in_code_fence = False
    # When we hit an outbound section header (without ### Body), skip the
    # immediately-following meta block (consecutive **Field:** + blanks).
    pending_meta_skip = False

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Frontmatter handling.
        if i == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and stripped == "---":
            in_frontmatter = False
            continue
        if in_frontmatter:
            continue

        # State transitions: figure out if THIS line starts/ends body.
        # Order matters: post-body markers and ### Body must be checked
        # BEFORE generic ### / ## end-of-body fallback.
        if BODY_HEADER_RE.match(stripped):
            in_body = True
            pending_meta_skip = False
            continue

        if _starts_post_body(stripped):
            in_body = False
            pending_meta_skip = False
            continue

        if OUTBOUND_SECTION_RE.match(stripped):
            in_body = True
            pending_meta_skip = True
            continue

        # Any other ## or ### heading (that wasn't an outbound section,
        # ### Body, or a post-body marker) ends the body zone.
        if stripped.startswith("## ") or stripped.startswith("### "):
            in_body = False
            pending_meta_skip = False
            continue

        if not in_body:
            continue

        # Inside body: handle the meta-block skip after a fallback header.
        if pending_meta_skip:
            if not stripped or META_FIELD_RE.match(stripped):
                continue
            pending_meta_skip = False
            # fall through and scan THIS line as body

        # Code fence toggle. The fence line itself is a violation
        # (renders as ``` literally), and contents inside the fence are
        # skipped to avoid double-firing on inner Markdown.
        if CODE_FENCE_RE.match(line):
            context = stripped[:80]
            violations.append(Violation(
                rule="no-markdown-in-body",
                file_path=source,
                line=i,
                message=(
                    f"{source}:{i} code fence '```' inside body zone "
                    f"renders literally. Context: \"{context}\". Fix: "
                    f"remove the fence and use plain prose, or move "
                    f"the snippet outside the body zone. Override "
                    f"per-file with <!-- lint-disable "
                    f"no-markdown-in-body -->."
                ),
            ))
            in_code_fence = not in_code_fence
            continue

        if in_code_fence:
            continue

        # Skip Markdown horizontal rules / `* * *` patterns to avoid
        # FP on triple-star/triple-underscore separators.
        if re.fullmatch(r"\*[\s*]+\*", stripped) or re.fullmatch(r"_[\s_]+_", stripped):
            continue

        # Annotation-label whitelist: lines like '**Read:** value' are
        # author scaffolding inside body zones. Skip the bold-check on
        # these lines, but still scan for links, inline code, code
        # fences (which are real bugs even on label lines).
        is_label_line = bool(LABEL_RE.match(line))

        for label, pat in PATTERNS:
            if is_label_line and label in BOLD_LABELS:
                continue
            for m in pat.finditer(line):
                token = m.group(0)
                context = stripped[:80]
                violations.append(Violation(
                    rule="no-markdown-in-body",
                    file_path=source,
                    line=i,
                    message=(
                        f"{source}:{i} Markdown {label} '{token}' "
                        f"inside body zone renders literally in "
                        f"sent email/DM/SMS. Context: \"{context}\". "
                        f"Fix: use plain text inside the body. "
                        f"Override per-file with <!-- lint-disable "
                        f"no-markdown-in-body -->."
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

    return violations

"""Rule: configured project domains in body must include `https://` prefix.

LinkedIn and many email clients do not auto-link bare domains. With
``https://`` prefix the same domain renders as a clickable link.
Configure your project's domains in ``scripts/lint/_config.py``.

Severity: WARN (cosmetic — readable but not auto-linked).

Scope:
- cold_contacts/*.md (body, not frontmatter)
- drafts/*.md (body, not frontmatter)
- Gmail MCP create_draft body, subject, htmlBody

Allowed exceptions:
- The match is preceded by `://` within ~8 chars (i.e., already inside
  a full URL).
- File contains the marker `<!-- lint-disable link-prefix-https -->`
- YAML frontmatter (e.g., `linkedin:` field can contain bare domain refs).
"""
import re
from pathlib import Path

from lint import Violation
from lint._config import KNOWN_DOMAINS

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCOPED_PREFIXES = ("cold_contacts/", "drafts/")

DOMAIN_RE = (
    re.compile(r"\b(" + "|".join(re.escape(d) for d in KNOWN_DOMAINS) + r")\b")
    if KNOWN_DOMAINS
    else None
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


def _has_protocol_prefix(line: str, match_start: int) -> bool:
    """True if the match is already inside a URL or an email address.

    URL: `://` appears within ~10 chars before match_start.
    Email: the character immediately before match_start is `@`.
    """
    window_start = max(0, match_start - 10)
    if "://" in line[window_start:match_start]:
        return True
    if match_start > 0 and line[match_start - 1] == "@":
        return True
    return False


def _scan_text(text: str, source: str, skip_frontmatter: bool = True) -> list[Violation]:
    if DOMAIN_RE is None:
        return []
    if "<!-- lint-disable link-prefix-https -->" in text:
        return []

    lines = text.split("\n")
    in_frontmatter = False
    violations: list[Violation] = []

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if skip_frontmatter:
            if i == 1 and stripped == "---":
                in_frontmatter = True
                continue
            if in_frontmatter and stripped == "---":
                in_frontmatter = False
                continue
            if in_frontmatter:
                continue

        for m in DOMAIN_RE.finditer(line):
            if _has_protocol_prefix(line, m.start()):
                continue
            domain = m.group(1)
            violations.append(Violation(
                rule="link-prefix-https",
                file_path=source,
                line=i,
                severity="warn",
                message=(
                    f"{source}:{i} bare '{domain}' without 'https://' prefix. "
                    f"LinkedIn and many email clients won't auto-link bare "
                    f"domains. Prefix with 'https://' so recipients get a "
                    f"clickable link."
                ),
            ))
    return violations


def check(tool_name: str, tool_input: dict) -> list[Violation]:
    if DOMAIN_RE is None:
        return []
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
        for field in ("subject", "body", "htmlBody"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan_text(text, f"Gmail.{field}", skip_frontmatter=False))

    return violations

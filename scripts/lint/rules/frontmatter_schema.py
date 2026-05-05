"""Rule: YAML frontmatter must use only canonical keys per directory.

Canonical key lists live in scripts/lint/schemas.yml — one list per
directory (cold_contacts, vendors, pitch_events). A key not in the
list signals either a typo, an improvisation that should consolidate
into an existing field, or a new field that needs to be added to
schemas.yml first.

Worked-example failure: an improvised `from_email` field broke
multi-file consistency across the contact corpus. Adding fields to
the schema explicitly makes drift auditable as a single YAML diff
rather than a hunt across many files.

Scope:
- cold_contacts/*.md
- vendors/*.md
- pitch_events/*.md

Allowed exceptions:
- File contains the marker `<!-- lint-disable frontmatter-schema -->`
  in the body (not the frontmatter).
"""
from pathlib import Path

import yaml

from lint import Violation

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = PROJECT_ROOT / "scripts" / "lint" / "schemas.yml"

SCOPE_DIRS = ("cold_contacts/", "vendors/", "pitch_events/")


def _load_schemas() -> dict[str, set[str]]:
    if not SCHEMA_PATH.exists():
        return {}
    with SCHEMA_PATH.open() as f:
        data = yaml.safe_load(f) or {}
    return {k: set(v) for k, v in data.items() if isinstance(v, list)}


def _relpath(file_path: str) -> str:
    if not file_path:
        return ""
    p = str(file_path)
    root = str(PROJECT_ROOT) + "/"
    if p.startswith(root):
        return p[len(root):]
    return p


def _scope_for(file_path: str) -> str:
    rel = _relpath(file_path)
    for prefix in SCOPE_DIRS:
        if rel.startswith(prefix):
            return prefix.rstrip("/")
    return ""


def _parse_frontmatter(text: str) -> tuple[dict, int] | None:
    """Return (frontmatter_dict, end_line_number) or None if no frontmatter."""
    if not text.startswith("---"):
        return None
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            block = "\n".join(lines[1:i])
            try:
                fm = yaml.safe_load(block)
            except yaml.YAMLError:
                return None
            if isinstance(fm, dict):
                return fm, i + 1
            return None
    return None


def _scan_text(text: str, source: str, scope: str, schemas: dict[str, set[str]]) -> list[Violation]:
    if "<!-- lint-disable frontmatter-schema -->" in text:
        return []
    canonical = schemas.get(scope)
    if not canonical:
        return []
    parsed = _parse_frontmatter(text)
    if parsed is None:
        return []
    fm, _ = parsed

    violations: list[Violation] = []
    for key in fm:
        if key not in canonical:
            violations.append(Violation(
                rule="frontmatter-schema",
                file_path=source,
                line=None,
                severity="block",
                message=(
                    f"{source}: non-canonical frontmatter key '{key}' for "
                    f"{scope}/. Either rename to an existing field, fold the "
                    f"value into 'notes', or add '{key}' to "
                    f"scripts/lint/schemas.yml under '{scope}:' if it should "
                    f"be canonical."
                ),
            ))
    return violations


def check(tool_name: str, tool_input: dict) -> list[Violation]:
    file_path = tool_input.get("file_path", "") or ""
    if not file_path:
        return []
    scope = _scope_for(file_path)
    if not scope:
        return []

    schemas = _load_schemas()
    violations: list[Violation] = []

    rel = _relpath(file_path)
    for field in ("content", "new_string"):
        text = tool_input.get(field, "") or ""
        if text:
            violations.extend(_scan_text(text, rel, scope, schemas))
    for edit in tool_input.get("edits", []) or []:
        ns = edit.get("new_string", "") or ""
        if ns:
            violations.extend(_scan_text(ns, rel, scope, schemas))

    return violations

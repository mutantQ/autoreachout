"""Rule: drafts/{slug}.md may only exist for entities NOT already in cold_contacts/.

Also blocks subfolders under drafts/ (flat only).

The convention: one per-entity file at cold_contacts/{slug}.md is the
source of truth for both metadata and message log. drafts/ is only
for entities that have not yet entered the cold-contact corpus.
"""
from pathlib import Path

from lint import Violation

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DRAFTS_DIR = (PROJECT_ROOT / "drafts").resolve()
COLD_CONTACTS_DIR = (PROJECT_ROOT / "cold_contacts").resolve()


def check(tool_name: str, tool_input: dict) -> list[Violation]:
    file_path_raw = tool_input.get("file_path", "") or ""
    if not file_path_raw:
        return []

    try:
        file_path = Path(file_path_raw).resolve()
    except (OSError, RuntimeError):
        return []

    try:
        rel = file_path.relative_to(DRAFTS_DIR)
    except ValueError:
        return []

    if len(rel.parts) > 1:
        return [Violation(
            rule="drafts-no-subfolder",
            file_path=str(file_path),
            message=(
                f"Flat directory only under outreach/drafts/. Found nested path: {rel}. "
                f"Do not create subfolders; each counterparty gets a single file at outreach/drafts/{{slug}}.md."
            ),
        )]

    slug = rel.stem  # filename without .md
    cold_contact_path = COLD_CONTACTS_DIR / f"{slug}.md"

    if cold_contact_path.exists():
        return [Violation(
            rule="one-file-per-entity",
            file_path=str(file_path),
            message=(
                f"cold_contacts/{slug}.md already exists. All drafts, call notes, follow-ups, and planned messages for this contact must go INSIDE that file (as new ## sections). "
                f"Do NOT create a parallel drafts/{slug}.md — it fragments the record. "
                f"If this Write is intentional (e.g., migrating content OUT of cold_contacts), add a rationale comment and use Bash to force-write instead."
            ),
        )]

    return []

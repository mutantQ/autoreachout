#!/usr/bin/env python3
"""Generate cold_contacts.yml index from .md frontmatter.

Usage: uv run python scripts/build_index.py
"""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
CONTACTS_DIR = ROOT / "cold_contacts"
OUTPUT_FILE = ROOT / "cold_contacts.yml"

# Fields to strip from the index (channel-/contact-specific noise)
EXCLUDED_FIELDS = {
    "method",
    "cc",
    "to",
    "phone",
    "kakaotalk",
    "instagram",
    "office",
    "kakaotalk_chat_id",
    "see_also",
}

REQUIRED_FIELDS = {"slug", "name", "status", "contact_type"}
STATUS_NEEDS_MEETING_AT = {"meeting_scheduled"}
STATUS_NEEDS_REPLIED_AT = {"replied", "met", "mou_signed"}


def parse_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter between --- markers. Returns None if not found."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return None
    fm_text = "\n".join(lines[1:end])
    try:
        data = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def strip_excluded(data: dict) -> dict:
    return {k: v for k, v in data.items() if k not in EXCLUDED_FIELDS}


def sort_key(contact: dict):
    """Sort by sent_at descending; nulls/empty go last."""
    val = contact.get("sent_at")
    if not val:
        return (1, "")
    return (0, "-" + str(val))  # negate string for descending order via lexicographic trick


def lint(contacts: list[dict], paths_by_slug: dict[str, list[Path]]) -> None:
    warnings = []

    seen_slugs: dict[str, str] = {}

    for contact in contacts:
        slug = contact.get("slug", "")
        name = contact.get("name", slug or "???")
        ref = f"{slug or '???'} ({name})"

        # Duplicate slug check
        if slug:
            if slug in seen_slugs:
                warnings.append(f"DUPLICATE slug '{slug}': also in {seen_slugs[slug]}")
            else:
                seen_slugs[slug] = name

        # Required fields
        for field in REQUIRED_FIELDS:
            if not contact.get(field):
                warnings.append(f"MISSING required field '{field}': {ref}")

        # meeting_scheduled without meeting_at
        status = contact.get("status")
        if status in STATUS_NEEDS_MEETING_AT and not contact.get("meeting_at"):
            warnings.append(f"status=meeting_scheduled but no meeting_at: {ref}")

        # replied/met/mou_signed without last_replied_at
        if status in STATUS_NEEDS_REPLIED_AT and not contact.get("last_replied_at"):
            # Accept replied_at as alias (some contacts use it)
            if not contact.get("replied_at"):
                warnings.append(f"status={status} but no last_replied_at: {ref}")

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)


def main() -> None:
    md_files = sorted(CONTACTS_DIR.glob("*.md"))

    contacts: list[dict] = []
    bad_files: list[Path] = []
    paths_by_slug: dict[str, list[Path]] = {}

    for path in md_files:
        # Skip supplementary channel files
        if path.stem.endswith("-email"):
            continue

        data = parse_frontmatter(path)
        if data is None:
            bad_files.append(path)
            print(f"WARN: no valid frontmatter: {path.name}", file=sys.stderr)
            continue

        slug = data.get("slug", "")
        paths_by_slug.setdefault(slug, []).append(path)
        contacts.append(strip_excluded(data))

    # Sort by sent_at descending, nulls last
    contacts.sort(key=sort_key)

    # Lint warnings
    lint(contacts, paths_by_slug)

    # Write output
    header = "# GENERATED — do not edit. Run: uv run python scripts/build_index.py\n"
    body = yaml.dump(
        contacts,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    OUTPUT_FILE.write_text(header + body, encoding="utf-8")

    print(f"Wrote {len(contacts)} contacts to {OUTPUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

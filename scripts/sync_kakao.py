#!/usr/bin/env python3
"""Sync KakaoTalk messages for outreach contacts via kakaocli.

Reads cold_contacts.yml for contacts with kakaotalk channel, checks their
.md frontmatter for kakaotalk_chat_id, fetches recent messages via kakaocli,
and flags contacts with unlogged recent activity.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
CONTACTS_YML = PROJECT_ROOT / "cold_contacts.yml"
CONTACTS_DIR = PROJECT_ROOT / "cold_contacts"
VENDORS_DIR = PROJECT_ROOT / "vendors"

# Personal / non-outreach chat IDs to skip during sync (e.g. family groups,
# unrelated DMs that happened to land in cold_contacts.yml during a refactor).
# Populate with the integer chat_id values from your kakaocli inventory; the
# default is empty so a fresh checkout never accidentally talks to a personal
# chat. See SETUP.md for how to discover chat IDs.
EXCLUDED_CHAT_IDS: set[int] = set()


def parse_frontmatter(md_path: Path) -> dict:
    """Parse YAML frontmatter from a markdown file."""
    text = md_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def parse_date_field(val) -> datetime | None:
    """Parse a date or datetime string/object into a timezone-aware datetime."""
    if val is None:
        return None
    s = str(val).strip()
    # Try ISO 8601 with timezone info first
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    # Try plain date (YYYY-MM-DD)
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    return None


def resolve_kakao_db_and_key() -> tuple[str, str]:
    """Resolve the kakaocli database path and encryption key.

    The kakaocli shell wrapper normally injects these, but subprocess
    calls bypass the shell function. We replicate the logic here.
    """
    import os

    home = os.path.expanduser("~")
    db_dir = os.path.join(
        home, "Library", "Containers", "com.kakao.KakaoTalkMac",
        "Data", "Library", "Application Support", "com.kakao.KakaoTalkMac",
    )
    # Find the database file (long hash-named file, not directory)
    db_path = ""
    if os.path.isdir(db_dir):
        for entry in os.listdir(db_dir):
            candidate = os.path.join(db_dir, entry)
            if os.path.isfile(candidate) and len(entry) > 20 and not entry.endswith(("-shm", "-wal")):
                db_path = candidate
                break

    # Get key from macOS keychain
    key = ""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""), "-s", "kakaocli-key", "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            key = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return db_path, key


# Resolve once at module level
_KAKAO_DB, _KAKAO_KEY = resolve_kakao_db_and_key()


def fetch_kakao_messages(chat_id: int, since: str) -> list[dict] | None:
    """Run kakaocli and return parsed messages, or None on failure.

    Returns:
        list[dict]: parsed message objects (may be empty)
        None: kakaocli not available, chat not found, or parse error
    Raises:
        RuntimeError: if kakaocli binary is not found (caller should stop)
    """
    cmd = ["kakaocli", "messages", "--chat-id", str(chat_id), "--since", since, "--json"]
    if _KAKAO_DB:
        cmd.extend(["--db", _KAKAO_DB])
    if _KAKAO_KEY:
        cmd.extend(["--key", _KAKAO_KEY])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        raise RuntimeError("kakaocli not found")
    except subprocess.TimeoutExpired:
        print(f"WARNING: kakaocli timed out for chat_id={chat_id}", file=sys.stderr)
        return None

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if stderr:
            print(f"WARNING: kakaocli error for chat_id={chat_id}: {stderr}", file=sys.stderr)
        return None

    if not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
        if isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError as e:
        print(f"WARNING: failed to parse kakaocli JSON for chat_id={chat_id}: {e}", file=sys.stderr)
        return None


def get_latest_message_timestamp(messages: list[dict]) -> datetime | None:
    """Return the most recent message timestamp from a list of message objects."""
    latest: datetime | None = None
    for msg in messages:
        ts_raw = msg.get("timestamp")
        if ts_raw is None:
            continue
        dt = parse_date_field(str(ts_raw))
        if dt is None:
            continue
        if latest is None or dt > latest:
            latest = dt
    return latest


def is_hidden_event(msg: dict) -> bool:
    """Return True if a kakaocli message is a hidden system/feed event, not user content.

    KakaoTalk emits hidden events for edits, unsends, joins/leaves, and other state
    changes. kakaocli sometimes serialises the feed payload into the `text` field
    as JSON (e.g. `{"logId":...,"targetRevision":1,"hidden":true,"feedType":25}`),
    which masquerades as message content. Treating these as user-visible text has
    produced false "no new content" readouts in past sync runs.
    """
    # Top-level explicit markers from kakaocli
    if msg.get("hidden") is True:
        return True
    if msg.get("feed_type") is not None or msg.get("feedType") is not None:
        return True

    # Text-as-JSON masquerade
    text = (msg.get("text") or "").strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return False
        if not isinstance(payload, dict):
            return False
        if payload.get("hidden") is True:
            return True
        if "feedType" in payload or "feed_type" in payload:
            return True
        # logId + targetRevision is the edit-revision pattern
        if "logId" in payload and "targetRevision" in payload:
            return True

    return False


def _truncate(text: str, limit: int = 120) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def build_summary(messages: list[dict]) -> str:
    """Build a short summary string from the most recent NON-HIDDEN message.

    Falls back to "(no user-content messages, N hidden events only)" if every
    message in the window is a hidden system event.
    """
    if not messages:
        return ""

    def ts_key(m):
        dt = parse_date_field(str(m.get("timestamp", "")))
        return dt or datetime.min.replace(tzinfo=timezone.utc)

    sorted_msgs = sorted(messages, key=ts_key, reverse=True)
    for m in sorted_msgs:
        if is_hidden_event(m):
            continue
        return _truncate(m.get("text", ""), 80)

    return f"(no user-content messages, {len(messages)} hidden events only)"


def build_recent_non_hidden(messages: list[dict], limit: int = 5) -> list[dict]:
    """Return up to `limit` most-recent non-hidden messages, newest first.

    Each entry has {at, sender, text} where sender is whichever of
    `sender`, `sender_name`, `sender_id`, or `from_me` kakaocli supplies.
    Text is truncated to ~120 chars. Surfaces all real conversation in the
    delta window so summary-only false readouts cannot hide real content.
    """
    def ts_key(m):
        dt = parse_date_field(str(m.get("timestamp", "")))
        return dt or datetime.min.replace(tzinfo=timezone.utc)

    sorted_msgs = sorted(messages, key=ts_key, reverse=True)
    out: list[dict] = []
    for m in sorted_msgs:
        if is_hidden_event(m):
            continue
        sender = (
            m.get("sender")
            or m.get("sender_name")
            or (m.get("sender_id") and str(m.get("sender_id")))
            or ("me" if m.get("from_me") else None)
            or "?"
        )
        out.append({
            "at": str(m.get("timestamp", "")),
            "sender": sender,
            "text": _truncate(m.get("text", ""), 120),
        })
        if len(out) >= limit:
            break
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Sync KakaoTalk messages for outreach contacts"
    )
    parser.add_argument(
        "--since",
        default="7d",
        help="How far back to fetch messages (e.g. 7d, 14d). Default: 7d",
    )
    parser.add_argument(
        "--json",
        dest="output_json",
        action="store_true",
        default=True,
        help="Output results as JSON (default: true)",
    )
    args = parser.parse_args()

    # Build the unified list of files-with-chat-ids to track.
    # Sources: cold_contacts/ (filtered by channel=kakaotalk via YAML index)
    # + vendors/ (any vendor with kakaotalk_chat_id frontmatter, regardless of channel).
    tracked: list[dict] = []  # each entry: {slug, kind, md_path, tracked_raw}

    # Cold contacts via YAML index
    with open(CONTACTS_YML, encoding="utf-8") as f:
        all_contacts = yaml.safe_load(f)
    for c in all_contacts:
        if "kakaotalk" not in str(c.get("channel", "")).lower():
            continue
        slug = c.get("slug", "")
        if not slug:
            continue
        md_path = CONTACTS_DIR / f"{slug}.md"
        if not md_path.exists():
            continue
        tracked.append({
            "slug": slug,
            "kind": "cold_contact",
            "md_path": md_path,
            "tracked_raw": c.get("last_replied_at") or c.get("sent_at"),
        })

    # Vendors: scan vendors/*.md directly for kakaotalk_chat_id presence.
    # Vendors don't have a YAML index; channel field optional.
    if VENDORS_DIR.is_dir():
        for vendor_md in sorted(VENDORS_DIR.glob("*.md")):
            fm = parse_frontmatter(vendor_md)
            if fm.get("kakaotalk_chat_id") is None:
                continue
            slug = fm.get("slug") or vendor_md.stem
            # Vendors typically lack last_replied_at; fall back to file mtime
            # as the "last logged" anchor (logs are appended manually).
            mtime_dt = datetime.fromtimestamp(vendor_md.stat().st_mtime, tz=timezone.utc)
            tracked.append({
                "slug": slug,
                "kind": "vendor",
                "md_path": vendor_md,
                "tracked_raw": fm.get("last_replied_at") or mtime_dt.date().isoformat(),
            })

    checked_at = datetime.now(tz=timezone.utc).astimezone().isoformat()
    contacts_checked = 0
    updates_found = []

    for entry in tracked:
        slug = entry["slug"]
        md_path = entry["md_path"]
        tracked_raw = entry["tracked_raw"]

        # Parse frontmatter from .md to get chat ID
        fm = parse_frontmatter(md_path)
        chat_id_raw = fm.get("kakaotalk_chat_id")
        if chat_id_raw is None:
            continue

        try:
            chat_id = int(chat_id_raw)
        except (ValueError, TypeError):
            print(f"WARNING: invalid kakaotalk_chat_id for {slug}: {chat_id_raw!r}", file=sys.stderr)
            continue

        # Skip excluded (personal/family) chats
        if chat_id in EXCLUDED_CHAT_IDS:
            continue

        contacts_checked += 1

        # Fetch messages via kakaocli
        try:
            messages = fetch_kakao_messages(chat_id, args.since)
        except RuntimeError as e:
            print(f"WARNING: {e}, skipping all KakaoTalk checks", file=sys.stderr)
            contacts_checked -= 1
            break

        if messages is None:
            continue

        if not messages:
            continue

        # Compare latest KakaoTalk message vs tracked anchor (last_replied_at,
        # sent_at, or vendor file mtime as fallback)
        tracked_dt = parse_date_field(tracked_raw)
        latest_dt = get_latest_message_timestamp(messages)
        if latest_dt is None:
            continue

        # Flag if latest KakaoTalk message is newer than our tracked date
        if tracked_dt is None or latest_dt > tracked_dt:
            last_tracked_str = str(tracked_raw) if tracked_raw else "unknown"
            latest_date_str = latest_dt.date().isoformat()
            summary = build_summary(messages)
            hidden_count = sum(1 for m in messages if is_hidden_event(m))
            non_hidden_count = len(messages) - hidden_count
            updates_found.append(
                {
                    "slug": slug,
                    "kind": entry["kind"],
                    "last_tracked": last_tracked_str,
                    "latest_message_at": latest_date_str,
                    "message_count": len(messages),
                    "non_hidden_count": non_hidden_count,
                    "hidden_count": hidden_count,
                    "summary": summary,
                    "recent_non_hidden": build_recent_non_hidden(messages, limit=5),
                }
            )

    output = {
        "checked_at": checked_at,
        "contacts_checked": contacts_checked,
        "updates_found": updates_found,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

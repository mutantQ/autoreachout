# Setup

This guide walks you from a fresh clone to a working dev environment with
a populated contact database, optional KakaoTalk sync, and the lint hook
wired into Claude Code.

If you only want to read the code or run the test suite against the
example fixtures, follow [Installation](README.md#installation)
(remember `uv sync --extra dev` to pull in pytest) and stop there.
The rest of this document is about wiring up real-world data.

---

## 1. Configure project identifiers

Project-specific identifiers (founder name, project domains, forbidden
email, in-house abbreviations) live in `scripts/lint/_config.py`. The
file ships with placeholder values that obviously need editing before
live use.

```bash
$EDITOR scripts/lint/_config.py
```

Re-run the lint test suite after changes:

```bash
uv run pytest scripts/lint/tests/ -q
```

---

## 2. Migrate your real contact data in

The example data ships 60 fictional contacts in `cold_contacts/`. To
move your own data in:

1. **Decide on the gitignore boundary.** The simplest path: put real
   data in a sibling directory (`../my-outreach/cold_contacts/`) and
   keep this repo as the harness only. The next-simplest: add a top-
   level `private/` directory and gitignore it.
2. **Create one `.md` per contact.** Use one of the example files as a
   template. Frontmatter fields must come from `scripts/lint/schemas.yml`
   (the `frontmatter-schema` lint rule blocks unknown fields).
3. **Generate the index.** `uv run python scripts/build_index.py`.
   The YAML index is regenerated; do not hand-edit it.

### What the index contains and excludes

`scripts/build_index.py` strips a small set of channel-specific noise
from the index (e.g., `kakaotalk_chat_id`, `phone`, `see_also`) so that
the index file you commit does not leak personal contact data even if
the per-contact `.md` files are kept private.

---

## 3. KakaoTalk sync (optional, macOS only)

The KakaoTalk sync reads the local KakaoTalk DB on macOS via
`kakaocli` (a CLI wrapper around the encrypted local KakaoTalk DB)
and flags contacts whose KakaoTalk activity is newer than the logged
anchor. It is opt-in per-contact: a contact is only synced if its
`.md` frontmatter has a `kakaotalk_chat_id:` integer.

### Install kakaocli

Follow the upstream install instructions for the `kakaocli` binary
you choose to use. The harness invokes it as a subprocess and reads
JSON from stdout. The expected shape is documented in
`scripts/sync_kakao.py` (`fetch_kakao_messages`).

### Discover chat IDs

Run kakaocli's chat-list command once to get the integer ID for each
chat thread you want to track:

```bash
kakaocli chats --json | jq '.[] | {chat_id, name}'
```

### Wire the IDs into your contact files

Add the integer to the relevant contact's frontmatter:

```yaml
kakaotalk_chat_id: 1234567890123
```

### Exclude personal chats

`scripts/sync_kakao.py` exposes an `EXCLUDED_CHAT_IDS` set near the top
of the file. Populate it with chat IDs that should be hard-skipped
(family groups, unrelated DMs that landed in the contact list during a
migration, etc.). The default is empty, so a fresh checkout never
accidentally talks to a personal chat.

### Run the sync

```bash
uv run python scripts/sync_kakao.py --since 7d
```

The output is JSON: contacts whose latest KakaoTalk message is newer
than their tracked anchor (`last_replied_at` or `sent_at` from
frontmatter), with truncated previews of the most-recent non-hidden
messages.

---

## 4. Wire the lint hook into Claude Code

The lint runner is designed to be invoked from a Claude Code PreToolUse
hook. The hook payload is read from stdin as JSON; the runner exits
non-zero (with a stderr message) if any rule flags a BLOCK violation.

### Hook configuration

Add to your project's `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|mcp__claude_ai_Gmail__create_draft",
        "hooks": [
          {
            "type": "command",
            "command": "uv run python scripts/lint/run_lint.py"
          }
        ]
      }
    ]
  }
}
```

### Manual sweep mode

To run the full lint pass over every committed markdown file (use
before report regens to catch drift from terminal/external edits that
bypassed the hook):

```bash
uv run python scripts/lint/run_lint.py --all
```

The sweep prints a per-file violation count to stderr and exits non-
zero if any BLOCK violations are found.

---

## 5. Optional: Gmail / Calendar MCPs

The harness reads send/reply state from the per-contact `.md` files,
not from Gmail or Calendar directly. If you want Claude Code to draft
into Gmail or schedule into Calendar, install the Anthropic Gmail and
Google Calendar MCPs and grant access at the workspace level. The lint
runner already scopes the appropriate rules to
`mcp__claude_ai_Gmail__create_draft` payloads.

---

## 6. Periodic regen

The status report at `reports/OUTREACH_REPORT.md` is manually authored,
not auto-generated. The intended cadence is weekly to bi-weekly:

1. Run `uv run python scripts/lint/run_lint.py --all` and resolve every
   block.
2. Run `uv run python scripts/build_index.py` and commit the diff.
3. Run `uv run python scripts/analyze.py` and capture the metrics.
4. Edit `reports/OUTREACH_REPORT.md` against the new metrics. Diff
   against the previous version to surface what changed.

The `.claude/skills/contact-manager/regen.md` skill captures this
workflow in detail; invoke it from Claude Code via `/contact-manager
regen`.

# Update Contact Status

### `update`, Change contact status

Valid transitions:
- `draft` → `sent` (set `sent_at`, update `.md` body with actual text sent)
- `sent` → `accepted` | `replied` | `meeting_scheduled` | `declined` | `no_response`
- `accepted` → `replied` | `meeting_scheduled` | `declined` | `no_response`
- `replied` → `meeting_scheduled` | `declined`

Edit the `.md` frontmatter, then run `uv run python scripts/build_index.py`.

Can also update: `notes`, `tags`, `subject`.

**When updating to `sent`:** also update the `.md` body to record actual text sent.

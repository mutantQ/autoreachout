# Sync: Gmail / KakaoTalk / GCal

## Context Loading

**Before any other operation, get the current date.** Run `date '+%Y-%m-%d %H:%M %Z'` via Bash. If it disagrees with the cached date in context, trust the shell.

**Then run these checks in parallel before any contact operation:**

1. **Gmail batch sync**, single `gmail_search_messages("newer_than:1d -from:me -label:sent")` call. Filter results locally against known contact emails/domains from the YAML index. If a reply exists but the contact status hasn't been updated:
   - Update the contact's `.md` frontmatter: `status` → `replied`, `last_replied_at` → reply date
   - Append reply summary to the `.md` body (`## Reply ({date})`)

2. **KakaoTalk sync**, run `uv run python scripts/sync_kakao.py`. Review JSON output. For each flagged contact with unlogged activity, update the `.md` file.

3. **Google Calendar check** (low frequency, roughly once per 15 invocations, or when the user asks about meetings/scheduling), use `gcal_list_events` for the next 7 days. Cross-reference against contacts with `status: meeting_scheduled`. Flag imminent meetings (within 24h) and update past ones to `met`.

4. **If any updates from steps 1-3:** run `uv run python scripts/build_index.py` to regenerate the YAML index.

5. **Read `reports/OUTREACH_REPORT.md`** to load pipeline context, engagement rates, active conversations, action items, and warnings.

Gmail is ground truth for email replies. kakaocli is ground truth for KakaoTalk. GCal is ground truth for meetings.

## Read the body, not the summary

`sync_kakao.py` returns one preview string per flagged contact (`summary` field). **Never report status from the JSON alone.** For every contact in `updates_found`:

1. Open `cold_contacts/{slug}.md` (or `vendors/{slug}.md`) and read the full body, not just frontmatter.
2. Compare the latest `## Sent (...)`, `## Reply received (...)`, or `### Founder → ...` / `### {name} → Founder ...` sections against `last_replied_at` / `followed_up_at` in frontmatter. The body is the source of truth; frontmatter dates can lag.
3. Only after the body read may you state any claim of the form "pending send", "not yet sent", "awaiting Founder reply", or "draft only". If a `## Sent` (or `### Founder → ...`) section newer than your anchor date exists, the claim is false, re-state from the body.

Hidden/system events (`feedType:25`, `hidden:true`, edit-revision blobs like `{"logId":...,"targetRevision":1}`) can leak into the JSON `summary` even when real outbound + inbound exist underneath. The `is_hidden_event` filter blocks them and `recent_non_hidden` surfaces the last 5 user-content messages. The body-readback rule above is the durable guard: trust the file, not the JSON.

## Date Drift Mid-Conversation

Long sessions can cross midnight. Re-check `date` whenever:
- The user says "next day", "I just woke up", "today" after a long pause
- You're about to write a `sent_at` timestamp
- You're about to convert a relative date ("Thursday", "next week") into an absolute one

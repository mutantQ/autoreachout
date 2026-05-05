---
name: contact-manager
description: Manage all outreach contacts for your project, cold, warm, inbound, referral. Track messages, check duplicates, enforce rate limits, and coordinate with the outreach-email skill (and any browser-automation tooling you bring).
user_invocable: true
---

# Contact Manager

Manage the outreach contact database. `.md frontmatter` is the single source of truth.

## Data Layout

```
cold_contacts/*.md             ← SOURCE OF TRUTH (all metadata in frontmatter)
cold_contacts.yml              ← GENERATED index (run: uv run python scripts/build_index.py)
reports/OUTREACH_REPORT.md     ← GENERATED dashboard (agent-written from analyze.py --json)
reports/charts/*.png           ← GENERATED charts (scripts/charts.py)
scripts/build_index.py         ← Generates YAML from .md frontmatter
scripts/analyze.py             ← Metrics (text default, --json for structured output)
scripts/charts.py              ← Generates PNG charts from metrics (matplotlib)
scripts/sync_kakao.py          ← KakaoTalk message sync
```

**Never hand-edit `cold_contacts.yml`.** All writes go to `.md frontmatter`, then `build_index.py` regenerates the YAML.

## Sub-file Reference

<!-- Keep this table in sync with sub-files in this directory. -->

| Task | File | When to read |
|------|------|-------------|
| Gmail/Kakao/GCal sync | sync.md | Session start (auto-invoked via CLAUDE.md) |
| Add a new contact | add.md | Creating a contact, running dedup/rate-limit checks |
| Send via LinkedIn | send-linkedin.md | Delivering connection notes or DMs via browser |
| Send via Remember (리멤버) | send-remember.md | Sending Remember (리멤버) DMs, credit checks |
| Update contact status | update-status.md | Changing status, logging sent body |
| Regenerate report | regen.md | Force rebuild of OUTREACH_REPORT.md |

## Contact Types

| `contact_type` | Description | Example |
|----------------|-------------|---------|
| `cold` | No prior relationship. First touch is outbound. | Most LinkedIn outreach |
| `warm` | Prior interaction exists (Discord, conference, mutual acquaintance). | [community contact] (standards Discord since prior year) |
| `referral` | Introduced by a named third party. | [crypto-academic] (via [law-academic]) |
| `inbound` | They reached out to us first. | Someone responding to the website or blog |

Default is `cold`.

## Contact Schema (frontmatter)

All metadata lives in the `.md` frontmatter. Canonical field order (omit empty fields, `notes` always last):

```yaml
---
slug: example-contact
name: Example Contact
company: Example Co
role: Example Role
linkedin: https://www.linkedin.com/in/example/
email: contact@example.com
channel: linkedin
method: connection-note
display_name: Founder
subject: "short hook from your recent article"
status: sent
contact_type: cold
related_to: acme
referred_by: ""
vertical: media
tags: [example, illustrative]
sent_at: "YYYY-MM-DD"
accepted_at: ""
last_replied_at: ""
followed_up_at: ""
meeting_at: ""
met_at: ""
kakaotalk_chat_id: ""
see_also: ""
notes: "Brief, factual context (where you met or what you read). Avoid internal scoring or specific calendar windows in this field."
---
```

Valid statuses: `draft | sent | accepted | replied | meeting_scheduled | declined | no_response | mou_signed | met | connected | skipped`

Valid verticals: `forensic | proctoring | security | insurance | media | legal | standards | investor | academic | hiring | other`

### Notes field conventions
- Always prefix with delivery method: `"Sent via connection note."` or `"NOT SENT - needs email to connect."`
- For new contacts: keep concise (1-2 sentences). The `.md` body has the full detail.
- Use YAML block scalar (`|`) for multiline notes.
- **LinkedIn UI artifacts:** see `send-linkedin.md` "LinkedIn Logging Gotchas" section.

## Message File Format

The `.md` file is the **source of truth** for both metadata (frontmatter) and message content (body).

### Connection Note (primary method)

```markdown
---
slug: jane-doe
name: Jane Doe
company: Example Org
role: Founder
linkedin: https://www.linkedin.com/in/example-jane-doe/
channel: linkedin
method: connection-note
display_name: Founder
status: sent
contact_type: cold
related_to: acme
vertical: media
tags: [example, illustrative]
sent_at: "2026-02-19"
notes: "Illustrative frontmatter. Replace with your real contact's data."
---

## Sent (connection note)

[exact text of the ≤300 char note that was actually sent]
```

### Key rules
- **MUST log what was actually sent.** Never leave the draft version in the file after sending.
- `method` required: `connection-note`, `direct-message`, `email`, `phone`, etc.
- `linkedin` required for LinkedIn contacts.
- Follow-ups appended to the same `.md` file. One file per contact.
- After creating the file, open it automatically so the user can review.
- **For email drafts:** Use `pbcopy` to copy body to clipboard. Remind: "Send from your project's canonical address, not from an institutional email."

### Draft File Location Rules (Anti-Patterns)

| Don't | Do | Why |
|-------|----|-----|
| Save outbound drafts under `.omc/team-*/drafts/` or any `.omc/` subdir | Append to `cold_contacts/{slug}.md` (existing contact) or `vendors/{slug}.md` (vendor) as new `## Outbound draft pending review (date)` section | Fragments the per-entity record. Lint rule `drafts-in-omc` blocks these writes. |
| Create `outreach/drafts/{slug}.md` when `cold_contacts/{slug}.md` already exists | Append to the existing canonical file | Lint rule `one-file-per-entity` blocks these collisions. |
| Mix multiple recipients' drafts into one strategy/template file under `.omc/` | Split per recipient into each canonical per-entity file | Each entity's file should hold all drafts/threads/notes for that one entity. |
| Use `####` (level-4) or deeper Markdown headings inside outbound drafts in `cold_contacts/` or `vendors/` | Use bold inline (`**1. point name**`) or simple numbered prose for body sub-sections | Email body text doesn't render markdown headings; level-4 hashes appear literally in sent messages. Lint rule `body-headings` blocks. |
| Use Markdown formatting (`**bold**`, `__bold__`, `[text](url)`, inline `` `code` ``, code fences) inside the email/DM/SMS body of outbound drafts in `cold_contacts/` or `vendors/` | Plain text only inside body zones. Meta scaffolding outside body zones (e.g., `**Channel:**`, `**To:**`, `**Subject:**`, items under `### Acceptance check` / `### Reviewer attention flags` / `### Why this exists`) stays markdown-OK | Email/DM/SMS bodies render Markdown literally, recipients see asterisks, brackets, backticks. Single-asterisk emphasis (`*x*`) is NOT blocked (false-positive risk). Lint rule `no-markdown-in-body` blocks; override per-file with `<!-- lint-disable no-markdown-in-body -->`. |

**Lint enforcement:** `scripts/lint/rules/drafts_in_omc.py` blocks writes to `.omc/**/*.md` whose body contains outbound-message markers (canonical `## Outbound draft pending review` header, OR the `**To:**` + `**Subject:**`/`**Channel:**` metadata block). Strategy / research / spec docs in `.omc/` lack these markers and pass through automatically. Override per-file with `<!-- lint-disable drafts-in-omc -->` if a `.omc/` file legitimately contains message-format snippets as reference (not as a draft to send).

## Operations

### `list`, Show all contacts
Read the generated YAML. Supports filters: `status:sent`, `tag:deepfake-interviews`, `channel:linkedin`. Default: all contacts sorted by `sent_at` descending.

### `check`, Dedup + Ecosystem Collision check
Read the generated YAML. Returns:
- CLEAR: no matches found
- BLOCK: exact LinkedIn URL match
- WARN: fuzzy name match
- INFORM: same company, different person

Ecosystem collision check:
- 3+ contacts in same ecosystem within 7 days → WARNING
- Same company within 14 days → WARNING with existing contact's name and date

### `stats`, Summary statistics
Run `uv run python scripts/analyze.py --json` for structured metrics.

### `follow-ups`, Contacts due for follow-up
Show contacts where:
- `status: accepted` → draft follow-up using `outreach-email`
- `status: sent` and `sent_at` > 7 days ago → check if accepted or no_response
- `status: replied` with no further action

For `add`, `update`, and `regen` operations, see the sub-files in the Sub-file Reference table above.

## Three-Skill Workflow

```
1. RESEARCH    → agent + web search + playwright-cli
2. CHECK       → contact-manager check (dedup + rate limits)
3. COMPOSE     → outreach-email (draft connection note only)
4. RECORD      → contact-manager add (creates .md, status: draft)
5. SEND        → playwright-cli (REQUIRES human approval)
6. LOG         → contact-manager update (status: sent, record actual text in .md)
7. FOLLOW-UP   → when status changes, draft follow-up with real context
```

### Integration with outreach-email

1. contact-manager runs `check` first (dedup + rate limits)
2. outreach-email drafts the message
3. contact-manager records with `add` (status: draft, creates .md)
4. After human-approved send, contact-manager updates to `sent`

### Integration with playwright-cli

- RESEARCH: find targets on LinkedIn
- SEND: deliver connection notes (with human approval)
- FOLLOW-UP: check if connections accepted, send follow-up messages

## Git Commit Hygiene

**After every write operation:** run `uv run python scripts/build_index.py` before staging.

**How to commit:**
- Stage: `git add cold_contacts/{slug}.md cold_contacts.yml` (YAML is generated but committed)
- Never `git add -A` or `git add .`
- Message prefix: `outreach:`. Examples:
  - `outreach: add example-contact (warm, university faculty referral)`
  - `outreach: example-contact -> met (call recap)`

**Don't commit:** secrets, `.playwright-cli/`, scratch PDFs, `.DS_Store`

**Verify:** `git status` after committing.

## Status Transitions

```
draft ──> sent ──> accepted ──> replied ──> meeting_scheduled ──> mou_signed
                   │             │            │
                   │             ├──> met ──> mou_signed
                   │             │
                   │             ├──> declined
                   │             │
                   │             └──> no_response
                   │
                   ├──> replied (direct message, no acceptance step)
                   ├──> declined
                   └──> no_response
```

- `accepted`: Connection request accepted, follow-up not yet sent
- `connected`: Mutual connection established (e.g., LinkedIn)
- `met`: In-person or video meeting completed
- `mou_signed`: Formal agreement signed

## Slug Generation

1. Lowercase
2. Replace spaces with hyphens
3. Remove special characters (parentheses, periods, commas)
4. Remove honorifics (Dr., Mr., Ms.)
5. Example: "Pat Singh (Patricia Singh)" → "pat-singh-patricia-singh" (hypothetical)

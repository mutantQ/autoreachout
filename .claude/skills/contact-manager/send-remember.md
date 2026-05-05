# Send via Remember (리멤버 커넥트)

> **External tools required, not bundled with this repo.**
> This skill assumes you have `playwright-cli` (browser automation) and a `remember-cli` (Remember session helper) installed locally. autoreachout does not ship these. The workflow below is illustrative; bring your own automation, or run the steps manually in the browser.

## Purpose

리멤버 커넥트 is a Korean B2B contact / DM platform commonly used for cold outreach to Korean professionals. Use this sub-file when sending a connection-request DM via Remember (`rememberapp.co.kr`) after a contact has been added to `cold_contacts/` and the message has been approved by the user.

## Channel Rules

- **300-character limit.** DM textarea enforces this. Count before sending.
- **Plain Korean text only.** No markdown, no em-dashes, no URL links in body, they render literally.
- **1 credit per send.** Credits are consumed on send confirmation (not on modal open). Check credit balance before batch sends.
  - Pricing tiers are subject to change; check the platform's current pricing page before sending a batch.
- **Sender field:** Messages appear from your Remember account. No `display_name` override.
- **Rate limit:** Remember tracks aggressive cold outreach. Stay below ~20 sends/day cold. Apply the same rate-limit gates as LinkedIn (see `add.md` Safety Checks).

If you have a `remember-cli` skill of your own at `.claude/skills/remember-cli/SKILL.md`, it should handle session management, company ID resolution, and candidate selection heuristics.

## Send Workflow

1. Confirm the contact's `.md` body contains the approved DM text (status: `draft`, human-approved).
2. Open the browser session:
   ```bash
   playwright-cli -s=remember open --persistent --headed
   playwright-cli -s=remember goto https://connect.rememberapp.co.kr/
   playwright-cli -s=remember snapshot   # confirm /feed redirect = logged in
   ```
3. Navigate to the candidate's profile (`/profile/<id>`).
4. Locate the "메시지 보내기" or "커넥트 신청" button; click to open the compose modal.
5. Type the body from the `.md` file. Do NOT free-type, paste exactly what the user approved.
6. Verify character count is below 300.
7. **STOP. Show the user the exact text and confirm before clicking 보내기.** No exceptions (same rule as LinkedIn).
8. Click 보내기. Credit is consumed on send confirmation.
9. Update `.md` frontmatter: `status` → `sent`, `sent_at` → today, `channel: remember`. Run `uv run python scripts/build_index.py`.

## Logging Format

After send, append to the `.md` body:

```markdown
## Sent (Remember 리멤버, {date})

[exact text sent, verbatim, no summarizing]
```

Update frontmatter `notes` to confirm delivery: `"Sent via 리멤버 커넥트 connection DM."` If credit balance drops to 0 after send, note it: `"Credit balance 0 after send, recharge before next batch."`

## CRITICAL RULE

**Agent MUST ask for explicit human approval before sending any message via remember-cli / playwright-cli.** The user must see the exact text and confirm. No exceptions.

# Send via LinkedIn

> **External tool required, not bundled with this repo.**
> This skill assumes you have `playwright-cli` (browser automation) installed locally. autoreachout does not ship it. The workflow below is illustrative; bring your own browser automation, or run the steps manually.

## LinkedIn Logging Gotchas

LinkedIn's DM UI shows a quick-reaction picker (a row of preset emojis, by default the trio clap / thumbs-up / smiley) above the message input. When pasted into a `.md` file alongside a verbatim DM thread, this picker row gets mislogged as reactions sent by the recipient.

**The signature artifact** is three reaction emojis appearing together on one line, OR stacked on consecutive lines (each emoji alone on its line).

**Filtering rule:**
- A reaction-picker row is NOT content. Strip it from the log, or annotate it with a disclaimer that uses keywords like `picker`, `UI artifact`, or `not reactions` so the meta-note is clearly distinguished from misattributed content.
- A REAL reaction appears as ONE emoji (occasionally two), separately from the picker row. Log only the real reaction.
- If you see the picker trio appearing back-to-back on a paste, treat it as picker UI by default.

**Lint enforcement:** `scripts/lint/rules/linkedin_ui_artifacts.py` blocks writes that contain the picker trio inline in `cold_contacts/` or `drafts/` files unless the line includes a meta keyword. Override per-file with `<!-- lint-disable linkedin-ui-artifacts -->` at the top of the file.

### LinkedIn Send Workflow

**Always open browser in headed mode with persistent profile:**
```
playwright-cli open --headed --persistent
```

1. Navigate to profile
2. Open "More" dropdown → click "Connect"
3. Click "Add a note"
4. Type connection note (≤300 chars) using `keyboard.type('...', { delay: 5 })`
   - Do NOT use `insertText()`, LinkedIn's Send button won't activate
5. Verify character count and Send button enabled
6. Click "Send invitation"
7. Update `.md` frontmatter (status: sent) + record exact text in body. Run `build_index.py`.

### Blocked connections (email required)

When LinkedIn shows "please enter their email to connect":
- Dismiss dialog
- Keep status as `draft`
- Update `.md` frontmatter notes: `"NOT SENT - needs email to connect."`
- Report to user which contacts are blocked

### CRITICAL RULE

**Agent MUST ask for explicit human approval before sending any message via playwright-cli.** The user must see the exact text and confirm. No exceptions.

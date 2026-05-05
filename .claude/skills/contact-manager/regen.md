# Regenerate Outreach Report

### `regen`, Force rebuild (git-diff-based)

**Why git-based:** `.md` bodies accumulate follow-ups, replies, and notes between report versions. The old regen only read frontmatter metrics (via analyze.py), so prose sections (Active Conversations, Action Items, Stalled, Tier 3) went stale whenever a conversation advanced without a frontmatter status change. Git diff catches every body-level change.

**Tracking file:** `reports/.last_report_commit` stores the commit hash from the last successful regen. Left dirty after each regen, picked up by the next snapshot commit.

#### Step 0: Read last report baseline

```bash
LAST_HASH=$(cat reports/.last_report_commit 2>/dev/null || echo "")
```

If empty (first run), treat every active contact as changed, read all `.md` files with status in `{replied, met, meeting_scheduled, accepted, mou_signed, declined}`.

#### Step 1: Snapshot current state

```bash
git add cold_contacts/ cold_contacts.yml reports/ scripts/ drafts/
# Only commit if there are staged changes
git diff --cached --quiet || git commit -m "outreach: snapshot before regen"
```

This captures all working-tree changes (follow-ups sent, replies logged, frontmatter edits) into a commit so the diff in step 2 is complete.

#### Step 2: Diff since last report

```bash
# List changed contact files
git diff --name-only $LAST_HASH..HEAD -- cold_contacts/

# Full diff for reading conversation changes
git diff $LAST_HASH..HEAD -- cold_contacts/
```

Read the diff output. The key signals are:
- New `## Follow-up` / `## Sent` / `## Reply` sections → conversation advanced
- Frontmatter field changes (status, dates, notes)
- New files → new contacts added

**For every changed `.md` file:** read the full file (not just the diff) so you have complete context.

#### Step 3: Refine frontmatter from diff

For each changed file, verify frontmatter reflects body content:

| Body signal | Check frontmatter |
|------------|-------------------|
| New `## Follow-up DM sent ({date})` | `followed_up_at` matches that date? |
| New `## Reply received ({date})` | `last_replied_at` matches? `status` ≥ `replied`? |
| New `## Call completed` / `## Meeting` | `met_at` set? `status` = `met`? |
| New `## Sent ({date})` on a draft | `status` = `sent`? `sent_at` set? |

Fix any drift, then rebuild the index:
```bash
uv run python scripts/build_index.py
```

#### Step 4: Generate metrics and charts

```bash
uv run python scripts/charts.py
uv run python scripts/analyze.py --json
```

#### Step 5: Write OUTREACH_REPORT.md

Two data sources, each for a different part of the report:

| Report section | Source |
|---------------|--------|
| Numbers, tables, rates (Sections 1, 2, 8) | `analyze.py --json` |
| Prose (Sections 3 Active Conversations, 7 Action Items, Tier 3, Stalled) | **Git diff + full .md reads** |
| Discoveries, System Changes (Sections 4, 5) | Carry forward unless user adds new |
| Verticals Ranked (Section 6) | `analyze.py --json` + prose from diff |

**For prose sections:**
- **Changed contacts (in diff):** Re-read their `.md` file. Rewrite their report entry from the current file state, do NOT patch the old prose.
- **Unchanged contacts (not in diff):** Keep existing prose from the previous report.

#### Step 6: Generate PDF

```bash
cd reports
pandoc OUTREACH_REPORT.md -o OUTREACH_REPORT.html --standalone --css style.css --embed-resources --metadata title=" "
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --print-to-pdf=OUTREACH_REPORT.pdf --no-pdf-header-footer "file://$(pwd)/OUTREACH_REPORT.html"
rm OUTREACH_REPORT.html
cd ..
```

#### Step 7: Commit and save baseline

```bash
git add cold_contacts/ cold_contacts.yml reports/OUTREACH_REPORT.md reports/OUTREACH_REPORT.pdf reports/charts/
git commit -m "outreach: regen report vN (date)"
git rev-parse HEAD > reports/.last_report_commit
```

The hash file is left dirty, next regen's step 1 snapshot picks it up.

#### Rules

- Always generate charts before the PDF so images are fresh.
- Always generate PDF via `pandoc → HTML → Chrome --print-to-pdf`. Never use pdflatex/xelatex directly (CJK glyphs break).
- MUST use `file://` absolute path and run from `reports/` so relative `charts/*.png` paths resolve in Chrome.
- Charts are embedded in OUTREACH_REPORT.md as `![alt](charts/filename.png)`, relative to reports/.
- Clean up intermediate `OUTREACH_REPORT.html` after PDF generation.
- **HARD CONSTRAINT:** Engagement rate tables/charts MUST show cold-only and overall side by side. Warm/ref/inbound is ~100% always so it's noise, omit it. Cold-only is the honest signal. Status counts and contact-type breakdowns don't need the split (they ARE the split).

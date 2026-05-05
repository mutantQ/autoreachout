---
name: outreach-reflection
description: Evidence-based retrospective on recently-sent outreach messages. Pulls verbatim message bodies from cold_contacts/, compares replied vs silent within a cohort, surfaces 4-7 themes with concrete file-cited evidence, and proposes specific copy/process changes. Run regularly (weekly to bi-weekly) to keep cold-message quality from drifting back to template-bait.
user_invocable: true
triggers:
  - reflect on outreach
  - reflection
  - what could've gotten better
  - cold-send retro
  - outreach retrospective
---

# Outreach Reflection Skill

A reusable retrospective on the cold messages we've sent. The point is **action**, not narrative, output should change the next batch's copy or process, not generate prose.

## When to run

- Weekly to bi-weekly cadence (default cohort: last 14 days of sends).
- After any batch of ≥5 sends has reached its wait-window (3+ days for 리멤버, 5+ for email, 7+ for LinkedIn) and we have replied/silent buckets to compare.
- Before drafting the next batch into a similar vertical or channel.
- After any single high-value reply (e.g. positive forward, declined-with-reason), even one strong signal can re-target the rest of an in-flight cohort.

## Hard rules

1. **Evidence or it didn't happen.** Every theme cites at least 2 specific contact files (path:line or slug). No abstract themes ("be more personal", "improve tone"), those are forbidden.
2. **Quote verbatim.** Never summarize a sent body when comparing winners vs silents. Use markdown blockquotes with the actual text.
3. **Counter-examples first.** Before declaring a pattern, actively grep for messages that broke the pattern AND replied, or followed the pattern AND succeeded. Survivorship bias is the default failure mode of this skill.
4. **Action-only output.** Themes must end in either (a) a concrete copy change a draft can apply tomorrow, or (b) a lint-rule candidate, or (c) a process change with a measurable trigger. "We should be more careful about X" is not action.

## Workflow

### 1. Define the cohort

Default: contacts where `sent_at` is within the last 14 days, regardless of channel.

```bash
uv run python scripts/analyze.py --json | jq '.contacts[] | select(.sent_at >= "<today-14d>")'
```

Or grep `cold_contacts.yml` for `sent_at: '2026-04-XX'` patterns within window.

Alternative cohorts:
- Last N sends regardless of date (good for low-volume periods)
- By vertical (e.g. all `vertical: insurance` sends in last 30 days)
- By channel (e.g. all `리멤버` sends since the last reflection)
- By drafter pattern (e.g. all sends with the same anecdote opener)

### 2. Read the bodies, verbatim, not summary

For each contact in the cohort, open `cold_contacts/{slug}.md` and read:
- The first `## Sent (...)` section (the cold body)
- Any `## Reply received (...)` section
- Any `## Follow-up (...)` if relevant

**Do not read frontmatter and infer.** The body is the only valid evidence. Sample size of 8-15 contacts is the sweet spot, fewer = thin patterns, more = analysis paralysis.

### 3. Bucketize

| Bucket | Definition | Treat as |
|---|---|---|
| **A. Replied** | Any inbound after the cold, regardless of warmth | Winning copy candidate |
| **B. Accepted-no-reply** | LinkedIn accepted but no message back | Weak winner / template-OK signal |
| **C. Silent past wait** | No reply, past channel-specific wait window | Loser candidate |
| **D. Too-early** | Past wait undefined / < window | Exclude from this reflection |
| **E. Declined / negative** | Explicit decline | Special-case: read for counter-evidence on why |

### 4. Pattern extract, the comparison axes

For each axis, look at A vs C side-by-side (not A alone). At least 2 pieces of evidence per pattern before it becomes a theme.

| Axis | What to look for |
|---|---|
| **Opener (sentence 1)** | Recipient-specific reputation/article/data point vs generic self-intro vs universal anecdote |
| **Ask shape** | Routing ask ("라인 소개 부탁드립니다") vs commitment ask ("15분 통화") vs no-ask vs multi-ask |
| **Reframe presence** | Does any sentence re-pose the recipient's problem, or only describe ours? |
| **Hedge phrases** | "필요시...도 가능", "혹시...괜찮으시다면", "may be of interest", soft-yes language |
| **Reference strength** | Anonymized vs named; permission-bound limit vs self-imposed limit |
| **Templating signal** | When 3+ messages share a scaffold (≥70% sentence overlap), batch-fatigue risk |
| **Length distribution** | 280-300자 vs <250자 vs over-cap; English ≥250 vs <200 chars |
| **Channel-specific tells** | 리멤버 (DM-quick), LinkedIn (profile-aware), email (signature, threading) |
| **Send timing** | Bunched (5+ in 48h same channel) vs staggered |

### 5. Write the reflection

Output structure (target ≤800 words):

```markdown
## Reflection, [cohort window], [N] sends

Cohort: [N replied / N silent / N accepted / N too-early]. Channel mix: [...]. Vertical mix: [...].

### Winner anatomy, what the [N] reply(ies) had

[Verbatim quote from the strongest winner, with file:line citation.]

[2-4 traits, each grounded in a specific quote or comparison.]

### Silent anatomy, what failed

[Verbatim quote(s) from typical silent message(s).]

[3-5 failure modes, each with at least 2 files as evidence.]

### Themes & action items

| # | Theme | Evidence | Action |
|---|---|---|---|
| 1 | [Specific claim] | [slug-A vs slug-B-and-C] | [Concrete copy change OR lint-rule candidate OR process change] |
| ... |
```

### 6. Optional: lint-rule promotion

If a theme has clear binary detection (e.g. "drop the '필요시...도 가능합니다' hedge"), offer to /skillify it as a lint rule in the next pass. Don't promote on the same pass, lint rules need their own surface and tests. Just flag candidates.

### 7. Optional: log to reports/

If running this regularly (weekly+), append the reflection to `reports/REFLECTION_LOG.md` with date stamp. Cross-reflection comparison (week-over-week themes) is one of the most useful artifacts this produces, the same theme appearing 3 weeks running is the strongest signal that it's a process problem, not a copy problem.

## Pitfalls

- **Permission-scope misreading.** Before recommending "use a stronger reference," re-read the actual permission grant verbatim. A permission scoped to anonymous reference (e.g. "OK to refer to me as 'a person in role X', name and company private") is NOT permission to name the contact. Recommending naming when permission was for anonymous is a privacy and trust breach masquerading as a copy improvement.
- **Evidence design vs copy failure conflation.** When N≥4 sends share a scaffold within a tight window in one vertical, that's likely a **deliberate controlled experiment** (hold scaffold constant, vary recipient, observe reply-rate distribution), not a copy weakness. Default reflection question = "did this scaffold land in this vertical?", not "did we template too much?" Do not propose "stagger sends" or "vary scaffold per recipient within the batch" without first asking which mode the user is optimizing for: replies-per-send (vary scaffold) vs evidence-per-vertical (hold constant). Action items should target the **next** batch's scaffold (different opener, ask, reframe), not the within-batch variance.
- **Survivorship bias.** One reply is not a pattern. Need 2+ winners showing the same trait, or 3+ silents lacking the same trait, before declaring a theme. The lone exception: if a strong negative reply (decline) explicitly cites a reason, that single piece of evidence may anchor a theme.
- **Reply ≠ buying.** A passive routing reply ("관련될만한 팀들에게 공유드려보겠습니다") is success on the *opener*, not on the *product*. Don't conflate the two when extracting traits to keep.
- **Confirmation bias.** Once you've identified a candidate pattern, actively grep for messages that broke it AND replied. If you find one, the pattern is weaker than it looks.
- **Stale anecdote drift.** When the same opener appears in N+5 sends across multiple cohorts, freshness has decayed regardless of original strength. Track opener-reuse across cohorts as its own axis.
- **Reflection ritual without reflection action.** If a reflection produces themes but the next batch shows the same failure modes, the skill failed even if the report read well. Compare consecutive reflection logs for repeated themes, that's the real KPI.
- **Korean / English drift.** Don't reflect on Korean and English cohorts together; the norms differ. Run two separate reflections if the cohort is mixed.

## What this skill is NOT

- Not a status report (use `contact-manager sync` + `reports/OUTREACH_REPORT.md` regen).
- Not a draft-quality lint (use `typo-prevention-cold-drafts` + `scripts/lint/`).
- Not a metrics dashboard (use `scripts/analyze.py`).
- Not a 1-on-1 message review (use `outreach-email` with a single recipient).

It's a copy/process retrospective grounded in actual recent sends.

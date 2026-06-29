# Batch Draft Pipeline

`$ARGUMENTS`

## Purpose

Prepare outreach drafts in one unattended pass while keeping the human in
control of sending.

The pipeline has two modes:

1. **New-batch mode:** discover or accept N new targets, research them,
   write N draft records, review the drafts, and leave them in
   `cold_contacts/` with `status: draft`.
2. **Existing-contact mode:** resolve existing contact files or live
   threads, append reply/follow-up/re-approach drafts into those files,
   review the drafts, and leave the files ready for manual review.

This pipeline never clicks send. Drafts in files are the artifact.

## Mode Selection

Select **new-batch mode** when the request includes a count and a target
category, or when the user explicitly asks to discover new targets.

Select **existing-contact mode** when the request names existing people,
slugs, files, threads, or says reply, follow up, re-approach, or review
pending drafts.

Ask one concise question only when the target set cannot be resolved and
guessing would change who receives a draft.

## Accepted Arguments

### New-batch mode

```text
/batch-draft <vertical> <N> [channel] [--source linkedin|remember|manual]
```

- `vertical`: one of the valid `vertical` values in
  `contact-manager/SKILL.md`.
- `N`: integer from 1 to 10. Split larger batches.
- `channel`: `linkedin`, `email`, `kakaotalk`, `remember`, or another
  channel already supported by the project's schema.
- `--source`: where discovery starts. Use `manual` when the user gives a
  named list.

### Existing-contact mode

```text
/batch-draft follow up <slug|name> [and <slug|name> ...]
/batch-draft reply <slug|name|thread>
/batch-draft re-approach <slug|name>
/batch-draft review [pending drafts|<slug|name> ...]
```

Resolve targets in this order:

1. Exact file path or slug under `cold_contacts/`, `vendors/`, or another
   entity directory.
2. Generated index lookup in `cold_contacts.yml`.
3. Full-text search over contact files.
4. Optional email/calendar/contact MCP lookup if the workspace has one
   installed and the request depends on live thread state.

If multiple contacts match and context does not disambiguate, ask one
question.

## Output Guarantees

- New-batch mode creates exactly N new or updated files with
  `status: draft`.
- Existing-contact mode updates existing files only. It does not create
  duplicate contact files.
- Draft bodies appear only inside entity files, never in chat.
- The final chat response lists changed paths, review result summary,
  validation status, and concrete blockers.
- No commit is created automatically.

## Preflight

Before drafting, run:

```bash
uv run python scripts/build_index.py
uv run python scripts/analyze.py --json >/tmp/autoreachout-analyze.json
```

Then check:

- **Rate limits:** use `contact-manager/add.md` thresholds. Hard-limit
  violations block the run.
- **Dedup:** exact LinkedIn URL or one-file-per-entity matches block new
  file creation.
- **Ecosystem collision:** same company, same small professional circle,
  same standards body, same event, or same niche community should trigger
  staggered timing or clearly different message structures.
- **Known-facts availability:** the agent needs a project-specific
  known-facts list from the local skill, private notes, or the user's
  prompt. If none exists, drafts must avoid maturity, pricing,
  partnership, deployment, customer, and roadmap claims.
- **Channel availability:** browser automation, Remember, Gmail, and
  calendar tools are optional external integrations. If unavailable, use
  file context and manual user-provided details rather than pretending
  live state was checked.

Hard stops:

- `N` is outside 1 to 10.
- New-batch target cannot be deduplicated safely.
- A live thread fact is required but unavailable.
- Discovery cannot produce enough verified candidates and the user did
  not provide a manual list.

## New-Batch Pipeline

### Phase 1: Candidate Pool

Build a pool of at least `2N` candidates when discovery is requested.
Each candidate row should include:

- name
- company
- role
- profile URL or source reference
- current-affiliation evidence if available
- one-sentence relevance to the vertical
- channel-fit note

Default channel-fit order for first outreach:

1. warm intro
2. in-person or event context
3. community where the problem is visible
4. manual outbound by LinkedIn, email, Remember, or another configured
   channel

Do not default to cold outbound just because it is easy. If a warmer
channel is obvious, note it and either use it or mark the cold draft as
lower confidence.

Auto-pick N candidates using deterministic rules:

1. Drop candidates with unverified or missing required profile/source
   references.
2. Drop candidates whose entity already has a file.
3. Prefer specific public hooks over generic job-title matches.
4. Prefer role relevance and current activity over seniority alone.
5. Diversify by company and sub-ecosystem.

If the user provides explicit candidates, skip discovery but still run
dedup, research, drafting, and review.

### Phase 2: Per-Target Research

For each selected target, gather:

1. Audience type from `outreach-email/cold.md`.
2. Why they might reply, using `outreach-email/SKILL.md`.
3. Warmth: HOT, WARM, or COLD.
4. Channel-fit verdict: warm intro, event, community, email, LinkedIn,
   Remember, phone, or unknown.
5. One specific recipient hook from a public artifact or user-provided
   context.
6. Claims the draft might use, tagged `[VERIFIED]`, `[LIKELY]`, or
   `[UNVERIFIED]`.
7. Any affiliation or activity claim marked for anchor eligibility:
   `[anchor_eligible: true]` only when a current primary source supports
   using it as the hook.

Fail closed. If a claim is stale-prone, inferred from a title, sourced
from an old directory, or not confirmed by the recipient's own words or
a current primary source, mark it `[anchor_eligible: false]`.

Do not assert what a recipient does day to day unless it is confirmed.
When the draft needs to test an inferred workflow or pain, phrase it as
a self-qualifying question.

### Phase 3: Draft Plan

Before writing, compute:

- target, audience type, why-reply motivation, and warmth
- discovery vs solution mode
- hidden assumption the message is testing
- commitment signal sought, such as current spend, failed workaround,
  intro to owner, paid pilot interest, call, or explicit no
- ecosystem collisions inside the batch and against recent outreach
- pattern assignment from `outreach-email/cold.md`

First-touch cold outreach defaults to discovery mode. It should ask
about the recipient's current workflow, pain, alternatives, or buying
signal before leading with the sender's product.

### Phase 4: File-Only Drafting

Write each draft into the correct file.

For a new cold contact, create:

```text
cold_contacts/{slug}.md
```

For an existing entity, append a dated pending-review section to the
existing file.

Use the canonical frontmatter schema from `contact-manager/SKILL.md` and
`scripts/lint/schemas.yml`. Use `status: draft` for unsent outreach.

Recommended section headers:

```markdown
## Outbound draft pending review (linkedin, YYYY-MM-DD)
## Outbound draft pending review (email, YYYY-MM-DD)
## Outbound draft pending review (kakaotalk, YYYY-MM-DD)
## Outbound draft pending review (remember, YYYY-MM-DD)
```

Channel constraints:

- `linkedin`: connection note <= 300 characters, no email address, no
  signature, no meeting CTA.
- `remember`: concise plain text, front-load context, no markdown, no
  signature, no links unless the project has verified they render well.
- `email`: subject plus plain-text body. First-touch cold email should
  usually be under 75 words unless a file note explains why it needs
  more detail.
- `kakaotalk`: short plain text, no markdown.

Do not create X/Twitter sendable drafts. Use a reminder/status note
instead, because those channels are easy to mis-handle without native
context.

## Review Pipeline

For new-batch mode, use the 4N + 1 review architecture from
`outreach-email/batch.md`.

Per draft:

1. **Fact-check:** recipient claims and profile/source references.
2. **Overstatement:** project claims against the user's known-facts list.
3. **Tone:** mechanical style, fake warmth, platform mismatch, markdown,
   over-polish, and presumptuous asks.
4. **Recipient perspective:** whether the draft gives this specific
   recipient a reason to accept or reply.

Across the batch:

5. **Template detection:** repeated openings, repeated claims, same
   pattern in a shared ecosystem, channel length rules, and cross-draft
   sameness.

For existing-contact mode, use the same review lenses but scale the
number of agents to the risk and target count. One or two warm replies
can be reviewed in a single careful pass if subagents are unavailable.
Three or more drafts should use parallel review when possible.

Fix review findings in the files. Strip or generalize unverified claims
from draft bodies unless the user explicitly asked to keep a marked
uncertainty. Rewrite hooks anchored on stale affiliations or unconfirmed
activities.

## Validation

After writing and fixing drafts, run:

```bash
uv run python scripts/lint/run_lint.py --all
uv run python scripts/build_index.py
```

Open changed files for review when the environment supports it:

```bash
open cold_contacts/{slug}.md
```

Do not bypass lint. Fix the underlying issue.

## Hand-Off

Final response should include:

- changed file paths
- review summary with PASS or concrete issues
- validation commands run and whether they passed
- any unresolved blocker or user-confirmation item
- suggested manual next step by channel

Do not include draft bodies or excerpts.

Suggested commit shape, if the user asks:

```bash
git add cold_contacts/<slug>.md cold_contacts.yml
git commit -m "outreach: batch-draft <vertical> (<N> drafts)"
```

Do not auto-commit.

## Public-Repo Privacy Rule

This skill must stay project-agnostic. Do not add real names, private
company facts, internal pricing, confidential roadmap details, personal
email addresses, private thread IDs, or proprietary playbooks to this
file. Keep project-specific facts in the user's private known-facts file
or in private contact records outside the public repository.

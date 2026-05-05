---
name: outreach-email
description: Write cold and follow-up outreach messages for your project, targeting potential partners and customers. Use when writing B2B outreach, partnership outreach, follow-ups, or technical business development messages, cold, warm, referral, or inbound.
user_invocable: true
---

# Outreach Message Skill

> `cold_contacts.yml` is generated from .md frontmatter, query it freely but never hand-edit. Periodic regenerable report at `reports/OUTREACH_REPORT.md`.

**IMPORTANT: Before composing any message, ensure `contact-manager` has run dedup and rate limit checks.** Run `/contact-manager check` with the target's LinkedIn URL or name first.

Write outreach where the recipient has a clear reason to reply.

## Output

**Hard rule: NEVER paste the draft body or any portion of it in chat. The file is the only artifact.**

After writing or editing a draft, the chat response must be at most one short sentence confirming the file was written + opened, plus an offer to adjust. No body. No excerpts. No "here's the new version". No diff-style before/after. No "preview". Even ONE sentence of the body in chat is a violation.

Acceptable chat output examples:
- "Drafted at `cold_contacts/{slug}.md`, opened for review."
- "Updated. Open the file to see the changes."
- "Fixed the timeline language. Want me to adjust further?"

Forbidden chat output (regardless of how short):
- "New body: …"
- "Updated to: …"
- "Quick preview: …"
- "The opening now reads: …"
- Any quoted line of the email/DM body, even partially

Why: chat tokens for already-written file content are pure waste. The user reads the file, not the chat echo.

**Routing (where the file lives):**
- **Existing contact** (`cold_contacts/{slug}.md` already exists): append a new section with header `## Outbound draft pending review (channel + topic, YYYY-MM-DD)`.
- **New cold contact** (no existing file, will become a recipient of outreach): create `cold_contacts/{slug}.md` with full frontmatter (`status: draft`) and the body in an `## Outbound draft pending review (...)` section. Run `contact-manager check` first for dedup + rate limits.
- **Vendor / service provider** (law firm, contractor, accountant, etc.): use `vendors/{slug}.md`. Vendor schema differs from cold_contacts (see `scripts/lint/schemas.yml` for the canonical key list).
- **Pitch event** (demo day, judging panel, accelerator pitch): use `pitch_events/{slug}.md` with the event-specific schema.
- **Not yet ready to promote** (early research, no clear contact path): `outreach/drafts/{slug}.md` is acceptable as a temporary staging area. Promote to `cold_contacts/` and consolidate when engagement begins. Per `feedback_drafts_one_file_per_entity.md`: never duplicate, if `cold_contacts/{slug}.md` already exists, the draft must go inside that file.

**Section header conventions inside contact files:**
- `## Outbound draft pending review (channel, YYYY-MM-DD)`, active draft, NOT yet sent. The `connection-note-length` lint rule scans this section.
- `## Sent (channel, YYYY-MM-DD)`, historical record of sent message, body verbatim. Lint rules treat this as archive (skip leak/length checks).
- `## Reply received (channel, YYYY-MM-DD)`, recipient's reply, body verbatim. Archive section.
- `## Follow-up sent (YYYY-MM-DD)`, historical follow-up. Archive section.
- `## Call completed (YYYY-MM-DD)` / `## Meeting (YYYY-MM-DD)`, call notes. Archive section.

The `## Sent (connection note)` form (no date in parens) is also recognized by `connection-note-length` for legacy compatibility.

**Always run `open {path}`** after the file write so the editor surfaces it.

**Inline-review exception:** ONLY when the user explicitly says "show inline", "in chat", "preview here", "what does it say now", or similar direct request. Default behavior is never inline.

**Output kinds (inside the file):**
- **Connection note** (≤300 characters): The first thing they see. Natural reason to connect. NOT a compressed pitch.
- **Follow-up / email / DM**: appended to the same contact `.md` as a new section, only after the recipient accepts or replies. Do NOT draft follow-ups upfront.

---

## Pre-Draft Checkpoint (mandatory)

Complete these three checks BEFORE writing anything. Show results to user.

### 1. "Why would they reply?"

State in one sentence what the recipient gains from responding. Must be one of:

| Motivation | Example | Reply likelihood |
|-----------|---------|-----------------|
| We solve a problem they have RIGHT NOW | a specific failure in their stack that your project addresses | High |
| We advance their publicly stated goal | a public goal they have stated that your project moves forward | Medium-High |
| We are a story worth covering | "underdog angle: a small team building a category-disruptive version of an established product" | Medium |
| We offer information they genuinely want | "Novel research data relevant to their field" | Medium |
| We ask advice on something they care about | "Conformance question about their own standard" | Low-Medium |

If you cannot articulate a specific, concrete motivation from the recipient's perspective, tell the user: "I can't identify a clear reason this person would reply. Consider seeking a warm intro or choosing a different contact."

### 2. Warmth Assessment

Check for shared context that can be referenced:

- **HOT**: Existing relationship, prior conversation, mutual introduced by someone
- **WARM**: Shared alma mater (university network), shared investors ([VC-D]), shared accelerator ([accelerator]), mutual LinkedIn connections (1st degree), same conference attendee
- **COLD**: No connection whatsoever

For COLD contacts who are high-profile (>50K followers, C-suite at major company, public figure), recommend seeking a warm intro instead of cold outreach. State this clearly to the user.

### 3. Ecosystem Collision Check

Query `outreach/cold_contacts.yml` before drafting. Flag if:

- Another contact at the **same company** was messaged in the last 14 days
- 3+ contacts with **overlapping tags** were messaged in the last 7 days
- The recipient is likely to know someone already contacted (same standard body, same industry conference circuit, same newsroom network)

If collision detected, advise the user to stagger by 1-2 weeks and vary message structure significantly.

### 4. Risk Note (if applicable)

After drafting, if the message contains information that is NOT already public on your project's website or blog, add a brief **⚠ Risk note** at the end of the draft for the user's review. This is not a blocker, it's a heads-up so the user can make an informed call.

Hard rule: **Never include internal cost data (BOM, margin, runway) in any outreach draft.** Everything else is a judgment call for the user.

---

## Context: your project

> **REPLACE THIS SECTION** with your own project context before using the skill in production. The bundled fixtures use a fictional company "Acme" as a placeholder; the structure below is the shape the rest of the skill expects to find.

A short Context section should cover:

- **What the project actually is** (one sentence). Avoid jargon a recipient outside your domain wouldn't recognize.
- **Product lineup if multiple products / tiers exist.** Lead which product matches which audience. Avoid leaking pricing tiers that aren't already public.
- **Current milestones / proof points** that are *already public* (website, blog, public talk). Anything not yet public needs a per-draft risk note (above).
- **Audience-to-vocabulary mapping.** What technical depth each audience type expects. (e.g., engineers get spec language; journalists get story angles; recruiters get plain-language outcomes.)
- **What NOT to claim.** Specific maturity claims, partnerships, or features the project does not yet have. This is the most important sub-section; LLMs will paraphrase upward without it.
- **Differentiator vs. existing solutions** in one sentence. Where you are *complementary* vs. *competing*. Most cold outreach should lead with complementary framing.

Keep this section under ~40 lines. The drafting agent reads it on every invocation, so brevity matters; expand only when a specific anti-pattern keeps showing up.

---

## Sub-file Reference

<!-- Keep this table in sync with sub-files in this directory. -->

| Task | File | When to read |
|------|------|-------------|
| Draft cold connection note | cold.md | Writing first-touch messages, choosing audience type + pattern |
| Draft follow-up after acceptance/reply | followup.md | Writing DMs/emails after connection accepted or reply received |
| Batch drafting (2+ targets) | batch.md | Multi-target sessions, parallel review, staggering rules |

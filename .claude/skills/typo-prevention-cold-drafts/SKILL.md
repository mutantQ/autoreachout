---
name: typo-prevention-cold-drafts
description: Pre-send typo gate for cold drafts that share a narrative scaffold across multiple recipients. Enforces cross-batch scaffold consistency, canonical-source copy-paste discipline, and domain-noun semantic verification before status flips to sent.
triggers:
  - "drafting cold message in cold_contacts/"
  - "cold outreach batch"
  - "before marking status: sent"
  - "user says send / 보냈어 / 発送 / sent"
  - "logging verbatim ## Sent section"
---

# Typo Prevention for Cold Drafts (cross-batch scaffolds)

## The failure mode this skill exists to prevent

When a batch of cold messages share an identical narrative scaffold sentence (the "spine" of the pitch, reused across N recipients), retyping that sentence N times gives N chances to drift. Domain-specific terms in non-English locales are the easiest place to drift: a single mistyped noun produces a body that is grammatically valid but semantically wrong, which a casual review pass will not catch.

**Cost of a single semantic typo to a high-value target:** the recipient reads a sentence whose noun is incoherent for the surrounding clause and silently downgrades trust. You will not get told.

## When to activate

Apply this gate when ANY of:

- Drafting a cold message destined for `cold_contacts/{slug}.md`.
- Drafting a batch (2+ drafts sharing a narrative scaffold).
- About to flip `status: draft` → `status: sent`.
- User says "send" / "보냈어" / "発送" / "sent" / etc.
- Writing a `## Sent (..., verbatim)` section.

## The four checks

### 1. Canonical-source copy-paste

Identify the canonical source for any scaffold sentence shared across multiple drafts. Suggested sources, in order of preference:

- A previously-sent draft that was confirmed-received without correction.
- A canonical "ground truth" file you maintain for your domain (e.g., a verbatim quote from a domain expert, a public industry report sentence, a regulatory phrasing).

When a scaffold appears in multiple drafts, **copy-paste from the canonical, then edit only the per-recipient anchors. Never retype.**

### 2. Cross-batch scaffold diff

Before marking any draft sent, diff its scaffold sentence against the canonical and against batch siblings. Any token-level divergence is either an intentional per-recipient variation OR a typo. Verify which.

```
canonical scaffold: <reference sentence>
draft N:            <draft sentence>
                          ^^^^ DIVERGENCE  ← intentional or typo?
```

### 3. Domain-noun semantic check

Read each domain-specific noun in context and ask: *"Does this noun fit this clause?"*

The high-trap categories are language-specific. Maintain a project-specific trap list as you accumulate incidents. Generic categories to watch for:

| Trap category | Example shape (any locale) |
|---|---|
| Confusable homophones / near-homophones | two domain nouns that sound similar but mean different things |
| Word-spacing changes meaning | one-word fixed term vs. two-word compound (very common in Korean / Japanese / Chinese) |
| Term-vs-process distinction | a noun for the artifact vs. a noun for the act ("photo" vs "photographing") |
| Synonym variants in same body | e.g. mixing "ins. company" / "insurer" / "carrier" within one message |
| Tense / aspect on key verbs | "shoot" vs "re-shoot", "verify" vs "verified" |

For terms outside your trap list, the question is always: *"If a recipient reads this noun cold, will it parse correctly given the surrounding clause?"*

### 4. Pre-mark-sent verbatim re-read

Before flipping `status: sent` and writing the `## Sent (verbatim)` section:

- Re-read the entire body once.
- Focus on every domain-specific noun.
- Compare against canonical scaffold for shared sentences.
- ANY divergence = halt and surface to user before logging.

## Success criteria

- Zero domain-incoherent typos in sent cold drafts.
- All drafts in a batch share a byte-identical narrative scaffold (modulo intentional per-recipient anchors).
- `## Sent (verbatim)` body matches what the recipient actually saw.

## Anti-patterns

| Don't | Do |
|---|---|
| Retype a shared scaffold sentence from memory for each draft | Copy-paste from a canonical source, edit only anchors |
| Trust user review to catch body typos | The user edits anchors and skims body; body verification is yours |
| Mark sent immediately on user "send" signal | Always do step 4 (pre-mark verbatim re-read) before flipping status |
| Rely on locale spell-check as the gate | Spell-check does not catch domain-semantic errors (the typo is a real word, just the wrong real word) |
| Treat scaffolds as flexible boilerplate | Scaffolds are templates; copy-paste discipline is non-negotiable |

## Recovery if a typo escapes

1. Log the typo as-sent (verbatim rule trumps correction).
2. Note the typo in the file's `notes` field.
3. If a follow-up message is queued, the follow-up can use the corrected term and naturally overwrite. Do NOT send a "correction" message.
4. Add the specific trap to your project's trap list so it is caught next time.

## Open questions

- Should this gate run as a Bash diff (e.g., extracting scaffold lines from recently-modified `cold_contacts/*.md` and diff-ing them automatically)? The current form is a behavioral checklist; an automated diff step is a clean upgrade.
- For projects with multiple working locales, is one multilingual skill sufficient, or do per-locale sibling skills compound better?

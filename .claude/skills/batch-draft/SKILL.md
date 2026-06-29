---
name: batch-draft
description: Batch outreach draft pipeline for autoreachout. Use for new cold-contact batches, existing-contact replies, follow-ups, re-approaches, and multi-contact draft review. Discovers or researches targets when needed, writes draft bodies only to cold_contacts/ or the correct entity file, reviews them, validates lint/build_index, and never sends.
user_invocable: true
---

# Batch Draft

Use this skill when the user asks to prepare multiple outreach drafts,
discover a small batch of new targets, draft follow-ups for existing
contacts, or review pending outreach drafts.

This is a file-first pipeline. It prepares drafts for human review. It
does not send messages.

## Modes

### New-batch mode

Use when the request includes a target category plus a count, or when the
user explicitly asks to find new targets.

```text
/batch-draft <vertical> <N> [channel] [--source linkedin|remember|manual]
```

### Existing-contact mode

Use when the user names existing people, files, threads, or pending
drafts.

```text
/batch-draft follow up <slug|name> [and <slug|name> ...]
/batch-draft reply <slug|name|thread>
/batch-draft re-approach <slug|name>
/batch-draft review [pending drafts|<slug|name> ...]
```

If the mode is ambiguous, infer from context. Ask one concise question
only when both the mode and target set cannot be determined.

## Required Workflow

Read and follow [command.md](command.md). It contains the public,
project-agnostic pipeline.

Also read the relevant local skill files:

- `contact-manager/SKILL.md` for schema, dedup, rate limits, and status
  transitions.
- `contact-manager/add.md` before creating new contact files.
- `outreach-email/SKILL.md` before writing draft bodies.
- `outreach-email/cold.md` for first-touch patterns.
- `outreach-email/followup.md` for replies and follow-ups.
- `outreach-email/batch.md` for multi-draft review architecture.

## Hard Constraints

- Never send anything.
- Never paste draft body text in chat unless the user explicitly asks
  for an inline preview.
- Write draft bodies only into `cold_contacts/{slug}.md` or the correct
  entity file such as `vendors/{slug}.md` or `pitch_events/{slug}.md`.
- Do not create a duplicate file for an entity that already has one.
- Preserve the existing channel/account/thread for replies unless the
  user explicitly asks to switch.
- Use only claims supported by the contact file, public sources, or the
  user's private known-facts list.
- Treat missing or stale recipient facts as reasons to generalize the
  hook, not as permission to invent.
- Validate after writes:
  ```bash
  uv run python scripts/lint/run_lint.py --all
  uv run python scripts/build_index.py
  ```

## Final Response

Return changed file paths, validation status, and concrete blockers if
any. Do not include draft bodies.

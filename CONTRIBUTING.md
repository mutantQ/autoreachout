# Contributing

Welcome. This document describes the development workflow we follow on
`autoreachout`. Read it once before opening your first PR; the rules are
short and load-bearing.

---

## Ground rules

1. **Never commit real contact data.** The example `cold_contacts/*.md`
   files in this repo are fictional. Real contact data lives outside
   the harness, either in a sibling directory or in a gitignored
   subfolder. Names, emails, phone numbers, and verbatim message
   content of real people must not land in git.
2. **Lint before send.** The `scripts/lint/run_lint.py --all` sweep
   must pass clean before any report regen or status flip from
   `draft` to `sent`. The hook also enforces this on individual
   writes, but the sweep catches drift from external edits.
3. **No real outbound from the harness.** The harness drafts, lints,
   logs, and measures. It never clicks send. Any change that
   automates an outbound click on LinkedIn / Gmail / KakaoTalk will
   be rejected.
4. **One file per entity.** If `cold_contacts/{slug}.md` exists, all
   drafts and threads for that entity go there. Don't open a parallel
   `drafts/` file for a contact that already has a `cold_contacts/`
   record. The `one-file-per-entity` lint rule enforces this.

---

## Branch naming

Use one of these prefixes, followed by a short kebab-case slug:

| Prefix | When to use |
|---|---|
| `feat/` | New rule, new script, new pipeline stage |
| `fix/` | Bug fix; reference the failing test or issue number in the body |
| `refactor/` | Behaviour-preserving restructure (no test changes expected beyond moves) |
| `test/` | Test-only changes (new coverage, flake fixes) |
| `docs/` | README / SETUP / inline doc changes |
| `chore/` | Dependency bumps, CI tweaks, gitignore edits |

Examples: `feat/lint-rule-domain-acronym`, `fix/sync-kakao-hidden-events`,
`refactor/analyze-vertical-breakdown`.

Branch off `main`. Keep branches short-lived (under a week is the goal).

---

## Commit style

- One logical change per commit. If you can't describe a commit in one
  sentence, split it.
- Subject line in the imperative mood, ≤ 72 characters, no trailing
  period.
- Body wrapped at 72 columns. Explain *why*, not *what*, the diff
  shows the what.
- Reference issues/PRs by number in the body, not the subject.

```
feat(lint): block in-house abbreviations in conversational outbound

Adds a configurable rule that flags forbidden abbreviations in
outbound body zones (cold_contacts, vendors, Gmail drafts) while
leaving internal notes and blockquotes free. Configured via
IN_HOUSE_ABBREVIATIONS in scripts/lint/_config.py.

Refs #17
```

---

## Adding a new lint rule

1. Drop a new file at `scripts/lint/rules/<rule_name>.py`. Each rule
   exports a single `check(tool_name, tool_input) -> list[Violation]`.
2. Add it to the import block and the `RULES` list in
   `scripts/lint/run_lint.py`.
3. Write a paired test file at `scripts/lint/tests/test_<rule_name>.py`
   covering: positive case (rule fires), negative case (rule doesn't
   fire), exempt-zone case (frontmatter, blockquote, or
   `lint-disable` marker), and Gmail-payload case if the rule scopes
   to Gmail.
4. Run `uv run pytest scripts/lint/tests/ -q` and confirm green.
5. Run `uv run python scripts/lint/run_lint.py --all` to confirm the
   sweep stays clean against the example data.

---

## Adding a new frontmatter field

1. Add the field to `scripts/lint/schemas.yml` under the right
   directory section.
2. Update `scripts/build_index.py` if the field should be excluded
   from the generated YAML index (channel-specific noise, personal
   data).
3. Document the field's meaning in `.claude/skills/contact-manager/
   SKILL.md` in the canonical-schema section.
4. Run the sweep to confirm no existing files break.

---

## Test bar

Before pushing:

```bash
uv run pytest scripts/lint/tests/ scripts/tests/ -q
uv run python scripts/lint/run_lint.py --all
uv run python scripts/build_index.py
uv run python scripts/analyze.py >/dev/null   # smoke test
```

All four must succeed. The sweep must report zero blocks (warnings are
allowed but should be discussed in the PR).

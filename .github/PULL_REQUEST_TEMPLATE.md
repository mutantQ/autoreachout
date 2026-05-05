# What this PR does

One-sentence summary.

## Why

If this is a new lint rule, link to the issue with the worked-example
failure mode. If this is a channel integration, link to the issue
with the channel-integration spec.

## Test bar

- [ ] `uv run pytest scripts/lint/tests/ scripts/tests/ -q` is green
- [ ] `uv run python scripts/lint/run_lint.py --all` reports zero
      blocks
- [ ] If touching a lint rule: paired test file added/updated
- [ ] If touching frontmatter shape: `scripts/lint/schemas.yml`
      updated

## Anything reviewers should know

False-positive zones you tested by hand, edge cases you considered,
or open questions for the maintainer.

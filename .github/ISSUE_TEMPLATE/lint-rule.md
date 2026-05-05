---
name: New lint rule (worked example)
about: Propose a new lint rule from a real outreach failure
title: "lint: <one-line description>"
labels: ["lint-rule", "good first issue"]
---

## The failure mode

Describe the outreach mistake that triggered this rule. Be concrete:
what was the actual message, channel, recipient context?

## What the rule should catch

What pattern in the message body / frontmatter / Gmail draft should
fire? Keep the surface narrow: rules that catch one specific failure
are more trustworthy than rules that try to do too much.

## What the rule should NOT catch (false-positive zones)

Where does the same pattern legitimately appear? (Frontmatter,
blockquotes, archive sections, internal notes — these are usually
exempt zones for body-scoped rules.)

## Severity

- [ ] block (catches a real send-time error)
- [ ] warn (cosmetic / could-be-better)

## Test cases you'll write

- Positive: rule fires on the failure-mode example
- Negative: rule does not fire on the legitimate pattern
- Exempt zone: rule does not fire inside frontmatter / blockquote /
  archive / `lint-disable` marker
- Hook integration: Gmail draft payload (if applicable)

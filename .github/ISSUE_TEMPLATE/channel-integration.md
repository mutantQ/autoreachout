---
name: New channel / source integration
about: Propose support for a new outreach channel or contact source
title: "channel: <name of the channel>"
labels: ["channel-integration"]
---

## The channel

Which platform? What's the user's actual interaction model (DM,
broadcast, business-card import, calendar invite)?

## Who would use this

Solo founders running which kind of outreach (B2B, media relations,
enterprise sales, recruiting, etc.). Be specific about the user.

## Sync surface

How should the harness read activity from this channel?
- [ ] Local DB / file
- [ ] Public API (rate-limited, requires auth)
- [ ] Browser automation
- [ ] Manual paste (frontmatter + verbatim body, no auto-sync)

## Failure modes specific to this channel

Each channel has its own footguns (length caps, threading model,
hidden-event payloads, attachment handling, etc.). What should a
future lint rule catch on this channel?

## Are you willing to help build it

- [ ] Yes, opening a PR
- [ ] Yes, but want to discuss design first
- [ ] No, just flagging

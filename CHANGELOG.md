# Changelog

All notable changes to `autoreachout`. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and dates use
ISO 8601.

## [0.1.0], 2026-05-05 (initial release)

### Added
- 16 pre-send lint rules with paired tests (349 tests, all passing).
  Each rule traces back to a specific outreach failure mode and ships
  with a `<!-- lint-disable rule-name -->` per-file escape hatch.
- `scripts/build_index.py`: regenerate `cold_contacts.yml` from
  `cold_contacts/*.md` frontmatter (excluding personal fields).
- `scripts/analyze.py`: engagement metrics broken out by vertical,
  channel, contact_type, and time period. Text + JSON output.
- `scripts/charts.py`: matplotlib charts for the periodic report
  (status distribution, vertical breakdown, channel breakdown,
  contact-type breakdown, period comparison).
- `scripts/sync_kakao.py`: opt-in KakaoTalk activity sync via
  `kakaocli`, with hidden-event filtering and per-contact
  `kakaotalk_chat_id` gating. macOS only.
- 4 reusable Claude Code skills:
  - `contact-manager` (umbrella + sync / add / regen /
    send-linkedin / send-remember / update-status sub-files)
  - `outreach-email` (umbrella + cold / followup / batch sub-files)
  - `outreach-reflection` (periodic retrospective)
  - `typo-prevention-cold-drafts` (pre-send typo gate for KR drafts)
- 50 fictional cold-contact records spanning the full status pipeline
  and 10 verticals, plus one vendor, one standards-body, one event,
  and one pitch-event example so the lint sweep, build_index,
  analyze, and chart generators all run clean against the bundled
  fixtures.
- `scripts/lint/_config.py`: single editable surface for adapting
  the harness to a new project (founder name, domains, forbidden
  email, in-house abbreviations, primary-entity tag).
- Worked-example `OUTREACH_REPORT.md` regenerated against the bundled
  data, demonstrating the periodic report format.

### Notes
- The harness never automates outbound sends. Every actual click on
  LinkedIn / Gmail / KakaoTalk stays manual. This is a design
  invariant, not a TODO.
- `kakaocli` is macOS-first today. Linux/Windows support is on the
  [roadmap](README.md#roadmap--where-help-is-wanted).

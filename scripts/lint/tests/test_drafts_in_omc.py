"""Tests for drafts_in_omc rule."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.drafts_in_omc import (  # noqa: E402
    _scan_text,
    _is_in_scope,
    _has_outbound_markers,
    check,
)


PROJECT = Path(__file__).resolve().parents[3]


def _omc_path(rel: str) -> str:
    return str(PROJECT / ".omc" / rel)


def _vendors_path(rel: str) -> str:
    return str(PROJECT / "vendors" / rel)


def _cold_contacts_path(rel: str) -> str:
    return str(PROJECT / "cold_contacts" / rel)


def _outreach_drafts_path(rel: str) -> str:
    return str(PROJECT / "drafts" / rel)


class TestOutboundHeaderTrigger(unittest.TestCase):
    def test_outbound_draft_header_triggers(self):
        text = (
            "# Investor v7\n\n"
            "## Outbound draft pending review (2026-04-26)\n\n"
            "파트너님, 안녕하세요.\n"
        )
        v = _scan_text(text, ".omc/team-april26/drafts/02-contact-b.md")
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].rule, "drafts-in-omc")

    def test_outbound_draft_header_with_suffix_triggers(self):
        text = (
            "## Outbound draft pending review (Email payment timeline, "
            "2026-04-26)\n\nHi Counsel,\n"
        )
        v = _scan_text(text, ".omc/team-april26/drafts/07-counsel.md")
        self.assertEqual(len(v), 1)


class TestMetadataBlockTrigger(unittest.TestCase):
    def test_to_plus_subject_triggers(self):
        text = (
            "# CA inquiry\n\n"
            "**To:** sales@vendor-a.example\n"
            "**Subject:** Root cross-sign\n\n"
            "Hi vendor,\n"
        )
        v = _scan_text(text, ".omc/team-april26/drafts/06-vendor-a.md")
        self.assertEqual(len(v), 1)

    def test_to_plus_channel_triggers(self):
        text = (
            "**To:** 담당자 팀장\n"
            "**Channel:** SMS 010-3225-1921\n\n"
            "담당자 팀장님, 안녕하세요.\n"
        )
        v = _scan_text(text, ".omc/team-april26/drafts/01-contact-a.md")
        self.assertEqual(len(v), 1)

    def test_to_alone_does_not_trigger(self):
        # Only **To:** without **Subject:** or **Channel:** is ambiguous.
        # (e.g., a meeting note that records "**To:** ... was sent earlier")
        text = (
            "# Meeting note\n\n"
            "**To:** Founder\n\n"
            "Discussed the patent strategy.\n"
        )
        v = _scan_text(text, ".omc/research/meeting-note.md")
        self.assertEqual(len(v), 0)

    def test_subject_alone_does_not_trigger(self):
        text = (
            "# Press inquiry log\n\n"
            "**Subject:** Hardware-anchored provenance\n\n"
            "We received this from Wired UK.\n"
        )
        v = _scan_text(text, ".omc/research/press.md")
        self.assertEqual(len(v), 0)


class TestSummaryFilesPass(unittest.TestCase):
    def test_worker_summary_table_passes(self):
        # w1 summary lists draft files in a markdown table but is itself
        # NOT a draft. Must not trigger.
        text = (
            "# w1 deliverable summary\n\n"
            "| # | File path | Recipient | Channel | Lint |\n"
            "|---|-----------|-----------|---------|------|\n"
            "| 1 | `01-contact-a.md` | 담당자 | SMS | PASS |\n"
            "| 2 | `02-contact-b.md` | 투자자 | Email | PASS |\n"
        )
        v = _scan_text(text, ".omc/team-april26/drafts/00-w1-summary.md")
        self.assertEqual(len(v), 0)

    def test_strategy_doc_passes(self):
        # Bundle pricing internal doc has tables and headers but no
        # outbound message markers.
        text = (
            "# Bundle Pricing Model\n\n"
            "## Section 1: BOM vs MSRP vs TCO\n\n"
            "Product BOM: ~$N. MSRP: $X/yr. TCO: variable.\n"
        )
        v = _scan_text(text, ".omc/team-april26/drafts/05-bundle-pricing.md")
        self.assertEqual(len(v), 0)

    def test_research_memo_passes(self):
        text = (
            "# Prior art memo: s41928\n\n"
            "## Bibliographic data\n\n"
            "Cardes et al., Nature Electronics, 2026.\n\n"
            "## Risk classification\n\n"
            "MODERATE for camera, SEVERE for audio.\n"
        )
        v = _scan_text(text, ".omc/team-april26/research/01-priorart.md")
        self.assertEqual(len(v), 0)


class TestExemptions(unittest.TestCase):
    def test_lint_disable_marker(self):
        text = (
            "<!-- lint-disable drafts-in-omc -->\n\n"
            "# Reference templates with intentional draft snippets\n\n"
            "## Outbound draft pending review (template, not a draft)\n\n"
            "**To:** placeholder\n"
            "**Subject:** placeholder\n"
        )
        v = _scan_text(text, ".omc/team-april26/drafts/04-templates.md")
        self.assertEqual(len(v), 0)

    def test_lint_disable_marker_anywhere_in_file(self):
        # The marker can be anywhere, not just at the top.
        text = (
            "# Templates\n\n"
            "## Outbound draft pending review\n\n"
            "**To:** x\n"
            "**Subject:** y\n\n"
            "<!-- lint-disable drafts-in-omc -->\n"
        )
        v = _scan_text(text, ".omc/x.md")
        self.assertEqual(len(v), 0)


class TestScope(unittest.TestCase):
    def test_omc_root_in_scope(self):
        self.assertTrue(_is_in_scope(_omc_path("anything.md")))

    def test_omc_subdir_in_scope(self):
        self.assertTrue(_is_in_scope(_omc_path("team-april26/drafts/02-contact-b.md")))

    def test_omc_research_in_scope(self):
        # Research files are in scope but the content-based filter lets
        # genuine research memos through. This is intentional: a research
        # file that DOES contain outbound markers is suspicious.
        self.assertTrue(_is_in_scope(_omc_path("research/01-priorart.md")))

    def test_cold_contacts_out_of_scope(self):
        self.assertFalse(_is_in_scope(_cold_contacts_path("contact-a.md")))

    def test_vendors_out_of_scope(self):
        self.assertFalse(_is_in_scope(_vendors_path("vendor-a.md")))

    def test_outreach_drafts_out_of_scope(self):
        # outreach/drafts/ is the legitimate scratch dir per skill spec.
        self.assertFalse(_is_in_scope(_outreach_drafts_path("contact-c.md")))

    def test_skill_md_out_of_scope(self):
        self.assertFalse(_is_in_scope(
            str(PROJECT / ".claude/skills/contact-manager/SKILL.md")
        ))


class TestHasOutboundMarkers(unittest.TestCase):
    def test_canonical_header_only(self):
        self.assertTrue(_has_outbound_markers(
            "## Outbound draft pending review\n\nbody"
        ))

    def test_to_subject_only(self):
        self.assertTrue(_has_outbound_markers(
            "**To:** x@y.com\n**Subject:** Hello\n\nbody"
        ))

    def test_to_channel_only(self):
        self.assertTrue(_has_outbound_markers(
            "**To:** Founder\n**Channel:** SMS\n\nbody"
        ))

    def test_neither_returns_false(self):
        self.assertFalse(_has_outbound_markers(
            "# Strategy doc\n\nNo outbound markers here.\n"
        ))


class TestEditHook(unittest.TestCase):
    def test_write_to_omc_with_draft_blocked(self):
        v = check(
            "Write",
            {
                "file_path": _omc_path("team-april26/drafts/09-vendor-a.md"),
                "content": (
                    "## Outbound draft pending review (2026-04-26)\n\n"
                    "**To:** attorney@example.com\n"
                    "**Subject:** Re: 의견\n\n"
                    "변리사님,\n"
                ),
            },
        )
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].rule, "drafts-in-omc")

    def test_write_to_omc_without_draft_passes(self):
        v = check(
            "Write",
            {
                "file_path": _omc_path("research/01-priorart.md"),
                "content": (
                    "# Prior art memo\n\n"
                    "## Risk classification\n\n"
                    "MODERATE for camera.\n"
                ),
            },
        )
        self.assertEqual(len(v), 0)

    def test_write_to_cold_contacts_with_draft_passes(self):
        # cold_contacts is the canonical location, so out of scope.
        v = check(
            "Write",
            {
                "file_path": _cold_contacts_path("contact-a.md"),
                "content": (
                    "## Outbound draft pending review\n\n"
                    "**To:** 담당자\n"
                    "**Channel:** SMS\n\n"
                    "담당자 팀장님,\n"
                ),
            },
        )
        self.assertEqual(len(v), 0)

    def test_edit_new_string_in_omc_blocked(self):
        v = check(
            "Edit",
            {
                "file_path": _omc_path("team-april26/drafts/02-contact-b.md"),
                "old_string": "x",
                "new_string": (
                    "## Outbound draft pending review\n\n"
                    "**To:** partner@vc.example\n"
                    "**Subject:** Re: meeting\n\n"
                    "파트너님,\n"
                ),
            },
        )
        self.assertEqual(len(v), 1)

    def test_multiedit_blocked(self):
        v = check(
            "MultiEdit",
            {
                "file_path": _omc_path("team-april26/drafts/02-contact-b.md"),
                "edits": [
                    {
                        "old_string": "x",
                        "new_string": (
                            "## Outbound draft pending review\n"
                            "**To:** x@y\n**Channel:** Email\nbody"
                        ),
                    },
                ],
            },
        )
        self.assertEqual(len(v), 1)

    def test_edit_clean_passes(self):
        v = check(
            "Edit",
            {
                "file_path": _omc_path("research/01-priorart.md"),
                "old_string": "x",
                "new_string": "## Updated finding\n\nClean prose, no markers.\n",
            },
        )
        self.assertEqual(len(v), 0)


if __name__ == "__main__":
    unittest.main()

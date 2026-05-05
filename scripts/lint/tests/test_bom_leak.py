"""Tests for bom_leak rule."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.bom_leak import _scan, check, PROXIMITY_WINDOW  # noqa: E402

PROJECT_ROOT = ROOT.parent


class TestProximityPattern(unittest.TestCase):
    def test_dollar_then_bom_blocked(self):
        text = "---\n---\n\nOur $16 BOM is competitive."
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].severity, "warn")
        self.assertIn("$16", v[0].message)

    def test_bom_then_dollar_blocked(self):
        text = "---\n---\n\nThe BOM cost is $27 for the module."
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)

    def test_dollar_far_from_bom_passes(self):
        # Build a string where $99 is far from BOM (>200 chars)
        filler = " word" * 80  # ~400 chars
        text = f"---\n---\n\n$99 retail.{filler} The BOM line is empty."
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_dollar_no_bom_passes(self):
        text = "---\n---\n\n$99 retail price for MyProduct."
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_bom_no_dollar_passes(self):
        # If 'BOM' appears with no dollar amount nearby, no leak
        text = "---\n---\n\nThe BOM is being audited."
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_lowercase_bom_blocked(self):
        text = "---\n---\n\nour bom at $16 each."
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)


class TestLiteralPhrases(unittest.TestCase):
    def test_commodity_bom_blocked(self):
        text = "---\n---\n\nWe use a commodity BOM strategy."
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)
        self.assertIn("commodity bom", v[0].message.lower())

    def test_budget_parts_blocked(self):
        text = "---\n---\n\nbudget parts make this affordable."
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)

    def test_cheap_parts_blocked(self):
        text = "---\n---\n\nUses cheap parts to hit price."
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)

    def test_capitalization_variants(self):
        text = "---\n---\n\nWe use Commodity BOM throughout."
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)


class TestArchiveSectionExempt(unittest.TestCase):
    """Archive sections (`## Sent`, `## Reply`, `## Follow-up`, etc.) hold
    historical content. BOM mentions there are records, not future risk."""

    def test_bom_in_reply_section_passes(self):
        text = (
            "---\n---\n\nclean preamble.\n\n"
            "## Reply received (2026-04-15)\n\n"
            "Recipient asked about $16 BOM details.\n"
        )
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_bom_in_sent_section_passes(self):
        # `## Sent` is also archive (historical sent message, can't undo)
        text = "---\n---\n\n## Sent\n\nOur $16 BOM is a winner.\n"
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_bom_in_followup_passes(self):
        text = "---\n---\n\n## Followup\n\nThe BOM was $16.\n"
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_bom_in_outbound_draft_blocks(self):
        # `## Outbound draft pending review` is the active draft section,
        # NOT archive. Leaks here are real future risk.
        text = (
            "---\n---\n\n## Outbound draft pending review (LinkedIn, 2026-04-25)\n\n"
            "Pitch: $16 BOM hits the price target.\n"
        )
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)

    def test_bom_in_preamble_blocks(self):
        # Body text before any section header is also scanned (default).
        text = "---\n---\n\nNote to self: $16 BOM target.\n"
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)


class TestFrontmatterExempt(unittest.TestCase):
    def test_bom_in_frontmatter_notes_passes(self):
        # 'notes' may legitimately reference cost internally
        text = (
            "---\nslug: foo\nnotes: \"$16 BOM target hit\"\n"
            "---\n\nclean body.\n"
        )
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True)
        self.assertEqual(len(v), 0)


class TestExceptions(unittest.TestCase):
    def test_lint_disable_marker(self):
        text = "<!-- lint-disable bom-leak -->\n\n$16 BOM all day."
        v = _scan(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestGmailDraft(unittest.TestCase):
    def test_gmail_body_blocked(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {
            "subject": "Pricing",
            "body": "Our BOM cost is $16 each.",
        })
        self.assertEqual(len(v), 1)

    def test_gmail_clean_passes(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {
            "subject": "Pricing",
            "body": "Retail is $99 with volume options.",
        })
        self.assertEqual(len(v), 0)


class TestEditHook(unittest.TestCase):
    def test_edit_blocks_bom_leak(self):
        v = check("Edit", {
            "file_path": str(PROJECT_ROOT / "cold_contacts/foo.md"),
            "old_string": "x",
            "new_string": "---\n---\n\nWe ship BOM at $16 per unit.",
        })
        self.assertEqual(len(v), 1)


if __name__ == "__main__":
    unittest.main()

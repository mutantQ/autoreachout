"""Tests for timezone_conversion rule."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.timezone_conversion import _scan_text, _is_in_scope, check  # noqa: E402


class TestArithmeticPositive(unittest.TestCase):
    def test_cest_kst_off_by_one(self):
        v = _scan_text("Lock 14:00 CEST (= 22:00 KST)", "t.md")
        self.assertEqual(len(v), 1)
        self.assertIn("21:00", v[0].message)
        self.assertIn("22:00", v[0].message)
        self.assertEqual(v[0].severity, "block")

    def test_cest_kst_paren_no_equals(self):
        v = _scan_text("Wed Apr 29 14:00 CEST (22:00 KST)", "t.md")
        self.assertEqual(len(v), 1)

    def test_edt_kst_wrong(self):
        # 10:00 EDT = 23:00 KST (correct), but say 22:00 KST (wrong)
        v = _scan_text("Mon May 4, 10:00 EDT (= 22:00 KST)", "t.md")
        self.assertEqual(len(v), 1)
        self.assertIn("23:00", v[0].message)

    def test_pst_kst_wrong(self):
        # 09:00 PST + 17h = 02:00 KST (next day). Text says 01:00 → wrong.
        v = _scan_text("9:00 PST (= 1:00 KST)", "t.md")
        self.assertEqual(len(v), 1)


class TestArithmeticCorrect(unittest.TestCase):
    def test_correct_cest_kst(self):
        v = _scan_text("Wed Apr 29 14:00 CEST (= 21:00 KST)", "t.md")
        self.assertEqual(len(v), 0)

    def test_correct_range_endpoints_only(self):
        # Only endpoint times have TZ adjacent
        v = _scan_text("Mon May 4, 10:00 to 10:30 CEST (17:00 to 17:30 KST)", "t.md")
        self.assertEqual(len(v), 0)

    def test_correct_range_both_endpoints_tz(self):
        v = _scan_text(
            "10:00 CEST to 10:30 CEST (17:00 KST to 17:30 KST)",
            "t.md",
        )
        self.assertEqual(len(v), 0)

    def test_midnight_wrap(self):
        # 17:00 CEST + 7h = 24:00 = 00:00 KST next day; 17:30 CEST = 00:30 KST
        v = _scan_text("Wed May 6, 17:30 CEST (00:30 KST)", "t.md")
        self.assertEqual(len(v), 0)

    def test_24_00_form_accepted(self):
        v = _scan_text("17:00 CEST (24:00 KST)", "t.md")
        self.assertEqual(len(v), 0)

    def test_correct_edt_kst(self):
        v = _scan_text("10:00 EDT (= 23:00 KST)", "t.md")
        self.assertEqual(len(v), 0)


class TestNoFalsePositive(unittest.TestCase):
    def test_or_listing(self):
        # "or" between is not a conversion
        v = _scan_text("Available 14:00 CEST or 14:00 KST", "t.md")
        self.assertEqual(len(v), 0)

    def test_same_tz_range(self):
        v = _scan_text("From 14:00 CEST to 16:00 CEST", "t.md")
        self.assertEqual(len(v), 0)

    def test_no_separator_skipped(self):
        v = _scan_text("14:00 CEST 22:00 KST done", "t.md")
        self.assertEqual(len(v), 0)

    def test_unknown_tz_skipped(self):
        # CST is ambiguous (US Central -6 vs China +8)
        v = _scan_text("14:00 CST (= 22:00 KST)", "t.md")
        self.assertEqual(len(v), 0)

    def test_two_separate_events_not_paired(self):
        # Sentence boundary breaks the pair
        v = _scan_text(
            "We met at 14:00 CEST on Monday. The other call was at 22:00 KST on Tuesday.",
            "t.md",
        )
        self.assertEqual(len(v), 0)


class TestExemptions(unittest.TestCase):
    def test_lint_disable_marker(self):
        txt = "<!-- lint-disable timezone-conversion -->\n14:00 CEST (= 22:00 KST)"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_yaml_frontmatter_skipped(self):
        txt = (
            "---\n"
            "notes: '14:00 CEST (= 22:00 KST)'\n"
            "---\n"
            "body\n"
        )
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_archive_section_skipped(self):
        txt = (
            "## Sent (email, 2026-04-28)\n"
            "Hello, lock 14:00 CEST (= 22:00 KST).\n"
        )
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_outbound_draft_section_scanned(self):
        txt = (
            "## Outbound draft pending review (2026-04-28)\n"
            "Hello, lock 14:00 CEST (= 22:00 KST).\n"
        )
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 1)


class TestScope(unittest.TestCase):
    PROJECT = ROOT.parent

    def test_cold_contacts_in_scope(self):
        self.assertTrue(_is_in_scope(str(self.PROJECT / "cold_contacts/test.md")))

    def test_vendors_in_scope(self):
        self.assertTrue(_is_in_scope(str(self.PROJECT / "vendors/test.md")))

    def test_drafts_in_scope(self):
        self.assertTrue(_is_in_scope(str(self.PROJECT / "drafts/test.md")))

    def test_scripts_out_of_scope(self):
        self.assertFalse(_is_in_scope(str(self.PROJECT / "scripts/foo.py")))

    def test_skill_md_out_of_scope(self):
        self.assertFalse(
            _is_in_scope(str(self.PROJECT / ".claude/skills/outreach-email/SKILL.md"))
        )


class TestEditHook(unittest.TestCase):
    def test_edit_new_string_blocked(self):
        v = check(
            "Edit",
            {
                "file_path": str(
                    Path(__file__).resolve().parents[2].parent
                    / "cold_contacts/contact-c.md"
                ),
                "old_string": "x",
                "new_string": "Lock Wed Apr 29 14:00 CEST (= 22:00 KST) for our call",
            },
        )
        self.assertEqual(len(v), 1)

    def test_edit_clean_passes(self):
        v = check(
            "Edit",
            {
                "file_path": str(
                    Path(__file__).resolve().parents[2].parent
                    / "cold_contacts/contact-c.md"
                ),
                "old_string": "x",
                "new_string": "Lock Wed Apr 29 14:00 CEST (= 21:00 KST) for our call",
            },
        )
        self.assertEqual(len(v), 0)


class TestGmailHook(unittest.TestCase):
    def test_gmail_draft_body_checked(self):
        v = check(
            "mcp__claude_ai_Gmail__create_draft",
            {"body": "Locking 14:00 CEST (= 22:00 KST) for our call."},
        )
        self.assertEqual(len(v), 1)
        self.assertIn("21:00", v[0].message)

    def test_gmail_draft_correct_passes(self):
        v = check(
            "mcp__claude_ai_Gmail__create_draft",
            {"body": "Locking 14:00 CEST (= 21:00 KST) for our call."},
        )
        self.assertEqual(len(v), 0)


if __name__ == "__main__":
    unittest.main()

"""Tests for body_headings rule."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.body_headings import _scan_text, _is_in_scope, check  # noqa: E402


class TestHeadingScan(unittest.TestCase):
    def test_h4_triggers(self):
        v = _scan_text("#### 1. OEM 라인업 evidence", "t.md")
        self.assertEqual(len(v), 1)
        self.assertIn("level-4", v[0].message)

    def test_h5_triggers(self):
        v = _scan_text("##### deeper", "t.md")
        self.assertEqual(len(v), 1)
        self.assertIn("level-5", v[0].message)

    def test_h6_triggers(self):
        v = _scan_text("###### deepest", "t.md")
        self.assertEqual(len(v), 1)
        self.assertIn("level-6", v[0].message)

    def test_h1_allowed(self):
        v = _scan_text("# Top-level title", "t.md")
        self.assertEqual(len(v), 0)

    def test_h2_allowed(self):
        v = _scan_text("## Sent (2026-04-26)", "t.md")
        self.assertEqual(len(v), 0)

    def test_h3_allowed(self):
        v = _scan_text("### Body", "t.md")
        self.assertEqual(len(v), 0)

    def test_no_space_after_hashes_allowed(self):
        # Not a heading without a trailing space; could be `####foo` text.
        v = _scan_text("####foo", "t.md")
        self.assertEqual(len(v), 0)

    def test_bare_four_hashes_allowed(self):
        # `####` alone (no space, no trailing content) is not a heading.
        v = _scan_text("####", "t.md")
        self.assertEqual(len(v), 0)

    def test_lint_disable_marker(self):
        txt = "<!-- lint-disable body-headings -->\n#### should not trigger"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_yaml_frontmatter_skipped(self):
        # `####` inside frontmatter (unusual but possible) should not trigger.
        txt = "---\nslug: test\nnote: '#### inside frontmatter'\n---\nclean body"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_multiple_violations_separately_reported(self):
        txt = "#### one\nbody\n#### two\nmore\n##### three"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 3)
        self.assertEqual(v[0].line, 1)
        self.assertEqual(v[1].line, 3)
        self.assertEqual(v[2].line, 5)


class TestScope(unittest.TestCase):
    PROJECT = ROOT.parent

    def test_cold_contacts_in_scope(self):
        self.assertTrue(_is_in_scope(str(self.PROJECT / "cold_contacts/test.md")))

    def test_vendors_in_scope(self):
        self.assertTrue(_is_in_scope(str(self.PROJECT / "vendors/test.md")))

    def test_scripts_out_of_scope(self):
        self.assertFalse(_is_in_scope(str(self.PROJECT / "scripts/foo.py")))

    def test_dotclaude_out_of_scope(self):
        self.assertFalse(
            _is_in_scope(str(self.PROJECT / ".claude/skills/contact-manager/SKILL.md"))
        )

    def test_drafts_out_of_scope(self):
        self.assertFalse(_is_in_scope(str(self.PROJECT / "drafts/test.md")))

    def test_omc_out_of_scope(self):
        self.assertFalse(_is_in_scope(str(self.PROJECT / ".omc/notepad.md")))


class TestEditHook(unittest.TestCase):
    PROJECT = ROOT.parent

    def test_edit_new_string_checked(self):
        v = check(
            "Edit",
            {
                "file_path": str(self.PROJECT / "cold_contacts/contact-a.md"),
                "old_string": "x",
                "new_string": "#### 1. OEM 라인업 evidence",
            },
        )
        self.assertEqual(len(v), 1)

    def test_write_content_checked(self):
        v = check(
            "Write",
            {
                "file_path": str(self.PROJECT / "vendors/vendor-a.md"),
                "content": "## Sent\n#### bad heading\nbody",
            },
        )
        self.assertEqual(len(v), 1)

    def test_edit_clean_passes(self):
        v = check(
            "Edit",
            {
                "file_path": str(self.PROJECT / "cold_contacts/contact-a.md"),
                "old_string": "x",
                "new_string": "**1. OEM 라인업 evidence** — bold inline is fine.",
            },
        )
        self.assertEqual(len(v), 0)


if __name__ == "__main__":
    unittest.main()

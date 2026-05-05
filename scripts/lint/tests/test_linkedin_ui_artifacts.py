"""Tests for linkedin_ui_artifacts rule."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.linkedin_ui_artifacts import _scan_text, _is_in_scope, check  # noqa: E402


class TestInlineTrio(unittest.TestCase):
    def test_bare_trio_blocked(self):
        v = _scan_text("User: \U0001F44F \U0001F44D \U0001F60A (sent at 9:42)", "t.md")
        self.assertEqual(len(v), 1)
        self.assertIn("picker", v[0].message)

    def test_trio_with_reactions_label_blocked(self):
        v = _scan_text(
            "**Recipient 9:42 PM:** \U0001F44F \U0001F44D \U0001F60A "
            "*(LinkedIn reactions, no text)*",
            "t.md",
        )
        self.assertEqual(len(v), 1)

    def test_trio_with_picker_keyword_allowed(self):
        v = _scan_text(
            "(LinkedIn \U0001F44F \U0001F44D \U0001F60A picker buttons preceded the message)",
            "t.md",
        )
        self.assertEqual(len(v), 0)

    def test_trio_with_artifact_keyword_allowed(self):
        v = _scan_text(
            "\U0001F44F \U0001F44D \U0001F60A , UI artifact, not content.",
            "t.md",
        )
        self.assertEqual(len(v), 0)

    def test_trio_with_not_reactions_keyword_allowed(self):
        v = _scan_text(
            "Note: \U0001F44F \U0001F44D \U0001F60A are not reactions.",
            "t.md",
        )
        self.assertEqual(len(v), 0)

    def test_two_emojis_only_allowed(self):
        v = _scan_text("User: \U0001F44F \U0001F44D sent now", "t.md")
        self.assertEqual(len(v), 0)

    def test_single_real_reaction_allowed(self):
        v = _scan_text("User reacted with \U0001F44D (no text)", "t.md")
        self.assertEqual(len(v), 0)


class TestStackedSolos(unittest.TestCase):
    def test_three_consecutive_solo_lines_blocked(self):
        txt = "Header\n\n\U0001F44F\n\U0001F44D\n\U0001F60A\n\nbody"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 1)
        self.assertIn("stacked", v[0].message)

    def test_three_with_blockquote_prefix_blocked(self):
        txt = "Header\n\n> \U0001F44F\n> \U0001F44D\n> \U0001F60A\n\nbody"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 1)

    def test_two_consecutive_solo_lines_allowed(self):
        txt = "Header\n\n\U0001F44F\n\U0001F44D\n\nbody"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_three_same_emoji_allowed(self):
        # Three real reactions of the same emoji is unusual but not picker
        txt = "Header\n\n\U0001F44D\n\U0001F44D\n\U0001F44D\n\nbody"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_solo_emoji_with_text_lines_between_allowed(self):
        # Picker is contiguous; if text lines break the streak, no violation
        txt = "Header\n\nUser: \U0001F44F\nReplied: yes\n\U0001F60A\n\nbody"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)


class TestExceptions(unittest.TestCase):
    def test_lint_disable_marker(self):
        txt = "<!-- lint-disable linkedin-ui-artifacts -->\n\U0001F44F \U0001F44D \U0001F60A"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_yaml_frontmatter_skipped(self):
        txt = "---\nfoo: \U0001F44F \U0001F44D \U0001F60A\n---\nclean body"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)


class TestScope(unittest.TestCase):
    PROJECT = ROOT.parent

    def test_cold_contacts_in_scope(self):
        self.assertTrue(_is_in_scope(str(self.PROJECT / "cold_contacts/test.md")))

    def test_drafts_in_scope(self):
        self.assertTrue(_is_in_scope(str(self.PROJECT / "drafts/test.md")))

    def test_scripts_out_of_scope(self):
        self.assertFalse(_is_in_scope(str(self.PROJECT / "scripts/foo.py")))

    def test_skill_md_out_of_scope(self):
        self.assertFalse(
            _is_in_scope(str(self.PROJECT / ".claude/skills/contact-manager/SKILL.md"))
        )


class TestEditHook(unittest.TestCase):
    def test_edit_new_string_checked(self):
        v = check(
            "Edit",
            {
                "file_path": str(
                    Path(__file__).resolve().parents[2].parent
                    / "cold_contacts/contact-b.md"
                ),
                "old_string": "x",
                "new_string": "User: \U0001F44F \U0001F44D \U0001F60A sent",
            },
        )
        self.assertEqual(len(v), 1)

    def test_edit_clean_passes(self):
        v = check(
            "Edit",
            {
                "file_path": str(
                    Path(__file__).resolve().parents[2].parent
                    / "cold_contacts/contact-b.md"
                ),
                "old_string": "x",
                "new_string": "User reacted with \U0001F44D (no text)",
            },
        )
        self.assertEqual(len(v), 0)


if __name__ == "__main__":
    unittest.main()

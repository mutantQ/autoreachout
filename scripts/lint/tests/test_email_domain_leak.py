"""Tests for email_domain_leak rule.

These tests assume the default config values shipped in
``scripts/lint/_config.py`` (FORBIDDEN_EMAIL = "founder@university.edu",
FOUNDER_EMAIL = "founder@example.com"). If you change those values for
your project, update the test fixtures here to match.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.email_domain_leak import _scan_text, _is_in_scope, check  # noqa: E402

PROJECT_ROOT = ROOT.parent

FORBIDDEN = "founder@university.edu"
ALLOWED = "founder@example.com"


class TestBodyDetection(unittest.TestCase):
    def test_leak_in_body_blocked(self):
        text = f"---\nslug: foo\n---\nHi there, contact me at {FORBIDDEN}."
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].severity, "block")

    def test_uppercase_blocked(self):
        text = f"---\n---\nMail {FORBIDDEN.upper()} back."
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)

    def test_allowed_address_passes(self):
        text = f"---\n---\nWrite to {ALLOWED} instead."
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_other_university_address_passes(self):
        # Only the specific FORBIDDEN address should match. A different
        # local-part at the same domain should not trigger.
        text = "---\n---\nProf email: someone-else@university.edu"
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestFrontmatterExempt(unittest.TestCase):
    def test_frontmatter_email_field_passes(self):
        # Recipients in frontmatter ``email:`` may have ANY address.
        text = f"---\nemail: {FORBIDDEN}\n---\nclean body"
        v = _scan_text(text, "cold_contacts/foo.md", skip_frontmatter=True)
        self.assertEqual(len(v), 0)

    def test_body_after_frontmatter_still_blocks(self):
        text = (
            "---\nemail: ok@x.com\n---\n"
            f"Send to {FORBIDDEN}"
        )
        v = _scan_text(text, "cold_contacts/foo.md", skip_frontmatter=True)
        self.assertEqual(len(v), 1)


class TestExceptions(unittest.TestCase):
    def test_lint_disable_marker(self):
        text = f"<!-- lint-disable email-domain-leak -->\n{FORBIDDEN}"
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestScope(unittest.TestCase):
    def test_cold_contacts_in_scope(self):
        self.assertTrue(_is_in_scope(str(PROJECT_ROOT / "cold_contacts/x.md")))

    def test_vendors_out_of_scope(self):
        # vendors/ excluded by design (vendor email metadata is legit)
        self.assertFalse(_is_in_scope(str(PROJECT_ROOT / "vendors/x.md")))

    def test_drafts_in_scope(self):
        self.assertTrue(_is_in_scope(str(PROJECT_ROOT / "drafts/x.md")))

    def test_scripts_out_of_scope(self):
        self.assertFalse(_is_in_scope(str(PROJECT_ROOT / "scripts/foo.py")))

    def test_skill_out_of_scope(self):
        self.assertFalse(
            _is_in_scope(str(PROJECT_ROOT / ".claude/skills/foo/SKILL.md"))
        )


class TestGmailDraft(unittest.TestCase):
    def test_gmail_body_blocked(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {
            "subject": "Hi",
            "body": f"Best,\nFounder ({FORBIDDEN})",
        })
        self.assertEqual(len(v), 1)

    def test_gmail_subject_blocked(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {
            "subject": f"from {FORBIDDEN}",
            "body": "clean",
        })
        self.assertEqual(len(v), 1)

    def test_gmail_clean_passes(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {
            "subject": "Hi",
            "body": f"Best,\nFounder {ALLOWED}",
        })
        self.assertEqual(len(v), 0)


class TestEditHook(unittest.TestCase):
    def test_edit_new_string_blocked(self):
        v = check("Edit", {
            "file_path": str(PROJECT_ROOT / "cold_contacts/foo.md"),
            "old_string": "x",
            "new_string": f"---\n---\nReply to {FORBIDDEN}",
        })
        self.assertEqual(len(v), 1)


if __name__ == "__main__":
    unittest.main()

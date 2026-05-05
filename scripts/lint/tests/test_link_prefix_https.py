"""Tests for link_prefix_https rule.

Tests use the default KNOWN_DOMAINS shipped in
``scripts/lint/_config.py`` (``example.com``, ``demo.example.org``).
Update fixtures here if you change the default for your project.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.link_prefix_https import _scan_text, check  # noqa: E402

PROJECT_ROOT = ROOT.parent

DOMAIN_A = "example.com"
DOMAIN_B = "demo.example.org"


class TestBareDomains(unittest.TestCase):
    def test_bare_domain_warned(self):
        text = f"---\n---\nVisit {DOMAIN_A} to learn more."
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].severity, "warn")
        self.assertIn(DOMAIN_A, v[0].message)

    def test_https_prefix_passes(self):
        text = f"---\n---\nVisit https://{DOMAIN_A} to learn more."
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_http_prefix_passes(self):
        text = f"---\n---\nLegacy http://{DOMAIN_A}"
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_second_known_domain_warned(self):
        text = f"---\n---\nDemo: {DOMAIN_B}/abc123"
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)


class TestEmailDomainsExempt(unittest.TestCase):
    def test_email_address_passes(self):
        # `founder@example.com` should NOT trigger; the @-prefix tells the
        # rule the match is inside an email, not a bare URL.
        text = f"---\n---\nWrite to founder@{DOMAIN_A} if interested."
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestMultipleMatches(unittest.TestCase):
    def test_two_bare_domains_one_line(self):
        text = f"---\n---\nSee {DOMAIN_A} and {DOMAIN_B}/abc."
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 2)

    def test_one_bare_one_prefixed(self):
        text = f"---\n---\nMain: https://{DOMAIN_A} and demo at {DOMAIN_B}/abc."
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)


class TestUnknownDomains(unittest.TestCase):
    def test_other_bare_domain_passes(self):
        # Only configured project domains are flagged.
        text = "---\n---\nSee linkedin.com or wikipedia.org."
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestFrontmatterExempt(unittest.TestCase):
    def test_frontmatter_url_passes(self):
        # ``linkedin:`` in frontmatter often has bare URLs as part of profile link
        text = "---\nlinkedin: https://www.linkedin.com/in/foo\n---\nclean"
        v = _scan_text(text, "cold_contacts/foo.md", skip_frontmatter=True)
        self.assertEqual(len(v), 0)

    def test_frontmatter_with_bare_known_domain_passes(self):
        # Even bare domain in frontmatter is exempt (e.g., ``website:`` field).
        text = f"---\nwebsite: {DOMAIN_A}\n---\nclean body"
        v = _scan_text(text, "cold_contacts/foo.md", skip_frontmatter=True)
        self.assertEqual(len(v), 0)


class TestExceptions(unittest.TestCase):
    def test_lint_disable_marker(self):
        text = f"<!-- lint-disable link-prefix-https -->\n{DOMAIN_A}"
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestGmailDraft(unittest.TestCase):
    def test_gmail_body_warned(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {
            "subject": "Hi",
            "body": f"Visit {DOMAIN_A} for details.",
        })
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].severity, "warn")

    def test_gmail_clean_passes(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {
            "subject": "Hi",
            "body": f"Visit https://{DOMAIN_A} for details.",
        })
        self.assertEqual(len(v), 0)


class TestEditHook(unittest.TestCase):
    def test_edit_warned_not_blocked(self):
        v = check("Edit", {
            "file_path": str(PROJECT_ROOT / "cold_contacts/foo.md"),
            "old_string": "x",
            "new_string": f"---\n---\nSee {DOMAIN_A} for details.",
        })
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].severity, "warn")


if __name__ == "__main__":
    unittest.main()

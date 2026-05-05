"""Tests for vc_nda rule."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.vc_nda import _scan, _is_investor_contact, check  # noqa: E402

PROJECT_ROOT = ROOT.parent


def _investor_doc(body: str) -> str:
    return (
        "---\nslug: foo\nname: Foo\nvertical: investor\n"
        "tags: [investor, vc]\n---\n\n" + body
    )


def _non_investor_doc(body: str) -> str:
    return (
        "---\nslug: foo\nname: Foo\nvertical: forensic\n"
        "tags: [legal]\n---\n\n" + body
    )


class TestInvestorGate(unittest.TestCase):
    def test_nda_to_investor_blocked(self):
        text = _investor_doc("Hi, want to discuss under NDA before we share details.")
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].severity, "block")

    def test_nda_to_non_investor_passes(self):
        text = _non_investor_doc("Standard NDA process applies for forensic engagements.")
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 0)

    def test_tags_only_investor_blocks(self):
        text = (
            "---\nslug: foo\nvertical: other\ntags: [angel]\n---\n\n"
            "Sign an NDA first."
        )
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 1)


class TestNegation(unittest.TestCase):
    def test_no_nda_passes(self):
        text = _investor_doc("Don't worry, no NDA needed before our chat.")
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 0)

    def test_without_nda_passes(self):
        text = _investor_doc("Happy to share the deck without NDA up front.")
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 0)

    def test_no_need_for_nda_passes(self):
        text = _investor_doc("There's no need for an NDA at this stage.")
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 0)

    def test_korean_negation_passes(self):
        text = _investor_doc("NDA가 필요 없습니다. 편하게 검토하세요.")
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 0)

    def test_nda_eopsi_negation_passes(self):
        text = _investor_doc("NDA 없이 자료 공유 드립니다.")
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 0)

    def test_negation_far_away_doesnt_count(self):
        # Negation is too far from the match; doesn't apply
        body = "We will sign an NDA. " + ("filler. " * 50) + "By the way, no need."
        text = _investor_doc(body)
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 1)


class TestKoreanTerms(unittest.TestCase):
    def test_korean_nda_blocked(self):
        text = _investor_doc("비밀유지 계약 후에 자료 공유 가능합니다.")
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 1)

    def test_korean_nondisclosure_blocked(self):
        text = _investor_doc("비공개협약 체결 후 진행하시죠.")
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 1)

    def test_non_disclosure_english_blocked(self):
        text = _investor_doc("Need to set up a non-disclosure agreement first.")
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 1)


class TestReplyExempt(unittest.TestCase):
    def test_nda_in_reply_passes(self):
        # Recipient may have mentioned NDA in their reply; preserve verbatim
        text = _investor_doc(
            "## Sent\n\nclean.\n\n## Reply received\n\nWe always require NDA.\n"
        )
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 0)


class TestExceptions(unittest.TestCase):
    def test_lint_disable_marker(self):
        text = "<!-- lint-disable vc-nda -->\n" + _investor_doc("Sign an NDA please.")
        v = _scan(text, "cold_contacts/foo.md", skip_frontmatter=True, gate_on_investor=True)
        self.assertEqual(len(v), 0)


class TestInvestorDetection(unittest.TestCase):
    def test_vertical_investor_true(self):
        self.assertTrue(_is_investor_contact("---\nvertical: investor\n---"))

    def test_tag_vc_true(self):
        self.assertTrue(_is_investor_contact("---\ntags: [vc]\n---"))

    def test_tag_angel_true(self):
        self.assertTrue(_is_investor_contact("---\ntags: [angel, deepfake]\n---"))

    def test_no_investor_signal_false(self):
        self.assertFalse(_is_investor_contact("---\nvertical: forensic\ntags: [legal]\n---"))

    def test_malformed_yaml_false(self):
        self.assertFalse(_is_investor_contact("not yaml at all"))


class TestGmailDraft(unittest.TestCase):
    def test_gmail_body_with_nda_blocked(self):
        # Gmail drafts are scanned regardless of recipient class (conservative)
        v = check("mcp__claude_ai_Gmail__create_draft", {
            "subject": "Hi",
            "body": "Let's sign an NDA before our call.",
        })
        self.assertEqual(len(v), 1)

    def test_gmail_negated_passes(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {
            "subject": "Hi",
            "body": "No NDA needed for this introductory chat.",
        })
        self.assertEqual(len(v), 0)


class TestEditHook(unittest.TestCase):
    def test_edit_investor_with_nda_blocks(self):
        v = check("Edit", {
            "file_path": str(PROJECT_ROOT / "cold_contacts/foo.md"),
            "old_string": "x",
            "new_string": _investor_doc("Sign the NDA before we share."),
        })
        self.assertEqual(len(v), 1)

    def test_edit_non_investor_with_nda_passes(self):
        v = check("Edit", {
            "file_path": str(PROJECT_ROOT / "cold_contacts/foo.md"),
            "old_string": "x",
            "new_string": _non_investor_doc("Standard NDA applies for forensic eval."),
        })
        self.assertEqual(len(v), 0)


if __name__ == "__main__":
    unittest.main()

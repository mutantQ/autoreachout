"""Tests for em_dash rule."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.em_dash import _scan_text, _is_in_scope, check  # noqa: E402


class TestEmDashScan(unittest.TestCase):
    def test_em_dash_detected(self):
        v = _scan_text("hello — world", "t.md")
        self.assertEqual(len(v), 1)
        self.assertIn("em-dash", v[0].message)

    def test_en_dash_detected(self):
        v = _scan_text("range 2–4 weeks", "t.md")
        self.assertEqual(len(v), 1)
        self.assertIn("en-dash", v[0].message)

    def test_double_hyphen_detected(self):
        v = _scan_text("hello -- world", "t.md")
        self.assertEqual(len(v), 1)
        self.assertIn("double-hyphen", v[0].message)

    def test_clean_text_passes(self):
        v = _scan_text("clean korean 텍스트, 범위 2~4주, 정상 문장.", "t.md")
        self.assertEqual(len(v), 0)

    def test_single_hyphen_allowed(self):
        v = _scan_text("hyphen-word is fine", "t.md")
        self.assertEqual(len(v), 0)

    def test_markdown_horizontal_rule_allowed(self):
        txt = "paragraph\n\n---\n\nnext paragraph"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_yaml_frontmatter_delimiters_allowed(self):
        txt = "---\nslug: test\nvalue: ok\n---\nbody text"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_blockquote_skipped(self):
        txt = "> External said — like this."
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_lint_disable_marker(self):
        txt = "<!-- lint-disable em-dash -->\nhas — everywhere – and -- here"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_multiple_violations_counted(self):
        txt = "line one — a\nline two – b\nline three -- c"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 3)

    def test_html_comment_em_dash_disable_marker_passes(self):
        # The rule's own marker should not self-trigger via its `--` delimiters.
        # (Distinct from the file-level disable: this is a marker mid-body
        # that happens to live inside an HTML comment.)
        txt = "body line\n<!-- lint-disable em-dash -->\nmore body"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_html_comment_other_rule_disable_marker_passes(self):
        # Other rules' lint-disable markers contain `--` from delimiters AND
        # may contain `-` chars in the rule name (`connection-note-length`).
        txt = "body\n<!-- lint-disable connection-note-length -->\nmore"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_stacked_html_comment_markers_pass(self):
        txt = (
            "body\n"
            "<!-- lint-disable em-dash -->\n"
            "<!-- lint-disable connection-note-length -->\n"
            "more body"
        )
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_em_dash_inside_html_comment_passes(self):
        txt = "before\n<!-- TODO — fix this later -->\nafter"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_inline_html_comment_passes(self):
        txt = "Body before <!-- comment with -- inside --> body after."
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 0)

    def test_em_dash_outside_comment_still_triggers(self):
        # Critical negative test: real prose em-dash must still fire even
        # when HTML comments exist elsewhere in the text.
        txt = "<!-- lint-disable connection-note-length -->\nreal — em-dash here"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 1)
        self.assertIn("em-dash", v[0].message)

    def test_em_dash_inside_and_outside_comment(self):
        # Em-dash inside the comment is exempt; em-dash outside still fires.
        txt = "<!-- inside — exempt -->\noutside — triggers"
        v = _scan_text(txt, "t.md")
        self.assertEqual(len(v), 1)
        self.assertIn("em-dash", v[0].message)
        # Violation should be reported on line 2, the outside line.
        self.assertEqual(v[0].line, 2)


class TestScope(unittest.TestCase):
    # ROOT = scripts/, ROOT.parent = repo root (the PROJECT_ROOT)
    PROJECT = ROOT.parent
    REPO = ROOT.parent.parent

    def test_cold_contacts_in_scope(self):
        self.assertTrue(_is_in_scope(str(self.PROJECT / "cold_contacts/test.md")))

    def test_drafts_in_scope(self):
        self.assertTrue(_is_in_scope(str(self.PROJECT / "drafts/test.md")))

    def test_report_in_scope(self):
        self.assertTrue(_is_in_scope(str(self.PROJECT / "reports/OUTREACH_REPORT.md")))

    def test_scripts_out_of_scope(self):
        self.assertFalse(_is_in_scope(str(self.PROJECT / "scripts/foo.py")))

    def test_legal_out_of_scope(self):
        self.assertFalse(_is_in_scope(str(self.REPO / "legal/memo.md")))


class TestGmailHook(unittest.TestCase):
    def test_gmail_body_checked(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {"body": "has — em-dash", "subject": "ok"})
        self.assertEqual(len(v), 1)

    def test_gmail_subject_checked(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {"body": "clean", "subject": "has — here"})
        self.assertEqual(len(v), 1)

    def test_gmail_clean_passes(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {"body": "clean body", "subject": "clean subject"})
        self.assertEqual(len(v), 0)


if __name__ == "__main__":
    unittest.main()

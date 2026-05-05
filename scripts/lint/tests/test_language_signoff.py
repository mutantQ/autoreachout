"""Tests for language_signoff rule."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.language_signoff import _scan_text, _is_in_scope, _hangul_ratio, check  # noqa: E402

PROJECT_ROOT = ROOT.parent


def _draft(body: str) -> str:
    return f"---\nslug: foo\n---\n\n## Outbound draft pending review (LinkedIn, 2026-04-25)\n\n{body}\n"


class TestKoreanBodyEnglishSignoff(unittest.TestCase):
    def test_korean_body_with_co_founder_blocked(self):
        body = (
            "안녕하세요, 모니터입니다.\n"
            "하드웨어 보안 카메라 모듈을 만들고 있습니다.\n"
            "검토 부탁드립니다.\n\n"
            "Founder\n"
            "Co-founder & CEO, MyCo\n"
        )
        v = _scan_text(_draft(body), "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].severity, "block")
        self.assertIn("Hangul", v[0].message)

    def test_korean_body_with_ceo_blocked(self):
        body = "안녕하세요, 검토 부탁드립니다.\n\nFounder\nCEO, MyCo\n"
        v = _scan_text(_draft(body), "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)

    def test_korean_body_with_founder_blocked(self):
        body = "안녕하세요. 짧은 메시지입니다.\n\nFounder\nMyCo\n"
        v = _scan_text(_draft(body), "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)


class TestKoreanBodyKoreanSignoff(unittest.TestCase):
    def test_korean_body_with_drim_passes(self):
        body = (
            "안녕하세요. 하드웨어 보안 카메라를 만들고 있습니다.\n\n"
            "대표 드림\n"
        )
        v = _scan_text(_draft(body), "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_korean_body_with_olim_passes(self):
        body = "안녕하세요. 짧은 메시지입니다.\n\n대표 올림\n"
        v = _scan_text(_draft(body), "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_korean_body_with_kamsahapnida_passes(self):
        body = "안녕하세요.\n검토 부탁드립니다.\n감사합니다.\n대표\n"
        v = _scan_text(_draft(body), "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestEnglishBody(unittest.TestCase):
    def test_english_body_with_english_signoff_passes(self):
        body = (
            "Hi, I'm building a hardware-signed camera module.\n"
            "Curious if relevant.\n\n"
            "Founder\nCo-founder & CEO, MyCo\n"
        )
        v = _scan_text(_draft(body), "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_english_body_with_drim_blocked(self):
        # Pure English body with Korean closer = mistake
        body = (
            "Hi, I'm building a hardware-signed camera module.\n"
            "Curious if relevant.\n\n"
            "대표 드림\n"
        )
        v = _scan_text(_draft(body), "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)


class TestBilingualOK(unittest.TestCase):
    def test_korean_body_with_drim_only_passes(self):
        # Common pattern: Korean body + 대표 드림 alone (no English role marker)
        body = "안녕하세요. 짧은 메시지입니다.\n\n대표 드림\nfounder@example.com\n"
        v = _scan_text(_draft(body), "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_korean_body_with_just_name_line_passes(self):
        # Korean body + plain "Founder" line (not a role marker, just a name)
        body = "안녕하세요. 검토 부탁드립니다.\n\nFounder\nMyCo\nfounder@example.com\n"
        v = _scan_text(_draft(body), "cold_contacts/foo.md")
        # This passes because no English role marker (CEO/Founder/etc.)
        self.assertEqual(len(v), 0)


class TestArchiveExempt(unittest.TestCase):
    def test_archive_section_skipped(self):
        # Historical sent message with mismatched signoff - already happened, don't flag
        text = (
            "---\n---\n\n"
            "## Sent (LinkedIn, 2026-02-19)\n\n"
            "안녕하세요. 검토 부탁드립니다.\n\nFounder\nCo-founder & CEO, MyCo\n"
        )
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_reply_section_skipped(self):
        text = (
            "---\n---\n\n"
            "## Reply received (2026-04-15)\n\n"
            "감사합니다.\nRecipient\nCo-founder, OtherCo\n"
        )
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestExceptions(unittest.TestCase):
    def test_lint_disable_marker(self):
        text = (
            "<!-- lint-disable language-signoff -->\n"
            "## Outbound draft pending review (LinkedIn, 2026-04-25)\n\n"
            "안녕하세요.\n\nFounder\nCEO, MyCo\n"
        )
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestNoDraftSection(unittest.TestCase):
    def test_pure_body_no_section_skipped(self):
        # No `## Outbound draft pending review` heading -> no scan
        text = "---\n---\n\n안녕하세요.\n\nFounder\nCEO, MyCo\n"
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestHangulRatio(unittest.TestCase):
    def test_pure_korean(self):
        self.assertGreater(_hangul_ratio("안녕하세요 반갑습니다"), 0.9)

    def test_pure_english(self):
        self.assertEqual(_hangul_ratio("Hello world"), 0.0)

    def test_mixed_50_50(self):
        # 5 Hangul + 5 Latin = 0.5
        ratio = _hangul_ratio("안녕하세요hello")
        self.assertAlmostEqual(ratio, 0.5, places=1)

    def test_empty(self):
        self.assertEqual(_hangul_ratio(""), 0.0)

    def test_punctuation_only(self):
        # Punctuation doesn't count toward either; ratio should be 0
        self.assertEqual(_hangul_ratio("... ,, !"), 0.0)


class TestScope(unittest.TestCase):
    def test_cold_contacts_in_scope(self):
        self.assertTrue(_is_in_scope(str(PROJECT_ROOT / "cold_contacts/x.md")))

    def test_drafts_in_scope(self):
        self.assertTrue(_is_in_scope(str(PROJECT_ROOT / "drafts/x.md")))

    def test_vendors_out_of_scope(self):
        self.assertFalse(_is_in_scope(str(PROJECT_ROOT / "vendors/x.md")))

    def test_skill_out_of_scope(self):
        self.assertFalse(
            _is_in_scope(str(PROJECT_ROOT / ".claude/skills/foo/SKILL.md"))
        )


class TestEditHook(unittest.TestCase):
    def test_edit_korean_body_english_signoff_blocks(self):
        body = "안녕하세요. 검토 부탁드립니다.\n\nFounder\nCo-founder & CEO, MyCo\n"
        v = check("Edit", {
            "file_path": str(PROJECT_ROOT / "cold_contacts/foo.md"),
            "old_string": "x",
            "new_string": _draft(body),
        })
        self.assertEqual(len(v), 1)

    def test_edit_korean_body_korean_signoff_passes(self):
        body = "안녕하세요. 검토 부탁드립니다.\n\n대표 드림\n"
        v = check("Edit", {
            "file_path": str(PROJECT_ROOT / "cold_contacts/foo.md"),
            "old_string": "x",
            "new_string": _draft(body),
        })
        self.assertEqual(len(v), 0)


class TestGmailDraft(unittest.TestCase):
    def test_gmail_korean_body_english_signoff_blocks(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {
            "subject": "Hi",
            "body": "안녕하세요. 검토 부탁드립니다.\n\nFounder\nCo-founder & CEO, MyCo",
        })
        self.assertEqual(len(v), 1)

    def test_gmail_clean_passes(self):
        v = check("mcp__claude_ai_Gmail__create_draft", {
            "subject": "Hi",
            "body": "Hi, building a hardware-signed camera. Curious if relevant.\n\nFounder\nMyCo",
        })
        self.assertEqual(len(v), 0)


if __name__ == "__main__":
    unittest.main()

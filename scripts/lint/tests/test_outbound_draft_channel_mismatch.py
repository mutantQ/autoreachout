"""Tests for outbound_draft_channel_mismatch rule."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.outbound_draft_channel_mismatch import (  # noqa: E402
    _scan_text,
    _is_in_scope,
    _extract_channel,
    _detect_body_channel,
    check,
)


def _wrap(channel: str | None, section: str) -> str:
    """Build a fake cold_contact .md with optional `channel:` frontmatter."""
    if channel is None:
        return section
    return f"---\nslug: foo\nchannel: {channel}\n---\n\n{section}\n"


class TestFrontmatterSignal(unittest.TestCase):
    def test_kakaotalk_email_blocks_outbound_header(self):
        section = "## Outbound draft pending review: SAFE update\n\nbody text"
        v = _scan_text(_wrap("kakaotalk+email", section), "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)
        self.assertIn("kakaotalk+email", v[0].message)

    def test_email_only_blocks_outbound_header(self):
        section = "## Outbound draft pending review: hello\n\nbody"
        v = _scan_text(_wrap("email", section), "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)

    def test_kakaotalk_only_blocks_outbound_header(self):
        section = "## Outbound draft pending review: msg\n\nbody"
        v = _scan_text(_wrap("kakaotalk", section), "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)

    def test_linkedin_only_passes(self):
        section = "## Outbound draft pending review: connection note\n\n짧은 인사 메시지"
        v = _scan_text(_wrap("linkedin", section), "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_linkedin_email_passes_when_body_clean(self):
        section = "## Outbound draft pending review: connect\n\n짧은 메시지"
        v = _scan_text(_wrap("linkedin+email", section), "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestBodySignal(unittest.TestCase):
    def test_email_indicator_blocks_even_with_linkedin_frontmatter(self):
        section = (
            "## Outbound draft pending review: SAFE update\n\n"
            "**채널:** Email (founder@example.com → partner@vc.example)\n"
            "Body text here."
        )
        v = _scan_text(_wrap("linkedin", section), "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)
        self.assertIn("email", v[0].message.lower())

    def test_kakao_indicator_blocks_even_with_linkedin_frontmatter(self):
        section = (
            "## Outbound draft pending review: kakao msg\n\n"
            "**채널:** KakaoTalk (chat_id 1234567890123)\n"
            "Body."
        )
        v = _scan_text(_wrap("linkedin", section), "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)
        self.assertIn("kakaotalk", v[0].message.lower())

    def test_gmail_thread_indicator_blocks(self):
        section = (
            "## Outbound draft pending review: follow-up\n\n"
            "Reply in Gmail thread 19dbdf9c174e1b30 (subject ...)\n"
            "Body."
        )
        v = _scan_text(_wrap(None, section), "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)

    def test_kakaotalk_chat_id_indicator_blocks(self):
        section = (
            "## Outbound draft pending review: msg\n\n"
            "kakaotalk_chat_id: 12345\n"
            "Body."
        )
        v = _scan_text(_wrap(None, section), "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)

    def test_no_indicator_no_frontmatter_passes(self):
        # Permissive: if neither signal is present, allow it.
        section = "## Outbound draft pending review: msg\n\nshort linkedin-style note"
        v = _scan_text(_wrap(None, section), "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestSectionBoundaries(unittest.TestCase):
    def test_indicator_in_other_section_does_not_trigger(self):
        # An archive section AFTER the Outbound draft section contains
        # `Gmail thread` — should NOT count toward the draft's body.
        text = _wrap(
            "linkedin",
            "## Outbound draft pending review: connection note\n\n"
            "짧은 메시지\n\n"
            "## Email sent (2026-04-24)\n\n"
            "Body. Gmail thread 19dbdf9c.\n",
        )
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_correct_email_header_does_not_trigger(self):
        # `## Email draft pending review` is the right convention; not
        # caught by this rule even with email indicators in body.
        text = _wrap(
            "kakaotalk+email",
            "## Email draft pending review: timeline update\n\n"
            "**채널:** Email\nBody.",
        )
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_kakaotalk_dm_header_does_not_trigger(self):
        text = _wrap(
            "kakaotalk+email",
            "## KakaoTalk DM v2 pending review (2026-04-26)\n\n"
            "**채널:** KakaoTalk (chat_id 1234567890123)\nBody.",
        )
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestExceptions(unittest.TestCase):
    def test_lint_disable_marker_skips(self):
        section = "## Outbound draft pending review: x\n\n**채널:** Email\nbody"
        text = "<!-- lint-disable outbound-draft-channel-mismatch -->\n" + _wrap(
            "kakaotalk+email", section
        )
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_no_channel_in_frontmatter_no_body_signal_passes(self):
        text = "---\nslug: foo\n---\n\n## Outbound draft pending review: x\n\nbody"
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestScope(unittest.TestCase):
    PROJECT = ROOT.parent

    def test_cold_contacts_in_scope(self):
        self.assertTrue(_is_in_scope(str(self.PROJECT / "cold_contacts/test.md")))

    def test_drafts_in_scope(self):
        self.assertTrue(_is_in_scope(str(self.PROJECT / "drafts/test.md")))

    def test_skill_md_out_of_scope(self):
        self.assertFalse(
            _is_in_scope(str(self.PROJECT / ".claude/skills/outreach-email/cold.md"))
        )

    def test_scripts_out_of_scope(self):
        self.assertFalse(_is_in_scope(str(self.PROJECT / "scripts/foo.py")))


class TestHelpers(unittest.TestCase):
    def test_extract_channel_quoted(self):
        lines = ['---', 'channel: "linkedin+email"', '---']
        self.assertEqual(_extract_channel(lines), "linkedin+email")

    def test_extract_channel_unquoted(self):
        lines = ["---", "channel: kakaotalk", "---"]
        self.assertEqual(_extract_channel(lines), "kakaotalk")

    def test_extract_channel_missing(self):
        lines = ["---", "slug: foo", "---"]
        self.assertIsNone(_extract_channel(lines))

    def test_extract_channel_no_frontmatter(self):
        self.assertIsNone(_extract_channel(["body line", "more"]))

    def test_detect_body_email(self):
        self.assertEqual(_detect_body_channel("**채널:** Email"), "email")

    def test_detect_body_kakao(self):
        self.assertEqual(_detect_body_channel("kakaotalk_chat_id: 1"), "kakaotalk")

    def test_detect_body_clean(self):
        self.assertIsNone(_detect_body_channel("just some plain text"))


class TestEditHook(unittest.TestCase):
    PROJECT = ROOT.parent

    def test_edit_with_email_indicator_blocked(self):
        # Edit's new_string contains the bad header + email body indicator.
        # Even without frontmatter visible, body signal catches it.
        v = check(
            "Edit",
            {
                "file_path": str(self.PROJECT / "cold_contacts/sample.md"),
                "old_string": "x",
                "new_string": (
                    "## Outbound draft pending review: 외환 timeline\n\n"
                    "**채널:** Email (founder@example.com → partner@vc.example)\n"
                    "Body."
                ),
            },
        )
        self.assertEqual(len(v), 1)

    def test_edit_with_correct_email_header_passes(self):
        v = check(
            "Edit",
            {
                "file_path": str(self.PROJECT / "cold_contacts/sample.md"),
                "old_string": "x",
                "new_string": (
                    "## Email draft pending review: timeline\n\n"
                    "**채널:** Email\nBody."
                ),
            },
        )
        self.assertEqual(len(v), 0)

    def test_write_full_file_with_kakaotalk_email_frontmatter_blocks(self):
        v = check(
            "Write",
            {
                "file_path": str(self.PROJECT / "cold_contacts/sample.md"),
                "content": _wrap(
                    "kakaotalk+email",
                    "## Outbound draft pending review: SAFE\n\nbody",
                ),
            },
        )
        self.assertEqual(len(v), 1)


if __name__ == "__main__":
    unittest.main()

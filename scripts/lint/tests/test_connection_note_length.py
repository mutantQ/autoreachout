"""Tests for connection_note_length rule."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.connection_note_length import _scan_text, check, LIMIT  # noqa: E402

PROJECT_ROOT = ROOT.parent


def _make_doc(section_header: str, body: str) -> str:
    return f"---\nslug: foo\n---\n\n{section_header}\n\n{body}\n"


class TestSentSection(unittest.TestCase):
    def test_short_note_passes(self):
        body = "Hi Foo, building a hardware-signed camera. Curious if relevant."
        text = _make_doc("## Sent (connection note)", body)
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_exactly_300_chars_passes(self):
        body = "x" * 300
        text = _make_doc("## Sent (connection note)", body)
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_301_chars_blocks(self):
        body = "x" * 301
        text = _make_doc("## Sent (connection note)", body)
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].severity, "block")
        self.assertIn("301", v[0].message)

    def test_350_chars_blocks_with_trim_count(self):
        body = "x" * 350
        text = _make_doc("## Sent (connection note)", body)
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)
        self.assertIn("by 50 chars", v[0].message)


class TestOutboundDraftSection(unittest.TestCase):
    def test_short_draft_passes(self):
        body = "Short pending draft."
        text = _make_doc("## Outbound draft pending review (LinkedIn, 2026-04-25)", body)
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_long_draft_blocks(self):
        body = "y" * 500
        text = _make_doc("## Outbound draft pending review (LinkedIn, 2026-04-25)", body)
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)


class TestSectionScoping(unittest.TestCase):
    def test_long_email_section_passes(self):
        # `## Sent (email to ...)` is NOT a connection note; should not flag
        body = "z" * 5000
        text = _make_doc("## Sent (email to foo@bar, 2026-04-25)", body)
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_reply_section_passes(self):
        body = "z" * 5000
        text = _make_doc("## Reply received (2026-04-15)", body)
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_section_ends_at_next_heading(self):
        # Note section is short; next section is irrelevant
        text = (
            "---\n---\n\n## Sent (connection note)\n\n"
            "short\n\n"
            "## Reply received\n\n"
            + "z" * 5000
            + "\n"
        )
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestMultipleSections(unittest.TestCase):
    def test_two_long_connection_sections_both_flagged(self):
        text = (
            "---\n---\n\n## Sent (connection note)\n\n"
            + "x" * 320 + "\n\n"
            + "## Outbound draft pending review (LinkedIn, 2026-04-25)\n\n"
            + "y" * 350 + "\n"
        )
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 2)


class TestEdgeCases(unittest.TestCase):
    def test_no_relevant_section(self):
        text = "---\n---\n\nJust some body text\n"
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_blank_lines_in_body_dont_inflate_count(self):
        # Body is two short lines separated by a blank — count should be
        # len of joined text including the blank line's newline (2 newlines)
        body = "first line\n\nsecond line"  # 11 + 1 + 1 + 11 = 24 chars
        text = _make_doc("## Sent (connection note)", body)
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_korean_chars_count_as_1_each(self):
        # 100 Korean chars counted; well under 300
        body = "안" * 250
        text = _make_doc("## Sent (connection note)", body)
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)

    def test_korean_chars_over_limit(self):
        body = "안" * 320  # 320 chars
        text = _make_doc("## Sent (connection note)", body)
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 1)


class TestLintDisable(unittest.TestCase):
    def test_marker_skips(self):
        body = "x" * 500
        text = (
            "---\n---\n\n<!-- lint-disable connection-note-length -->\n\n"
            "## Sent (connection note)\n\n" + body + "\n"
        )
        v = _scan_text(text, "cold_contacts/foo.md")
        self.assertEqual(len(v), 0)


class TestEditHook(unittest.TestCase):
    def test_edit_long_note_blocks(self):
        body = "z" * 400
        v = check("Edit", {
            "file_path": str(PROJECT_ROOT / "cold_contacts/foo.md"),
            "old_string": "x",
            "new_string": _make_doc("## Sent (connection note)", body),
        })
        self.assertEqual(len(v), 1)

    def test_edit_short_note_passes(self):
        body = "Short and sweet."
        v = check("Edit", {
            "file_path": str(PROJECT_ROOT / "cold_contacts/foo.md"),
            "old_string": "x",
            "new_string": _make_doc("## Sent (connection note)", body),
        })
        self.assertEqual(len(v), 0)


if __name__ == "__main__":
    unittest.main()

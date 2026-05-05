"""Tests for no_markdown_in_body rule."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.no_markdown_in_body import (  # noqa: E402
    _scan_text,
    _is_in_scope,
    check,
)


PROJECT = Path(__file__).resolve().parents[3]


def _cold(rel: str) -> str:
    return str(PROJECT / "cold_contacts" / rel)


def _vendor(rel: str) -> str:
    return str(PROJECT / "vendors" / rel)


# --- Body-zone POSITIVES (should block) -------------------------------------


class TestBodyZoneBoldStar(unittest.TestCase):
    def test_bold_inside_sent_section_blocks(self):
        text = (
            "## Sent (2026-04-26)\n\n"
            "안녕하세요, **중요한** 메시지입니다.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 1)
        self.assertIn("**중요한**", v[0].message)

    def test_bold_inside_outbound_draft_pending_review_blocks(self):
        text = (
            "## Outbound draft pending review (2026-04-26)\n\n"
            "**To:** kim@example.com\n"
            "**Subject:** test\n\n"
            "### Body\n\n"
            "Hi Kim, this is **bold** text.\n\n"
            "### Acceptance check\n"
        )
        v = _scan_text(text, "vendors/x.md")
        self.assertEqual(len(v), 1)

    def test_bold_underscores_inside_body_blocks(self):
        text = (
            "## Sent (2026-04-26)\n\n"
            "Hello __team__, please review.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 1)
        self.assertIn("__team__", v[0].message)


class TestBodyZoneLinks(unittest.TestCase):
    def test_link_inside_body_blocks(self):
        text = (
            "## Sent (2026-04-26)\n\n"
            "See our blog at [our blog](https://example.com).\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 1)
        self.assertIn("link", v[0].message)


class TestBodyZoneInlineCode(unittest.TestCase):
    def test_backtick_code_inside_body_blocks(self):
        text = (
            "## Sent (2026-04-26)\n\n"
            "Use the `npm install` command first.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 1)
        self.assertIn("inline code", v[0].message)


class TestBodyZoneCodeFence(unittest.TestCase):
    def test_code_fence_inside_body_blocks(self):
        text = (
            "## Sent (2026-04-26)\n\n"
            "Here is sample code:\n"
            "```\n"
            "x = 1\n"
            "```\n"
            "End.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        # Two fence lines (open + close) trigger; inner content skipped.
        self.assertEqual(len(v), 2)
        self.assertTrue(all("code fence" in vio.message for vio in v))


# --- Body-zone NEGATIVES (should NOT block) ---------------------------------


class TestMetaScaffoldingPasses(unittest.TestCase):
    def test_channel_meta_passes(self):
        # **Channel:** appears in the meta block, before body starts.
        text = (
            "## Outbound draft pending review (2026-04-26)\n\n"
            "**To:** kim@example.com\n"
            "**Channel:** linkedin\n"
            "**Subject:** test\n\n"
            "### Body\n\n"
            "Plain prose body.\n"
        )
        v = _scan_text(text, "vendors/x.md")
        self.assertEqual(len(v), 0)

    def test_meta_inside_outbound_section_without_explicit_body_marker(self):
        # No `### Body`; meta block follows the section header directly.
        # The meta lines should be skipped.
        text = (
            "## Sent (2026-04-26)\n\n"
            "**To:** kim@example.com\n"
            "**Channel:** linkedin\n\n"
            "Plain prose with no markdown here.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)

    def test_acceptance_check_section_with_bold_passes(self):
        text = (
            "## Outbound draft pending review (2026-04-26)\n\n"
            "**To:** kim@example.com\n\n"
            "### Body\n\n"
            "Plain body.\n\n"
            "### Acceptance check\n\n"
            "- **must** be under 300 chars\n"
            "- [link to spec](https://x.com) is fine here\n"
        )
        v = _scan_text(text, "vendors/x.md")
        self.assertEqual(len(v), 0)

    def test_reviewer_attention_flags_with_bold_passes(self):
        text = (
            "## Outbound draft pending review (2026-04-26)\n\n"
            "**To:** kim@example.com\n\n"
            "### Body\n\n"
            "Hi Kim.\n\n"
            "### Reviewer attention flags\n\n"
            "- **TODO:** confirm the date\n"
            "- `inline-code` allowed in flags too\n"
        )
        v = _scan_text(text, "vendors/x.md")
        self.assertEqual(len(v), 0)

    def test_why_this_exists_with_bold_passes(self):
        text = (
            "## Outbound draft pending review (2026-04-26)\n\n"
            "### Why this exists\n\n"
            "We need **this** because of context.\n\n"
            "### Body\n\n"
            "Plain body.\n"
        )
        v = _scan_text(text, "vendors/x.md")
        self.assertEqual(len(v), 0)


class TestFrontmatterPasses(unittest.TestCase):
    def test_yaml_frontmatter_with_bold_passes(self):
        text = (
            "---\n"
            "slug: test\n"
            "notes: '**this is yaml not body**'\n"
            "---\n"
            "## Sent (2026-04-26)\n\n"
            "Plain body.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)


class TestFalsePositiveControl(unittest.TestCase):
    def test_single_asterisk_emphasis_does_not_trigger(self):
        # Single * is high-FP (multiplication, footnotes, names).
        text = (
            "## Sent (2026-04-26)\n\n"
            "We had 3 * 4 = 12 results, *not bad*.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)

    def test_horizontal_rule_does_not_trigger(self):
        # `* * *` and `***` separators must not trigger.
        text = (
            "## Sent (2026-04-26)\n\n"
            "Section one.\n\n"
            "* * *\n\n"
            "Section two.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)

    def test_bold_spanning_multiple_lines_does_not_match(self):
        # `**` open on one line, close on another should NOT match
        # (constrained to single line by [^*\n]+).
        text = (
            "## Sent (2026-04-26)\n\n"
            "Open **here\n"
            "and close** there.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)

    def test_outside_body_zone_anything_passes(self):
        # No outbound section header at all.
        text = (
            "# Notes\n\n"
            "Random **bold** prose with [a link](https://x.com).\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)


# --- Annotation-label whitelist (refinement 2026-04-26) ---------------------


class TestAnnotationLabelWhitelist(unittest.TestCase):
    """Lines starting with '**Label:**' are author scaffolding, not body
    content. The bold-check must skip them. Real bold-as-emphasis (no
    colon) must still fire."""

    def test_read_label_passes(self):
        text = (
            "## Sent (2026-04-26)\n\n"
            "Plain prose body.\n\n"
            "**Read:** Recipient understood the ask.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)

    def test_status_label_passes(self):
        text = (
            "## Sent (2026-04-26)\n\n"
            "Plain.\n\n"
            "**Status:** in progress\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)

    def test_action_with_parenthetical_label_passes(self):
        # Parenthetical inside the label name (common pattern).
        text = (
            "## Sent (2026-04-26)\n\n"
            "Plain.\n\n"
            "**Action (Founder):** ship eval unit\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)

    def test_korean_label_passes(self):
        text = (
            "## Sent (2026-04-26)\n\n"
            "본문.\n\n"
            "**경위:** 4/23 미팅에서 합의된 내용 정리.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)

    def test_channel_label_passes(self):
        # Inside body zone (post-meta), Channel-as-label is still ok.
        text = (
            "## Sent (2026-04-26)\n\n"
            "Plain prose body.\n\n"
            "**Channel:** Email\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)

    def test_bold_subheading_no_colon_still_blocks(self):
        # Real bug pattern from a vendor brief: bold-as-subheading.
        text = (
            "## Sent (2026-04-26)\n\n"
            "Plain.\n\n"
            "**(A) On-sensor 음원 분류**\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 1)
        self.assertIn("(A) On-sensor", v[0].message)

    def test_bold_numbered_heading_no_colon_still_blocks(self):
        # Real bug pattern: numbered bold heading without colon.
        text = (
            "## Sent (2026-04-26)\n\n"
            "Plain.\n\n"
            "**1. OEM 라인업 evidence**\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 1)
        self.assertIn("1. OEM", v[0].message)

    def test_bold_emphasis_in_prose_still_blocks(self):
        # Bold-as-emphasis in middle of prose, no colon.
        text = (
            "## Sent (2026-04-26)\n\n"
            "We had a **really important** result.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 1)
        self.assertIn("really important", v[0].message)

    def test_label_with_leading_whitespace_passes(self):
        # Indented label (e.g., inside bullet) still recognized.
        text = (
            "## Sent (2026-04-26)\n\n"
            "Plain.\n\n"
            "  **Status:** value\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)

    def test_label_only_no_value_passes(self):
        # Bare '**Status:**' followed by EOL (no trailing content).
        text = (
            "## Sent (2026-04-26)\n\n"
            "Plain.\n\n"
            "**Status:**\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)

    def test_label_with_inline_link_in_value_still_blocks_link(self):
        # Whitelist scope is JUST the bold-check. Links/code in the
        # value portion still fire.
        text = (
            "## Sent (2026-04-26)\n\n"
            "Plain.\n\n"
            "**Read:** see [link](https://x.com)\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 1)
        self.assertIn("link", v[0].message)


# --- Exemption ---------------------------------------------------------------


class TestExemption(unittest.TestCase):
    def test_lint_disable_marker_exempts_file(self):
        text = (
            "<!-- lint-disable no-markdown-in-body -->\n\n"
            "## Sent (2026-04-26)\n\n"
            "**bold** [link](https://x) `code` __more__ here.\n"
        )
        v = _scan_text(text, "cold_contacts/x.md")
        self.assertEqual(len(v), 0)


# --- Scope -------------------------------------------------------------------


class TestScope(unittest.TestCase):
    def test_cold_contacts_in_scope(self):
        self.assertTrue(_is_in_scope(_cold("test.md")))

    def test_vendors_in_scope(self):
        self.assertTrue(_is_in_scope(_vendor("test.md")))

    def test_scripts_out_of_scope(self):
        self.assertFalse(_is_in_scope(str(PROJECT / "scripts/foo.py")))

    def test_dotclaude_out_of_scope(self):
        self.assertFalse(
            _is_in_scope(str(PROJECT / ".claude/skills/contact-manager/SKILL.md"))
        )

    def test_omc_out_of_scope(self):
        self.assertFalse(_is_in_scope(str(PROJECT / ".omc/notepad.md")))

    def test_drafts_out_of_scope(self):
        # outreach/drafts/ is the legitimate scratch dir per other rules.
        self.assertFalse(_is_in_scope(str(PROJECT / "drafts/test.md")))


# --- Edit/Write hook plumbing -----------------------------------------------


class TestEditHook(unittest.TestCase):
    def test_write_content_with_body_bold_blocks(self):
        v = check(
            "Write",
            {
                "file_path": _vendor("vendor-a.md"),
                "content": (
                    "## Outbound draft pending review (2026-04-26)\n\n"
                    "**To:** contact@vendor-a.example\n\n"
                    "### Body\n\n"
                    "한 변리사님, **이슈** 보고드립니다.\n"
                ),
            },
        )
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].rule, "no-markdown-in-body")

    def test_edit_new_string_with_body_link_blocks(self):
        v = check(
            "Edit",
            {
                "file_path": _cold("contact-a.md"),
                "old_string": "x",
                "new_string": (
                    "## Sent (2026-04-26)\n\n"
                    "담당자님, [링크](https://x.com) 참고 부탁드립니다.\n"
                ),
            },
        )
        self.assertEqual(len(v), 1)

    def test_multiedit_with_body_inline_code_blocks(self):
        v = check(
            "MultiEdit",
            {
                "file_path": _vendor("vendor-a.md"),
                "edits": [
                    {
                        "old_string": "x",
                        "new_string": (
                            "## Sent (2026-04-26)\n\n"
                            "Hi vendor, run `openssl x509 -text` first.\n"
                        ),
                    }
                ],
            },
        )
        self.assertEqual(len(v), 1)

    def test_edit_clean_passes(self):
        v = check(
            "Edit",
            {
                "file_path": _cold("contact-a.md"),
                "old_string": "x",
                "new_string": (
                    "## Sent (2026-04-26)\n\n"
                    "담당자님, 보고드립니다. 1. OEM 라인업 evidence.\n"
                ),
            },
        )
        self.assertEqual(len(v), 0)


if __name__ == "__main__":
    unittest.main()

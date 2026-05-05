"""Tests for frontmatter_schema rule."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lint.rules.frontmatter_schema import _scan_text, _scope_for, check  # noqa: E402

PROJECT_ROOT = ROOT.parent

# Frozen test fixtures — small canonical schemas independent of the live
# schemas.yml so tests don't drift if the real schema is edited.
COLD_SCHEMA = {"slug", "name", "company", "status", "notes", "phone"}
VENDOR_SCHEMA = {"slug", "type", "vendor_category", "contact_email", "notes"}
EVENT_SCHEMA = {"slug", "event_name", "date", "venue", "notes"}
TEST_SCHEMAS = {
    "cold_contacts": COLD_SCHEMA,
    "vendors": VENDOR_SCHEMA,
    "pitch_events": EVENT_SCHEMA,
}


class TestColdContactsScope(unittest.TestCase):
    def test_canonical_only_passes(self):
        text = "---\nslug: foo\nname: Foo\nstatus: sent\nnotes: bar\n---\nbody"
        v = _scan_text(text, "cold_contacts/foo.md", "cold_contacts", TEST_SCHEMAS)
        self.assertEqual(len(v), 0)

    def test_unknown_key_blocked(self):
        text = "---\nslug: foo\naudience_type: journalist\n---\nbody"
        v = _scan_text(text, "cold_contacts/foo.md", "cold_contacts", TEST_SCHEMAS)
        self.assertEqual(len(v), 1)
        self.assertIn("audience_type", v[0].message)
        self.assertEqual(v[0].severity, "block")

    def test_multiple_unknown_keys_each_flagged(self):
        text = "---\nslug: foo\nfrom_email: x@y\nweird_thing: bar\n---\nbody"
        v = _scan_text(text, "cold_contacts/foo.md", "cold_contacts", TEST_SCHEMAS)
        self.assertEqual(len(v), 2)
        flagged = {vio.message.split("'")[1] for vio in v}
        self.assertEqual(flagged, {"from_email", "weird_thing"})

    def test_lint_disable_marker_skips(self):
        text = (
            "---\nslug: foo\naudience_type: journalist\n---\n"
            "<!-- lint-disable frontmatter-schema -->\n"
            "body"
        )
        v = _scan_text(text, "cold_contacts/foo.md", "cold_contacts", TEST_SCHEMAS)
        self.assertEqual(len(v), 0)


class TestVendorScope(unittest.TestCase):
    def test_vendor_canonical_passes(self):
        text = "---\nslug: foo\ntype: vendor\nvendor_category: law-firm\n---\nbody"
        v = _scan_text(text, "vendors/foo.md", "vendors", TEST_SCHEMAS)
        self.assertEqual(len(v), 0)

    def test_cold_field_in_vendor_blocked(self):
        # `name` is canonical in cold_contacts but not vendors.
        text = "---\nslug: foo\ntype: vendor\nname: Bar\n---\nbody"
        v = _scan_text(text, "vendors/foo.md", "vendors", TEST_SCHEMAS)
        self.assertEqual(len(v), 1)
        self.assertIn("name", v[0].message)


class TestPitchEventsScope(unittest.TestCase):
    def test_event_canonical_passes(self):
        text = "---\nslug: e1\nevent_name: Foo\ndate: '2026-04-23'\n---\nbody"
        v = _scan_text(text, "pitch_events/e1.md", "pitch_events", TEST_SCHEMAS)
        self.assertEqual(len(v), 0)

    def test_event_unknown_field_blocked(self):
        text = "---\nslug: e1\nevent_name: Foo\nunlisted_speaker: x\n---\nbody"
        v = _scan_text(text, "pitch_events/e1.md", "pitch_events", TEST_SCHEMAS)
        self.assertEqual(len(v), 1)


class TestNonScope(unittest.TestCase):
    def test_other_paths_untouched(self):
        # No scope match → no violations even with garbage frontmatter
        text = "---\nslug: foo\nrandom_garbage: yes\n---\nbody"
        v = _scan_text(text, "drafts/foo.md", "", TEST_SCHEMAS)
        self.assertEqual(len(v), 0)

    def test_empty_scope_returns_nothing(self):
        v = _scan_text("---\nfoo: bar\n---\n", "drafts/x.md", "", TEST_SCHEMAS)
        self.assertEqual(len(v), 0)


class TestScopeDetection(unittest.TestCase):
    def test_cold_contacts_path(self):
        self.assertEqual(
            _scope_for(str(PROJECT_ROOT / "cold_contacts/x.md")), "cold_contacts"
        )

    def test_vendors_path(self):
        self.assertEqual(_scope_for(str(PROJECT_ROOT / "vendors/x.md")), "vendors")

    def test_pitch_events_path(self):
        self.assertEqual(
            _scope_for(str(PROJECT_ROOT / "pitch_events/x.md")), "pitch_events"
        )

    def test_drafts_out_of_scope(self):
        self.assertEqual(_scope_for(str(PROJECT_ROOT / "drafts/x.md")), "")

    def test_skill_md_out_of_scope(self):
        self.assertEqual(
            _scope_for(str(PROJECT_ROOT / ".claude/skills/foo/SKILL.md")), ""
        )


class TestEdgeCases(unittest.TestCase):
    def test_no_frontmatter_passes(self):
        v = _scan_text("just markdown body, no frontmatter\n", "cold_contacts/x.md",
                       "cold_contacts", TEST_SCHEMAS)
        self.assertEqual(len(v), 0)

    def test_unclosed_frontmatter_passes(self):
        # If the file is malformed, don't crash; let other rules handle it.
        text = "---\nslug: foo\nnot a closing fence"
        v = _scan_text(text, "cold_contacts/x.md", "cold_contacts", TEST_SCHEMAS)
        self.assertEqual(len(v), 0)

    def test_empty_frontmatter_passes(self):
        text = "---\n---\nbody"
        v = _scan_text(text, "cold_contacts/x.md", "cold_contacts", TEST_SCHEMAS)
        self.assertEqual(len(v), 0)


class TestEditHook(unittest.TestCase):
    def test_edit_new_string_with_unknown_key_blocked(self):
        # Use the LIVE schema for this end-to-end check (cold_contacts canonical).
        v = check("Edit", {
            "file_path": str(PROJECT_ROOT / "cold_contacts/foo.md"),
            "old_string": "x",
            "new_string": "---\nslug: foo\naudience_type: journalist\n---\nbody",
        })
        # audience_type is NOT in the live schema, should flag
        self.assertEqual(len(v), 1)

    def test_edit_clean_passes(self):
        v = check("Edit", {
            "file_path": str(PROJECT_ROOT / "cold_contacts/foo.md"),
            "old_string": "x",
            "new_string": "---\nslug: foo\nname: Foo\nstatus: sent\n---\nbody",
        })
        self.assertEqual(len(v), 0)

    def test_out_of_scope_path_passes(self):
        v = check("Write", {
            "file_path": str(PROJECT_ROOT / "drafts/foo.md"),
            "content": "---\nfoo: bar\n---\nbody",
        })
        self.assertEqual(len(v), 0)


if __name__ == "__main__":
    unittest.main()

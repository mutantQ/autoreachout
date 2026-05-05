"""Tests for one_file_per_entity rule."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import lint.rules.one_file_per_entity as rule  # noqa: E402


class TestOneFilePerEntity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "outreach" / "cold_contacts").mkdir(parents=True)
        (self.root / "outreach" / "drafts").mkdir(parents=True)
        # Patch the module-level constants
        self._orig_root = rule.PROJECT_ROOT
        self._orig_drafts = rule.DRAFTS_DIR
        self._orig_cc = rule.COLD_CONTACTS_DIR
        rule.PROJECT_ROOT = self.root.resolve()
        rule.DRAFTS_DIR = (self.root / "outreach" / "drafts").resolve()
        rule.COLD_CONTACTS_DIR = (self.root / "outreach" / "cold_contacts").resolve()

    def tearDown(self):
        rule.PROJECT_ROOT = self._orig_root
        rule.DRAFTS_DIR = self._orig_drafts
        rule.COLD_CONTACTS_DIR = self._orig_cc
        self.tmp.cleanup()

    def test_blocks_when_cold_contact_exists(self):
        (rule.COLD_CONTACTS_DIR / "john-doe.md").write_text("existing")
        target = str(rule.DRAFTS_DIR / "john-doe.md")
        v = rule.check("Write", {"file_path": target})
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].rule, "one-file-per-entity")

    def test_allows_when_no_cold_contact(self):
        target = str(rule.DRAFTS_DIR / "lawmission.md")
        v = rule.check("Write", {"file_path": target})
        self.assertEqual(len(v), 0)

    def test_blocks_subfolder(self):
        target = str(rule.DRAFTS_DIR / "legal-followup" / "some.md")
        v = rule.check("Write", {"file_path": target})
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].rule, "drafts-no-subfolder")

    def test_ignores_writes_outside_drafts(self):
        target = str(rule.COLD_CONTACTS_DIR / "john-doe.md")
        v = rule.check("Write", {"file_path": target})
        self.assertEqual(len(v), 0)

    def test_ignores_non_write_tools(self):
        v = rule.check("Read", {"file_path": str(rule.DRAFTS_DIR / "anything.md")})
        # Read tool without file_path in drafts area still returns [] if no cold_contact collision
        self.assertEqual(len(v), 0)


if __name__ == "__main__":
    unittest.main()

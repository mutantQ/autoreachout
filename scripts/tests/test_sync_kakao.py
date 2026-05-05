"""Tests for sync_kakao hidden-event filter and summary/recent_non_hidden output.

Worked-example failure: the kakaocli `text` field for one of three outbound
messages was the JSON edit-revision metadata
`{"logId":...,"targetRevision":1,"hidden":true,"feedType":25}`.
That blob landed as the single `summary` of the sync output, masking the real
outbound thread underneath. These tests lock in the filter that prevents the
recurrence.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sync_kakao import (  # noqa: E402
    is_hidden_event,
    build_summary,
    build_recent_non_hidden,
)


HIDDEN_TEXT_BLOB = (
    '{"logId":1234567890,"targetRevision":1,"hidden":true,"feedType":25}'
)


class TestIsHiddenEvent(unittest.TestCase):
    def test_plain_user_text_not_hidden(self):
        self.assertFalse(is_hidden_event({"text": "안녕하세요, 인사드립니다."}))

    def test_top_level_hidden_true(self):
        self.assertTrue(is_hidden_event({"text": "x", "hidden": True}))

    def test_top_level_feed_type(self):
        self.assertTrue(is_hidden_event({"text": "x", "feed_type": 25}))
        self.assertTrue(is_hidden_event({"text": "x", "feedType": 25}))

    def test_text_as_json_with_hidden_true(self):
        self.assertTrue(is_hidden_event({"text": HIDDEN_TEXT_BLOB}))

    def test_text_as_json_feed_type_only(self):
        self.assertTrue(is_hidden_event({"text": '{"feedType": 4}'}))

    def test_text_as_json_log_id_target_revision(self):
        self.assertTrue(is_hidden_event({"text": '{"logId":1,"targetRevision":2}'}))

    def test_text_as_json_innocuous_does_not_trigger(self):
        # Plain JSON quoted in a message should NOT be misclassified
        self.assertFalse(is_hidden_event({"text": '{"name":"foo"}'}))

    def test_malformed_json_not_hidden(self):
        self.assertFalse(is_hidden_event({"text": "{not really json"}))

    def test_empty_text(self):
        self.assertFalse(is_hidden_event({"text": ""}))
        self.assertFalse(is_hidden_event({}))


class TestBuildSummary(unittest.TestCase):
    def test_picks_latest_user_message_skipping_hidden_tail(self):
        msgs = [
            {"timestamp": "2026-05-02T05:48:11+00:00", "text": "안녕하세요 메시지 첫 번째"},
            {"timestamp": "2026-05-02T05:48:45+00:00", "text": "두 번째 후속 안내"},
            {"timestamp": "2026-05-02T05:50:15+00:00", "text": "세 번째 마무리 메시지"},
            {"timestamp": "2026-05-02T05:50:19+00:00", "text": HIDDEN_TEXT_BLOB},
        ]
        summary = build_summary(msgs)
        self.assertIn("세 번째", summary)
        self.assertNotIn("logId", summary)
        self.assertNotIn("feedType", summary)

    def test_all_hidden_falls_through(self):
        msgs = [
            {"timestamp": "2026-05-02T05:50:19+00:00", "text": HIDDEN_TEXT_BLOB},
            {"timestamp": "2026-05-02T05:50:20+00:00", "text": '{"feedType": 4}'},
        ]
        summary = build_summary(msgs)
        self.assertIn("hidden events only", summary)
        self.assertIn("2", summary)

    def test_empty_messages(self):
        self.assertEqual(build_summary([]), "")

    def test_no_hidden_events(self):
        msgs = [
            {"timestamp": "2026-05-02T05:00:00+00:00", "text": "first"},
            {"timestamp": "2026-05-02T06:00:00+00:00", "text": "second"},
        ]
        self.assertEqual(build_summary(msgs), "second")


class TestBuildRecentNonHidden(unittest.TestCase):
    def test_returns_only_non_hidden_newest_first(self):
        msgs = [
            {"timestamp": "2026-05-02T05:48:11+00:00", "text": "msg1"},
            {"timestamp": "2026-05-02T05:48:45+00:00", "text": "msg2"},
            {"timestamp": "2026-05-02T05:50:15+00:00", "text": "msg3"},
            {"timestamp": "2026-05-02T05:50:19+00:00", "text": HIDDEN_TEXT_BLOB},
        ]
        out = build_recent_non_hidden(msgs, limit=5)
        self.assertEqual(len(out), 3)
        self.assertEqual([m["text"] for m in out], ["msg3", "msg2", "msg1"])

    def test_respects_limit(self):
        msgs = [
            {"timestamp": f"2026-05-02T0{i}:00:00+00:00", "text": f"m{i}"}
            for i in range(8)
        ]
        out = build_recent_non_hidden(msgs, limit=3)
        self.assertEqual(len(out), 3)
        self.assertEqual([m["text"] for m in out], ["m7", "m6", "m5"])

    def test_truncates_long_text(self):
        long_text = "가" * 200
        msgs = [{"timestamp": "2026-05-02T05:00:00+00:00", "text": long_text}]
        out = build_recent_non_hidden(msgs, limit=1)
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0]["text"].endswith("..."))
        self.assertLessEqual(len(out[0]["text"]), 120)

    def test_sender_resolution(self):
        msgs = [
            {"timestamp": "2026-05-02T05:00:00+00:00", "text": "a", "sender": "대표"},
            {"timestamp": "2026-05-02T06:00:00+00:00", "text": "b", "from_me": True},
            {"timestamp": "2026-05-02T07:00:00+00:00", "text": "c", "sender_id": 12345},
        ]
        out = build_recent_non_hidden(msgs, limit=5)
        senders = {m["text"]: m["sender"] for m in out}
        self.assertEqual(senders["a"], "대표")
        self.assertEqual(senders["b"], "me")
        self.assertEqual(senders["c"], "12345")

    def test_all_hidden_returns_empty(self):
        msgs = [{"timestamp": "2026-05-02T05:00:00+00:00", "text": HIDDEN_TEXT_BLOB}]
        self.assertEqual(build_recent_non_hidden(msgs), [])


if __name__ == "__main__":
    unittest.main()

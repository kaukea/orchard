"""Unit tests for tools/boxes.py — docs/testing/01-inbox-outbox.md."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
import boxes  # noqa: E402


def env_in(tmp: str) -> dict:
    return {"XDG_RUNTIME_DIR": tmp}


class EnvelopeValidationTests(unittest.TestCase):
    def valid(self) -> dict:
        return {"from": ":session:a", "to": ":session:b",
                "subject": "orchard:agent:message:content", "body": "hi"}

    def test_valid_envelope_with_body_passes(self):
        self.assertEqual(boxes.validate_envelope(self.valid()), self.valid())

    def test_valid_envelope_without_body_passes(self):
        envelope = self.valid()
        del envelope["body"]
        self.assertEqual(boxes.validate_envelope(envelope), envelope)

    def test_non_dict_is_rejected(self):
        with self.assertRaisesRegex(boxes.EnvelopeError, "not an object"):
            boxes.validate_envelope(["not", "a", "dict"])

    def test_each_missing_required_field_is_rejected(self):
        for field in boxes.REQUIRED_FIELDS:
            envelope = self.valid()
            del envelope[field]
            with self.assertRaisesRegex(boxes.EnvelopeError, f"missing required field: {field}"):
                boxes.validate_envelope(envelope)

    def test_unknown_field_is_rejected(self):
        envelope = self.valid()
        envelope["priority"] = "immediate"
        with self.assertRaisesRegex(boxes.EnvelopeError, "unknown fields.*priority"):
            boxes.validate_envelope(envelope)

    def test_non_session_from_address_is_rejected(self):
        envelope = self.valid()
        envelope["from"] = ":topic:build"
        with self.assertRaisesRegex(boxes.EnvelopeError, "not a :session: address"):
            boxes.validate_envelope(envelope)

    def test_dotted_session_id_is_rejected(self):
        envelope = self.valid()
        envelope["to"] = ":session:a.b"
        with self.assertRaises(boxes.EnvelopeError):
            boxes.validate_envelope(envelope)

    def test_off_corpus_subject_is_rejected(self):
        envelope = self.valid()
        envelope["subject"] = "orchard:agent:signal:finished"
        with self.assertRaisesRegex(boxes.EnvelopeError, "unknown subject"):
            boxes.validate_envelope(envelope)

    def test_non_string_body_is_rejected(self):
        envelope = self.valid()
        envelope["body"] = {"nested": True}
        with self.assertRaisesRegex(boxes.EnvelopeError, "body is not a string"):
            boxes.validate_envelope(envelope)

    def test_corpus_is_the_ruled_twenty_two(self):
        self.assertEqual(len(boxes.SUBJECTS), 22)

    def test_make_envelope_builds_and_validates(self):
        envelope = boxes.make_envelope("a", ":session:b", "orchard:agent:status", "working")
        self.assertEqual(envelope["from"], ":session:a")
        self.assertEqual(envelope["body"], "working")

    def test_make_envelope_omits_absent_body(self):
        envelope = boxes.make_envelope("a", ":session:b", "orchard:agent:status")
        self.assertNotIn("body", envelope)


class BoxLocationTests(unittest.TestCase):
    def test_unset_runtime_dir_is_a_hard_error(self):
        with self.assertRaisesRegex(boxes.EnvelopeError, "XDG_RUNTIME_DIR"):
            boxes.boxes_root({})

    def test_the_three_boxes_live_under_the_runtime_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            root = Path(tmp) / "orchard" / "boxes"
            self.assertEqual(boxes.outbox_dir(env), root / "outbox")
            self.assertEqual(boxes.inbox_dir(env), root / "inbox")
            self.assertEqual(boxes.quarantine_dir(env), root / "quarantine")


class OutboxTests(unittest.TestCase):
    def test_put_outbox_writes_sender_keyed_roundtripping_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            envelope = boxes.make_envelope("sender1", ":session:rcpt", "orchard:agent:status", "ok")
            path = boxes.put_outbox(envelope, env)
            self.assertTrue(path.name.startswith("sender1."))
            self.assertTrue(path.name.endswith(".json"))
            self.assertEqual(json.loads(path.read_text()), envelope)

    def test_put_outbox_rejects_invalid_before_touching_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            with self.assertRaises(boxes.EnvelopeError):
                boxes.put_outbox({"from": ":session:a"}, env)
            self.assertFalse(boxes.outbox_dir(env).exists())

    def test_write_is_atomic_no_tmp_file_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            boxes.put_outbox(boxes.make_envelope("a", ":session:b", "orchard:agent:status"), env)
            leftovers = [p for p in boxes.outbox_dir(env).iterdir()
                         if p.name.startswith(boxes.TMP_PREFIX)]
            self.assertEqual(leftovers, [])


class InboxTests(unittest.TestCase):
    def deliver(self, env, recipient, body):
        envelope = boxes.make_envelope("x", f":session:{recipient}",
                                       "orchard:agent:message:content", body)
        boxes.write_atomic(boxes.inbox_dir(env), boxes.message_name(recipient), envelope)

    def test_missing_inbox_receives_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(boxes.receive("nobody", env_in(tmp)), [])

    def test_receive_returns_own_messages_oldest_first_and_deletes(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            self.deliver(env, "me", "first")
            self.deliver(env, "me", "second")
            received = boxes.receive("me", env)
            self.assertEqual([m["body"] for m in received], ["first", "second"])
            self.assertEqual(boxes.receive("me", env), [])
            self.assertEqual(list(boxes.inbox_dir(env).glob("me.*")), [])

    def test_receive_leaves_other_sessions_messages_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            self.deliver(env, "me", "mine")
            self.deliver(env, "other", "theirs")
            boxes.receive("me", env)
            self.assertEqual(len(list(boxes.inbox_dir(env).glob("other.*.json"))), 1)


class CliTests(unittest.TestCase):
    def test_send_then_receive_after_manual_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            code = boxes.main(["send", "--from-sid", "a", "--to", ":session:b",
                               "--subject", "orchard:agent:status", "--body", "up"], env)
            self.assertEqual(code, 0)
            code = boxes.main(["receive", "--sid", "b"], env)
            self.assertEqual(code, 0)

    def test_send_body_dash_reads_stdin(self):
        import io
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            with mock.patch("sys.stdin", io.StringIO("piped body")):
                code = boxes.main(["send", "--from-sid", "a", "--to", ":session:b",
                                   "--subject", "orchard:agent:status", "--body", "-"], env)
            self.assertEqual(code, 0)
            path = next(boxes.outbox_dir(env).glob("a.*.json"))
            self.assertEqual(json.loads(path.read_text())["body"], "piped body")

    def test_send_rejects_bad_subject_with_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = boxes.main(["send", "--from-sid", "a", "--to", ":session:b",
                               "--subject", "made:up:subject"], env_in(tmp))
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

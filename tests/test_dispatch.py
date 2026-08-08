"""Unit tests for tools/dispatch.py — docs/testing/01-inbox-outbox.md."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
import boxes  # noqa: E402
import dispatch  # noqa: E402


def env_in(tmp: str) -> dict:
    return {"XDG_RUNTIME_DIR": tmp}


def send(env, sender="a", to=":session:b", body="hello"):
    return boxes.put_outbox(
        boxes.make_envelope(sender, to, "orchard:agent:message:content", body), env)


class DispatchTests(unittest.TestCase):
    def test_missing_outbox_is_a_zero_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(dispatch.dispatch_once(env_in(tmp)),
                             {"delivered": 0, "quarantined": 0})

    def test_valid_envelope_moves_to_recipient_keyed_inbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            outbox_name = send(env, sender="alice", to=":session:bob", body="the goods").name
            stats = dispatch.dispatch_once(env)
            self.assertEqual(stats, {"delivered": 1, "quarantined": 0})
            self.assertEqual(list(boxes.outbox_dir(env).glob("*.json")), [])
            delivered = list(boxes.inbox_dir(env).glob("bob.*.json"))
            self.assertEqual(len(delivered), 1)
            self.assertEqual(delivered[0].name, "bob." + outbox_name.split(".", 1)[1])
            self.assertEqual(json.loads(delivered[0].read_text())["body"], "the goods")

    def test_received_body_is_byte_identical_to_sent(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            body = "exact é content\nwith newline"
            send(env, to=":session:bob", body=body)
            dispatch.dispatch_once(env)
            self.assertEqual(boxes.receive("bob", env)[0]["body"], body)

    def test_unreadable_json_is_quarantined_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            outbox = boxes.outbox_dir(env)
            outbox.mkdir(parents=True)
            (outbox / "evil.20260808.x.json").write_text("{not json")
            stats = dispatch.dispatch_once(env)
            self.assertEqual(stats, {"delivered": 0, "quarantined": 1})
            quarantined = boxes.quarantine_dir(env) / "evil.20260808.x.json"
            self.assertEqual(quarantined.read_text(), "{not json")

    def test_off_schema_envelope_is_quarantined_not_delivered(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            outbox = boxes.outbox_dir(env)
            outbox.mkdir(parents=True)
            bad = {"from": ":session:a", "to": ":session:b",
                   "subject": "orchard:agent:status", "smuggled": True}
            (outbox / "a.20260808.y.json").write_text(json.dumps(bad))
            stats = dispatch.dispatch_once(env)
            self.assertEqual(stats, {"delivered": 0, "quarantined": 1})
            self.assertFalse(boxes.inbox_dir(env).exists())

    def test_tmp_files_are_skipped_not_dispatched(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            outbox = boxes.outbox_dir(env)
            outbox.mkdir(parents=True)
            (outbox / f"{boxes.TMP_PREFIX}half.json").write_text("{")
            stats = dispatch.dispatch_once(env)
            self.assertEqual(stats, {"delivered": 0, "quarantined": 0})
            self.assertTrue((outbox / f"{boxes.TMP_PREFIX}half.json").exists())

    def test_second_run_after_drain_delivers_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            send(env)
            dispatch.dispatch_once(env)
            self.assertEqual(dispatch.dispatch_once(env),
                             {"delivered": 0, "quarantined": 0})

    def test_mixed_batch_counts_both_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = env_in(tmp)
            send(env)
            outbox = boxes.outbox_dir(env)
            (outbox / "z.20260808.q.json").write_text("broken")
            self.assertEqual(dispatch.dispatch_once(env),
                             {"delivered": 1, "quarantined": 1})


class DispatchCliTests(unittest.TestCase):
    def test_once_runs_and_reports_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(dispatch.main(["once"], env_in(tmp)), 0)

    def test_anything_else_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(dispatch.main(["forever"], env_in(tmp)), 2)


if __name__ == "__main__":
    unittest.main()

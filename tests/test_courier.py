"""Unit tests for tools/courier.py's operator_origin provenance flag, and the
`ask`/answer question protocol (sidebar-polish item 12c-f).

Mirrors the notify_user coverage style used elsewhere in this suite (see
tests/test_sidebar_model.py, tests/support.py): a real git-init'd temp repo,
the module under test exercised end to end rather than mocked.

Runs under both `python3 -m unittest discover` and `pytest`.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover - environment-dependent
    jsonschema = None

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import courier  # noqa: E402

from support import make_repo  # noqa: E402

_SCHEMA_PATH = os.path.join(_TOOLS_DIR, "message.schema.json")
_COURIER_PY = os.path.join(_TOOLS_DIR, "courier.py")


def _schema() -> dict:
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


class MakeEnvelopeTests(unittest.TestCase):
    """Unit-level: make_envelope() itself, no subprocess involved."""

    def test_operator_origin_true_is_present(self):
        env = courier.make_envelope("senderX", "recipientA", operator_origin=True)
        self.assertTrue(env["operator_origin"])

    def test_operator_origin_false_is_absent(self):
        env = courier.make_envelope("senderX", "recipientA")
        self.assertNotIn("operator_origin", env)

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_operator_origin_envelope_validates_against_schema(self):
        env = courier.make_envelope("senderX", "recipientA", operator_origin=True)
        jsonschema.validate(instance=env, schema=_schema())


class CliRoundTripTests(unittest.TestCase):
    """CLI-level: `send --operator-origin` then `receive`, in a real repo."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)

    def _courier(self, *args):
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=self.repo, check=True, capture_output=True, text=True,
        )

    def test_operator_origin_round_trips_through_send_and_receive(self):
        self._courier("init", "recipientA")
        self._courier(
            "send", "--from", "senderX", "--to", "recipientA",
            "--operator-origin", "--body", "hello",
        )

        out = self._courier("receive", "recipientA")
        messages = json.loads(out.stdout)

        self.assertEqual(len(messages), 1)
        msg = messages[0]
        self.assertTrue(msg["operator_origin"])
        self.assertEqual(msg["from"], "senderX")
        self.assertEqual(msg["body"], "hello")

        if jsonschema is not None:
            jsonschema.validate(instance=msg, schema=_schema())

    def test_broadcast_operator_origin_round_trips(self):
        self._courier("init", "senderX")
        self._courier("init", "recipientA")
        self._courier("broadcast", "--from", "senderX", "--operator-origin", "--body", "hi")

        out = self._courier("receive", "recipientA")
        messages = json.loads(out.stdout)

        self.assertEqual(len(messages), 1)
        self.assertTrue(messages[0]["operator_origin"])


class SignalAttributionTests(unittest.TestCase):
    """CLI-level: `signal` always attributes the envelope to the caller's own
    session — there is no way to signal as someone else."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)

    def _courier(self, *args, session_id):
        env = dict(os.environ, CLAUDE_CODE_SESSION_ID=session_id)
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=self.repo, check=True, capture_output=True, text=True, env=env,
        )

    def test_signal_uses_caller_as_from(self):
        self._courier("init", "watcher2", session_id="watcher2")
        self._courier(
            "signal", "--state", "finished", "--feature", "own-feature",
            session_id="selfSignallerA",
        )

        out = self._courier("receive", "watcher2", session_id="watcher2")
        messages = json.loads(out.stdout)

        self.assertEqual(messages[0]["from"], "selfSignallerA")


class QuestionEnvelopeUnitTests(unittest.TestCase):
    """Unit-level: _question_envelope() itself, no subprocess involved."""

    def test_carries_notify_user_and_interrupt_question_body_for_the_existing_sidebar_signal(self):
        env = courier._question_envelope("askerX", "peerA", "q1", "Proceed?", ["Yes", "No"])
        self.assertTrue(env["notify_user"])
        self.assertEqual(env["body"], "orchid:interrupt:question:Proceed?")

    def test_interrupt_question_body_uses_title_as_subject_when_given(self):
        env = courier._question_envelope(
            "askerX", "peerA", "q1", "Proceed?", ["Yes", "No"], title="Deploy gate",
        )
        self.assertEqual(env["body"], "orchid:interrupt:question:Deploy gate")

    def test_interrupt_question_body_falls_back_to_question_text_without_a_title(self):
        env = courier._question_envelope("askerX", "peerA", "q1", "Ship it?", ["Yes", "No"])
        self.assertEqual(env["body"], "orchid:interrupt:question:Ship it?")

    def test_carries_question_fields(self):
        env = courier._question_envelope("askerX", "peerA", "q1", "Proceed?", ["Yes", "No"])
        self.assertEqual(env["question_id"], "q1")
        self.assertEqual(env["question"], "Proceed?")
        self.assertEqual(env["options"], ["Yes", "No"])

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_question_envelope_validates_against_schema(self):
        env = courier._question_envelope("askerX", "peerA", "q1", "Proceed?", ["Yes", "No"])
        jsonschema.validate(instance=env, schema=_schema())

    def test_title_summary_multi_carried_when_given(self):
        env = courier._question_envelope(
            "askerX", "peerA", "q1", "Proceed?", ["Yes", "No"],
            title="Deploy gate", summary="Ship now or wait.", multi=True,
        )
        self.assertEqual(env["title"], "Deploy gate")
        self.assertEqual(env["summary"], "Ship now or wait.")
        self.assertTrue(env["multi"])

    def test_title_summary_multi_absent_by_default(self):
        env = courier._question_envelope("askerX", "peerA", "q1", "Proceed?", ["Yes", "No"])
        self.assertNotIn("title", env)
        self.assertNotIn("summary", env)
        self.assertNotIn("multi", env)

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_question_envelope_with_title_summary_multi_validates_against_schema(self):
        env = courier._question_envelope(
            "askerX", "peerA", "q1", "Proceed?", ["Yes", "No"],
            title="Deploy gate", summary="Ship now or wait.", multi=True,
        )
        jsonschema.validate(instance=env, schema=_schema())


class MatchAnswerUnitTests(unittest.TestCase):
    """Unit-level: _match_answer() — consumes only the matching reply,
    leaves every other message in the inbox untouched."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.box = Path(self._tmp.name)

    def _write(self, name, env):
        (self.box / name).write_text(json.dumps(env), encoding="utf-8")

    def test_no_reply_yet_returns_none(self):
        self._write("unrelated.json", {"id": "1", "from": "x", "to": "y", "body": "hi"})
        self.assertIsNone(courier._match_answer(self.box, "q1"))
        self.assertTrue((self.box / "unrelated.json").exists())

    def test_matching_reply_is_consumed_and_returned(self):
        self._write("other.json", {"id": "1", "from": "x", "to": "y",
                                    "in_reply_to": "q-other", "body": "not this one"})
        self._write("answer.json", {"id": "2", "from": "question-broker", "to": "askerX",
                                     "in_reply_to": "q1", "body": '{"index": 0, "option": "Yes"}'})

        answer = courier._match_answer(self.box, "q1")

        self.assertEqual(answer, '{"index": 0, "option": "Yes"}')
        self.assertFalse((self.box / "answer.json").exists())
        self.assertTrue((self.box / "other.json").exists())  # untouched — belongs to someone else


class AskCliRoundTripTests(unittest.TestCase):
    """CLI-level: `ask` broadcasts, blocks, and returns once a reply
    addressed back to it (via the existing `send --in-reply-to`) arrives —
    the live-tmux-popup half of item 12c is NOT exercised here (see the
    orchard-question-broker tests/report for that boundary); this is the
    bus message protocol only."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)

    def _courier(self, *args, session_id=None, **kwargs):
        env = dict(os.environ)
        if session_id is not None:
            env["CLAUDE_CODE_SESSION_ID"] = session_id
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=self.repo, capture_output=True, text=True, env=env, **kwargs,
        )

    def test_ask_round_trips_to_an_answer(self):
        self._courier("init", "peerA", session_id="peerA")

        proc = subprocess.Popen(
            [sys.executable, _COURIER_PY, "ask", "--question", "Proceed?",
             "--option", "Yes", "--option", "No", "--poll-interval", "0.05"],
            cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=dict(os.environ, CLAUDE_CODE_SESSION_ID="askerX"),
        )
        try:
            # the broadcast lands in peerA's inbox almost immediately
            deadline = time.time() + 5
            question_id = None
            while time.time() < deadline and question_id is None:
                out = self._courier("receive", "peerA", session_id="peerA")
                messages = json.loads(out.stdout)
                for m in messages:
                    if m.get("question_id"):
                        question_id = m["question_id"]
                        received = m
                if question_id is None:
                    time.sleep(0.05)
            self.assertIsNotNone(question_id, "ask() never broadcast a question")

            self.assertTrue(received["notify_user"])
            self.assertEqual(received["question"], "Proceed?")
            self.assertEqual(received["options"], ["Yes", "No"])
            self.assertEqual(received["body"], "orchid:interrupt:question:Proceed?")

            # the "broker" (standing in for tools/orchard-question-broker.py)
            # answers directly over the bus, exactly like it would after a
            # real popup returned a keypress
            self._courier(
                "send", "--from", "question-broker", "--to", "askerX",
                "--in-reply-to", question_id, "--body", '{"index": 0, "option": "Yes"}',
            )

            stdout, stderr = proc.communicate(timeout=5)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()

        self.assertEqual(proc.returncode, 0, stderr)
        self.assertEqual(json.loads(stdout), {"index": 0, "option": "Yes"})

    def test_ask_requires_at_least_two_options(self):
        proc = self._courier(
            "ask", "--question", "Proceed?", "--option", "OnlyOne",
            session_id="askerY",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("at least two", proc.stderr)

    def _round_trip(self, extra_ask_args, reply_body, session_id):
        """Shared CLI round trip: broadcast, a stand-in broker answers
        directly over the bus (exactly like the real popup would after
        returning a keypress), `ask` prints whatever body it received."""
        self._courier("init", "peerA", session_id="peerA")
        proc = subprocess.Popen(
            [sys.executable, _COURIER_PY, "ask", "--question", "Proceed?",
             "--option", "Yes", "--option", "No", "--poll-interval", "0.05",
             *extra_ask_args],
            cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=dict(os.environ, CLAUDE_CODE_SESSION_ID=session_id),
        )
        try:
            deadline = time.time() + 5
            question_id = None
            received = None
            while time.time() < deadline and question_id is None:
                out = self._courier("receive", "peerA", session_id="peerA")
                messages = json.loads(out.stdout)
                for m in messages:
                    if m.get("question_id"):
                        question_id = m["question_id"]
                        received = m
                if question_id is None:
                    time.sleep(0.05)
            self.assertIsNotNone(question_id, "ask() never broadcast a question")

            self._courier(
                "send", "--from", "question-broker", "--to", session_id,
                "--in-reply-to", question_id, "--body", reply_body,
            )
            stdout, stderr = proc.communicate(timeout=5)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()
        self.assertEqual(proc.returncode, 0, stderr)
        return received, json.loads(stdout)

    def test_ask_multi_flag_broadcasts_multi_true_and_prints_indices_shape(self):
        received, answer = self._round_trip(
            ["--multi"], '{"indices": [0, 1], "options": ["Yes", "No"]}', "askerMulti",
        )
        self.assertTrue(received["multi"])
        self.assertEqual(answer, {"indices": [0, 1], "options": ["Yes", "No"]})

    def test_ask_without_multi_omits_multi_field(self):
        received, answer = self._round_trip(
            [], '{"index": 1, "option": "No"}', "askerSingle",
        )
        self.assertNotIn("multi", received)
        self.assertEqual(answer, {"index": 1, "option": "No"})

    def test_ask_title_and_summary_broadcast_through(self):
        received, _answer = self._round_trip(
            ["--title", "Deploy gate", "--summary", "Ship now or wait."],
            '{"index": 0, "option": "Yes"}', "askerTitled",
        )
        self.assertEqual(received["title"], "Deploy gate")
        self.assertEqual(received["summary"], "Ship now or wait.")

    def test_ask_continue_outcome_prints_continue_sentinel(self):
        _received, answer = self._round_trip(
            [], '{"continue": true}', "askerEscape",
        )
        self.assertEqual(answer, {"continue": True})

    def test_ask_gate_outcome_prints_gate_phrase(self):
        _received, answer = self._round_trip(
            [], '{"gate": "MAKE IT SO"}', "askerGate",
        )
        self.assertEqual(answer, {"gate": "MAKE IT SO"})


class OrchidGrammarCliTests(unittest.TestCase):
    """CLI-level: WIRE GRAMMAR v1 enforcement in `send` and `broadcast`
    (docs/TODO.md.d/bus-message-specifying.md) — valid orchid:* bodies pass,
    malformed/unknown ones argparse-error out naming the allowed classes."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)
        self._courier("init", "peerA")

    def _courier(self, *args):
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=self.repo, capture_output=True, text=True,
        )

    def _send(self, body, *extra):
        return self._courier("send", "--from", "senderX", "--to", "peerA",
                          "--body", body, *extra)

    def assertRejected(self, proc, *fragments):
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for fragment in fragments:
            self.assertIn(fragment, proc.stderr)

    def test_non_orchid_body_stays_free(self):
        proc = self._send("just some peer prose")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_json_reply_body_stays_free(self):
        proc = self._send('{"index": 0, "option": "Yes"}')
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_status_single_word_is_valid(self):
        proc = self._send("orchid:status:reading")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_status_two_words_is_valid(self):
        proc = self._send("orchid:status:reading logs")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_status_three_words_is_rejected(self):
        self.assertRejected(self._send("orchid:status:reading old logs"), "allowed orchid:* classes")

    def test_status_uppercase_word_is_rejected(self):
        self.assertRejected(self._send("orchid:status:Reading"), "lowercase")

    def test_status_word_with_digits_is_rejected(self):
        self.assertRejected(self._send("orchid:status:reading2"), "lowercase")

    def test_status_denylisted_word_is_rejected(self):
        self.assertRejected(self._send("orchid:status:building"), "lifecycle state")

    def test_status_denylisted_second_word_is_rejected(self):
        self.assertRejected(self._send("orchid:status:currently testing"), "lifecycle state")

    def test_status_hyphenated_word_is_valid(self):
        proc = self._send("orchid:status:re-reading")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_update_with_text_is_valid(self):
        proc = self._send("orchid:update:wrote the missing test cases")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_update_with_empty_text_is_rejected(self):
        self.assertRejected(self._send("orchid:update:"), "non-empty")

    def test_phase_alone_is_valid(self):
        proc = self._send("orchid:phase:building")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_phase_with_tick_is_valid(self):
        proc = self._send("orchid:phase:building:3/5")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_phase_unknown_name_is_rejected(self):
        self.assertRejected(self._send("orchid:phase:coding"), "not one of")

    def test_phase_tick_k_greater_than_n_is_rejected(self):
        self.assertRejected(self._send("orchid:phase:building:5/3"), "k <= n")

    def test_phase_tick_zero_is_rejected(self):
        self.assertRejected(self._send("orchid:phase:building:0/5"), "k <= n")

    def test_phase_tick_non_numeric_is_rejected(self):
        self.assertRejected(self._send("orchid:phase:building:a/b"), "positive integers")

    def test_subagent_queue_is_valid(self):
        proc = self._send("orchid:subagent:queue:builder-1")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_subagent_start_is_valid(self):
        proc = self._send("orchid:subagent:start:builder-1")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_subagent_done_is_valid(self):
        proc = self._send("orchid:subagent:done:builder-1")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_subagent_unknown_verb_is_rejected(self):
        self.assertRejected(self._send("orchid:subagent:pause:builder-1"), "queue, start, or done")

    def test_subagent_empty_label_is_rejected(self):
        self.assertRejected(self._send("orchid:subagent:start:"), "non-empty")

    def test_hand_sent_interrupt_question_is_rejected(self):
        self.assertRejected(
            self._send("orchid:interrupt:question:Proceed?"), "courier.py ask",
        )

    def test_unknown_orchid_class_is_rejected(self):
        self.assertRejected(
            self._send("orchid:bogus:hi"), "unknown orchid:* class", "allowed orchid:* classes",
        )

    def test_legacy_activity_body_is_rejected(self):
        self.assertRejected(
            self._send("orchid:activity:working on it"), "unknown orchid:* class",
        )

    def test_malformed_body_names_allowed_classes(self):
        proc = self._send("orchid:bogus:hi")
        self.assertIn("status, update, phase, subagent", proc.stderr)

    def test_notify_user_rejected_on_status(self):
        self.assertRejected(
            self._send("orchid:status:reading", "--notify-user"), "--notify-user",
        )

    def test_notify_user_rejected_on_update(self):
        self.assertRejected(
            self._send("orchid:update:wrote tests", "--notify-user"), "--notify-user",
        )

    def test_notify_user_rejected_on_phase(self):
        self.assertRejected(
            self._send("orchid:phase:building", "--notify-user"), "--notify-user",
        )

    def test_notify_user_rejected_on_subagent(self):
        self.assertRejected(
            self._send("orchid:subagent:start:builder-1", "--notify-user"), "--notify-user",
        )

    def test_notify_user_stays_legal_on_free_bodies(self):
        proc = self._send("please look at this", "--notify-user")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_broadcast_enforces_the_same_grammar(self):
        self._courier("init", "senderX")
        proc = self._courier("broadcast", "--from", "senderX", "--body", "orchid:status:building")
        self.assertRejected(proc, "lifecycle state")

    def test_broadcast_accepts_valid_orchid_body(self):
        self._courier("init", "senderX")
        proc = self._courier("broadcast", "--from", "senderX", "--body", "orchid:phase:building")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_broadcast_rejects_hand_sent_interrupt(self):
        self._courier("init", "senderX")
        proc = self._courier(
            "broadcast", "--from", "senderX", "--body", "orchid:interrupt:question:hi",
        )
        self.assertRejected(proc, "courier.py ask")


class SignalNotifyLegalityCliTests(unittest.TestCase):
    """CLI-level: `signal --notify-user` is legal only with
    --state done|blocked|abandoned (docs/TODO.md.d/bus-message-specifying.md)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)

    def _courier(self, *args, session_id="s1"):
        env = dict(os.environ, CLAUDE_CODE_SESSION_ID=session_id)
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=self.repo, capture_output=True, text=True, env=env,
        )

    def test_notify_user_legal_with_done(self):
        proc = self._courier("signal", "--state", "done", "--notify-user")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_notify_user_legal_with_blocked(self):
        proc = self._courier("signal", "--state", "blocked", "--notify-user")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_notify_user_legal_with_abandoned(self):
        proc = self._courier("signal", "--state", "abandoned", "--notify-user")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_notify_user_rejected_with_started(self):
        proc = self._courier("signal", "--state", "started", "--notify-user")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--notify-user", proc.stderr)

    def test_notify_user_rejected_with_building(self):
        proc = self._courier("signal", "--state", "building", "--notify-user")
        self.assertNotEqual(proc.returncode, 0)

    def test_notify_user_rejected_with_testing(self):
        proc = self._courier("signal", "--state", "testing", "--notify-user")
        self.assertNotEqual(proc.returncode, 0)

    def test_notify_user_rejected_with_finished(self):
        proc = self._courier("signal", "--state", "finished", "--notify-user")
        self.assertNotEqual(proc.returncode, 0)

    def test_signal_without_notify_user_is_unrestricted(self):
        proc = self._courier("signal", "--state", "building")
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()

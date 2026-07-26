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


class SignalAttributionTests(unittest.TestCase):
    """CLI-level: `signal` is directed at the parent alone, over the orchard
    transport (courier.py cmd_signal) — there is no broadcast fallback any
    more. With a parent known (ORCHID_PARENT_SESSION + ORCHID_PARENT_PROJECT,
    cross-project allowlist-gated exactly like any other :session: send) the
    envelope lands in the parent's project mailbox, attributed to the
    caller's own session. With no parent known, nothing is delivered."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.runtime_dir = base / "run"
        self.runtime_dir.mkdir()
        self.cache_home = base / "cache"
        self.cache_home.mkdir()
        self.home = base / "home"
        self.home.mkdir()
        self.repo = make_repo(str(base))
        self.parent_repo = make_repo(str(base))

    def _env(self, session_id, **extra):
        # the ambient environment (this suite itself typically runs as a
        # sub-session under the bus/courier system) may already carry
        # ORCHID_PARENT_SESSION/ORCHID_PARENT_PROJECT — strip them so "no
        # parent known" is genuinely no parent, not an inherited one.
        env = {k: v for k, v in os.environ.items()
               if k not in ("ORCHID_PARENT_SESSION", "ORCHID_PARENT_PROJECT")}
        env.update(
            CLAUDE_CODE_SESSION_ID=session_id,
            XDG_RUNTIME_DIR=str(self.runtime_dir), XDG_CACHE_HOME=str(self.cache_home),
            HOME=str(self.home),
        )
        env.update(extra)
        return env

    def _courier(self, repo, *args, session_id, extra_env=None):
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=repo, capture_output=True, text=True,
            env=self._env(session_id, **(extra_env or {})),
        )

    def _slug(self, repo):
        proc = subprocess.run(
            [sys.executable, "-c", "import courier; print(courier.project_slug())"],
            cwd=repo, capture_output=True, text=True,
            env=self._env("slug-probe", PYTHONPATH=_TOOLS_DIR), check=True,
        )
        return proc.stdout.strip()

    def _allow(self, *slugs):
        cfg_dir = self.home / ".config" / "orchids"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "sidebar-registry.json").write_text(
            json.dumps(list(slugs)), encoding="utf-8",
        )

    def test_signal_with_known_parent_lands_in_parent_project_attributed_to_caller(self):
        parent_slug = self._slug(self.parent_repo)
        self._allow(parent_slug)

        proc = self._courier(
            self.repo, "signal", "--state", "finished", "--feature", "own-feature",
            session_id="selfSignallerA",
            extra_env={"ORCHID_PARENT_SESSION": "watcher2", "ORCHID_PARENT_PROJECT": parent_slug},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        project_path = self.runtime_dir / "orchard" / "projects" / parent_slug
        files = [f for f in project_path.glob("watcher2.*.json") if not f.name.startswith(".")]
        self.assertEqual(len(files), 1)

        env = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(env["from"], ":session:selfSignallerA")
        self.assertEqual(env["to"], ":session:watcher2")
        body = env["body"]
        self.assertEqual(body["kind"], "lifecycle")
        self.assertEqual(body["state"], "finished")
        self.assertEqual(body["feature_id"], "own-feature")

    def test_signal_with_no_parent_delivers_nothing(self):
        proc = self._courier(
            self.repo, "signal", "--state", "finished", session_id="lonelySignaller",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("not delivered", proc.stdout)

        project_dirs = list((self.runtime_dir / "orchard" / "projects").glob("*")) \
            if (self.runtime_dir / "orchard" / "projects").is_dir() else []
        self.assertEqual(project_dirs, [])


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
    """CLI-level: `ask` sends exactly ONE directed orchard request to the
    reserved `:session:operator` mailbox (projects/<slug>/operator.<ts>.json,
    no fan-out) and blocks until a `reply --to :session:<asker>
    --in-reply-to <request id> --subject orchard:operator:message:response`
    answers it — standing in for the standalone question-broker
    (tools/orchard-question-broker.py). The live-tmux-popup half of item 12c
    is NOT exercised here; this is the orchard message protocol only."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.runtime_dir = base / "run"
        self.runtime_dir.mkdir()
        self.cache_home = base / "cache"
        self.cache_home.mkdir()
        self.home = base / "home"
        self.home.mkdir()
        self.repo = make_repo(str(base))

    def _env(self, session_id=None):
        env = dict(
            os.environ, XDG_RUNTIME_DIR=str(self.runtime_dir),
            XDG_CACHE_HOME=str(self.cache_home), HOME=str(self.home),
        )
        if session_id is not None:
            env["CLAUDE_CODE_SESSION_ID"] = session_id
        return env

    def _courier(self, *args, session_id=None, **kwargs):
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=self.repo, capture_output=True, text=True, env=self._env(session_id), **kwargs,
        )

    def _slug(self):
        proc = subprocess.run(
            [sys.executable, "-c", "import courier; print(courier.project_slug())"],
            cwd=self.repo, capture_output=True, text=True,
            env=dict(self._env(), PYTHONPATH=_TOOLS_DIR), check=True,
        )
        return proc.stdout.strip()

    def _operator_mailbox(self):
        return self.runtime_dir / "orchard" / "projects" / self._slug()

    def _poll_for_operator_request(self, deadline):
        """Non-destructive read of the operator mailbox for the one
        `orchard:agent:message:request` `ask` wrote — never deletes, so the
        file count assertion afterwards still sees exactly one."""
        box = self._operator_mailbox()
        while time.time() < deadline:
            if box.is_dir():
                for f in sorted(box.glob("operator.*.json")):
                    if f.name.startswith("."):
                        continue
                    try:
                        env = json.loads(f.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        continue
                    if env.get("subject") == "orchard:agent:message:request":
                        return env
            time.sleep(0.05)
        return None

    def test_ask_writes_exactly_one_request_to_the_operator_mailbox(self):
        proc = subprocess.Popen(
            [sys.executable, _COURIER_PY, "ask", "--question", "Proceed?",
             "--option", "Yes", "--option", "No", "--poll-interval", "0.05"],
            cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=self._env("askerX"),
        )
        try:
            env = self._poll_for_operator_request(time.time() + 5)
            self.assertIsNotNone(env, "ask() never reached the operator mailbox")

            box = self._operator_mailbox()
            files = [f for f in box.glob("operator.*.json") if not f.name.startswith(".")]
            self.assertEqual(len(files), 1)  # no fan-out — exactly one file

            self.assertEqual(env["to"], ":session:operator")
            self.assertEqual(env["from"], ":session:askerX")
            body = env["body"]
            self.assertEqual(body["question"], "Proceed?")
            self.assertEqual(body["options"], ["Yes", "No"])

            self._courier(
                "reply", "--to", ":session:askerX", "--in-reply-to", env["id"],
                "--subject", "orchard:operator:message:response",
                "--body", '{"index": 0, "option": "Yes"}', session_id="question-broker",
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
        """Shared CLI round trip: `ask` sends its one directed request to the
        operator mailbox; a stand-in broker (in place of
        tools/orchard-question-broker.py) replies over the same
        request/reply mechanism `request`/`reply` already use; `ask` prints
        whatever body it received."""
        proc = subprocess.Popen(
            [sys.executable, _COURIER_PY, "ask", "--question", "Proceed?",
             "--option", "Yes", "--option", "No", "--poll-interval", "0.05",
             *extra_ask_args],
            cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=self._env(session_id),
        )
        try:
            env = self._poll_for_operator_request(time.time() + 5)
            self.assertIsNotNone(env, "ask() never reached the operator mailbox")

            self._courier(
                "reply", "--to", f":session:{session_id}", "--in-reply-to", env["id"],
                "--subject", "orchard:operator:message:response",
                "--body", reply_body, session_id="question-broker",
            )
            stdout, stderr = proc.communicate(timeout=5)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()
        self.assertEqual(proc.returncode, 0, stderr)
        return env["body"], json.loads(stdout)

    def test_ask_multi_flag_request_carries_multi_true_and_prints_indices_shape(self):
        body, answer = self._round_trip(
            ["--multi"], '{"indices": [0, 1], "options": ["Yes", "No"]}', "askerMulti",
        )
        self.assertTrue(body["multi"])
        self.assertEqual(answer, {"indices": [0, 1], "options": ["Yes", "No"]})

    def test_ask_without_multi_omits_multi_field(self):
        body, answer = self._round_trip(
            [], '{"index": 1, "option": "No"}', "askerSingle",
        )
        self.assertNotIn("multi", body)
        self.assertEqual(answer, {"index": 1, "option": "No"})

    def test_ask_title_and_summary_carried_in_request_body(self):
        body, _answer = self._round_trip(
            ["--title", "Deploy gate", "--summary", "Ship now or wait."],
            '{"index": 0, "option": "Yes"}', "askerTitled",
        )
        self.assertEqual(body["title"], "Deploy gate")
        self.assertEqual(body["summary"], "Ship now or wait.")

    def test_ask_continue_outcome_prints_continue_sentinel(self):
        _body, answer = self._round_trip(
            [], '{"continue": true}', "askerEscape",
        )
        self.assertEqual(answer, {"continue": True})

    def test_ask_gate_outcome_prints_gate_phrase(self):
        _body, answer = self._round_trip(
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

    def test_broadcast_is_retired_regardless_of_grammar(self):
        """broadcast no longer parses or enforces WIRE GRAMMAR v1 at all — it
        hard-errors unconditionally, pointing at orchard_topic.py post
        (telemetry) or send/request (directed), whether the body would have
        been valid, invalid, or the ask-only interrupt class."""
        self._courier("init", "senderX")
        for body in ("orchid:phase:building", "orchid:status:building", "orchid:interrupt:question:hi"):
            proc = self._courier("broadcast", "--from", "senderX", "--body", body)
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("broadcast is retired", proc.stderr)
            self.assertIn("orchard_topic.py post", proc.stderr)
            self.assertIn("send --to", proc.stderr)


class SignalNotifyLegalityCliTests(unittest.TestCase):
    """CLI-level: `signal --notify-user` is legal only with
    --state done|blocked|abandoned (docs/TODO.md.d/bus-message-specifying.md)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)
        self.runtime_dir = os.path.join(self._tmp.name, "run")
        self.cache_home = os.path.join(self._tmp.name, "cache")
        os.makedirs(self.runtime_dir, exist_ok=True)
        os.makedirs(self.cache_home, exist_ok=True)

    def _courier(self, *args, session_id="s1"):
        env = dict(os.environ)
        env["CLAUDE_CODE_SESSION_ID"] = session_id
        env["XDG_RUNTIME_DIR"] = self.runtime_dir
        env["XDG_CACHE_HOME"] = self.cache_home
        env.pop("ORCHID_PARENT_SESSION", None)
        env.pop("ORCHID_PARENT_PROJECT", None)
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


class OrchardSubjectValidationTests(unittest.TestCase):
    """Unit-level: orchard subject validation is EXACT membership against the
    closed 22-item set (operator ruling, 2026-07-25; `delegation:schedule`
    restored into the set the same day) — no startswith/regex/split
    derivation. A subject the OLD family/prefix validator used to accept by
    pattern (a delegation subject with an appended subagent id, a
    `bus:subscribe:<topic>` with an appended topic) must be rejected
    outright: variable data belongs in the body, not the subject."""

    def test_every_valid_subject_is_accepted(self):
        for subject in courier.ORCHARD_VALID_SUBJECTS:
            self.assertIsNone(courier._orchard_subject_error(subject), subject)

    def test_exactly_22_valid_subjects(self):
        self.assertEqual(len(courier.ORCHARD_VALID_SUBJECTS), 22)

    def test_old_delegation_with_appended_subagent_is_rejected(self):
        self.assertIsNotNone(
            courier._orchard_subject_error("orchard:agent:delegation:begin:builder-1"))

    def test_delegation_schedule_bare_is_accepted(self):
        self.assertIsNone(
            courier._orchard_subject_error("orchard:agent:delegation:schedule"))

    def test_delegation_schedule_with_appended_subagent_is_rejected(self):
        self.assertIsNotNone(
            courier._orchard_subject_error("orchard:agent:delegation:schedule:builder-1"))

    def test_bus_subscribe_with_appended_topic_is_rejected(self):
        self.assertIsNotNone(
            courier._orchard_subject_error("orchard:bus:subscribe:some-topic"))

    def test_bus_subscribe_bare_is_accepted(self):
        self.assertIsNone(courier._orchard_subject_error("orchard:bus:subscribe"))

    def test_unknown_subject_is_rejected(self):
        self.assertIsNotNone(courier._orchard_subject_error("orchard:made:up"))


class OrchardSubjectCliTests(unittest.TestCase):
    """CLI-level: `send --to :session:<id> --subject ...` — exact accept/
    reject over the closed subject set, and gardener-only enforcement on
    orchard:task:outcome:* (a task is fully complete only when the gardener
    says so — now also gated here, not only in orchard_topic.py's do_post,
    since these two subjects are members of the valid set and so now pass
    courier.py's own subject check on a hand-sent send)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.runtime_dir = base / "run"
        self.runtime_dir.mkdir()
        self.cache_home = base / "cache"
        self.cache_home.mkdir()
        self.home = base / "home"
        self.home.mkdir()
        self.repo = make_repo(str(base))

    def _env(self, session_id, **extra):
        env = {k: v for k, v in os.environ.items()
               if k not in ("ORCHID_PARENT_SESSION", "ORCHID_PARENT_PROJECT", "CLAUDE_CODE_AGENT")}
        env.update(
            CLAUDE_CODE_SESSION_ID=session_id,
            XDG_RUNTIME_DIR=str(self.runtime_dir), XDG_CACHE_HOME=str(self.cache_home),
            HOME=str(self.home),
        )
        env.update(extra)
        return env

    def _send(self, subject, session_id="senderX", **extra_env):
        return subprocess.run(
            [sys.executable, _COURIER_PY, "send", "--to", ":session:recipientA",
             "--subject", subject],
            cwd=self.repo, capture_output=True, text=True,
            env=self._env(session_id, **extra_env),
        )

    def test_valid_subject_is_accepted(self):
        proc = self._send("orchard:agent:status")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_off_list_subject_is_rejected(self):
        proc = self._send("orchard:agent:delegation:begin:builder-1")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unknown orchard subject", proc.stderr)

    def test_delegation_schedule_with_appended_subagent_is_rejected(self):
        proc = self._send("orchard:agent:delegation:schedule:builder-1")
        self.assertNotEqual(proc.returncode, 0)

    def test_delegation_schedule_bare_subject_is_accepted(self):
        proc = self._send("orchard:agent:delegation:schedule")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_delegation_begin_exact_subject_is_accepted(self):
        proc = self._send("orchard:agent:delegation:begin")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_task_outcome_by_non_gardener_is_rejected(self):
        proc = self._send("orchard:task:outcome:completed")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("gardener", proc.stderr)

    def test_task_outcome_completed_by_gardener_is_accepted(self):
        proc = self._send("orchard:task:outcome:completed", CLAUDE_CODE_AGENT="gardener")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_task_outcome_failed_by_gardener_is_accepted(self):
        proc = self._send("orchard:task:outcome:failed", CLAUDE_CODE_AGENT="gardener")
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()

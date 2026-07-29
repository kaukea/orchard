"""Unit tests for tools/courier.py's session-message relaying families
(docs/courier-wire.md §2 — the operator/agent `orchard:*:message:*` subject
families, structural provenance, and the agent-family priority classes), and
the `ask`/answer question protocol (sidebar-polish item 12c-f).

Mirrors the notify_user coverage style used elsewhere in this suite (see
tests/test_sidebar_model.py, tests/support.py): a real git-init'd temp repo,
the module under test exercised end to end rather than mocked.

Runs under both `python3 -m unittest discover` and `pytest`.
"""
import fcntl
import json
import os
import re
import select
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

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


class StructuralProvenanceTests(unittest.TestCase):
    """Unit-level: the operator/agent relaying families carry provenance in
    the SUBJECT, not an envelope flag — `operator_origin` dissolved into this
    split (docs/courier-wire.md §2, "ruled 2026-07-29")."""

    def test_operator_message_subjects_are_operator_authority(self):
        for subject in (
            "orchard:operator:message:todo", "orchard:operator:message:instructions",
            "orchard:operator:message:request", "orchard:operator:message:response",
            "orchard:operator:message:content",
        ):
            self.assertTrue(courier.is_operator_authority(subject), subject)

    def test_agent_message_subjects_are_not_operator_authority(self):
        for subject in (
            "orchard:agent:message:request", "orchard:agent:message:response",
            "orchard:agent:message:content", "orchard:agent:status",
        ):
            self.assertFalse(courier.is_operator_authority(subject), subject)

    def test_make_envelope_carries_no_operator_origin_field(self):
        env = courier.make_envelope("senderX", "recipientA")
        self.assertNotIn("operator_origin", env)

    def test_make_orchard_envelope_carries_no_operator_origin_field(self):
        env = courier.make_orchard_envelope(
            ":session:senderX", ":session:recipientA", "orchard:operator:message:content",
        )
        self.assertNotIn("operator_origin", env)

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_schema_no_longer_declares_operator_origin(self):
        self.assertNotIn("operator_origin", _schema()["properties"])


class RelayingFamilyCliTests(unittest.TestCase):
    """CLI-level: the two relaying families over the real orchard `:session:`
    transport. `--operator-origin` is gone outright — the operator family
    subject itself is the provenance, so sending on it needs no flag."""

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

    def _env(self, session_id):
        return dict(
            os.environ, CLAUDE_CODE_SESSION_ID=session_id,
            XDG_RUNTIME_DIR=str(self.runtime_dir), XDG_CACHE_HOME=str(self.cache_home),
            HOME=str(self.home),
        )

    def _courier(self, session_id, *args, check=True):
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=self.repo, check=check, capture_output=True, text=True,
            env=self._env(session_id),
        )

    def test_operator_message_round_trips_with_no_flag_needed(self):
        self._courier(
            "senderX", "send", "--to", ":session:recipientA",
            "--subject", "orchard:operator:message:content", "--body", "hello",
        )

        out = self._courier("recipientA", "receive")
        messages = json.loads(out.stdout)

        self.assertEqual(len(messages), 1)
        msg = messages[0]
        self.assertNotIn("operator_origin", msg)
        self.assertEqual(msg["subject"], "orchard:operator:message:content")
        self.assertTrue(courier.is_operator_authority(msg["subject"]))
        self.assertEqual(msg["from"], ":session:senderX")
        self.assertEqual(msg["body"], "hello")

        if jsonschema is not None:
            jsonschema.validate(instance=msg, schema=_schema())

    def test_operator_origin_flag_no_longer_recognised(self):
        proc = self._courier(
            "senderX", "send", "--to", ":session:recipientA",
            "--subject", "orchard:operator:message:content",
            "--operator-origin", "--body", "hello", check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unrecognized arguments", proc.stderr)

    def test_operator_subject_rejects_non_immediate_priority(self):
        proc = self._courier(
            "senderX", "send", "--to", ":session:recipientA",
            "--subject", "orchard:operator:message:content",
            "--body", "hello", "--priority", "batch", check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("always immediate", proc.stderr)

    def test_agent_message_default_priority_is_immediate_direct_write(self):
        self._courier(
            "senderX", "send", "--to", ":session:recipientA",
            "--subject", "orchard:agent:message:content", "--body", "hi",
        )
        out = json.loads(self._courier("recipientA", "receive").stdout)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["body"], "hi")
        # immediate never queues: nothing was left in the outbox
        box = courier.outbox_dir()
        self.assertEqual(list(box.glob("*.json")) if box.is_dir() else [], [])


class WakeFilterTests(unittest.TestCase):
    """Unit-level: `_wait_for_orchard_activity` — the blocking wait used by
    `request`/`ask` — filters its inotifywait watch to exactly the recipient's
    own reply pattern (docs/courier-wire.md §4, "[GAP, remaining]"), the same
    `--include` regex `monitor`'s own mailbox source already uses, instead of
    waking on every sibling session's traffic in the shared project
    directory."""

    def test_activity_wait_includes_the_recipients_own_pattern(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0)

        with mock.patch("courier.shutil.which", return_value="/usr/bin/inotifywait"), \
             mock.patch("courier.subprocess.run", side_effect=fake_run):
            courier._wait_for_orchard_activity(Path("/tmp/some-project-dir"), "recipientA", 1.0)

        cmd = captured["cmd"]
        self.assertIn("--include", cmd)
        include_value = cmd[cmd.index("--include") + 1]
        self.assertEqual(include_value, courier._own_mailbox_path_filter("recipientA"))

    def test_activity_wait_filter_matches_own_reply_not_a_sibling(self):
        pattern = courier._own_mailbox_path_filter("recipientA")
        self.assertIsNotNone(re.search(pattern, "/some/dir/recipientA.2026-01-01T00-00-00.000000.json"))
        self.assertIsNone(re.search(pattern, "/some/dir/siblingB.2026-01-01T00-00-00.000000.json"))
        self.assertIsNone(re.search(pattern, "/some/dir/recipientA.marker"))


class PriorityQueueingTests(unittest.TestCase):
    """Unit-level: batch/wait-a-round priority queues into the outbox
    instead of writing straight through, and the flusher (`_drain_outbox`)
    replays it exactly like an immediate send would have."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.runtime_dir = base / "run"
        self.runtime_dir.mkdir()
        self._patch_env = mock.patch.dict(
            os.environ, {"XDG_RUNTIME_DIR": str(self.runtime_dir)},
        )
        self._patch_env.start()
        self.addCleanup(self._patch_env.stop)

    def test_batch_priority_enqueues_rather_than_writes_directly(self):
        target = self.runtime_dir / "orchard" / "projects" / "own.repo@main"
        env = courier.make_orchard_envelope(
            ":session:senderX", ":session:recipientA",
            "orchard:agent:message:content", body="queued",
        )
        courier.deliver_with_priority(target, "recipientA", env, "batch")

        self.assertFalse(target.is_dir() and any(target.glob("recipientA.*.json")),
                          "batch priority wrote directly instead of queueing")
        queued = list(courier.outbox_dir().glob("*.json"))
        self.assertEqual(len(queued), 1)

    def test_drain_outbox_delivers_and_empties_the_queue(self):
        target = self.runtime_dir / "orchard" / "projects" / "own.repo@main"
        env = courier.make_orchard_envelope(
            ":session:senderX", ":session:recipientA",
            "orchard:agent:message:content", body="queued",
        )
        courier.deliver_with_priority(target, "recipientA", env, "batch")

        drained = courier._drain_outbox()
        self.assertEqual(drained, 1)
        self.assertEqual(list(courier.outbox_dir().glob("*.json")), [])
        delivered = list(target.glob("recipientA.*.json"))
        self.assertEqual(len(delivered), 1)
        self.assertEqual(json.loads(delivered[0].read_text())["body"], "queued")

    def test_immediate_priority_never_queues(self):
        target = self.runtime_dir / "orchard" / "projects" / "own.repo@main"
        env = courier.make_orchard_envelope(
            ":session:senderX", ":session:recipientA",
            "orchard:agent:message:content", body="now",
        )
        courier.deliver_with_priority(target, "recipientA", env, "immediate")

        self.assertTrue(any(target.glob("recipientA.*.json")))
        self.assertFalse(courier.outbox_dir().is_dir()
                          and list(courier.outbox_dir().glob("*.json")))


class OutboxFlusherProcessTests(unittest.TestCase):
    """CLI-level: the real `flush-outbox` subprocess — lockfile-singleton,
    drains on a cadence, and closes itself once a drain finds nothing left
    (Decision-129's owner-closes shape)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.runtime_dir = Path(self._tmp.name) / "run"
        self.runtime_dir.mkdir()

    def _env(self):
        return dict(os.environ, XDG_RUNTIME_DIR=str(self.runtime_dir))

    def test_flusher_drains_a_queued_entry_then_exits_on_an_empty_drain(self):
        outbox = self.runtime_dir / "orchard" / "outbox"
        outbox.mkdir(parents=True)
        target = self.runtime_dir / "orchard" / "projects" / "own.repo@main"
        entry = {
            "dir": str(target), "sid": "recipientA",
            "envelope": {
                "id": "e1", "ts": "2026-01-01T00-00-00.000000",
                "from": ":session:senderX", "to": ":session:recipientA",
                "subject": "orchard:agent:message:content", "body": "flushed",
            },
        }
        (outbox / "q1.json").write_text(json.dumps(entry), encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, _COURIER_PY, "flush-outbox", "--interval", "0.2"],
            env=self._env(), capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(list(outbox.glob("*.json")), [])
        delivered = list(target.glob("recipientA.*.json"))
        self.assertEqual(len(delivered), 1)
        self.assertEqual(json.loads(delivered[0].read_text())["body"], "flushed")

    def test_second_flusher_loses_the_lock_and_exits_immediately(self):
        lock_path = self.runtime_dir / "orchard" / "outbox.flusher.lock"
        lock_path.parent.mkdir(parents=True)
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        start = time.monotonic()
        proc = subprocess.run(
            [sys.executable, _COURIER_PY, "flush-outbox", "--interval", "5"],
            env=self._env(), capture_output=True, text=True, timeout=10,
        )
        elapsed = time.monotonic() - start
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(elapsed, 4, "second flusher should lose the lock race instantly")


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
    """CLI-level: WIRE GRAMMAR v1 enforcement in `send`
    (docs/TODO.md.d/bus-message-specifying.md) — valid orchid:* bodies pass,
    malformed/unknown ones argparse-error out naming the allowed classes.

    Exercised over the orchard `:session:` transport — the legacy per-agent
    mailbox this used to run against via `init` + a plain address is gone
    (operator ruling, 2026-07-27). `enforce_orchid_grammar` now runs for
    every `send` (it used to run only on the removed legacy branch; moved
    rather than dropped, since an orchard `--body` can carry an orchid:*
    string exactly as a legacy one could) — see broadcast's OWN retirement
    test in BroadcastRetiredCliTests, split out below since broadcast never
    reaches this grammar at all (it hard-errors unconditionally)."""

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

    def _courier(self, *args):
        env = dict(
            os.environ, CLAUDE_CODE_SESSION_ID="senderX",
            XDG_RUNTIME_DIR=str(self.runtime_dir), XDG_CACHE_HOME=str(self.cache_home),
            HOME=str(self.home),
        )
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=self.repo, capture_output=True, text=True, env=env,
        )

    def _send(self, body, *extra):
        return self._courier(
            "send", "--to", ":session:peerA",
            "--subject", "orchard:agent:message:content",
            "--body", body, *extra,
        )

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


class BroadcastRetiredCliTests(unittest.TestCase):
    """CLI-level: `broadcast` hard-errors unconditionally, pointing at
    orchard_topic.py post (telemetry) or send/request (directed) — split out
    of OrchidGrammarCliTests since it never reaches WIRE GRAMMAR v1 at all,
    valid, invalid, or the ask-only interrupt class, and has no dependency
    on any mailbox (legacy or orchard)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)

    def _courier(self, *args):
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=self.repo, capture_output=True, text=True,
        )

    def test_broadcast_is_retired_regardless_of_grammar(self):
        for body in ("orchid:phase:building", "orchid:status:building", "orchid:interrupt:question:hi"):
            proc = self._courier("broadcast", "--from", "senderX", "--body", body)
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("broadcast is retired", proc.stderr)
            self.assertIn("orchard_topic.py post", proc.stderr)
            self.assertIn("send --to", proc.stderr)


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


class MonitorCliTests(unittest.TestCase):
    """CLI-level: `courier.py monitor` (close-family-fakes) — filters at the
    orchard SOURCE (inotifywait --include, verified working pattern
    `/<sid>\\..*\\.json$`) rather than waking on every sibling session's
    traffic and every marker touch, and hands up the PARSED envelope itself
    instead of a filename to go look up. Reuses orchard_receive_own() for
    the actual parse/delete, so delete-on-consumption semantics carry over
    unchanged. Every assertion here is on a BOUNDED wait — a monitor that
    never fires must not hang the suite."""

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

    def _env(self, session_id):
        return dict(
            os.environ, CLAUDE_CODE_SESSION_ID=session_id,
            XDG_RUNTIME_DIR=str(self.runtime_dir), XDG_CACHE_HOME=str(self.cache_home),
            HOME=str(self.home),
        )

    def _courier(self, session_id, *args):
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=self.repo, check=True, capture_output=True, text=True,
            env=self._env(session_id),
        )

    def _project_dir(self):
        proc = subprocess.run(
            [sys.executable, _COURIER_PY, "project-dir"],
            cwd=self.repo, capture_output=True, text=True,
            env=self._env("dir-probe"), check=True,
        )
        return Path(proc.stdout.strip())

    def _stop_monitor(self, proc):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)

    def _start_monitor(self, session_id):
        proc = subprocess.Popen(
            [sys.executable, _COURIER_PY, "monitor"],
            cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=self._env(session_id), bufsize=1,
        )
        self.addCleanup(self._stop_monitor, proc)
        return proc

    def _readline_within(self, proc, timeout):
        ready, _, _ = select.select([proc.stdout], [], [], timeout)
        if not ready:
            return None
        return proc.stdout.readline()

    def _remaining_files(self, sid):
        box = self._project_dir()
        return [f for f in box.glob(f"{sid}.*.json") if not f.name.startswith(".")]

    def test_message_addressed_to_this_session_appears_as_parsed_json(self):
        proc = self._start_monitor("recipientA")
        self._courier(
            "senderX", "send", "--to", ":session:recipientA",
            "--subject", "orchard:agent:message:content", "--body", "hello there",
        )

        line = self._readline_within(proc, 10)
        self.assertIsNotNone(line, "monitor produced no output for its own mail within 10s")
        env = json.loads(line)
        self.assertEqual(env["to"], ":session:recipientA")
        self.assertEqual(env["body"], "hello there")
        self.assertEqual(self._remaining_files("recipientA"), [])  # consumed, delete-on-read

    def test_sibling_session_message_does_not_wake_it(self):
        proc = self._start_monitor("recipientA")
        self._courier(
            "senderX", "send", "--to", ":session:siblingB",
            "--subject", "orchard:agent:message:content", "--body", "not for you",
        )

        self.assertIsNone(
            self._readline_within(proc, 2),
            "monitor woke on a sibling session's message in the same project directory",
        )

    def test_marker_touch_does_not_wake_it(self):
        proc = self._start_monitor("recipientA")
        box = self._project_dir()
        box.mkdir(parents=True, exist_ok=True)
        (box / "recipientA.marker").touch()

        self.assertIsNone(
            self._readline_within(proc, 2),
            "monitor woke on its own marker heartbeat touch",
        )

    def test_reply_in_flight_is_left_for_the_request_waiter(self):
        """A running monitor must not steal an envelope a blocked
        `request`/`ask` caller is polling for (docs: the reply-race the
        operator flagged) — it is left on disk, untouched, while an
        ordinary unsolicited message alongside it is still delivered."""
        proc = self._start_monitor("recipientA")
        self._courier(
            "question-broker", "reply", "--to", ":session:recipientA",
            "--in-reply-to", "req-123", "--subject", "orchard:operator:message:response",
            "--body", "the answer",
        )

        self.assertIsNone(
            self._readline_within(proc, 2),
            "monitor printed a reply that a request/ask waiter is owed",
        )
        remaining = self._remaining_files("recipientA")
        self.assertEqual(len(remaining), 1, "monitor deleted a reply it should have left untouched")

        self._courier(
            "senderY", "send", "--to", ":session:recipientA",
            "--subject", "orchard:agent:message:content", "--body", "unsolicited",
        )
        line = self._readline_within(proc, 10)
        self.assertIsNotNone(line, "monitor did not deliver an ordinary message alongside a held reply")
        self.assertEqual(json.loads(line)["body"], "unsolicited")
        self.assertEqual(len(self._remaining_files("recipientA")), 1)  # only the untouched reply left

    def test_monitor_leaves_no_watcher_process_behind_on_termination(self):
        proc = self._start_monitor("recipientA")
        self._readline_within(proc, 1)  # let it actually arm its watch
        pid = proc.pid
        self._stop_monitor(proc)

        check = subprocess.run(
            ["pgrep", "-f", "inotifywait.*recipientA"],
            capture_output=True, text=True,
        )
        self.assertEqual(
            check.stdout.strip(), "",
            f"a watcher spawned by monitor (pid {pid}) is still running: {check.stdout!r}",
        )

    def test_monitor_wakes_on_a_subscribed_topic_publish(self):
        """`_monitor_sources` folds in one source per subscribed topic
        (docs/courier-wire.md §2 PubSub) alongside the own-mailbox source —
        `monitor` must wake on both, not just direct mail."""
        self._courier("recipientA", "subscribe", "--topic", "widgets")
        proc = self._start_monitor("recipientA")
        self._courier(
            "publisherX", "send", "--to", ":topic:widgets",
            "--subject", "orchard:agent:message:content", "--body", "topic hello",
        )

        line = self._readline_within(proc, 10)
        self.assertIsNotNone(line, "monitor produced no output for a subscribed topic publish")
        env = json.loads(line)
        self.assertEqual(env["to"], ":topic:widgets")
        self.assertEqual(env["body"], "topic hello")


if __name__ == "__main__":
    unittest.main()

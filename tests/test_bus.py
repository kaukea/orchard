"""Unit tests for tools/bus.py's operator_origin provenance flag.

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
import unittest

try:
    import jsonschema
except ImportError:  # pragma: no cover - environment-dependent
    jsonschema = None

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import bus  # noqa: E402

from support import make_repo  # noqa: E402

_SCHEMA_PATH = os.path.join(_TOOLS_DIR, "message.schema.json")
_BUS_PY = os.path.join(_TOOLS_DIR, "bus.py")


def _schema() -> dict:
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


class MakeEnvelopeTests(unittest.TestCase):
    """Unit-level: make_envelope() itself, no subprocess involved."""

    def test_operator_origin_true_is_present(self):
        env = bus.make_envelope("senderX", "recipientA", operator_origin=True)
        self.assertTrue(env["operator_origin"])

    def test_operator_origin_false_is_absent(self):
        env = bus.make_envelope("senderX", "recipientA")
        self.assertNotIn("operator_origin", env)

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_operator_origin_envelope_validates_against_schema(self):
        env = bus.make_envelope("senderX", "recipientA", operator_origin=True)
        jsonschema.validate(instance=env, schema=_schema())


class IdentityOfExitGraceTests(unittest.TestCase):
    """Unit-level: identity_of()'s exit_grace_seconds field, no subprocess."""

    def test_default_is_ten_seconds(self):
        self.assertEqual(bus.identity_of()["exit_grace_seconds"], 10)
        self.assertEqual(bus.DEFAULT_EXIT_GRACE_SECONDS, 10)

    def test_override_is_carried_through(self):
        self.assertEqual(bus.identity_of(30)["exit_grace_seconds"], 30)


class CliRoundTripTests(unittest.TestCase):
    """CLI-level: `send --operator-origin` then `receive`, in a real repo."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)

    def _bus(self, *args):
        return subprocess.run(
            [sys.executable, _BUS_PY, *args],
            cwd=self.repo, check=True, capture_output=True, text=True,
        )

    def test_operator_origin_round_trips_through_send_and_receive(self):
        self._bus("init", "recipientA")
        self._bus(
            "send", "--from", "senderX", "--to", "recipientA",
            "--operator-origin", "--body", "hello",
        )

        out = self._bus("receive", "recipientA")
        messages = json.loads(out.stdout)

        self.assertEqual(len(messages), 1)
        msg = messages[0]
        self.assertTrue(msg["operator_origin"])
        self.assertEqual(msg["from"], "senderX")
        self.assertEqual(msg["body"], "hello")

        if jsonschema is not None:
            jsonschema.validate(instance=msg, schema=_schema())

    def test_broadcast_operator_origin_round_trips(self):
        self._bus("init", "senderX")
        self._bus("init", "recipientA")
        self._bus("broadcast", "--from", "senderX", "--operator-origin", "--body", "hi")

        out = self._bus("receive", "recipientA")
        messages = json.loads(out.stdout)

        self.assertEqual(len(messages), 1)
        self.assertTrue(messages[0]["operator_origin"])


class AnnounceExitGraceCliTests(unittest.TestCase):
    """CLI-level: `announce --exit-grace-seconds N` reaches peers on the field,
    and omitting the flag still defaults to 10 (identity_of()'s default)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)

    def _bus(self, *args, session_id):
        env = dict(os.environ, CLAUDE_CODE_SESSION_ID=session_id)
        return subprocess.run(
            [sys.executable, _BUS_PY, *args],
            cwd=self.repo, check=True, capture_output=True, text=True, env=env,
        )

    def test_exit_grace_seconds_flag_is_broadcast(self):
        self._bus("init", "peerA", session_id="peerA")
        self._bus("announce", "--exit-grace-seconds", "45", session_id="announcerX")

        out = self._bus("receive", "peerA", session_id="peerA")
        messages = json.loads(out.stdout)

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["body"]["exit_grace_seconds"], 45)
        self.assertEqual(messages[0]["from"], "announcerX")

    def test_announce_without_flag_defaults_to_ten(self):
        self._bus("init", "peerB", session_id="peerB")
        self._bus("announce", session_id="announcerY")

        out = self._bus("receive", "peerB", session_id="peerB")
        messages = json.loads(out.stdout)

        self.assertEqual(messages[0]["body"]["exit_grace_seconds"], 10)


class SignalOnBehalfOfTests(unittest.TestCase):
    """CLI-level: `signal --on-behalf-of ID` attributes the envelope to ID, not
    the caller — the orchestrator's path for broadcasting a killed agent's own
    terminal lifecycle signal (docs/TODO.md.d/sidebar-polish.md item 2)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)

    def _bus(self, *args, session_id):
        env = dict(os.environ, CLAUDE_CODE_SESSION_ID=session_id)
        return subprocess.run(
            [sys.executable, _BUS_PY, *args],
            cwd=self.repo, check=True, capture_output=True, text=True, env=env,
        )

    def test_on_behalf_of_sets_envelope_from(self):
        self._bus("init", "watcher", session_id="watcher")
        # the orchestrator's own session ("orchestratorZ") issues the signal,
        # naming the killed architect ("killed-arch-1") as the sender.
        self._bus(
            "signal", "--state", "abandoned", "--feature", "some-feature",
            "--on-behalf-of", "killed-arch-1", session_id="orchestratorZ",
        )

        out = self._bus("receive", "watcher", session_id="watcher")
        messages = json.loads(out.stdout)

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["from"], "killed-arch-1")
        self.assertEqual(messages[0]["body"]["state"], "abandoned")
        self.assertEqual(messages[0]["body"]["feature_id"], "some-feature")

    def test_without_on_behalf_of_signal_still_uses_caller(self):
        self._bus("init", "watcher2", session_id="watcher2")
        self._bus(
            "signal", "--state", "finished", "--feature", "own-feature",
            session_id="selfSignallerA",
        )

        out = self._bus("receive", "watcher2", session_id="watcher2")
        messages = json.loads(out.stdout)

        self.assertEqual(messages[0]["from"], "selfSignallerA")


if __name__ == "__main__":
    unittest.main()

"""Unit tests for hooks/courier-only-transport.sh — the PreToolUse gate that
makes an agent structurally unable to post on the transport without going
through its courier subagent (operator ruling, see docs/decisions.md).

The hook's decision logic is pure: JSON on stdin, a decision out. So it is
exercised directly here by piping synthetic PreToolUse payloads at the real
script and asserting on stdout, with no harness involved.
"""
import json
import os
import subprocess
import unittest

_HOOK = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "hooks", "courier-only-transport.sh",
)


def _run(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_HOOK], input=json.dumps(payload), capture_output=True, text=True,
        check=False,
    )


def _payload(agent_type, command) -> dict:
    body = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": command}}
    if agent_type is not None:
        body["agent_type"] = agent_type
    return body


def _is_deny(result: subprocess.CompletedProcess) -> bool:
    if not result.stdout.strip():
        return False
    out = json.loads(result.stdout)
    decision = out.get("hookSpecificOutput", {}).get("permissionDecision")
    return decision == "deny"


class CourierOnlyTransportHookTests(unittest.TestCase):

    def test_courier_posting_is_allowed(self) -> None:
        result = _run(_payload("courier", "python3 tools/courier.py send --to :session:x --body hi"))
        self.assertEqual(result.returncode, 0)
        self.assertFalse(_is_deny(result))

    def test_main_agent_posting_is_denied(self) -> None:
        result = _run(_payload("sower", "python3 tools/courier.py send --to :session:x --body hi"))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_courier_unrelated_command_is_allowed(self) -> None:
        result = _run(_payload("courier", "ls -la"))
        self.assertEqual(result.returncode, 0)
        self.assertFalse(_is_deny(result))

    def test_main_agent_unrelated_command_is_allowed(self) -> None:
        result = _run(_payload("sower", "ls -la"))
        self.assertEqual(result.returncode, 0)
        self.assertFalse(_is_deny(result))

    def test_missing_agent_type_posting_is_denied(self) -> None:
        result = _run(_payload(None, "python3 tools/courier.py send --to :session:x --body hi"))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_orchard_topic_post_is_denied_for_non_courier(self) -> None:
        result = _run(_payload("landscaper", "python3 tools/orchard_topic.py post status --body hi"))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_signal_ask_announce_variants_are_denied_for_non_courier(self) -> None:
        for sub in ("signal", "ask", "announce"):
            with self.subTest(sub=sub):
                result = _run(_payload("sower", "python3 tools/courier.py %s --to :session:x" % sub))
                self.assertTrue(_is_deny(result))

    def test_grep_for_courier_send_string_is_allowed(self) -> None:
        result = _run(_payload("sower", 'grep -rn "courier.py signal" agents/*.md'))
        self.assertEqual(result.returncode, 0)
        self.assertFalse(_is_deny(result))

    def test_grep_for_orchard_topic_post_string_is_allowed(self) -> None:
        result = _run(_payload("sower", 'grep -n "orchard_topic.py post" agents/gardener.md'))
        self.assertEqual(result.returncode, 0)
        self.assertFalse(_is_deny(result))

    def test_echo_mentioning_courier_send_is_allowed(self) -> None:
        result = _run(_payload("sower", 'echo "run courier.py send later"'))
        self.assertEqual(result.returncode, 0)
        self.assertFalse(_is_deny(result))

    def test_direct_orchard_topic_invocation_is_denied_for_non_courier(self) -> None:
        result = _run(_payload("sower", 'python3 tools/orchard_topic.py post status "x"'))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_invocation_after_cd_and_and_is_denied_for_non_courier(self) -> None:
        result = _run(_payload("sower", "cd /tmp && python3 tools/courier.py send --to :topic:x"))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_invocation_after_semicolon_is_denied_for_non_courier(self) -> None:
        result = _run(_payload("sower", "ls; python3 tools/courier.py signal --state done"))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_direct_invocation_is_allowed_for_courier(self) -> None:
        result = _run(_payload("courier", "python3 tools/courier.py send --to :topic:x"))
        self.assertEqual(result.returncode, 0)
        self.assertFalse(_is_deny(result))

    def test_invocation_with_leading_env_assignment_is_denied_for_non_courier(self) -> None:
        result = _run(_payload("sower", "FOO=bar python3 tools/courier.py send --to :topic:x"))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_quoted_env_assignment_with_space_is_denied_for_non_courier(self) -> None:
        result = _run(_payload("sower", 'FOO="a b" python3 tools/courier.py send --to :topic:x'))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_bash_c_wrapped_invocation_is_denied_for_non_courier(self) -> None:
        result = _run(_payload("sower", "bash -c 'python3 tools/courier.py send --to :topic:x'"))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_eval_wrapped_invocation_is_denied_for_non_courier(self) -> None:
        result = _run(_payload("sower", 'eval "python3 tools/courier.py send --to :topic:x"'))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_python_c_import_courier_is_denied_for_non_courier(self) -> None:
        result = _run(_payload("sower", "python3 -c 'import courier; courier.orchard_deliver(1)'"))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_python_c_import_orchard_topic_is_denied_for_non_courier(self) -> None:
        result = _run(_payload("sower", 'python3 -c "import orchard_topic; orchard_topic.post()"'))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_command_substitution_wrapped_invocation_is_denied_for_non_courier(self) -> None:
        result = _run(_payload("sower", "$(python3 tools/courier.py send --to :topic:x)"))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))

    def test_backtick_wrapped_invocation_is_denied_for_non_courier(self) -> None:
        result = _run(_payload("sower", "`python3 tools/courier.py send --to :topic:x`"))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(_is_deny(result))


if __name__ == "__main__":
    unittest.main()

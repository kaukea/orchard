"""The agent-communication seam, through the real CLI.

Three separate processes — a sender, the dispatch, a receiver — sharing
nothing but the filesystem, exactly as two agents and the dispatch would.
Ruled by the feature's testing doctrine: the seam everyone always skips.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).parent.parent / "tools"


def run(script: str, *args: str, tmp: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOLS / script), *args],
        capture_output=True, text=True,
        env={"XDG_RUNTIME_DIR": tmp},
    )


class SeamTests(unittest.TestCase):
    def test_send_dispatch_receive_across_three_processes(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = "seam-proof body with ünïcode"
            sent = run("boxes.py", "send", "--from-sid", "agent-a",
                       "--to", ":session:agent-b",
                       "--subject", "orchard:agent:message:content",
                       "--body", body, tmp=tmp)
            self.assertEqual(sent.returncode, 0, sent.stderr)

            moved = run("dispatch.py", "once", tmp=tmp)
            self.assertEqual(moved.returncode, 0, moved.stderr)
            self.assertEqual(json.loads(moved.stdout),
                             {"delivered": 1, "quarantined": 0})

            received = run("boxes.py", "receive", "--sid", "agent-b", tmp=tmp)
            self.assertEqual(received.returncode, 0, received.stderr)
            messages = json.loads(received.stdout)
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["body"], body)
            self.assertEqual(messages[0]["from"], ":session:agent-a")

            again = run("boxes.py", "receive", "--sid", "agent-b", tmp=tmp)
            self.assertEqual(json.loads(again.stdout), [])

    def test_sender_cli_refuses_an_invented_subject(self):
        with tempfile.TemporaryDirectory() as tmp:
            sent = run("boxes.py", "send", "--from-sid", "agent-a",
                       "--to", ":session:agent-b",
                       "--subject", "orchard:agent:signal:finished", tmp=tmp)
            self.assertEqual(sent.returncode, 1)
            self.assertIn("rejected", sent.stderr)


if __name__ == "__main__":
    unittest.main()

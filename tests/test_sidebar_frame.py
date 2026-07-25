"""Emulator frame check for tools/sidebar.py's curses renderer.

Runs the REAL curses app inside a detached tmux pane, against a fixture courier
built from the scenario baked into the blessed reference frame
(.git/the-works/bus-message-specifying/approved-frame.ans and its generator,
sidebar-mock.py) — the source of truth for the visual grammar declared in
sidebar.py's own module docstring (bus-message-specifying B5).

Assertions are SEMANTIC (glyphs, text, colour family) rather than a byte
diff against the mock: curses may map truecolor down to the nearest
xterm-256 index depending on what the terminal advertises, and the working
row's band sweep animates. Colour-family checks accept either the mock's
exact truecolor RGB or tools/sidebar.py's own `_rgb_to_xterm256` fallback
for that RGB — never a hand-guessed index.

Skips cleanly (unittest.skipUnless) when tmux is not on PATH.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sidebar  # noqa: E402
import sidebar_model  # noqa: E402

from support import envelope, identity_body, lifecycle_body, write_message  # noqa: E402

_SIDEBAR_PY = os.path.join(_TOOLS_DIR, "sidebar.py")
_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")

_HAS_TMUX = shutil.which("tmux") is not None


def _make_named_repo(tmp_root: str, name: str) -> str:
    repo_dir = os.path.join(tmp_root, name)
    os.makedirs(repo_dir, exist_ok=True)
    subprocess.run(
        ["git", "init", "--quiet"], cwd=repo_dir, check=True,
        capture_output=True, text=True,
    )
    return repo_dir


def _strip_sgr(raw_line: str) -> str:
    return _SGR_RE.sub("", raw_line)


def _sgr_code_lists(raw_line: str) -> list[list[str]]:
    return [codes.split(";") for codes in _SGR_RE.findall(raw_line)]


def _has_subsequence(codes: list[str], pattern: list[str]) -> bool:
    n = len(pattern)
    return any(codes[i:i + n] == pattern for i in range(len(codes) - n + 1))


def _has_fg(raw_line: str, rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    true_pattern = ["38", "2", str(r), str(g), str(b)]
    index_pattern = ["38", "5", str(sidebar._rgb_to_xterm256(rgb))]
    return any(
        _has_subsequence(codes, true_pattern) or _has_subsequence(codes, index_pattern)
        for codes in _sgr_code_lists(raw_line)
    )


def _has_any_bg(raw_line: str) -> bool:
    for codes in _sgr_code_lists(raw_line):
        for i, code in enumerate(codes):
            if code == "48" and i + 1 < len(codes) and codes[i + 1] in ("2", "5"):
                return True
    return False


def _has_basic_red(raw_line: str) -> bool:
    return any("31" in codes or "41" in codes for codes in _sgr_code_lists(raw_line))


@unittest.skipUnless(_HAS_TMUX, "tmux not available in this environment")
class SidebarEmulatorFrameTests(unittest.TestCase):
    """One fixture fleet — an orchids repo with a done feature and a working
    feature, plus a signmc repo with an open-question feature — rendered by
    the real curses app in a detached tmux pane and captured with SGR."""

    PANE_WIDTH = 29
    PANE_HEIGHT = 50

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.orchids_repo = _make_named_repo(self._tmp.name, "orchids")
        self.signmc_repo = _make_named_repo(self._tmp.name, "signmc")
        self._seed_orchids_courier()
        self._seed_signmc_courier()
        self._repolist_path = os.path.join(self._tmp.name, "repolist.txt")
        Path(self._repolist_path).write_text(
            f"{self.orchids_repo}\n{self.signmc_repo}\n", encoding="utf-8",
        )
        self._socket = f"sidebar-frame-{uuid.uuid4().hex[:8]}"
        self.addCleanup(self._kill_tmux_server)

    def _kill_tmux_server(self) -> None:
        self._tmux("kill-server")

    def _tmux(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["tmux", "-L", self._socket, *args], check=check,
            capture_output=True, text=True,
        )

    def _courier_root(self, repo_path: str) -> Path:
        roots = sidebar_model.iter_courier_roots([repo_path])
        assert roots, f"no courier root resolved for {repo_path}"
        return roots[0]

    def _put(self, courier_root, folder, msg_id, sender, body, notify_user=None) -> None:
        write_message(
            courier_root, folder,
            envelope(msg_id, sender, body=body, notify_user=notify_user),
        )

    def _put_question(self, courier_root, folder, msg_id, sender, question_id, subject) -> None:
        env = envelope(
            msg_id, sender, body=f"orchid:interrupt:question:{subject}", notify_user=True,
        )
        env["question_id"] = question_id
        write_message(courier_root, folder, env)

    def _seed_orchids_courier(self) -> None:
        courier_root = self._courier_root(self.orchids_repo)

        done_session = "orch-bloomer"
        self._put(courier_root, done_session, "d-id", done_session,
                   identity_body(done_session, agent_type="landscaper",
                                 feature_id="bloomer-v1", name="bloomer v1"))
        self._put(courier_root, done_session, "d-fin", done_session,
                   lifecycle_body("finished", feature_id="bloomer-v1"))

        live_session = "orch-arch"
        identity = identity_body(live_session, agent_type="landscaper",
                                  feature_id="sidebar-titling", name="sidebar titling")
        identity["model"] = "opus-4.8"
        self._put(courier_root, live_session, "l-id", live_session, identity)
        for i, body in enumerate((
            "orchid:status:writing",
            "orchid:phase:building:2/4",
            "orchid:subagent:start:sower-a",
            "orchid:subagent:start:sower-b",
            "orchid:subagent:start:sower-c",
            "orchid:subagent:queue:sower-d",
            "orchid:subagent:queue:sower-e",
        )):
            self._put(courier_root, live_session, f"l-{i}", live_session, body)

    def _seed_signmc_courier(self) -> None:
        courier_root = self._courier_root(self.signmc_repo)
        session = "sign-arch"
        self._put(courier_root, session, "s-id", session,
                   identity_body(session, agent_type="landscaper",
                                 feature_id="focus-returning", name="focus returning"))
        self._put(courier_root, session, "s-phase", session, "orchid:phase:building")
        self._put_question(courier_root, session, "s-q1", session, "q1", "scope fork")

    def _pane_size_settled(self) -> bool:
        expected = f"{self.PANE_WIDTH}x{self.PANE_HEIGHT}"
        actual = self._tmux("list-windows", "-F", "#{window_width}x#{window_height}").stdout.strip()
        return actual == expected

    def _await_pane_size(self, timeout: float = 3.0) -> None:
        """tmux's `-x`/`-y` at `new-session` time races a freshly-forked
        server's own default sizing on this host — observed empirically as
        curses reading LINES/COLS=24x80 (the tmux default) instead of the
        requested pane size, purely under pytest's process-timing profile.
        Creating the session bare, resizing explicitly, and confirming the
        size via `list-windows` before starting the app closes that race
        (the app is only started once the pty is provably the right size)."""
        deadline = time.time() + timeout
        while time.time() < deadline and not self._pane_size_settled():
            time.sleep(0.05)

    def _launch(self) -> None:
        self._tmux("new-session", "-d", "-x", str(self.PANE_WIDTH), "-y", str(self.PANE_HEIGHT),
                    check=True)
        self._tmux("resize-window", "-x", str(self.PANE_WIDTH), "-y", str(self.PANE_HEIGHT))
        self._await_pane_size()
        command = f"ORCHIDS_SIDEBAR_REPOS={self._repolist_path} {sys.executable} {_SIDEBAR_PY}"
        self._tmux("send-keys", command, "Enter")

    def _capture(self) -> list[str]:
        return self._tmux("capture-pane", "-e", "-p", check=True).stdout.splitlines()

    def _looks_complete(self, lines: list[str]) -> bool:
        stripped = [_strip_sgr(line) for line in lines]
        return (any("orchids" in line for line in stripped)
                and any("signmc" in line for line in stripped)
                and any("scope fork" in line for line in stripped))

    def _capture_when_ready(self, timeout: float = 10.0) -> list[str]:
        """Poll until two SUCCESSIVE captures are both complete and
        byte-identical — a single complete-looking capture is not enough,
        since curses erases and redraws the whole pane every ~125ms tick
        (even when nothing changed) and capture-pane can catch that
        redraw mid-flight, momentarily missing a line."""
        deadline = time.time() + timeout
        previous = None
        while time.time() < deadline:
            current = self._capture()
            if self._looks_complete(current) and current == previous:
                return current
            previous = current
            time.sleep(0.15)
        return previous or []

    def test_frame_matches_approved_visual_grammar(self) -> None:
        self._launch()
        lines = self._capture_when_ready()
        stripped = [_strip_sgr(line) for line in lines]

        header_idx = next(i for i, l in enumerate(stripped) if l.strip() == "orchids")
        self.assertTrue(_has_any_bg(lines[header_idx]))
        leading_spaces = len(stripped[header_idx]) - len(stripped[header_idx].lstrip(" "))
        self.assertGreater(leading_spaces, 0)

        done_idx = next(
            i for i, l in enumerate(stripped)
            if "✓" in l and "bloomer v1" in l and "100%" in l
        )
        self.assertTrue(_has_fg(lines[done_idx], sidebar.GREEN)
                         or _has_fg(lines[done_idx], sidebar.GREEN_SOFT))

        working_idx = next(
            i for i, l in enumerate(stripped)
            if "⠧" in l and "sidebar titling" in l
        )
        self.assertLess(done_idx, working_idx)
        self.assertTrue(_has_any_bg(lines[working_idx]))
        self.assertTrue(stripped[working_idx].rstrip().endswith("62%"))

        phase_label_line = stripped[working_idx + 1]
        self.assertIn(sidebar.small_caps("building"), phase_label_line)

        identity_idx = next(
            i for i, l in enumerate(stripped)
            if i > working_idx and "writing" in l and "⋮" in l
        )
        self.assertIn("landscaper", stripped[identity_idx])

        checklist_start = next(
            i for i, l in enumerate(stripped) if i > working_idx and "ideation" in l
        )
        expected = [
            ("ideation", "●"), ("scoping", "●"), ("designing", "●"),
            ("building", "⠧"), ("releasing", "○"),
        ]
        for offset, (word, mark) in enumerate(expected):
            checklist_line = stripped[checklist_start + offset]
            self.assertIn(word, checklist_line)
            self.assertIn(mark, checklist_line)
        active_line = stripped[checklist_start + 3]
        self.assertIn("●●●○○", active_line)

        signmc_header_idx = next(i for i, l in enumerate(stripped) if l.strip() == "signmc")
        question_row_idx = next(
            i for i, l in enumerate(stripped)
            if i > signmc_header_idx and "?1" in l and "focus returning" in l
        )
        question_count_idx = next(
            i for i, l in enumerate(stripped)
            if i > question_row_idx and "question" in l
        )
        why_idx = next(
            i for i, l in enumerate(stripped)
            if i > question_row_idx and "why:" in l and "scope fork" in l
        )
        self.assertTrue(_has_fg(lines[question_row_idx], sidebar.AMBER))
        self.assertTrue(_has_fg(lines[question_count_idx], sidebar.AMBER))
        self.assertTrue(_has_fg(lines[why_idx], sidebar.AMBER))

        full_text = "\n".join(stripped)
        self.assertNotIn("⌚", full_text)
        for raw_line in lines:
            self.assertFalse(_has_basic_red(raw_line), raw_line)

    def test_working_band_animates_while_other_lines_stay_static(self) -> None:
        self._launch()
        first = self._capture_when_ready()
        stripped_first = [_strip_sgr(line) for line in first]
        working_idx = next(
            i for i, l in enumerate(stripped_first)
            if "⠧" in l and "sidebar titling" in l
        )

        time.sleep(0.4)
        second = self._capture()

        self.assertEqual(len(first), len(second))
        self.assertNotEqual(first[working_idx], second[working_idx])
        for i in range(len(first)):
            if i == working_idx:
                continue
            self.assertEqual(first[i], second[i], f"unexpected change on line {i}")


if __name__ == "__main__":
    unittest.main()

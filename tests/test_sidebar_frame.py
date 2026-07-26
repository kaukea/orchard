"""Emulator frame check for tools/sidebar.py's curses renderer.

Runs the REAL curses app inside a detached tmux pane, seeded with fixture
event files written straight into a temp `$XDG_RUNTIME_DIR/orchard/projects/`
tree — the on-disk layout tools/sidebar.py's `build_model()` reads directly
(bus-finishing: sidebar_model.py/sidebar_v3.py are both retired and folded
into sidebar.py; there is no more repo-list env var to seed, `build_model()`
scans the whole projects root).

Assertions are SEMANTIC (glyphs, text, colour family) rather than a byte
diff against the mock: curses may map truecolor down to the nearest
xterm-256 index depending on what the terminal advertises, and the working
row's band sweep animates. Colour-family checks accept either the mock's
exact truecolor RGB or tools/sidebar.py's own `_rgb_to_xterm256` fallback
for that RGB — never a hand-guessed index.

NOT asserted here (no source in the new event grammar — see sidebar.py's
module docstring): phase checklist content, identity-line footer stats
(age/worked/tokens/dollars), open-question badges/rows. progress_pct is
never populated by build_model() either, so a "done" row's percentage tail
always reads "0%" here, not "100%" — an acknowledged, in-docstring gap, not
something this test pretends is otherwise.

Skips cleanly (unittest.skipUnless) when tmux is not on PATH.
"""
import itertools
import json
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

_SIDEBAR_PY = os.path.join(_TOOLS_DIR, "sidebar.py")
_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")

_HAS_TMUX = shutil.which("tmux") is not None

_counter = itertools.count()


def _write_event(projects_root, slug, sid, subject, *, identity=None, status=None, body=None):
    """One event file under `projects_root`/`slug`/ — the same shape
    orchard_topic.py's build_envelope()/write_message() produce (see
    tests/test_sidebar.py, which owns the fuller build_model() unit-test
    coverage; this file only needs enough fixture machinery to drive the
    real curses app end to end)."""
    project_dir = Path(projects_root) / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    envelope = {"from": f":session:{sid}", "subject": subject}
    if body is not None:
        envelope["body"] = body
    if identity is not None:
        envelope["identity"] = identity
    if status is not None:
        envelope["status"] = status
    path = project_dir / f"{sid}.{next(_counter):08d}.json"
    path.write_text(json.dumps(envelope), encoding="utf-8")
    return path


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


def _skip_extended_colour(codes: list[str], i: int) -> int:
    """`codes[i]` is "38"/"48" (extended fg/bg) -- index just past however
    many parameters that extended colour consumes: 5 total for
    "38;2;r;g;b" (true colour), 3 for "38;5;idx" (palette index)."""
    if i + 1 < len(codes) and codes[i + 1] == "2":
        return i + 5
    if i + 1 < len(codes) and codes[i + 1] == "5":
        return i + 3
    return i + 1


def _has_basic_red(raw_line: str) -> bool:
    """True only for a literal basic-ANSI red code (31 fg / 41 bg) used as
    its own SGR attribute -- never a false hit off an R/G/B *value* of 31 or
    41 riding inside an extended-colour sequence ("38;2;r;g;b"/"38;5;idx"),
    which this renderer now emits once a direct-colour terminfo is active."""
    for codes in _sgr_code_lists(raw_line):
        i = 0
        while i < len(codes):
            code = codes[i]
            if code in ("38", "48"):
                i = _skip_extended_colour(codes, i)
                continue
            if code in ("31", "41"):
                return True
            i += 1
    return False


@unittest.skipUnless(_HAS_TMUX, "tmux not available in this environment")
class SidebarEmulatorFrameTests(unittest.TestCase):
    """One fixture fleet — an orchids repo with a done feature and a working
    feature (three running subagents, see _seed_orchids), plus a signmc repo
    with a working feature — rendered by the real curses app in a detached
    tmux pane and captured with SGR."""

    # Widened from 29 (2026-07-26): the six-level hierarchy (project ->
    # feature -> task -> step -> agent -> subagent) puts an agent's identity
    # line at depth 4 — 16 columns of indent before any text — where the
    # old model drew it as a decoration with a fixed 2-column prefix
    # regardless of depth. `compose_identity_line` never truncates the
    # "doing"/role segments (only the model), so a pane too narrow for
    # indent + doing + role just overflows past the visible column count
    # rather than eliding the role — this pane needs to be wide enough for
    # that not to matter.
    PANE_WIDTH = 60
    PANE_HEIGHT = 50

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.runtime_dir = Path(self._tmp.name) / "run"
        self.runtime_dir.mkdir()
        self.projects_root = self.runtime_dir / "orchard" / "projects"
        self.projects_root.mkdir(parents=True)
        self._seed_orchids()
        self._seed_signmc()
        self._socket = f"sidebar-frame-{uuid.uuid4().hex[:8]}"
        self.addCleanup(self._kill_tmux_server)

    def _kill_tmux_server(self) -> None:
        self._tmux("kill-server")

    def _tmux(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["tmux", "-L", self._socket, *args], check=check,
            capture_output=True, text=True,
        )

    def _event(self, slug, sid, subject, **kw):
        return _write_event(self.projects_root, slug, sid, subject, **kw)

    def _seed_orchids(self) -> None:
        # a done feature -- outcome:success is the terminal signal.
        self._event("orchids", "orch-bloomer", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "bloomer-v1",
                               "name": "bloomer v1"})
        self._event("orchids", "orch-bloomer", "orchard:agent:outcome:success",
                     identity={"agent": "landscaper", "feature": "bloomer-v1",
                               "name": "bloomer v1"})

        # a working feature with an identity line (role + model) and a mix
        # of running/queued subagents.
        identity = {"agent": "landscaper", "feature": "sidebar-titling",
                    "name": "sidebar titling"}
        status = {"model": "opus-4.8"}
        self._event("orchids", "orch-arch", "orchard:agent:lifecycle:starting",
                     identity=identity, status=status)
        self._event("orchids", "orch-arch", "orchard:agent:status",
                     identity=identity, status=status, body="writing")
        # EXACT subject, no appended subagent id — the subagent rides the
        # body instead (operator ruling: the orchard subject list is
        # closed, variable data never belongs in the subject). Only running
        # subagents are seeded here (`schedule`/queued has its own coverage
        # in tests/test_sidebar.py's SubagentDelegationTests).
        for sub in ("sower-a", "sower-b", "sower-c"):
            self._event("orchids", "orch-arch", "orchard:agent:delegation:begin",
                         identity=identity, status=status, body={"subagent": sub})

    def _seed_signmc(self) -> None:
        # deliberately STOPPED -- this repo exists purely to prove multiple
        # repos render correctly and that only the genuinely-"working" row
        # (orchids/sidebar-titling) carries the band sweep; a second
        # concurrently-animating row would defeat
        # test_working_band_animates_while_other_lines_stay_static's
        # "everything else is static" assertion.
        #
        # An explicit `lifecycle:stopped` is what makes this row idle. It
        # previously relied on posting no lifecycle event at all, which was
        # never a signal of idleness -- it was the absence of one, and a
        # live session that had simply outlived the 120-minute archival of
        # its own start event looked identical. That ambiguity was a defect
        # in the renderer, since a session posting fresh status is plainly
        # alive; this seed now states what it means rather than relying on
        # an absence that used to be misread.
        identity = {"agent": "landscaper", "feature": "focus-returning",
                    "name": "focus returning"}
        self._event("signmc", "sign-arch", "orchard:agent:status",
                     identity=identity, body="idle")
        self._event("signmc", "sign-arch", "orchard:agent:lifecycle:stopped",
                     identity=identity)

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
        command = f"XDG_RUNTIME_DIR={self.runtime_dir} {sys.executable} {_SIDEBAR_PY}"
        self._tmux("send-keys", command, "Enter")

    def _capture(self) -> list[str]:
        return self._tmux("capture-pane", "-e", "-p", check=True).stdout.splitlines()

    def _looks_complete(self, lines: list[str]) -> bool:
        stripped = [_strip_sgr(line) for line in lines]
        return (any("orchids" in line for line in stripped)
                and any("signmc" in line for line in stripped)
                and any("focus returning" in line for line in stripped))

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
            if "✓" in l and "bloomer v1" in l
        )
        self.assertTrue(_has_fg(lines[done_idx], sidebar.GREEN)
                         or _has_fg(lines[done_idx], sidebar.GREEN_SOFT))

        working_idx = next(
            i for i, l in enumerate(stripped)
            if "⠧" in l and "sidebar titling" in l
        )
        self.assertLess(done_idx, working_idx)
        self.assertTrue(_has_any_bg(lines[working_idx]))

        # Identity BLOCK (operator ruling, 2026-07-26, "very compact form"):
        # the agent's status is a quote ("writing") with its role riding
        # the SAME line by default ("writing" — 🌿 landscaper) rather than
        # the old one "⋮"-glued line or a separate attribution line — the
        # 2-line form is reserved for a frame with real slack to spare.
        quote_idx = next(
            i for i, l in enumerate(stripped)
            if i > working_idx and "“writing”" in l
        )
        self.assertIn("landscaper", stripped[quote_idx])

        signmc_header_idx = next(i for i, l in enumerate(stripped) if l.strip() == "signmc")
        signmc_feature_idx = next(
            i for i, l in enumerate(stripped)
            if i > signmc_header_idx and "focus returning" in l
        )
        self.assertGreater(signmc_feature_idx, signmc_header_idx)

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

        # Poll for a change rather than compare a single fixed-delay
        # snapshot: the tick-driven band sweep advances roughly every
        # ~125ms, but exactly when a poll lands relative to that cadence is
        # not guaranteed under shared-host CPU contention, so a bounded
        # retry window is the non-flaky way to observe "it does animate."
        deadline = time.time() + 5.0
        second = first
        while time.time() < deadline:
            second = self._capture()
            if len(second) == len(first) and second[working_idx] != first[working_idx]:
                break
            time.sleep(0.1)

        self.assertEqual(len(first), len(second))
        self.assertNotEqual(first[working_idx], second[working_idx],
                             "working row never changed within the poll window")
        for i in range(len(first)):
            if i == working_idx:
                continue
            self.assertEqual(first[i], second[i], f"unexpected change on line {i}")


_ONCE_EXIT_RE = re.compile(r"ONCE_EXIT:(\d+)")

# Raw pty bytes (see SidebarOnceCLITests) carry whatever SGR separator the
# active terminfo entry actually emits -- observed as colon-delimited
# ("38:2::r:g:b", the ITU-T416 form) under a direct-colour entry, unlike
# `capture-pane -e`'s reconstruction (semicolon-delimited, what `_SGR_RE`
# above assumes) which only reflects the CURRENTLY DISPLAYED screen and so
# is unusable once `--once` has already torn the alt-screen back down.
# Colon and semicolon are therefore both accepted here; an empty
# colour-space-id subfield ("2::") collapses away like any other empty
# split segment.
_RAW_SGR_RE = re.compile(rb"\x1b\[([0-9;:]*)m")


def _raw_param_lists(raw: bytes) -> list[list[bytes]]:
    return [
        [p for p in re.split(rb"[;:]", params) if p]
        for params in _RAW_SGR_RE.findall(raw)
    ]


def _raw_has_subsequence(params: list[bytes], pattern: list[bytes]) -> bool:
    n = len(pattern)
    return any(params[i:i + n] == pattern for i in range(len(params) - n + 1))


_RAW_ESCAPE_RE = re.compile(rb"\x1b(\[[0-9;:]*[A-Za-z]|[()][A-Za-z0-9]|[=>])")


def _raw_strip_escapes(raw: bytes) -> bytes:
    """Plain text out of a raw pty byte capture -- unlike `_strip_sgr`
    (SGR colour codes only, applied per already-split line), a one-shot
    frame's raw stream also carries cursor-addressing codes and a name can
    be split mid-word across a colour boundary (e.g. the fill/no-fill
    column split inside a feature name), so escapes are stripped from the
    whole byte stream before a text substring is looked for."""
    return _RAW_ESCAPE_RE.sub(b"", raw)


def _raw_has_colour(raw: bytes, rgb: tuple[int, int, int]) -> bool:
    r, g, b = (str(c).encode() for c in rgb)
    index = str(sidebar._rgb_to_xterm256(rgb)).encode()
    patterns = [
        [b"38", b"2", r, g, b], [b"48", b"2", r, g, b],
        [b"38", b"5", index], [b"48", b"5", index],
    ]
    return any(
        _raw_has_subsequence(params, pattern)
        for params in _raw_param_lists(raw) for pattern in patterns
    )


@unittest.skipUnless(_HAS_TMUX, "tmux not available in this environment")
class SidebarOnceCLITests(unittest.TestCase):
    """`--once` must be the REAL renderer (same terminal/colour/draw path as
    the live UI, operator ruling) so a test can assert on actual colour —
    paints exactly one frame and exits, with no input loop and no watch
    thread. Own tmux socket, killed in addCleanup, never touches an
    operator session.

    `--once` tears the alt-screen back down the instant it exits (curses'
    own `endwin()`), so by the time a poll could observe "the process
    returned to the shell" via `capture-pane`, the painted frame is already
    gone from the visible pane -- there is no live window to catch, unlike
    the long-running interactive app the sibling test class drives. `tmux
    pipe-pane` sidesteps that: it logs the raw bytes the app actually wrote
    to the pty as they were written, independent of what the pane displays
    afterwards, so the frame's real SGR colour escapes survive to be
    asserted on."""

    PANE_WIDTH = 29
    PANE_HEIGHT = 30

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.runtime_dir = Path(self._tmp.name) / "run"
        self.runtime_dir.mkdir()
        self.projects_root = self.runtime_dir / "orchard" / "projects"
        self.projects_root.mkdir(parents=True)
        _write_event(self.projects_root, "orchids", "orch-once",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "once-check",
                               "name": "once check"})
        self._raw_log = Path(self._tmp.name) / "once-raw.log"
        self._socket = f"sidebar-once-{uuid.uuid4().hex[:8]}"
        self.addCleanup(self._kill_tmux_server)

    def _kill_tmux_server(self) -> None:
        self._tmux("kill-server")

    def _tmux(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["tmux", "-L", self._socket, *args], check=check,
            capture_output=True, text=True,
        )

    def _await_pane_size(self, timeout: float = 3.0) -> None:
        expected = f"{self.PANE_WIDTH}x{self.PANE_HEIGHT}"
        deadline = time.time() + timeout
        while time.time() < deadline:
            actual = self._tmux("list-windows", "-F", "#{window_width}x#{window_height}").stdout.strip()
            if actual == expected:
                return
            time.sleep(0.05)

    def _launch(self) -> None:
        self._tmux("new-session", "-d", "-x", str(self.PANE_WIDTH), "-y", str(self.PANE_HEIGHT),
                    check=True)
        self._tmux("resize-window", "-x", str(self.PANE_WIDTH), "-y", str(self.PANE_HEIGHT))
        self._await_pane_size()
        self._tmux("pipe-pane", "-o", f"cat >> {self._raw_log}", check=True)
        command = (
            f"XDG_RUNTIME_DIR={self.runtime_dir} {sys.executable} {_SIDEBAR_PY} --once; "
            "echo ONCE_EXIT:$?"
        )
        self._tmux("send-keys", command, "Enter")

    def _capture(self) -> list[str]:
        return self._tmux("capture-pane", "-e", "-p", check=True).stdout.splitlines()

    def _await_exit_code(self, timeout: float = 10.0) -> str:
        """Poll the pane (post-teardown, primary screen) for the trailing
        `echo`'s digits-only marker -- not merely a line CONTAINING
        "ONCE_EXIT:", which would also match the shell's own local-echo of
        the not-yet-substituted "echo ONCE_EXIT:$?" command text an instant
        before it actually runs."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            for line in self._capture():
                match = _ONCE_EXIT_RE.search(_strip_sgr(line))
                if match:
                    return match.group(1)
            time.sleep(0.1)
        self.fail("--once never returned control to the shell within the timeout")

    def test_once_paints_one_real_frame_and_exits_zero(self) -> None:
        self._launch()
        exit_code = self._await_exit_code()
        self.assertEqual(exit_code, "0")

        raw = self._raw_log.read_bytes()
        text = _raw_strip_escapes(raw)
        self.assertIn(b"orchids", text)
        self.assertIn(b"once check", text)
        self.assertTrue(_raw_has_colour(raw, sidebar.HEADER_FG))
        self.assertTrue(_raw_has_colour(raw, sidebar.REPO_HUES["orchids"]["header"]))


if __name__ == "__main__":
    unittest.main()

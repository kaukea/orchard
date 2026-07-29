"""Width x height SWEEP harness for tools/sidebar.py's curses renderer.

Why this file exists (operator, 2026-07-28, on the branch renderer at 37
columns / 47 rows, real data): "the rendering is better but not correct
yet". Four defects were then measured directly off that pane's own emitted
bytes, and two of them contradicted claims this branch had already reported
as done AND tested by tests/test_sidebar_frame.py -- whose own pane is 60 (or
29) columns by 30/50 rows, fed simulated data. THE TESTS PASSED AND THE
SCREEN WAS WRONG, because no existing test ever looked at the geometry the
operator was actually looking at, and a pane can be resized to ANY width --
so no single hardcoded width (or pair of widths) is ever the right fix for
that gap. This file asserts a fixed set of invariants at EVERY geometry in a
swept range instead of at one or two hand-picked ones, plus across a live
resize, so "passes the suite" and "correct on the operator's own screen"
stop being two different claims.

Geometry-sweep specific -- test_sidebar_frame.py continues to own the
single-geometry contrast/animation/dead-space assertions it already has;
this file does not duplicate those, it generalises the ONE claim they can't
make: "true at width W" is not "true at every width".

Method: drives the REAL curses app (tools/sidebar.py) inside its own
detached tmux session, seeded with fixture event files written straight
into an isolated `$XDG_RUNTIME_DIR/orchard/projects/` tree (same on-disk
shape `build_model()` reads directly, see test_sidebar_frame.py's own
docstring) -- captured with `tmux capture-pane -p -e`. tmux right-trims
trailing whitespace-only screen content regardless of its colour (verified
empirically against this tmux build, 3.5a) -- a wholly blank, fully
background-painted row still comes back as just its own SGR-set code
followed immediately by end-of-line, with no literal trailing space
characters. Every invariant below is written against that trimming: text
equality compares `.rstrip()` results, and "this row carries an explicit
background of its own" is a substring search over the row's OWN raw SGR
codes, never a length comparison.

Also runnable against the operator's REAL runtime tree (no seeding, pure
read, same as the operator's own sidebar) -- see `_run_against_real_tree`
at the bottom, invoked with `python3 tests/test_sidebar_geometry_sweep.py
--real`. That path is deliberately NOT pytest-collected (module-level
`__main__` guard): real fleet content is not reproducible byte-for-byte, so
it cannot be a deterministic RED/GREEN assertion, but it is exactly the
same invariant-checking code path exercised on the seeded fixtures.
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

# SIDEBAR_SWEEP_TOOLS_DIR: baseline-verification escape hatch only -- lets
# this exact, unmodified test file be pointed at a DIFFERENT tools/
# checkout (e.g. commit 939c461's tools/sidebar.py extracted via `git show`
# into a scratch dir) to confirm an invariant genuinely exercises a defect
# against the code as it stood at this step's assigned HEAD, without
# disturbing the live worktree two other sowers are concurrently editing.
# Unset, this resolves to the normal in-tree tools/ exactly as before.
_TOOLS_DIR = os.environ.get("SIDEBAR_SWEEP_TOOLS_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sidebar  # noqa: E402

_SIDEBAR_PY = os.path.join(_TOOLS_DIR, "sidebar.py")
_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")
# A task row's own METRICS tail (`sidebar_text._format_running_time`'s own
# shapes: "0s"/"12m"/"1h05" -- moved here from sidebar_rows.py by M2 so
# sidebar_model.py could share it too, same function, new home) -- matched
# so BRAVO's ellipsis-suffix check below can peel it off before judging
# whether the NAME half was cut. None of this sweep's own fixtures set a
# `context_tokens` figure, so `_task_metrics_text`'s M2 addition (a
# trailing " N ctx" segment) never reaches this regex.
_METRICS_TAIL_RE = re.compile(r" \d+(?:h\d{2}|m|s)$")

_HAS_TMUX = shutil.which("tmux") is not None

_counter = itertools.count()


# ---------------------------------------------------------------------------
# Byte-level helpers -- deliberately self-contained (not imported from
# test_sidebar_frame.py) so this file never has to change because that one
# did, per the "own file" isolation this step was scoped to keep.
# ---------------------------------------------------------------------------

def _write_event(projects_root, slug, sid, subject, *, identity=None, status=None, body=None):
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


def _has_any_bg(raw_line: str) -> bool:
    for codes in _sgr_code_lists(raw_line):
        for i, code in enumerate(codes):
            if code == "48" and i + 1 < len(codes) and codes[i + 1] in ("2", "5"):
                return True
    return False


def _row_core(line: str, *, bar: str = "", status_alphabet: str = "",
              tail_alphabet: str = "") -> str:
    """The row's text with its structural glyphs peeled off both ends --
    a task-bar glyph (if `bar` is given), then ONE leading glyph out of
    `status_alphabet` plus the space after it, then ONE trailing glyph out
    of `tail_alphabet` (a progress circle) plus its leading space. What
    remains is exactly the row's own NAME, whatever the row kind -- used to
    assert a row is never left with a marker and a status glyph but no
    name (invariant 5)."""
    s = line
    if bar and s.startswith(bar):
        s = s[len(bar):]
    s = s.lstrip(" ")
    if status_alphabet and s and s[0] in status_alphabet:
        s = s[1:]
    s = s.strip(" ")
    while tail_alphabet and s and s[-1] in tail_alphabet:
        s = s[:-1].rstrip(" ")
    return s


# ---------------------------------------------------------------------------
# Fixture -- three features chosen to exercise each measured defect:
#   ALPHA -- sole task sharing its feature's exact name (no task/task_name
#            posted at all, the natural real-world shape per
#            docs/TODO.md.d/sidebar-teamwork.md item 0/6: nothing writes
#            distinct task identity today), unmapped role (no step
#            accordion, so the fixture stays small enough to fit even at
#            this sweep's shortest tested height) -- reproduces the
#            informationless task row directly.
#   BRAVO -- FAILED (the one status carrying an East-Asian-Wide glyph,
#            STATUS_EMOJI["failed"] == "❌", 2 cells) with a task whose
#            name genuinely differs from its feature's, both deliberately
#            longer than the widest swept pane -- exercises truncation +
#            the single ellipsis rule and wide-glyph column accounting at
#            every width.
#   CHARLIE -- DONE, sole task, collapses to one green row -- a second,
#            differently-hued feature immediately below BRAVO's failed
#            band, so two structurally adjacent rows must never share a
#            background by accident (Decision-111).
# ---------------------------------------------------------------------------

_ALPHA_SHARED_NAME = (
    "ALPHA sole task feature name repeated verbatim by its only task so the "
    "name drop rule fires exactly like it does on the operator's own real "
    "sessions, which never post a distinct task identity today"
)
_BRAVO_FEATURE_NAME = (
    "BRAVO feature name deliberately long enough that it must truncate at "
    "every single width this sweep exercises, from the narrowest to the "
    "widest, so the one truncation rule is exercised everywhere"
)
_BRAVO_TASK_NAME = (
    "BRAVO task name distinct from its feature and equally long so both "
    "rows are forced through the same width-aware cut at every geometry"
)
_CHARLIE_NAME = "CHARLIE done sole-task feature, collapses to one green row"


def _seed_fixture(projects_root: Path) -> None:
    # ALPHA -- idle (STATUS_EMOJI["idle"] == "○"), an UNMAPPED role (no
    # charter entry carries a step: key for "explorer") so the task never
    # grows a 5-row step accordion -- keeps this fixture's total row count
    # small enough that everything still fits even at this sweep's
    # shortest tested height (10 rows), so a row going missing there means
    # something real, never just "scrolled off". NO task/task_name posted,
    # which is what makes it the feature's own SOLE task under the SAME
    # name (see `_sole_same_named_task` in tools/sidebar.py).
    alpha_identity = {"agent": "explorer", "feature": "alpha-sole-task",
                       "name": _ALPHA_SHARED_NAME}
    _write_event(projects_root, "orchids", "alpha-sess",
                 "orchard:agent:lifecycle:starting", identity=alpha_identity)
    _write_event(projects_root, "orchids", "alpha-sess",
                 "orchard:agent:lifecycle:stopped", identity=alpha_identity)

    # BRAVO -- failed, "agent" present but an UNMAPPED role (no charter
    # entry carries a step: key for it) so no step mapping muddies the
    # expected progress tail -- deterministically empty. A record with NO
    # "agent" key at all never enters `agent_records`
    # (tools/sidebar_model.py:455) and earns no row whatsoever -- verified
    # the hard way, see this file's own commit history: an earlier draft of
    # this fixture omitted "agent" here and on CHARLIE/DELTA below, and the
    # sweep "failed" by finding nothing at any width because nothing was
    # ever on the board, not because the renderer was wrong.
    bravo_identity = {"agent": "explorer", "feature": "bravo-two-names",
                       "name": _BRAVO_FEATURE_NAME,
                       "task": "bravo-task-id", "task_name": _BRAVO_TASK_NAME}
    _write_event(projects_root, "orchids", "bravo-sess",
                 "orchard:agent:lifecycle:starting", identity=bravo_identity)
    _write_event(projects_root, "orchids", "bravo-sess",
                 "orchard:agent:outcome:fail", identity=bravo_identity)

    # CHARLIE -- done, sole same-named task -> feature collapses entirely.
    charlie_identity = {"agent": "explorer", "feature": "charlie-done", "name": _CHARLIE_NAME}
    _write_event(projects_root, "orchids", "charlie-sess",
                 "orchard:agent:lifecycle:starting", identity=charlie_identity)
    _write_event(projects_root, "orchids", "charlie-sess",
                 "orchard:agent:outcome:success", identity=charlie_identity)

    # A second repo, one idle feature -- multi-repo header distinctness,
    # same shape test_sidebar_frame.py's own fixture already relies on.
    delta_identity = {"agent": "landscaper", "feature": "delta-idle",
                       "name": "DELTA second repo feature"}
    _write_event(projects_root, "signmc", "delta-sess",
                 "orchard:agent:status", identity=delta_identity, body="idle")
    _write_event(projects_root, "signmc", "delta-sess",
                 "orchard:agent:lifecycle:stopped", identity=delta_identity)


# ---------------------------------------------------------------------------
# tmux driving -- one throwaway socket per launch, always killed.
# ---------------------------------------------------------------------------

class _TmuxDriver:
    def __init__(self, width: int, height: int, runtime_dir: Path) -> None:
        self.width = width
        self.height = height
        self.runtime_dir = runtime_dir
        self.socket = f"sidebar-sweep-{uuid.uuid4().hex[:8]}"

    def _tmux(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["tmux", "-L", self.socket, *args], check=check,
            capture_output=True, text=True,
        )

    def kill(self) -> None:
        self._tmux("kill-server")

    def _pane_size_settled(self) -> bool:
        expected = f"{self.width}x{self.height}"
        actual = self._tmux("list-windows", "-F", "#{window_width}x#{window_height}").stdout.strip()
        return actual == expected

    def _await_pane_size(self, timeout: float = 3.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline and not self._pane_size_settled():
            time.sleep(0.05)

    def launch(self, *, extra_args: str = "") -> None:
        self._tmux("new-session", "-d", "-x", str(self.width), "-y", str(self.height),
                    check=True)
        self._tmux("resize-window", "-x", str(self.width), "-y", str(self.height))
        self._await_pane_size()
        command = (
            f"HOME={self.runtime_dir} XDG_RUNTIME_DIR={self.runtime_dir} "
            f"{sys.executable} {_SIDEBAR_PY} {extra_args}"
        )
        self._tmux("send-keys", command, "Enter")

    def resize(self, width: int, height: int) -> None:
        self.width, self.height = width, height
        self._tmux("resize-window", "-x", str(width), "-y", str(height))
        self._await_pane_size()

    def capture(self) -> list[str]:
        return self._tmux("capture-pane", "-e", "-p", check=True).stdout.splitlines()

    def capture_when_ready(self, looks_complete, timeout: float = 10.0) -> list[str]:
        """Poll until two SUCCESSIVE captures are complete (per
        `looks_complete`) AND byte-identical -- curses redraws the whole
        pane on every ~125ms tick even when nothing changed, and
        capture-pane can catch that mid-flight (same race
        test_sidebar_frame.py's own poller guards against)."""
        deadline = time.time() + timeout
        previous = None
        while time.time() < deadline:
            current = self.capture()
            if looks_complete(current) and current == previous:
                return current
            previous = current
            time.sleep(0.15)
        return previous or []


def _looks_complete(lines: list[str]) -> bool:
    stripped = [_strip_sgr(line) for line in lines]
    return (any("orchids" in line for line in stripped)
            and any("signmc" in line for line in stripped)
            and any("DELTA second repo" in line for line in stripped))


# ---------------------------------------------------------------------------
# Geometries -- narrow / previously-tested / the operator's own judged
# 37x47 / wide, crossed against short / typical-terminal / the operator's
# own 47 / tall heights. Not a full cross product (that would be 11x5 = 55
# launches): each row below is a deliberately chosen POINT, not a grid, to
# keep the sweep's wall-clock sane while still covering the whole range
# defect (a) ("worked at 150 rows, not at 47") showed height matters as
# much as width does.
# ---------------------------------------------------------------------------

# Trimmed from an original 15-point grid (each point costs a real tmux
# launch + settle + polled capture, ~10-15s worst case) after that first
# run took 205s in one session -- too slow for a single sower turn to
# finish and report inside. This keeps the three things the operator's own
# correction demanded: genuinely NARROW (12, below anything this renderer
# has ever been judged at), the REAL widths in play (23 -- his second
# complaint's original width; 37 -- the exact width he judged "not correct
# yet"), and comfortably WIDE (120) -- crossed against short/typical/the
# operator's own judged/tall HEIGHT (10/24/47/80), since defect (a) is a
# HEIGHT-driven bug ("worked at 150 rows, not at 47") as much as a width
# one. 8 points, not a full 4x4 grid, chosen to cover the boundaries and
# the one exact geometry that matters rather than every combination.
GEOMETRIES: list[tuple[int, int]] = [
    (12, 24),   # far below any width this renderer has ever been judged at
    (23, 24),   # the operator's own original narrow-complaint width
    (37, 24),   # the operator's own judged width, typical terminal height
    (37, 47),   # the EXACT geometry the operator judged "not correct yet"
    (37, 10),   # the judged width, a short pane
    (37, 80),   # the judged width, taller than judged
    (60, 24),   # comfortably wide, typical height
    (120, 24),  # very wide
]


@unittest.skipUnless(_HAS_TMUX, "tmux not available in this environment")
class SidebarGeometrySweepTests(unittest.TestCase):
    """Renders the SAME seeded fleet at every geometry in `GEOMETRIES` and
    asserts every invariant at each one, collecting ALL failures before
    reporting -- a single geometry failing must never hide a different one
    failing at a different point in the sweep, which is the entire reason
    a fixed pair of hardcoded widths was the wrong fix the first time."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.runtime_dir = Path(self._tmp.name) / "run"
        self.runtime_dir.mkdir()
        self.projects_root = self.runtime_dir / "orchard" / "projects"
        self.projects_root.mkdir(parents=True)
        _seed_fixture(self.projects_root)

    def _render_at(self, width: int, height: int) -> tuple[list[str], list[str]]:
        driver = _TmuxDriver(width, height, self.runtime_dir)
        try:
            driver.launch()
            lines = driver.capture_when_ready(_looks_complete)
        finally:
            driver.kill()
        stripped = [_strip_sgr(line) for line in lines]
        return lines, stripped

    def _check_geometry(self, width: int, height: int, failures: list[str]) -> None:
        lines, stripped = self._render_at(width, height)

        def fail(inv: str, reason: str) -> None:
            failures.append(f"{width}x{height} [{inv}]: {reason}")

        # ---- locate rows by short, truncation-safe prefixes -------------
        def find(prefix: str) -> int | None:
            for i, l in enumerate(stripped):
                if prefix in l:
                    return i
            return None

        # Shortened to the first 3 letters, not the full word: the feature
        # row's own identity marker (operator, 2026-07-28 — "🧩/<feature
        # name>", 3 cells of chrome before the name even starts, "count it
        # as three, not two") now eats into the same truncation budget the
        # name itself used to have exclusively, so at this sweep's own
        # narrowest width (12x24, "far below any width this renderer has
        # ever been judged at") the full word no longer survives -- 3
        # letters reliably do, here and at every wider geometry this sweep
        # covers.
        alpha_idx = find("ALP")
        bravo_idx = find("BRA")
        charlie_idx = find("CHA")

        if alpha_idx is None:
            fail("visibility", "ALPHA feature row not found at all")
        if bravo_idx is None:
            fail("visibility", "BRAVO feature row not found at all")
        if charlie_idx is None:
            fail("visibility", "CHARLIE feature row not found at all")

        # ---- invariant 6 (Decision-111): every row paints its OWN
        # background -- checked on every row this test can positively
        # identify, never inferred from a neighbour. ----------------------
        for name, idx in (("ALPHA feature", alpha_idx), ("BRAVO feature", bravo_idx),
                           ("CHARLIE feature", charlie_idx)):
            if idx is not None and not _has_any_bg(lines[idx]):
                fail("row-self-paints-background",
                     f"{name} row (line {idx}) carries no background of its "
                     f"own -- it can only be showing whatever was drawn "
                     f"before it")

        # ---- invariant 1/3/4 (exact width, wide-glyph cells, ONE
        # truncation rule) for BRAVO -- measured off the row's OWN captured
        # bytes, never by requiring byte-for-byte equality with
        # `compose_feature_row_text(width)`: exactly how many columns a
        # caller reserves for a wide leading glyph before invoking that
        # pure function is an internal budgeting choice (owned by the
        # concurrent sower fixing text composition/background painting in
        # tools/sidebar.py, not this file), so asserting the FINAL rendered
        # cell-width and the single-ellipsis-marking rule is what actually
        # matches the three invariants this step was scoped to -- not one
        # particular reservation amount. -----------------------------------
        if bravo_idx is not None:
            actual_feature = stripped[bravo_idx].rstrip(" ")
            actual_cells = sidebar._cell_width(actual_feature)
            if actual_cells > width:
                fail("no-cell-overflow",
                     f"BRAVO feature row's rendered text is {actual_cells} "
                     f"cells wide at pane width {width}: {actual_feature!r}")
            was_full_name = _BRAVO_FEATURE_NAME in actual_feature
            if not was_full_name and not actual_feature.endswith(sidebar.ELLIPSIS):
                fail("cut-marked-one-rule",
                     f"BRAVO feature row was cut but does not end with the "
                     f"ellipsis: {actual_feature!r}")

            bravo_task_idx = bravo_idx + 1
            if bravo_task_idx < len(stripped):
                # No task-bar column any more (operator ruling, 2026-07-28:
                # the quarter block is gone, the task row is now a flat
                # full-width band) -- the row starts directly with its own
                # status glyph, peeled off the same way `_row_core` already
                # peels every other row's leading glyph.
                actual_task_body = _row_core(
                    stripped[bravo_task_idx],
                    status_alphabet="".join(set(sidebar.STATUS_EMOJI.values())) + sidebar.SPINNER_FRAMES,
                )
                task_cells = sidebar._cell_width(actual_task_body)
                task_avail = max(width - 1, 0)
                if task_cells > task_avail:
                    fail("no-cell-overflow",
                         f"BRAVO task row's rendered body is {task_cells} "
                         f"cells wide with {task_avail} available: {actual_task_body!r}")
                task_full_name = _BRAVO_TASK_NAME in actual_task_body
                # The task row's own right-aligned METRICS tail (M1,
                # sidebar_rows.py's `_task_metrics_text`, wired in by
                # sidebar_paint_task.py) rides the same always-survives-
                # truncation slot the retired progress circle used to --
                # peeled here by PATTERN rather than `_row_core`'s
                # small-alphabet peel, since running-time text is free-form
                # ("0s"/"12m"/"1h05"), not a fixed glyph set. BRAVO is
                # terminal (outcome:fail), so its running time freezes at
                # whatever the fixture's own start/fail events measured --
                # real text, not a fixture artifact to special-case around.
                name_body = _METRICS_TAIL_RE.sub("", actual_task_body)
                if not task_full_name and not name_body.endswith(sidebar.ELLIPSIS):
                    fail("cut-marked-one-rule",
                         f"BRAVO task row was cut but does not end with the "
                         f"ellipsis: {actual_task_body!r}")
            else:
                fail("visibility", "BRAVO task row not found directly under its feature row")

        # ---- invariant 5: no row is informationless -- ALPHA's sole
        # same-named task must still identify itself somehow, not just
        # show a bar, a status glyph and a progress circle with nothing
        # naming which task it is. ----------------------------------------
        if alpha_idx is not None:
            alpha_task_idx = alpha_idx + 1
            if alpha_task_idx < len(stripped):
                # No task-bar column and no progress-circle tail any more
                # (both operator-ruled off, 2026-07-28: the quarter block
                # and the white bubble) -- just the leading status glyph
                # to peel off here.
                core = _row_core(
                    stripped[alpha_task_idx],
                    status_alphabet="".join(set(sidebar.STATUS_EMOJI.values())) + sidebar.SPINNER_FRAMES,
                )
                if not core:
                    fail("no-informationless-row",
                         f"ALPHA task row (line {alpha_task_idx}) carries a "
                         f"marker and a status glyph but no name at all: "
                         f"{stripped[alpha_task_idx]!r}")
            else:
                fail("visibility", "ALPHA task row not found directly under its feature row")

        # ---- invariant 2: dead space below the last content row is
        # painted in the repo's own fill tone, never bare terminal
        # default. -----------------------------------------------------
        last_content_idx = max((i for i, l in enumerate(stripped) if l.strip()), default=-1)
        dead_rows = range(last_content_idx + 1, height)
        if dead_rows:
            dead_zone_raw = "".join(lines[i] for i in dead_rows if i < len(lines))
            if not _has_any_bg(dead_zone_raw):
                fail("dead-space-painted",
                     f"no explicit background anywhere in rows "
                     f"{dead_rows.start}-{dead_rows.stop - 1} of {height}")

    def test_invariants_hold_across_the_width_and_height_sweep(self) -> None:
        failures: list[str] = []
        for width, height in GEOMETRIES:
            self._check_geometry(width, height, failures)
        if failures:
            report = "\n".join(f"  - {f}" for f in failures)
            self.fail(
                f"{len(failures)} invariant failure(s) across the "
                f"{len(GEOMETRIES)}-geometry sweep:\n{report}"
            )


@unittest.skipUnless(_HAS_TMUX, "tmux not available in this environment")
class SidebarResizePathTests(unittest.TestCase):
    """render, resize the pane, re-render, assert every invariant again --
    a renderer correct only on first paint is not correct (operator,
    2026-07-28: "the width is variable as the pane can be resized"). Reuses
    `SidebarGeometrySweepTests._check_geometry`'s own checks via a plain
    function extracted for that purpose would duplicate state; instead this
    class re-derives the same two structural checks directly against a
    SINGLE long-running session that is resized in place, which is the one
    thing a fresh-launch-per-geometry sweep cannot exercise."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.runtime_dir = Path(self._tmp.name) / "run"
        self.runtime_dir.mkdir()
        self.projects_root = self.runtime_dir / "orchard" / "projects"
        self.projects_root.mkdir(parents=True)
        _seed_fixture(self.projects_root)
        self.driver = _TmuxDriver(60, 24, self.runtime_dir)
        self.addCleanup(self.driver.kill)

    def _assert_no_bare_default_below_content(self, lines, stripped, height, when: str) -> None:
        last_content_idx = max((i for i, l in enumerate(stripped) if l.strip()), default=-1)
        dead_rows = range(last_content_idx + 1, height)
        if not dead_rows:
            return
        dead_zone_raw = "".join(lines[i] for i in dead_rows if i < len(lines))
        self.assertTrue(
            _has_any_bg(dead_zone_raw),
            f"{when}: no explicit background in rows "
            f"{dead_rows.start}-{dead_rows.stop - 1} of {height}",
        )

    def _assert_bravo_row_well_formed(self, stripped, width, when: str) -> None:
        """Same implementation-agnostic checks as
        `SidebarGeometrySweepTests._check_geometry` -- measured off the
        row's OWN rendered cell-width and ellipsis-marking, never by
        requiring exact equality with `compose_feature_row_text(width)`
        (see that method's own comment: the exact reservation a caller
        makes for a wide leading glyph is an internal budgeting choice
        owned by the concurrent sower fixing text composition, not a
        contract this file should pin to one specific number)."""
        bravo_idx = next(i for i, l in enumerate(stripped) if "BRAVO" in l)
        actual = stripped[bravo_idx].rstrip(" ")
        cells = sidebar._cell_width(actual)
        self.assertLessEqual(
            cells, width,
            f"{when}: BRAVO feature row is {cells} cells wide at pane width {width}: {actual!r}",
        )
        if _BRAVO_FEATURE_NAME not in actual:
            self.assertTrue(
                actual.endswith(sidebar.ELLIPSIS),
                f"{when}: BRAVO feature row was cut but does not end with "
                f"the ellipsis: {actual!r}",
            )
        return bravo_idx, actual

    def test_resize_path_repaints_correctly_at_the_new_geometry(self) -> None:
        self.driver.launch()
        before = self.driver.capture_when_ready(_looks_complete)
        before_stripped = [_strip_sgr(l) for l in before]
        self._assert_no_bare_default_below_content(
            before, before_stripped, self.driver.height, "before resize",
        )
        _, actual_before = self._assert_bravo_row_well_formed(
            before_stripped, self.driver.width, "before resize",
        )

        # Resize to the operator's own judged geometry -- narrower AND
        # shorter, so both the width-driven truncation point and the
        # height-driven dead-space fill must both re-derive, not carry over
        # stale values computed for the old 60x24 pane.
        self.driver.resize(37, 47)
        after = self.driver.capture_when_ready(_looks_complete)
        after_stripped = [_strip_sgr(l) for l in after]

        self.assertNotEqual(
            len(after), len(before),
            "capture-pane returned the same height after an actual resize "
            "-- the pane never really changed shape",
        )

        _, actual_after = self._assert_bravo_row_well_formed(
            after_stripped, self.driver.width, "after resize",
        )
        self.assertNotEqual(
            actual_before, actual_after,
            "the row's rendered text is byte-identical before and after "
            "resizing to a genuinely different width -- truncation did "
            "not re-derive against the new geometry",
        )
        self._assert_no_bare_default_below_content(
            after, after_stripped, self.driver.height, "after resize",
        )


@unittest.skipUnless(_HAS_TMUX, "tmux not available in this environment")
class SidebarMinimumWidthDegradationTests(unittest.TestCase):
    """No width is privileged, but a renderer still has to do SOMETHING at
    a pane too narrow to hold even one glyph plus its own name. This
    asserts the renderer's actual floor rather than describing one in a
    comment: `tools/sidebar.py` declares no MIN_WIDTH constant of its own,
    and every row-layout helper (`_feature_row_layout`, `_task_row_layout`,
    `_tight_quote_floor`) clamps its budget at `max(..., 0)` rather than
    raising -- so the observed floor is "never crashes, keeps painting a
    background, degrades to glyph-only or truncated-to-nothing" rather
    than a documented minimum column count. `--once` is used here (paints
    one real frame through the exact same draw path and exits) because a
    process that crashed cannot be waited on interactively -- an exit code
    and the absence of a traceback are the only two things worth asserting
    at a width this extreme."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.runtime_dir = Path(self._tmp.name) / "run"
        self.runtime_dir.mkdir()
        self.projects_root = self.runtime_dir / "orchard" / "projects"
        self.projects_root.mkdir(parents=True)
        _seed_fixture(self.projects_root)

    def _run_once(self, width: int, height: int) -> tuple[str | None, str]:
        """Exit status via a FILE the shell writes after `--once` returns,
        never by parsing the pane's own screen text -- at width=1/2/4 the
        wrapper's own `echo ONCE_EXIT:$?` marker wraps one character per
        physical screen LINE (an original draft of this test parsed that
        text and every one of these widths came back "never exited", which
        was this test's own detection breaking, not the app hanging)."""
        driver = _TmuxDriver(width, height, self.runtime_dir)
        raw_log = Path(self._tmp.name) / f"once-{width}x{height}.log"
        exit_file = Path(self._tmp.name) / f"exit-{width}x{height}.txt"
        try:
            driver._tmux("new-session", "-d", "-x", str(width), "-y", str(height), check=True)
            driver._tmux("resize-window", "-x", str(width), "-y", str(height))
            driver._await_pane_size()
            driver._tmux("pipe-pane", "-o", f"cat >> {raw_log}", check=True)
            command = (
                f"HOME={self.runtime_dir} XDG_RUNTIME_DIR={self.runtime_dir} "
                f"{sys.executable} {_SIDEBAR_PY} --once; echo $? > {exit_file}"
            )
            driver._tmux("send-keys", command, "Enter")
            deadline = time.time() + 10.0
            while time.time() < deadline and not exit_file.exists():
                time.sleep(0.1)
            exit_code = exit_file.read_text().strip() if exit_file.exists() else None
            raw_text = raw_log.read_bytes().decode("utf-8", errors="replace") if raw_log.exists() else ""
            return exit_code, raw_text
        finally:
            driver.kill()

    def test_extremely_narrow_widths_degrade_without_crashing(self) -> None:
        for width, height in ((1, 10), (2, 10), (4, 10), (8, 10), (12, 10)):
            with self.subTest(width=width, height=height):
                exit_code, raw_text = self._run_once(width, height)
                self.assertEqual(
                    exit_code, "0",
                    f"--once at {width}x{height} exited {exit_code}, raw output: {raw_text!r}",
                )
                self.assertNotIn(
                    "Traceback (most recent call last)", raw_text,
                    f"--once at {width}x{height} printed a traceback instead "
                    f"of degrading gracefully",
                )


# ---------------------------------------------------------------------------
# Real-runtime-tree run -- NOT pytest-collected (no test_ prefix reached
# from here down at module scope, and this is gated behind __main__). Reads
# the operator's ACTUAL $HOME/$XDG_RUNTIME_DIR exactly as his own sidebar
# does -- no seeding, no writes, so it cannot leak into the live tree the
# way tests/test_orchard_transport.py's own history did
# ($XDG_RUNTIME_DIR/orchard/projects/ leaking 1091 tmp* directories). Real
# fleet content is unpredictable, so this only ever reports what it finds;
# it is not part of the deterministic suite.
# ---------------------------------------------------------------------------

def _run_against_real_tree(width: int = 37, height: int = 47) -> None:
    socket = f"sidebar-real-{uuid.uuid4().hex[:8]}"

    def tmux(*args, check=False):
        return subprocess.run(["tmux", "-L", socket, *args], check=check,
                               capture_output=True, text=True)

    tmux("new-session", "-d", "-x", str(width), "-y", str(height), check=True)
    tmux("resize-window", "-x", str(width), "-y", str(height))
    deadline = time.time() + 3.0
    while time.time() < deadline:
        actual = tmux("list-windows", "-F", "#{window_width}x#{window_height}").stdout.strip()
        if actual == f"{width}x{height}":
            break
        time.sleep(0.05)
    tmux("send-keys", f"{sys.executable} {_SIDEBAR_PY}", "Enter")
    try:
        deadline = time.time() + 10.0
        previous = None
        lines: list[str] = []
        while time.time() < deadline:
            current = tmux("capture-pane", "-e", "-p", check=True).stdout.splitlines()
            if current and current == previous:
                lines = current
                break
            previous = current
            time.sleep(0.2)
        stripped = [_strip_sgr(l) for l in lines]
        print(f"--- real runtime tree at {width}x{height} ---")
        for i, l in enumerate(stripped):
            print(f"{i:3d}: {l}")
        last_content_idx = max((i for i, l in enumerate(stripped) if l.strip()), default=-1)
        dead_rows = range(last_content_idx + 1, height)
        if dead_rows:
            dead_zone_raw = "".join(lines[i] for i in dead_rows if i < len(lines))
            print(f"dead rows {dead_rows.start}-{dead_rows.stop - 1}: "
                  f"has_own_background={_has_any_bg(dead_zone_raw)}")
        else:
            print("no dead rows -- content fills the whole pane")
    finally:
        tmux("kill-server")


if __name__ == "__main__":
    if "--real" in sys.argv:
        w = 37
        h = 47
        args = [a for a in sys.argv[1:] if a != "--real"]
        if len(args) >= 2:
            w, h = int(args[0]), int(args[1])
        _run_against_real_tree(w, h)
    else:
        unittest.main()

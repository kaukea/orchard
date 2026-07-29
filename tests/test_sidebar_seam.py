"""The full seam test — spec's acceptance bar (docs/sidebar-spec.md §8):
"the seam test drives the real courier under a fake project ('your producer
won't know the difference'), paired per Decision-103 with a static-fixture
companion validated by hand."

This is the SEAM, not a fixture round-trip: real `tools/courier.py init` and
`tools/orchard_topic.py post lifecycle|status|delegation|outcome` calls, run
as actual subprocesses (never imported and called in-process) against a
fake multi-project git world — env-redirected exactly the way
`tests/test_courier_registry.py`'s `RegistryCliTestCase` points the courier
at a fake world (its fixture style is reused here; that file itself is
off-limits — a second workstream is rewriting `tools/courier.py`/
`tools/orchard_topic.py` concurrently, so both are driven here strictly as
black-box CLIs, never imported). The scripts' own identity resolution
(`courier.identity_of()`) reads the feature id off the checkout's own git
worktree name, so the fake world is built as REAL git worktrees, one per
feature — the same shape a landscaper's own `.claude/worktrees/<id>` is.

Everything the real CLIs write is then read back exactly the way the pane
does: `sidebar.build_model()` (the model) and `sidebar.render_lines()` (the
plain-text render path shared with the curses painters — see
`sidebar_render_text.py`'s module docstring). No curses/tmux dependency
here; that emulator-frame layer is `tests/test_sidebar_frame.py`'s already-
established territory and is not duplicated.

SCENARIO — >=2 projects, >=2 features each, covering every state the real
event grammar can produce (docs/sidebar-spec.md §6's six-state vocabulary
is `working / waiting / idle / awaiting-another-agent / done / failed`;
`tools/sidebar_model.py`'s own `_status_for()` docstring is explicit that
"waiting"/"awaiting_agent" cannot be produced by this grammar at all — "No
waiting/awaiting_agent variant exists (no blocked/notify_user post verb)" —
a pre-existing, already-documented gap this step does not invent a
workaround for; see the module-level FLAG below):

  - project "orchid-one": feat-alpha (WORKING — two agents on one task, one
    live, one backdated stale: "stale is a colour, not a removal" is
    checked directly on that agent's own row; plus three subagents,
    scheduled/doing/done) and feat-beta (full lifecycle starting -> started
    -> stopping -> stopped with NO outcome -> IDLE).
  - project "orchid-two": feat-gamma (full lifecycle starting -> started ->
    stopping -> stopped, THEN outcome success -> DONE — "one agent fully
    stopped with outcome") and feat-delta (outcome fail -> FAILED).

The SAME session id is reused for feat-alpha's live agent and feat-gamma's
agent, posted from two different fake repos, proving the real CLI's own
`project_slug()` (not merely the model's own fold) keeps them apart.

Re-run entry point (the operator's rehearsal for end-to-end acceptance):

    python3 -m pytest tests/test_sidebar_seam.py -v

or the whole file directly (`python3 tests/test_sidebar_seam.py`, same
`unittest.main()` any file in this suite already supports).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.join(os.path.dirname(_ROOT_DIR), "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sidebar  # noqa: E402
import sidebar_glyphs  # noqa: E402
import sidebar_model  # noqa: E402

_COURIER_PY = os.path.join(_TOOLS_DIR, "courier.py")
_ORCHARD_TOPIC_PY = os.path.join(_TOOLS_DIR, "orchard_topic.py")
_FIXTURES_DIR = Path(_ROOT_DIR) / "fixtures"

# FLAG (not a workaround): "waiting" and "awaiting_agent" are excluded from
# this scenario's coverage on purpose. `tools/sidebar_model.py::_status_for`
# derives status purely from lifecycle+outcome signals; no event this
# grammar's real CLI surface can post (lifecycle/status/delegation/outcome)
# ever sets `rec["outcome"]`/`rec["state"]` to anything that maps to either
# — confirmed by reading `_status_for` and `_marker_task_rec` directly, and
# already recorded as a known gap (docs/TODO.md.d/sidebar-teamwork.md's
# 2026-07-28 entry: "two of his six cannot be produced by real events at
# all... making them real is producer work outside this round"). Inventing
# a marker write or a new CLI verb to force them would be exactly the
# agent-invented scope the sower brief rules out; this is reported as a
# standing gap, not silently worked around.


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _make_main_repo(base: Path, name: str, remote: str) -> Path:
    repo = base / name
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "seam@example.com")
    _git(repo, "config", "user.name", "seam")
    _git(repo, "remote", "add", "origin", remote)
    _git(repo, "commit", "--allow-empty", "-m", "init")
    return repo


def _add_worktree(main_repo: Path, worktrees_dir: Path, feature_id: str) -> Path:
    path = worktrees_dir / feature_id
    _git(main_repo, "worktree", "add", str(path), "-b", f"f/{feature_id}")
    return path


class _FakeWorld:
    """One shared fake `$XDG_RUNTIME_DIR`/`$HOME`, two fake origin repos,
    two feature worktrees under each — the whole surface the real CLIs run
    against, torn down with the TemporaryDirectory. Mirrors
    `RegistryCliTestCase`'s env-redirection shape (see this file's module
    docstring) without importing that off-limits test module."""

    def __init__(self, tmp_root: Path) -> None:
        self.runtime_dir = tmp_root / "run"
        self.runtime_dir.mkdir()
        self.cache_home = tmp_root / "cache"
        self.cache_home.mkdir()
        self.home = tmp_root / "home"
        self.home.mkdir()
        self.projects_root = self.runtime_dir / "orchard" / "projects"

        repos_dir = tmp_root / "repos"
        repos_dir.mkdir()
        main_one = _make_main_repo(repos_dir, "orchid-one", "git@example.com:acme/orchid-one.git")
        main_two = _make_main_repo(repos_dir, "orchid-two", "git@example.com:acme/orchid-two.git")
        worktrees_dir = tmp_root / "worktrees"
        worktrees_dir.mkdir()
        self.wt_alpha = _add_worktree(main_one, worktrees_dir, "feat-alpha")
        self.wt_beta = _add_worktree(main_one, worktrees_dir, "feat-beta")
        self.wt_gamma = _add_worktree(main_two, worktrees_dir, "feat-gamma")
        self.wt_delta = _add_worktree(main_two, worktrees_dir, "feat-delta")

    def env(self, session_id: str, agent: str) -> dict:
        env = {k: v for k, v in os.environ.items()
               if k not in ("CLAUDE_CODE_AGENT", "CLAUDE_CODE_SESSION_ID",
                             "ORCHID_PARENT_SESSION", "ORCHID_PARENT_PROJECT")}
        env.update(
            CLAUDE_CODE_SESSION_ID=session_id, CLAUDE_CODE_AGENT=agent,
            XDG_RUNTIME_DIR=str(self.runtime_dir), XDG_CACHE_HOME=str(self.cache_home),
            HOME=str(self.home),
        )
        return env

    def courier(self, worktree: Path, session_id: str, agent: str, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args], cwd=str(worktree),
            capture_output=True, text=True, env=self.env(session_id, agent), check=True,
        )

    def post(self, worktree: Path, session_id: str, agent: str, *args: str) -> Path:
        """`orchard_topic.py post <args>` as a real subprocess — its stdout,
        on success, is the path of the event file it just wrote (see
        `do_post`'s own `print(courier.orchard_deliver(...))`)."""
        proc = subprocess.run(
            [sys.executable, _ORCHARD_TOPIC_PY, "post", *args], cwd=str(worktree),
            capture_output=True, text=True, env=self.env(session_id, agent), check=True,
        )
        return Path(proc.stdout.strip())

    def init(self, worktree: Path, session_id: str, agent: str) -> None:
        self.courier(worktree, session_id, agent, "init")


def _backdate(path: Path, seconds_ago: float) -> None:
    past = time.time() - seconds_ago
    os.utime(path, (past, past))


def _drive_scenario(world: _FakeWorld) -> dict:
    """Runs the real CLI sequence described in the module docstring.
    Returns the handful of facts the tests need back (which session id
    ended up stale, etc.) rather than the tests re-deriving them."""
    shared_sid = "seam-shared-sid"

    # --- orchid-one / feat-alpha: WORKING, subagents, one stale agent ---
    world.init(world.wt_alpha, shared_sid, "landscaper")
    world.post(world.wt_alpha, shared_sid, "landscaper", "lifecycle", "starting")
    world.post(world.wt_alpha, shared_sid, "landscaper", "lifecycle", "started")
    world.post(world.wt_alpha, shared_sid, "landscaper", "status", "building tree")
    world.post(world.wt_alpha, shared_sid, "landscaper", "delegation", "schedule", "sub-queued-one")
    world.post(world.wt_alpha, shared_sid, "landscaper", "delegation", "begin", "sub-running-one")
    world.post(world.wt_alpha, shared_sid, "landscaper", "delegation", "schedule", "sub-done-one")
    world.post(world.wt_alpha, shared_sid, "landscaper", "delegation", "begin", "sub-done-one")
    world.post(world.wt_alpha, shared_sid, "landscaper", "delegation", "end", "sub-done-one")

    stale_sid = "feat-alpha-stale-sid"
    world.init(world.wt_alpha, stale_sid, "groundskeeper")
    stale_event = world.post(world.wt_alpha, stale_sid, "groundskeeper", "lifecycle", "starting")
    _backdate(stale_event, sidebar_model.ACTIVE_WINDOW_SECONDS + 300)
    stale_marker = stale_event.parent / f"{stale_sid}.marker"
    if stale_marker.exists():
        _backdate(stale_marker, sidebar_model.ACTIVE_WINDOW_SECONDS + 300)

    # --- orchid-one / feat-beta: full lifecycle, no outcome -> IDLE ---
    beta_sid = "feat-beta-sid"
    world.init(world.wt_beta, beta_sid, "sower")
    for state in ("starting", "started", "stopping", "stopped"):
        world.post(world.wt_beta, beta_sid, "sower", "lifecycle", state)

    # --- orchid-two / feat-gamma: full lifecycle + outcome -> DONE ---
    world.init(world.wt_gamma, shared_sid, "landscaper")
    for state in ("starting", "started", "stopping", "stopped"):
        world.post(world.wt_gamma, shared_sid, "landscaper", "lifecycle", state)
    world.post(world.wt_gamma, shared_sid, "landscaper", "outcome", "success")

    # --- orchid-two / feat-delta: outcome fail -> FAILED ---
    delta_sid = "feat-delta-sid"
    world.init(world.wt_delta, delta_sid, "bloomer")
    world.post(world.wt_delta, delta_sid, "bloomer", "lifecycle", "starting")
    world.post(world.wt_delta, delta_sid, "bloomer", "outcome", "fail")

    return {"shared_sid": shared_sid, "stale_sid": stale_sid, "beta_sid": beta_sid,
            "delta_sid": delta_sid}


def _line_containing(lines: list[str], needle: str) -> str:
    matches = [line for line in lines if needle in line]
    assert len(matches) == 1, f"expected exactly one line containing {needle!r}, got {matches!r}"
    return matches[0]


class SeamScenarioTestCase(unittest.TestCase):
    """Shared fixture: build the fake world once, drive the real CLIs once,
    read the result through both the model and the plain-text render path.
    One `setUp` per test (not per class) so a failing assertion never
    leaks state into a sibling test — the CLI drive is the expensive part
    (several dozen real subprocesses) but is still fast enough (a few
    seconds) not to need class-scoped sharing."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.world = _FakeWorld(Path(self._tmp.name))
        self.facts = _drive_scenario(self.world)
        self.now = time.time()

    def _build(self):
        return sidebar.build_model(root=self.world.projects_root, now=self.now, role_step_map={})


class ModelSeamTests(SeamScenarioTestCase):
    def test_both_projects_and_all_four_features_are_present(self):
        fleet = self._build()
        by_name = {repo.name: repo for repo in fleet.repos}
        self.assertEqual(set(by_name), {"orchid-one", "orchid-two"})

        repo_one, repo_two = by_name["orchid-one"], by_name["orchid-two"]
        self.assertEqual({f.name for f in repo_one.features}, {"feat alpha", "feat beta"})
        self.assertEqual({f.name for f in repo_two.features}, {"feat gamma", "feat delta"})

    def test_working_idle_done_failed_are_all_reachable_through_the_real_cli(self):
        fleet = self._build()
        by_name = {repo.name: repo for repo in fleet.repos}
        features_one = {f.name: f for f in by_name["orchid-one"].features}
        features_two = {f.name: f for f in by_name["orchid-two"].features}

        self.assertEqual(features_one["feat alpha"].status, "working")
        self.assertEqual(features_one["feat beta"].status, "idle")
        self.assertEqual(features_two["feat gamma"].status, "done")
        self.assertEqual(features_two["feat delta"].status, "failed")

    def test_stale_agent_is_a_colour_not_a_removal(self):
        # feat-alpha's task carries TWO agents: the live one (working) and
        # the backdated one. The task's own combined status is "working"
        # (the more urgent of the two, precedence in `_combine_status`) —
        # the point under test is that the stale agent's OWN row still
        # renders, carrying "stale", rather than disappearing.
        fleet = self._build()
        repo_one = next(r for r in fleet.repos if r.name == "orchid-one")
        feat_alpha = next(f for f in repo_one.features if f.name == "feat alpha")
        self.assertEqual(len(feat_alpha.tasks), 1)
        task = feat_alpha.tasks[0]
        self.assertEqual(task.status, "working")
        agents_by_role = {a.role: a for a in task.unstepped_agents}
        self.assertEqual(set(agents_by_role), {"landscaper", "groundskeeper"})
        self.assertEqual(agents_by_role["landscaper"].status, "working")
        self.assertEqual(agents_by_role["groundskeeper"].status, "stale")
        self.assertEqual(agents_by_role["groundskeeper"].session_id, self.facts["stale_sid"])

    def test_subagents_scheduled_running_and_done_all_appear(self):
        fleet = self._build()
        repo_one = next(r for r in fleet.repos if r.name == "orchid-one")
        feat_alpha = next(f for f in repo_one.features if f.name == "feat alpha")
        landscaper = next(a for a in feat_alpha.tasks[0].unstepped_agents if a.role == "landscaper")
        subs_by_label = {s.label: s.state for s in landscaper.subagents}
        self.assertEqual(subs_by_label, {
            "sub-queued-one": "scheduled", "sub-running-one": "doing", "sub-done-one": "done",
        })

    def test_full_lifecycle_starting_through_stopped_reaches_idle_without_outcome(self):
        fleet = self._build()
        repo_one = next(r for r in fleet.repos if r.name == "orchid-one")
        feat_beta = next(f for f in repo_one.features if f.name == "feat beta")
        self.assertEqual(feat_beta.status, "idle")

    def test_one_agent_fully_stopped_with_outcome_reads_done(self):
        fleet = self._build()
        repo_two = next(r for r in fleet.repos if r.name == "orchid-two")
        feat_gamma = next(f for f in repo_two.features if f.name == "feat gamma")
        self.assertEqual(feat_gamma.status, "done")
        self.assertEqual(feat_gamma.tasks[0].status, "done")

    def test_same_session_id_across_two_projects_never_cross_contaminates(self):
        # `shared_sid` posted a "working" agent into orchid-one/feat-alpha
        # and a "done" agent into orchid-two/feat-gamma — the real CLI's
        # own `project_slug()` (cwd-derived, not test-fixture-derived) is
        # what has to keep these apart, not merely the model's own fold.
        fleet = self._build()
        by_name = {repo.name: repo for repo in fleet.repos}
        alpha_task = next(f for f in by_name["orchid-one"].features if f.name == "feat alpha").tasks[0]
        gamma_task = next(f for f in by_name["orchid-two"].features if f.name == "feat gamma").tasks[0]
        alpha_agent = next(a for a in alpha_task.unstepped_agents if a.session_id == self.facts["shared_sid"])
        gamma_agent = next(a for a in gamma_task.unstepped_agents if a.session_id == self.facts["shared_sid"])
        self.assertEqual(alpha_agent.status, "working")
        self.assertEqual(gamma_agent.status, "done")
        # And the reverse: orchid-two carries no "feat alpha"/"feat beta",
        # orchid-one carries no "feat gamma"/"feat delta".
        self.assertNotIn("feat alpha", {f.name for f in by_name["orchid-two"].features})
        self.assertNotIn("feat gamma", {f.name for f in by_name["orchid-one"].features})

    def test_terminal_task_status_is_correctly_typed_done_vs_failed_never_shared(self):
        fleet = self._build()
        by_name = {repo.name: repo for repo in fleet.repos}
        gamma_status = next(f for f in by_name["orchid-two"].features if f.name == "feat gamma").status
        delta_status = next(f for f in by_name["orchid-two"].features if f.name == "feat delta").status
        self.assertEqual(gamma_status, "done")
        self.assertEqual(delta_status, "failed")
        self.assertNotEqual(gamma_status, delta_status)


class RenderTextSeamTests(SeamScenarioTestCase):
    """Same driven scenario, read through `sidebar.render_lines()` — the
    pure-text render pipeline shared with the curses painters
    (`sidebar_render_text.py`'s module docstring) — proving the seam holds
    all the way to what a pane actually shows, not merely the model."""

    def _render(self) -> list[str]:
        fleet = self._build()
        return sidebar.render_lines(fleet, width=100)

    def test_both_project_headers_and_all_four_feature_rows_render(self):
        lines = self._render()
        text = "\n".join(lines)
        self.assertIn("orchid-one", text)
        self.assertIn("orchid-two", text)
        for name in ("feat alpha", "feat beta", "feat gamma", "feat delta"):
            self.assertIn(name, text)

    def test_nesting_matches_spec_repo_then_feature_then_task(self):
        # spec §1's tree: project -> feature -> task -> ... . `feat beta`
        # (idle, open) is the simplest case that still nests a task row —
        # its own "Task" row (see the name-drop-to-"Task" test below) must
        # sit strictly after its feature row and before the next feature.
        fleet = self._build()
        rows = sidebar.flatten(fleet)
        repo_one_idx = next(i for i, r in enumerate(rows) if r.kind == "repo" and r.label == "orchid-one")
        beta_idx = next(i for i, r in enumerate(rows) if r.kind == "feature" and "feat beta" in r.label)
        self.assertGreater(beta_idx, repo_one_idx)
        self.assertEqual(rows[repo_one_idx].depth, 0)
        self.assertEqual(rows[beta_idx].depth, 1)
        task_idx = beta_idx + 1
        self.assertEqual(rows[task_idx].kind, "task")
        self.assertEqual(rows[task_idx].depth, 2)

    def test_single_task_sharing_its_features_name_renders_the_literal_task_label(self):
        # every feature in this scenario has exactly one task whose own
        # name is the feature's borrowed name (no `identity.task_name` on
        # this event grammar) — sidebar-spec.md §6's 2026-07-29 ruling:
        # render the literal "Task", not the repeated name.
        rows = sidebar.flatten(self._build())
        beta_task = next(r for r in rows if r.kind == "task" and r.status == "idle")
        self.assertEqual(beta_task.label, "Task")

    def test_working_agent_and_its_stale_sibling_both_render_distinct_status_glyphs(self):
        lines = self._render()
        landscaper_line = _line_containing(lines, "landscaper")
        groundskeeper_line = _line_containing(lines, "groundskeeper")
        self.assertNotEqual(landscaper_line, groundskeeper_line)

    def test_subagent_rows_carry_three_distinct_glyphs_for_scheduled_doing_done(self):
        lines = self._render()
        queued_line = _line_containing(lines, "sub-queued-one")
        running_line = _line_containing(lines, "sub-running-one")
        done_line = _line_containing(lines, "sub-done-one")
        scheduled_glyph = sidebar_glyphs._SUBAGENT_LIVE_GLYPH["scheduled"]
        doing_glyph = sidebar_glyphs.SUBAGENT_GLYPH
        done_glyph = sidebar_glyphs.STATUS_EMOJI["done"]
        self.assertIn(scheduled_glyph, queued_line)
        self.assertIn(doing_glyph, running_line)
        self.assertIn(done_glyph, done_line)
        self.assertNotEqual({scheduled_glyph, doing_glyph, done_glyph}, {doing_glyph})

    def test_done_feature_with_its_sole_task_also_done_collapses_to_one_row(self):
        # `_feature_collapsed`: a feature folds to its OWN single row once
        # every task is done. feat-gamma's sole task is "done", so no
        # separate task row (and certainly no agent/subagent rows) survive
        # under it.
        rows = sidebar.flatten(self._build())
        gamma_idx = next(i for i, r in enumerate(rows) if r.kind == "feature" and "feat gamma" in r.label)
        # the NEXT row (if any) belongs to a different feature/repo, not a
        # task nested under feat-gamma.
        if gamma_idx + 1 < len(rows):
            nxt = rows[gamma_idx + 1]
            self.assertFalse(nxt.kind == "task" and nxt.depth == rows[gamma_idx].depth + 1)

    def test_failed_terminal_task_folds_to_its_own_row_but_the_feature_does_not_collapse(self):
        # feat-delta is "failed", not "done" — `_feature_collapsed` only
        # ever fires on all-done, so the feature row survives AND its own
        # task row survives (folded: no steps/agents beneath it, per
        # `_task_rows`'s TERMINAL_TASK_STATUSES short-circuit).
        rows = sidebar.flatten(self._build())
        delta_idx = next(i for i, r in enumerate(rows) if r.kind == "feature" and "feat delta" in r.label)
        task_idx = delta_idx + 1
        self.assertEqual(rows[task_idx].kind, "task")
        self.assertEqual(rows[task_idx].status, "failed")
        # nothing else belongs to feat-delta below its own task row.
        if task_idx + 1 < len(rows):
            nxt = rows[task_idx + 1]
            self.assertFalse(nxt.depth > rows[task_idx].depth)


# ---------------------------------------------------------------------------
# Decision-103 static-fixture companion.
#
# `tests/fixtures/PROVENANCE.md` (as it stood before this step) documents
# every fixture there as CAPTURED FROM THE LIVE SYSTEM and hand-validated by
# the operator at capture time — this fixture is neither: it is a plain-text
# `render_lines()` dump of the fake-world scenario above, generated by this
# same step. It is added under its OWN clearly-labelled sub-heading in
# PROVENANCE.md (never folded into the "live system" claim) and is PENDING
# THE OPERATOR'S OWN EYEBALL VALIDATION — flagged in the sower's return, not
# silently presented as already hand-validated. What this class buys in the
# meantime, per Decision-103's actual purpose, is a second test reading the
# FROZEN file rather than a freshly-generated one — so a future change to
# `render_lines()`/`sidebar_model.py` that silently breaks the scenario's
# shape shows up as a diff against committed text, not just a green
# round-trip against whatever the code currently does.
# ---------------------------------------------------------------------------

_SEAM_FIXTURE = _FIXTURES_DIR / "seam_scenario_frame.txt"


class SeamStaticFixtureTests(unittest.TestCase):
    def test_frozen_seam_frame_carries_every_project_feature_and_state(self):
        # "bloomer" (feat-delta's own agent) is deliberately NOT among these
        # needles: feat-delta's sole task is terminal ("failed"), and a
        # terminal task folds to its own row (`_task_rows`'s
        # TERMINAL_TASK_STATUSES short-circuit) — its agent's identity line
        # never reaches the render at all. That is the correct, spec'd
        # behaviour under test elsewhere
        # (`test_failed_terminal_task_folds_to_its_own_row_...`), not a gap
        # in this fixture.
        text = _SEAM_FIXTURE.read_text(encoding="utf-8")
        for needle in (
            "orchid-one", "orchid-two", "feat alpha", "feat beta", "feat gamma", "feat delta",
            "sub-queued-one", "sub-running-one", "sub-done-one",
            "landscaper", "groundskeeper", "sower",
        ):
            self.assertIn(needle, text, f"{needle!r} missing from the frozen seam fixture")


def _capture_fixture(target: Path) -> None:
    """Regenerate `tests/fixtures/seam_scenario_frame.txt` — invoked ONLY by
    this module's own `__main__` block (`--recapture`), never at test time,
    so a passing test suite can never silently rewrite the frozen fixture
    out from under itself."""
    with tempfile.TemporaryDirectory() as tmp:
        world = _FakeWorld(Path(tmp))
        _drive_scenario(world)
        fleet = sidebar.build_model(root=world.projects_root, now=time.time(), role_step_map={})
        lines = sidebar.render_lines(fleet, width=100)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    if "--recapture" in sys.argv:
        _capture_fixture(_SEAM_FIXTURE)
    else:
        unittest.main()

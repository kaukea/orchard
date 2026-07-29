"""Unit tests for tools/orchard_topic.py — the sanctioned project-topic poster.

The script is invoked via subprocess (matches how it actually runs — an agent
shells out to it), against a real git-init'd temp repo (see tests/support.py)
so `git rev-parse --git-common-dir` resolves for real rather than being
mocked. XDG_RUNTIME_DIR, CLAUDE_CODE_SESSION_ID, CLAUDE_CODE_AGENT and
ORCHID_PARENT_SESSION are pinned per-test via a private tmp_path (see
`_run`), so no real runtime dir or session is ever touched, `courier.identity_of()`
resolves deterministically, and any courier bounce the reject path triggers lands
inside the temp repo's own `.git/the-works/courier/` (explicitly cleaned in the
`repo` fixture's teardown) rather than this repo's.

Every valid post now carries an `identity` block (from `courier.identity_of()`,
via the producer's `_attach_snapshot`) alongside the fixed from/to/subject/
body fields — the temp repos here have no linked worktree and no transcript
under ~/.claude/projects, so `identity` resolves to just `{"agent": ...}`
(plus `parent` when ORCHID_PARENT_SESSION is set) and `status` never
resolves at all (courier.status_of() finds no transcript, so every key it would
contribute is empty and _status() drops them all) — asserted absent below
rather than guessed at.

Accepted events (lifecycle/status/delegation/outcome/task) now land through
`courier.orchard_deliver()` in the NEW per-session project layout —
`$XDG_RUNTIME_DIR/orchard/projects/<repo>.<project>/<sid>.<ts>.json`, with a
sibling `<sid>.marker` and a parent-project-dir mtime bump — matching
tests/test_orchard_transport.py's `project_slug()`-driven idiom exactly, so
the slug is asked of courier rather than re-derived here. The reject path's
location is unchanged: telemetry still lands under the OLD
`topics/telemetry/<repo>/` directory. Its NAMING is no longer local, though —
orchard_topic.py's `write_message()` now builds the filename via
`courier.orchard_message_name()`/`courier.write_orchard_file()`, the same
validated constructor orchard_deliver() uses, closing the gap where the old
ad hoc `f"{sid}.{ts}"` name silently dropped the `.json` extension.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from support import make_repo  # noqa: E402

_SCRIPT = os.path.join(_TOOLS_DIR, "orchard_topic.py")
SID = "test-sid-0001"
DEFAULT_AGENT = "landscaper"


def _run(cwd, runtime_dir, args, sid=SID, agent=DEFAULT_AGENT, parent=None, home=None,
         effort=None, reasoning_effort=None, orchid_effort=None):
    """Shell out to the script with a deterministic identity environment.

    CLAUDE_CODE_AGENT is pinned (default "landscaper", overridable for the
    gardener-only `task` cases) and ORCHID_PARENT_SESSION is pinned to
    `parent` or deleted outright — never left to whatever the real
    environment happens to hold — so `courier.identity_of()` resolves the same
    way on every run. `home`, when given, overrides HOME so
    `courier.status_of()`'s transcript lookup (`~/.claude/projects/*/<sid>.jsonl`)
    resolves against a fixture transcript instead of the real one. `effort`/
    `reasoning_effort`/`orchid_effort` are pinned the same deliberate way as
    `parent` (deleted unless given) so a test never inherits whatever
    CLAUDE_EFFORT/CLAUDE_CODE_REASONING_EFFORT/ORCHID_EFFORT this test
    process itself happens to be running under — the three-way reader chain
    (docs/courier-wire.md §2b) needs all three independently controllable to
    prove its priority order.
    """
    env = dict(os.environ)
    env["XDG_RUNTIME_DIR"] = str(runtime_dir)
    if home is not None:
        env["HOME"] = str(home)
    env["CLAUDE_CODE_SESSION_ID"] = sid
    env["CLAUDE_CODE_AGENT"] = agent
    if parent is None:
        env.pop("ORCHID_PARENT_SESSION", None)
    else:
        env["ORCHID_PARENT_SESSION"] = parent
    for var, value in (
        ("CLAUDE_EFFORT", effort),
        ("CLAUDE_CODE_REASONING_EFFORT", reasoning_effort),
        ("ORCHID_EFFORT", orchid_effort),
    ):
        if value is None:
            env.pop(var, None)
        else:
            env[var] = value
    return subprocess.run(
        [sys.executable, _SCRIPT, "post", *args],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=15,
    )


def _project_dir(runtime_dir, slug):
    return runtime_dir / "orchard" / "projects" / slug


def _telemetry_dir(runtime_dir, repo_name):
    return runtime_dir / "orchard" / "topics" / "telemetry" / repo_name


def _slug(repo):
    """Ask courier.project_slug() itself, from within `repo`, rather than
    re-deriving the <repo>.<project> / basename-fallback algorithm here —
    matches tests/test_orchard_transport.py's `_project_slug` idiom."""
    env = dict(os.environ)
    env["PYTHONPATH"] = _TOOLS_DIR
    proc = subprocess.run(
        [sys.executable, "-c", "import courier; print(courier.project_slug())"],
        cwd=repo, capture_output=True, text=True, env=env, check=True,
    )
    return proc.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A throwaway git repo — plus teardown for the courier inbox a reject-path
    bounce (orchard_topic.py's `reject()` shells out to `courier.py send`) writes
    under the repo's own git-common-dir, so no courier state leaks past the test
    even though tmp_path would eventually reclaim it anyway."""
    path = make_repo(str(tmp_path))
    yield path
    common = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"], cwd=path,
        capture_output=True, text=True,
    ).stdout.strip()
    if common:
        courier_dir = Path(common).resolve() / "the-works" / "courier"
        if courier_dir.exists():
            shutil.rmtree(courier_dir, ignore_errors=True)


@pytest.fixture
def runtime_dir(tmp_path):
    d = tmp_path / "xdg-runtime"
    d.mkdir()
    return d


# --- lifecycle -------------------------------------------------------------

@pytest.mark.parametrize("state", ["starting", "started", "stopping", "stopped"])
def test_lifecycle_post_writes_expected_envelope(repo, runtime_dir, state):
    result = _run(repo, runtime_dir, ["lifecycle", state])
    assert result.returncode == 0, result.stderr

    repo_name = Path(repo).name
    slug = _slug(repo)
    files = list(_project_dir(runtime_dir, slug).glob(f"{SID}.*.json"))
    assert len(files) == 1
    written = files[0]
    assert result.stdout.strip() == str(written)
    assert (_project_dir(runtime_dir, slug) / f"{SID}.marker").exists()

    envelope = json.loads(written.read_text(encoding="utf-8"))
    assert envelope["from"] == f":session:{SID}"
    assert envelope["to"] == f":topic:repository/{repo_name}"
    assert envelope["subject"] == f"orchard:agent:lifecycle:{state}"
    assert "body" not in envelope
    assert envelope["identity"]["agent"] == DEFAULT_AGENT
    assert "status" not in envelope


def test_lifecycle_post_carries_parent_when_orchid_parent_session_set(repo, runtime_dir):
    result = _run(repo, runtime_dir, ["lifecycle", "started"], parent="parent-sid-9")
    assert result.returncode == 0, result.stderr

    slug = _slug(repo)
    files = list(_project_dir(runtime_dir, slug).glob(f"{SID}.*.json"))
    assert len(files) == 1
    envelope = json.loads(files[0].read_text(encoding="utf-8"))
    assert envelope["identity"]["agent"] == DEFAULT_AGENT
    assert envelope["identity"]["parent"] == "parent-sid-9"


def test_lifecycle_bad_state_is_rejected(repo, runtime_dir):
    result = _run(repo, runtime_dir, ["lifecycle", "bogus"])
    assert result.returncode != 0
    assert result.stderr.strip().startswith("orchard-topic: rejected")

    repo_name = Path(repo).name
    assert not _project_dir(runtime_dir, _slug(repo)).exists()

    tfiles = list(_telemetry_dir(runtime_dir, repo_name).glob(f"{SID}.*"))
    assert len(tfiles) == 1
    envelope = json.loads(tfiles[0].read_text(encoding="utf-8"))
    assert envelope["subject"] == "orchard:agent:telemetry:rejected"
    assert envelope["body"]["attempted"] == ["post", "lifecycle", "bogus"]
    assert "reason" in envelope["body"]


# --- status ------------------------------------------------------------

@pytest.mark.parametrize("text", ["reading", "reading files"])
def test_status_post_writes_expected_envelope(repo, runtime_dir, text):
    result = _run(repo, runtime_dir, ["status", *text.split()])
    assert result.returncode == 0, result.stderr

    repo_name = Path(repo).name
    slug = _slug(repo)
    files = list(_project_dir(runtime_dir, slug).glob(f"{SID}.*.json"))
    assert len(files) == 1

    envelope = json.loads(files[0].read_text(encoding="utf-8"))
    assert envelope["subject"] == "orchard:agent:status"
    assert envelope["body"] == text
    assert envelope["from"] == f":session:{SID}"
    assert envelope["to"] == f":topic:repository/{repo_name}"
    assert envelope["identity"]["agent"] == DEFAULT_AGENT
    assert "status" not in envelope


def test_status_zero_words_is_rejected(repo, runtime_dir):
    result = _run(repo, runtime_dir, ["status"])
    assert result.returncode != 0
    assert result.stderr.strip().startswith("orchard-topic: rejected")

    repo_name = Path(repo).name
    assert not _project_dir(runtime_dir, _slug(repo)).exists()
    assert len(list(_telemetry_dir(runtime_dir, repo_name).glob(f"{SID}.*"))) == 1


def test_status_three_words_is_rejected(repo, runtime_dir):
    result = _run(repo, runtime_dir, ["status", "three", "word", "text"])
    assert result.returncode != 0
    assert result.stderr.strip().startswith("orchard-topic: rejected")

    repo_name = Path(repo).name
    assert not _project_dir(runtime_dir, _slug(repo)).exists()
    tfiles = list(_telemetry_dir(runtime_dir, repo_name).glob(f"{SID}.*"))
    assert len(tfiles) == 1
    envelope = json.loads(tfiles[0].read_text(encoding="utf-8"))
    assert envelope["body"]["attempted"] == ["post", "status", "three", "word", "text"]


def test_status_snapshot_promotes_tokens_in_out_and_effort(repo, runtime_dir, tmp_path):
    """docs/courier-wire.md §2b: tokens in/out are first-class snapshot
    fields, not only nested under `spend`, and effort rides through when
    CLAUDE_EFFORT is set — a fabricated transcript is the only way to make
    courier.status_of() resolve real usage counts (the default env under
    test has no transcript at all, per this module's own docstring)."""
    home = tmp_path / "fake-home"
    project_dir = home / ".claude" / "projects" / "fake-project"
    project_dir.mkdir(parents=True)
    (project_dir / f"{SID}.jsonl").write_text(
        json.dumps({"message": {"model": "claude-opus-5", "usage": {
            "input_tokens": 11, "output_tokens": 22,
            "cache_read_input_tokens": 33, "cache_creation_input_tokens": 0,
        }}}) + "\n",
        encoding="utf-8",
    )

    result = _run(repo, runtime_dir, ["status", "reading"], home=home, effort="high")
    assert result.returncode == 0, result.stderr

    slug = _slug(repo)
    files = list(_project_dir(runtime_dir, slug).glob(f"{SID}.*.json"))
    assert len(files) == 1
    envelope = json.loads(files[0].read_text(encoding="utf-8"))

    status = envelope["status"]
    assert status["tokens_in"] == 11
    assert status["tokens_out"] == 22
    assert status["spend"]["input_tokens"] == 11
    assert status["spend"]["output_tokens"] == 22
    assert status["model"] == "claude-opus-5"
    assert status["effort"] == "high"


def test_status_snapshot_has_no_effort_when_claude_effort_unset(repo, runtime_dir, tmp_path):
    """The companion negative case: no CLAUDE_EFFORT in the environment means
    no invented value — `effort` is simply absent, never guessed."""
    home = tmp_path / "fake-home"
    project_dir = home / ".claude" / "projects" / "fake-project"
    project_dir.mkdir(parents=True)
    (project_dir / f"{SID}.jsonl").write_text(
        json.dumps({"message": {"model": "claude-opus-5", "usage": {
            "input_tokens": 1, "output_tokens": 1,
        }}}) + "\n",
        encoding="utf-8",
    )

    result = _run(repo, runtime_dir, ["status", "reading"], home=home)
    assert result.returncode == 0, result.stderr

    slug = _slug(repo)
    files = list(_project_dir(runtime_dir, slug).glob(f"{SID}.*.json"))
    envelope = json.loads(files[0].read_text(encoding="utf-8"))
    assert "effort" not in envelope["status"]


def _effort_envelope(repo, runtime_dir, tmp_path, **effort_kwargs):
    home = tmp_path / "fake-home"
    project_dir = home / ".claude" / "projects" / "fake-project"
    project_dir.mkdir(parents=True)
    (project_dir / f"{SID}.jsonl").write_text(
        json.dumps({"message": {"model": "claude-opus-5", "usage": {
            "input_tokens": 1, "output_tokens": 1,
        }}}) + "\n",
        encoding="utf-8",
    )
    result = _run(repo, runtime_dir, ["status", "reading"], home=home, **effort_kwargs)
    assert result.returncode == 0, result.stderr
    slug = _slug(repo)
    files = list(_project_dir(runtime_dir, slug).glob(f"{SID}.*.json"))
    return json.loads(files[0].read_text(encoding="utf-8"))


def test_effort_reader_chain_claude_effort_wins_over_the_other_two(repo, runtime_dir, tmp_path):
    """docs/courier-wire.md §2b: the reader chain is CLAUDE_EFFORT (Claude
    Code's own documented hooks env var) -> CLAUDE_CODE_REASONING_EFFORT
    (its documented alias) -> ORCHID_EFFORT (ours, launch-time fallback).
    The first present wins, so CLAUDE_EFFORT beats the other two even when
    all three are set at once."""
    envelope = _effort_envelope(
        repo, runtime_dir, tmp_path,
        effort="high", reasoning_effort="low", orchid_effort="medium",
    )
    assert envelope["status"]["effort"] == "high"


def test_effort_reader_chain_reasoning_effort_wins_when_claude_effort_absent(repo, runtime_dir, tmp_path):
    """Second in the chain: with CLAUDE_EFFORT unset, the documented alias
    CLAUDE_CODE_REASONING_EFFORT is read next, ahead of ORCHID_EFFORT."""
    envelope = _effort_envelope(
        repo, runtime_dir, tmp_path,
        reasoning_effort="low", orchid_effort="medium",
    )
    assert envelope["status"]["effort"] == "low"


def test_effort_reader_chain_orchid_effort_is_the_last_resort(repo, runtime_dir, tmp_path):
    """Last in the chain: with neither documented var set, ORCHID_EFFORT —
    the variable WE set at launch sites — is read as the fallback."""
    envelope = _effort_envelope(repo, runtime_dir, tmp_path, orchid_effort="medium")
    assert envelope["status"]["effort"] == "medium"


def test_status_snapshot_promotes_dollars_from_estimates(repo, runtime_dir, tmp_path):
    """docs/courier-wire.md §2b: `dollars` is promoted out of
    `courier.status_of()`'s own `estimates.cost_usd` (built by
    `estimates_for()` from the existing per-model price table) — a
    recognised model (`claude-sonnet-5`, in `courier.MODEL_CARD`) yields a
    real figure, never a rate invented in this script."""
    home = tmp_path / "fake-home"
    project_dir = home / ".claude" / "projects" / "fake-project"
    project_dir.mkdir(parents=True)
    (project_dir / f"{SID}.jsonl").write_text(
        json.dumps({"message": {"model": "claude-sonnet-5", "usage": {
            "input_tokens": 1_000_000, "output_tokens": 0,
        }}}) + "\n",
        encoding="utf-8",
    )

    result = _run(repo, runtime_dir, ["status", "reading"], home=home)
    assert result.returncode == 0, result.stderr

    slug = _slug(repo)
    files = list(_project_dir(runtime_dir, slug).glob(f"{SID}.*.json"))
    envelope = json.loads(files[0].read_text(encoding="utf-8"))

    # 1,000,000 input tokens at claude-sonnet-5's $3/M input rate == $3.00.
    assert envelope["status"]["dollars"] == 3.0


def test_status_snapshot_has_no_dollars_for_an_unrecognised_model(repo, runtime_dir, tmp_path):
    """The companion negative case: `estimates_for()` returns `{}` for a
    model absent from `MODEL_CARD`, so no `cost_usd` exists to promote —
    `dollars` is simply absent, never guessed at a made-up rate."""
    home = tmp_path / "fake-home"
    project_dir = home / ".claude" / "projects" / "fake-project"
    project_dir.mkdir(parents=True)
    (project_dir / f"{SID}.jsonl").write_text(
        json.dumps({"message": {"model": "claude-opus-5", "usage": {
            "input_tokens": 1, "output_tokens": 1,
        }}}) + "\n",
        encoding="utf-8",
    )

    result = _run(repo, runtime_dir, ["status", "reading"], home=home)
    assert result.returncode == 0, result.stderr

    slug = _slug(repo)
    files = list(_project_dir(runtime_dir, slug).glob(f"{SID}.*.json"))
    envelope = json.loads(files[0].read_text(encoding="utf-8"))
    assert "dollars" not in envelope["status"]


# --- delegation ----------------------------------------------------------
#
# The subject is EXACT (`orchard:agent:delegation:schedule`/`begin`/`end`)
# and carries no variable data — the subagent id rides the body instead
# (operator ruling: the orchard subject list is closed, not extensible, and
# variable data never belongs in the subject). `schedule` was briefly
# retired then restored into the closed subject corpus (operator ruling,
# 2026-07-25): a session-id-less subagent queued/planned to be called.

@pytest.mark.parametrize("action", ["schedule", "begin", "end"])
def test_delegation_post_writes_expected_envelope(repo, runtime_dir, action):
    result = _run(repo, runtime_dir, ["delegation", action, "builder"])
    assert result.returncode == 0, result.stderr

    slug = _slug(repo)
    files = list(_project_dir(runtime_dir, slug).glob(f"{SID}.*.json"))
    assert len(files) == 1

    envelope = json.loads(files[0].read_text(encoding="utf-8"))
    assert envelope["subject"] == f"orchard:agent:delegation:{action}"
    assert envelope["body"] == {"subagent": "builder"}
    assert envelope["identity"]["agent"] == DEFAULT_AGENT
    assert "status" not in envelope


def test_delegation_bad_action_is_rejected(repo, runtime_dir):
    result = _run(repo, runtime_dir, ["delegation", "bogus", "builder"])
    assert result.returncode != 0
    assert result.stderr.strip().startswith("orchard-topic: rejected")

    repo_name = Path(repo).name
    assert not _project_dir(runtime_dir, _slug(repo)).exists()
    tfiles = list(_telemetry_dir(runtime_dir, repo_name).glob(f"{SID}.*"))
    assert len(tfiles) == 1
    envelope = json.loads(tfiles[0].read_text(encoding="utf-8"))
    assert envelope["body"]["attempted"] == ["post", "delegation", "bogus", "builder"]


# --- outcome ---------------------------------------------------------------

@pytest.mark.parametrize("value", ["success", "fail"])
def test_outcome_post_writes_expected_envelope(repo, runtime_dir, value):
    result = _run(repo, runtime_dir, ["outcome", value])
    assert result.returncode == 0, result.stderr

    slug = _slug(repo)
    files = list(_project_dir(runtime_dir, slug).glob(f"{SID}.*.json"))
    assert len(files) == 1

    envelope = json.loads(files[0].read_text(encoding="utf-8"))
    assert envelope["subject"] == f"orchard:agent:outcome:{value}"
    assert "body" not in envelope
    assert envelope["identity"]["agent"] == DEFAULT_AGENT
    assert "status" not in envelope


def test_outcome_bad_value_is_rejected(repo, runtime_dir):
    result = _run(repo, runtime_dir, ["outcome", "bogus"])
    assert result.returncode != 0
    assert result.stderr.strip().startswith("orchard-topic: rejected")

    repo_name = Path(repo).name
    assert not _project_dir(runtime_dir, _slug(repo)).exists()
    tfiles = list(_telemetry_dir(runtime_dir, repo_name).glob(f"{SID}.*"))
    assert len(tfiles) == 1
    envelope = json.loads(tfiles[0].read_text(encoding="utf-8"))
    assert envelope["body"]["attempted"] == ["post", "outcome", "bogus"]


# --- task (gardener-only) ---------------------------------------------

@pytest.mark.parametrize("value", ["completed", "failed"])
def test_task_post_by_gardener_writes_expected_envelope(repo, runtime_dir, value):
    result = _run(repo, runtime_dir, ["task", value], agent="gardener")
    assert result.returncode == 0, result.stderr

    slug = _slug(repo)
    files = list(_project_dir(runtime_dir, slug).glob(f"{SID}.*.json"))
    assert len(files) == 1

    envelope = json.loads(files[0].read_text(encoding="utf-8"))
    assert envelope["subject"] == f"orchard:task:outcome:{value}"
    assert "body" not in envelope
    assert envelope["identity"]["agent"] == "gardener"
    assert "status" not in envelope


def test_task_post_by_non_gardener_is_rejected(repo, runtime_dir):
    result = _run(repo, runtime_dir, ["task", "completed"], agent=DEFAULT_AGENT)
    assert result.returncode != 0
    assert result.stderr.strip().startswith("orchard-topic: rejected")
    assert "gardener" in result.stderr

    repo_name = Path(repo).name
    assert not _project_dir(runtime_dir, _slug(repo)).exists()
    tfiles = list(_telemetry_dir(runtime_dir, repo_name).glob(f"{SID}.*"))
    assert len(tfiles) == 1
    envelope = json.loads(tfiles[0].read_text(encoding="utf-8"))
    assert envelope["body"]["attempted"] == ["post", "task", "completed"]
    assert "gardener" in envelope["body"]["reason"]


def test_task_bad_value_is_rejected(repo, runtime_dir):
    result = _run(repo, runtime_dir, ["task", "bogus"], agent="gardener")
    assert result.returncode != 0
    assert result.stderr.strip().startswith("orchard-topic: rejected")

    repo_name = Path(repo).name
    assert not _project_dir(runtime_dir, _slug(repo)).exists()
    tfiles = list(_telemetry_dir(runtime_dir, repo_name).glob(f"{SID}.*"))
    assert len(tfiles) == 1
    envelope = json.loads(tfiles[0].read_text(encoding="utf-8"))
    assert envelope["body"]["attempted"] == ["post", "task", "bogus"]


# --- other rejections --------------------------------------------------

def test_unknown_family_is_rejected(repo, runtime_dir):
    result = _run(repo, runtime_dir, ["bogus", "thing"])
    assert result.returncode != 0
    assert result.stderr.strip().startswith("orchard-topic: rejected")

    repo_name = Path(repo).name
    assert not _project_dir(runtime_dir, _slug(repo)).exists()
    tfiles = list(_telemetry_dir(runtime_dir, repo_name).glob(f"{SID}.*"))
    assert len(tfiles) == 1
    envelope = json.loads(tfiles[0].read_text(encoding="utf-8"))
    assert envelope["subject"] == "orchard:agent:telemetry:rejected"
    assert envelope["body"]["attempted"] == ["post", "bogus", "thing"]
    assert "task" in envelope["body"]["reason"]


def test_bare_post_with_no_event_is_rejected(repo, runtime_dir):
    result = _run(repo, runtime_dir, [])
    assert result.returncode != 0
    assert result.stderr.strip().startswith("orchard-topic: rejected")

    repo_name = Path(repo).name
    assert not _project_dir(runtime_dir, _slug(repo)).exists()
    tfiles = list(_telemetry_dir(runtime_dir, repo_name).glob(f"{SID}.*"))
    assert len(tfiles) == 1
    envelope = json.loads(tfiles[0].read_text(encoding="utf-8"))
    assert envelope["body"]["attempted"] == ["post"]


# --- write mechanics -----------------------------------------------------

def test_no_leftover_partial_tempfile_after_post(repo, runtime_dir):
    """orchard_deliver()'s atomic write goes through a `.<name>.partial` temp
    file before the rename to the final `<sid>.<ts>.json` — that temp name
    must never survive a post. `.compacted` (maybe_compact's own sentinel)
    and `<sid>.marker` are expected dotted/plain siblings, not leftovers."""
    result = _run(repo, runtime_dir, ["lifecycle", "starting"])
    assert result.returncode == 0, result.stderr

    project_dir = _project_dir(runtime_dir, _slug(repo))
    names = [p.name for p in project_dir.iterdir()]
    assert any(n.endswith(".json") for n in names), "expected a written message file"
    assert not any(n.endswith(".partial") for n in names)


def test_marker_created_and_project_dir_mtime_bumped_on_post(repo, runtime_dir):
    first = _run(repo, runtime_dir, ["lifecycle", "starting"])
    assert first.returncode == 0, first.stderr

    project_dir = _project_dir(runtime_dir, _slug(repo))
    assert project_dir.is_dir()
    assert (project_dir / f"{SID}.marker").exists()

    # Force the project dir to a known-stale mtime, then post again — a real
    # bump (courier.orchard_deliver's os.utime(dir_path, None)) must move it
    # well past that.
    stale = time.time() - 10_000
    os.utime(project_dir, (stale, stale))

    second = _run(repo, runtime_dir, ["lifecycle", "started"])
    assert second.returncode == 0, second.stderr

    assert project_dir.stat().st_mtime > stale + 5000, "project dir mtime was not bumped"


def test_telemetry_rejection_filename_ends_in_json(repo, runtime_dir):
    """orchard_topic.py's reject() telemetry write goes through
    courier.write_orchard_file() via write_message()'s
    courier.orchard_message_name() — the same canonical namer every other
    orchard write uses. It used to build `f"{sid}.{ts}"` locally and
    silently drop the `.json` extension."""
    result = _run(repo, runtime_dir, ["lifecycle", "bogus"])
    assert result.returncode != 0

    repo_name = Path(repo).name
    tfiles = list(_telemetry_dir(runtime_dir, repo_name).glob(f"{SID}.*"))
    assert len(tfiles) == 1
    assert tfiles[0].name.endswith(".json")


# --- repo naming ---------------------------------------------------------

def test_each_worktree_gets_its_own_project_dir_under_a_shared_repo_name(
    tmp_path, runtime_dir,
):
    """A worktree posts into ITS OWN project directory, not the main repo's.

    `--git-common-dir` folds every worktree of a repo to one path, so a slug
    built from that alone was identical in all of them and every concurrent
    feature shared a directory — which meant every agent's monitor woke on
    every other agent's traffic. The branch half is what separates them. The
    repo half stays common, which is what lets the sidebar fold the worktrees
    back into one row for display.
    """
    main_repo = make_repo(str(tmp_path))

    subprocess.run(
        ["git", "commit", "--allow-empty", "--quiet", "-m", "init"],
        cwd=main_repo, check=True, capture_output=True, text=True,
    )
    worktree_path = tmp_path / "some-worktree-dirname"
    subprocess.run(
        ["git", "worktree", "add", "--quiet", "-b", "wt-branch", str(worktree_path)],
        cwd=main_repo, check=True, capture_output=True, text=True,
    )

    main_repo_slug = _slug(main_repo)
    worktree_slug = _slug(str(worktree_path))

    assert main_repo_slug != worktree_slug
    assert worktree_slug.endswith("@wt-branch")
    assert main_repo_slug.partition("@")[0] == worktree_slug.partition("@")[0]

    result = _run(str(worktree_path), runtime_dir, ["lifecycle", "starting"])
    assert result.returncode == 0, result.stderr

    assert _project_dir(runtime_dir, worktree_slug).exists()
    assert not _project_dir(runtime_dir, main_repo_slug).exists()
    assert not _project_dir(runtime_dir, worktree_path.name).exists()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))

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
the slug is asked of courier rather than re-derived here. The reject path is
unchanged: it still writes telemetry into the OLD
`topics/telemetry/<repo>/` directory via orchard_topic.py's own local
`write_message()`, which the script never migrated.
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


def _run(cwd, runtime_dir, args, sid=SID, agent=DEFAULT_AGENT, parent=None):
    """Shell out to the script with a deterministic identity environment.

    CLAUDE_CODE_AGENT is pinned (default "landscaper", overridable for the
    gardener-only `task` cases) and ORCHID_PARENT_SESSION is pinned to
    `parent` or deleted outright — never left to whatever the real
    environment happens to hold — so `courier.identity_of()` resolves the same
    way on every run.
    """
    env = dict(os.environ)
    env["XDG_RUNTIME_DIR"] = str(runtime_dir)
    env["CLAUDE_CODE_SESSION_ID"] = sid
    env["CLAUDE_CODE_AGENT"] = agent
    if parent is None:
        env.pop("ORCHID_PARENT_SESSION", None)
    else:
        env["ORCHID_PARENT_SESSION"] = parent
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


# --- repo naming ---------------------------------------------------------

def test_repo_name_from_worktree_resolves_to_main_repo_slug(tmp_path, runtime_dir):
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
    assert main_repo_slug == worktree_slug  # --git-common-dir folds both to one project

    result = _run(str(worktree_path), runtime_dir, ["lifecycle", "starting"])
    assert result.returncode == 0, result.stderr

    assert _project_dir(runtime_dir, main_repo_slug).exists()
    assert not _project_dir(runtime_dir, worktree_path.name).exists()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))

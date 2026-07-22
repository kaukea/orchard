"""Fixture helpers for the sidebar test suite.

Builds throwaway git repos with a bus laid out exactly as tools/bus.py and
tools/sidebar_model.py expect, so build_model()/iter_bus_roots() resolve
against them without touching any real repo's bus.

Not a test module itself (no test_/Test naming) — imported by the test_*.py
files in this directory.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sidebar_model  # noqa: E402


def make_repo(tmp_root: str) -> str:
    """git-init a fresh repo under tmp_root; return its path as a str."""
    repo_dir = tempfile.mkdtemp(dir=tmp_root)
    subprocess.run(
        ["git", "init", "--quiet"], cwd=repo_dir, check=True,
        capture_output=True, text=True,
    )
    return repo_dir


def bus_root_of(repo_path: str) -> Path:
    """The bus root sidebar_model itself resolves for repo_path — asking the
    module under test rather than re-deriving <repo>/.git/... by hand, so the
    fixture can't drift from whatever git-common-dir resolution actually
    does (symlinked temp dirs and all)."""
    roots = sidebar_model.iter_bus_roots([repo_path])
    assert roots, f"no bus root resolved for {repo_path}"
    return roots[0]


def identity_body(session_id, agent_type=None, worktree=None, feature_id=None,
                   name=None, parent_session=None) -> dict:
    """The identity_of() announce shape — all six keys must be present for
    sidebar_model to recognise it as an identity push."""
    return {
        "session_id": session_id,
        "agent_type": agent_type,
        "worktree": worktree,
        "feature_id": feature_id,
        "name": name,
        "parent_session": parent_session,
    }


def lifecycle_body(state, feature_id=None, blocked_on=None) -> dict:
    body = {"kind": "lifecycle", "state": state, "feature_id": feature_id}
    if blocked_on is not None:
        body["blocked_on"] = blocked_on
    return body


def envelope(msg_id, sender, to="*", body=None, notify_user=None, ts=None) -> dict:
    """One bus message envelope, matching tools/message.schema.json."""
    env = {
        "id": msg_id,
        "ts": ts or "2026-01-01T00:00:00.000000+00:00",
        "from": sender,
        "to": to,
    }
    if notify_user:
        env["notify_user"] = True
    if body is not None:
        env["body"] = body
    return env


def write_message(bus_root: Path, folder: str, env: dict, filename: str | None = None) -> None:
    """Physically place one message file under bus_root/folder.

    `folder` is the RECIPIENT inbox the file happens to sit in — independent
    of env["from"]. Attribution in sidebar_model is by envelope `from`, never
    by the folder a file was found in (fan_out delivers copies into every
    OTHER session's folder), so tests exercise that split deliberately.
    """
    d = Path(bus_root) / folder
    d.mkdir(parents=True, exist_ok=True)
    name = filename or f"{env['id']}.json"
    (d / name).write_text(json.dumps(env), encoding="utf-8")

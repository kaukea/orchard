"""Fixture helpers for the sidebar test suite.

Builds throwaway git repos with a legacy courier root laid out as tools/courier.py
expects, so directed send/receive tests resolve against them without touching any
real repo's courier.

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


def make_repo(tmp_root: str) -> str:
    """git-init a fresh repo under tmp_root; return its path as a str."""
    repo_dir = tempfile.mkdtemp(dir=tmp_root)
    subprocess.run(
        ["git", "init", "--quiet"], cwd=repo_dir, check=True,
        capture_output=True, text=True,
    )
    return repo_dir


def courier_root_of(repo_path: str) -> Path:
    """The legacy courier root for repo_path — <git-common-dir>/the-works/courier,
    resolved the same way tools/courier.py's courier_root() does, without the
    retired sidebar_model."""
    common = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "--git-common-dir"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return (Path(repo_path) / common).resolve() / "the-works" / "courier"


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


def envelope(msg_id, sender, to="*", body=None, notify_user=None, ts=None) -> dict:
    """One courier message envelope, matching tools/message.schema.json."""
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


def write_message(courier_root: Path, folder: str, env: dict, filename: str | None = None) -> None:
    """Physically place one message file under courier_root/folder.

    `folder` is the RECIPIENT inbox the file happens to sit in — independent
    of env["from"]. Attribution in sidebar_model is by envelope `from`, never
    by the folder a file was found in (fan_out delivers copies into every
    OTHER session's folder), so tests exercise that split deliberately.
    """
    d = Path(courier_root) / folder
    d.mkdir(parents=True, exist_ok=True)
    name = filename or f"{env['id']}.json"
    (d / name).write_text(json.dumps(env), encoding="utf-8")

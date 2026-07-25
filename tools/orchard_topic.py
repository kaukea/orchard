#!/usr/bin/env python3
"""Post a sanctioned agent event to this repository's project topic.

The project topic is the sidebar's activity feed. This script is the ONLY
sanctioned writer and it is a strict gate: it builds the message itself from
validated inputs, so an agent can supply only an allowed event — it can never
inject arbitrary content, and it can never fan a broadcast out to every peer
(the v1 traffic that costs). Reducing that traffic is the point.

Fixed message families (the Subject; subscribers filter on it):

    orchard:agent:lifecycle:<starting|started|stopping|stopped>
        starting = initializing/loading · started = ready ·
        stopping = cleaning up · stopped = done
    orchard:agent:status        (body = the activity, at most two words)

Addresses are discovered, never passed by the caller:

    From: :session:<session-id>          (CLAUDE_CODE_SESSION_ID)
    To:   :topic:repository/<repo>       (the repo, via --git-common-dir, so
                                          every worktree folds to one project)

Usage:

    orchard_topic.py post lifecycle started
    orchard_topic.py post status "reading files"

Validation is absolute. An off-list subject, a bad lifecycle state, or a status
over two words is refused: the attempt is captured as telemetry (what was tried,
to where, and why it failed — no log file, a telemetry topic) and a rejection is
bounced straight back to the calling session over the courier. Nothing is written.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent))  # for the sibling courier.py

TOPIC_FAMILY = "repository"
TELEMETRY_FAMILY = "telemetry"
LIFECYCLE_STATES = ("starting", "started", "stopping", "stopped")
STATUS_MAX_WORDS = 2


def _die(msg: str) -> NoReturn:
    sys.exit(f"orchard-topic: {msg}")


def topics_root() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        _die("XDG_RUNTIME_DIR is unset — no user-wide topic root")
    return Path(runtime) / "orchard" / "topics"


def repo_name() -> str:
    common = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True
    )
    path = common.stdout.strip()
    if common.returncode != 0 or not path:
        _die("not inside a repository — no project to post to")
    # --git-common-dir is the shared .git (identical for every worktree of a
    # repo); its parent is the repo root, so all worktrees fold to one project.
    return Path(path).resolve().parent.name


def session_id() -> str:
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    if not sid:
        _die("CLAUDE_CODE_SESSION_ID is unset — not inside an agent session")
    return sid


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S.%f")


def _bump_chain(leaf: Path, root: Path) -> None:
    """Advance mtime on the leaf and every ancestor up to (and including) root.

    A write already bumps the leaf; propagating it up the chain is the
    per-agent/per-project nested-mtime the sidebar aggregates on.
    """
    try:
        depth = len(leaf.relative_to(root).parts)
    except ValueError:
        os.utime(leaf, None)
        return
    node = leaf
    os.utime(node, None)
    for _ in range(depth):
        node = node.parent
        os.utime(node, None)


def write_message(topic_dir: Path, sid: str, envelope: dict) -> Path:
    """Write one event atomically: temp `.<sid>.<ts>` then rename to `<sid>.<ts>`.

    The leading dot marks the file in-progress (a monitor skips dotfiles); the
    rename drops it, publishing the event and advancing the directory mtime.
    """
    topic_dir.mkdir(parents=True, exist_ok=True)
    ts = _stamp()
    final = topic_dir / f"{sid}.{ts}"
    tmp = topic_dir / f".{sid}.{ts}"
    tmp.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    os.replace(tmp, final)
    _bump_chain(topic_dir, topics_root())
    return final


def build_envelope(sid: str, repo: str, subject: str, body: object = None) -> dict:
    envelope = {
        "from": f":session:{sid}",
        "to": f":topic:{TOPIC_FAMILY}/{repo}",
        "subject": subject,
    }
    if body is not None:
        envelope["body"] = body
    return envelope


def _identity() -> dict:
    """Immutable facts (the courier's identity operation) — never change for a session:
    agent role, feature, human name, parent. Session id already rides `from`."""
    try:
        import courier
        ident = courier.identity_of()
    except Exception:
        return {}
    keep = {
        "agent": ident.get("agent_type"),
        "feature": ident.get("feature_id"),
        "name": ident.get("name"),
        "parent": ident.get("parent_session"),
    }
    return {k: v for k, v in keep.items() if v}


def _status() -> dict:
    """Mutable metadata (the courier's status operation) — changes through the session:
    model, context occupancy, spend. Attached to every event so the latest is truth."""
    try:
        import courier
        st = courier.status_of()
    except Exception:
        return {}
    keep = {
        "model": st.get("model"),
        "context_tokens": st.get("context_tokens"),
        "spend": st.get("spend"),
    }
    return {k: v for k, v in keep.items() if v}


def _attach_snapshot(envelope: dict) -> dict:
    """Ride the two fixed operations the courier answers itself (never the agent):
    the immutable identity and the mutable status, so the consumer needs nothing else."""
    identity = _identity()
    if identity:
        envelope["identity"] = identity
    status = _status()
    if status:
        envelope["status"] = status
    return envelope


def _courier() -> Path:
    return Path(__file__).resolve().parent / "courier.py"


def reject(reason: str, attempted: list[str], sid: str, repo: str) -> NoReturn:
    """Absolute-validation failure: capture telemetry, bounce, then refuse."""
    # Telemetry — record what the agent wanted, to where, and why it failed, so
    # real gaps in the fixed list surface. Best-effort; never masks the reject.
    try:
        write_message(
            topics_root() / TELEMETRY_FAMILY / repo,
            sid,
            {
                "from": f":session:{sid}",
                "to": f":topic:{TELEMETRY_FAMILY}/{repo}",
                "subject": "orchard:agent:telemetry:rejected",
                "body": {"attempted": attempted, "reason": reason},
            },
        )
    except Exception:
        pass
    # Bounce the rejection straight back to the calling session over the courier.
    try:
        subprocess.run(
            [sys.executable, str(_courier()), "send", "--from", sid, "--to", sid,
             "--body", f"orchard-topic rejected: {reason}"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        pass
    _die(f"rejected — {reason}")


def do_post(rest: list[str]) -> None:
    sid = session_id()
    repo = repo_name()
    attempted = ["post", *rest]
    if not rest:
        reject("no event given; expected `lifecycle <state>` or `status <text>`",
               attempted, sid, repo)

    family, args = rest[0], rest[1:]
    if family == "lifecycle":
        if len(args) != 1 or args[0] not in LIFECYCLE_STATES:
            reject(f"lifecycle state must be one of {LIFECYCLE_STATES}",
                   attempted, sid, repo)
        envelope = build_envelope(sid, repo, f"orchard:agent:lifecycle:{args[0]}")
    elif family == "status":
        words = " ".join(args).split()
        if not 1 <= len(words) <= STATUS_MAX_WORDS:
            reject(f"status is one or two words; got {len(words)}",
                   attempted, sid, repo)
        envelope = build_envelope(sid, repo, "orchard:agent:status",
                                  " ".join(words))
    elif family == "delegation":
        # schedule = queued (so the UI can show it before it starts), begin =
        # active, end = done — three states, not two.
        if len(args) != 2 or args[0] not in ("schedule", "begin", "end"):
            reject("delegation is `schedule|begin|end <subagent>`",
                   attempted, sid, repo)
        envelope = build_envelope(
            sid, repo, f"orchard:agent:delegation:{args[0]}:{args[1]}")
    elif family == "outcome":
        if len(args) != 1 or args[0] not in ("success", "fail"):
            reject("outcome is `success` or `fail`", attempted, sid, repo)
        envelope = build_envelope(sid, repo, f"orchard:agent:outcome:{args[0]}")
    elif family == "task":
        # A task is fully complete only when the GARDENER says so — this
        # task-level outcome is gardener-only, enforced by the sender's role.
        if len(args) != 1 or args[0] not in ("completed", "failed"):
            reject("task is `completed` or `failed`", attempted, sid, repo)
        if _identity().get("agent") != "gardener":
            reject("orchard:task:outcome may only be sent by the gardener",
                   attempted, sid, repo)
        envelope = build_envelope(sid, repo, f"orchard:task:outcome:{args[0]}")
    else:
        reject(f"unknown event family {family!r}; allowed: "
               "lifecycle, status, delegation, outcome, task", attempted, sid, repo)

    _attach_snapshot(envelope)
    print(write_message(topics_root() / TOPIC_FAMILY / repo, sid, envelope))


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] != "post":
        sys.exit("usage: orchard_topic.py post "
                 "<lifecycle <state> | status <text>>")
    do_post(argv[1:])


if __name__ == "__main__":
    main()

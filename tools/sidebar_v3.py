#!/usr/bin/env python3
"""Sidebar v3 — the projects that are active right now, and who is doing what.

A project is present because its topic directory exists, and active because that
directory was touched inside the window. Under it, one line per session shows the
agent, its model, its lifecycle state and its two-word status — read straight from
the events orchard_topic writes (identity + status ride every event, latest wins).

This is the FUNCTIONAL view: the data made visible so it can be verified updating.
The 5-phase accordion, colours and collapse are a later, pretty phase.

    python3 tools/sidebar_v3.py            refresh until interrupted
    python3 tools/sidebar_v3.py --once     render one frame and exit
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

TOPIC_FAMILY = "repository"
ACTIVE_WINDOW_SECONDS = 60 * 60
REFRESH_SECONDS = 2
MODEL_TIERS = ("haiku", "sonnet", "opus", "fable")
_DELEGATION_STATE = {"schedule": "scheduled", "begin": "active", "end": "inactive"}

RESET = "\033[0m"
DIM = "\033[2m"


def topics_root() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        sys.exit("sidebar: XDG_RUNTIME_DIR is unset — no user-wide topic root")
    return Path(runtime) / "orchard" / "topics" / TOPIC_FAMILY


def _short_model(model: str | None) -> str:
    if not model:
        return "?"
    return next((tier for tier in MODEL_TIERS if tier in model), model)


def _latest(rec: dict, key: str, ts: float) -> bool:
    """True (and records ts) when this event is the newest of its kind for a session."""
    if ts < rec.get(key, -1.0):
        return False
    rec[key] = ts
    return True


def sessions(project_dir: Path) -> dict[str, dict]:
    """Fold a project's event files into one record per session — latest of each kind."""
    found: dict[str, dict] = {}
    for f in project_dir.iterdir():
        if f.name.startswith(".") or not f.is_file():
            continue
        try:
            env = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        sid = env.get("from", "").removeprefix(":session:")
        if not sid:
            continue
        ts = f.stat().st_mtime
        rec = found.setdefault(sid, {"sid": sid, "subs": {}})
        if _latest(rec, "_snap", ts):
            rec["identity"] = env.get("identity", rec.get("identity", {}))
            rec["status"] = env.get("status", rec.get("status", {}))
        subject = env.get("subject", "")
        if subject.startswith("orchard:agent:lifecycle:") and _latest(rec, "_life", ts):
            rec["state"] = subject.rsplit(":", 1)[-1]
        elif subject == "orchard:agent:status" and _latest(rec, "_stat", ts):
            rec["activity"] = env.get("body", "")
        elif subject.startswith("orchard:agent:outcome:") and _latest(rec, "_out", ts):
            rec["outcome"] = subject.rsplit(":", 1)[-1]
        elif subject.startswith("orchard:task:outcome:") and _latest(rec, "_task", ts):
            rec["task_outcome"] = subject.rsplit(":", 1)[-1]
        elif subject.startswith("orchard:agent:delegation:"):
            action, _, sub = subject[len("orchard:agent:delegation:"):].partition(":")
            state = _DELEGATION_STATE.get(action)
            if sub and state and _latest(rec, f"_sub_{sub}", ts):
                rec["subs"][sub] = state
    return found


def idle_text(seconds: float) -> str:
    minutes = int(seconds // 60)
    return "now" if minutes < 1 else f"{minutes}m"


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def _session_line(rec: dict) -> str:
    identity = rec.get("identity") or {}
    status = rec.get("status") or {}
    # lead with WHAT the work is (feature/task), then who, then what it's doing
    label = identity.get("name") or identity.get("feature")
    who = f"{identity.get('agent') or rec['sid'][:8]}·{_short_model(status.get('model'))}"
    bits = [_truncate(label, 42)] if label else []
    bits.append(who)
    if rec.get("state"):
        bits.append(rec["state"])
    if rec.get("activity"):
        bits.append(f'"{rec["activity"]}"')
    if rec.get("outcome"):
        bits.append("✓" if rec["outcome"] == "success" else "❌")
    return "  ".join(bits)


def _project_block(name: str, idle: float, sess: dict[str, dict]) -> list[str]:
    task = next((r["task_outcome"] for r in sess.values() if r.get("task_outcome")), None)
    header = f"{name}  {idle_text(idle)}"
    if task:
        header += "  " + ("✓" if task == "completed" else "❌")
    lines = [header]
    # gardener (the header agent) first, then the rest, stable by session id
    order = sorted(sess.values(),
                   key=lambda r: ((r.get("identity") or {}).get("agent") != "gardener",
                                  r["sid"]))
    for rec in order:
        lines.append("  " + _session_line(rec))
        for sub, state in sorted(rec.get("subs", {}).items()):
            lines.append(f"{DIM}    · {sub} ({state}){RESET}")
    return lines


def frame(root: Path, now: float, width: int) -> list[str]:
    if not root.is_dir():
        return [f"{DIM}⋮ no active project ⋮{RESET}"]
    out: list[str] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        idle = now - d.stat().st_mtime
        if idle < ACTIVE_WINDOW_SECONDS:
            out.extend(_project_block(d.name, idle, sessions(d)))
    return out or [f"{DIM}⋮ no active project ⋮{RESET}"]


def render(root: Path, now: float, width: int) -> None:
    print("\033[H\033[2J", end="")
    print("\n".join(frame(root, now, width)), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    root = topics_root()
    width = os.get_terminal_size().columns if sys.stdout.isatty() else 36

    if args.once:
        print("\n".join(frame(root, time.time(), width)))
        return 0

    while True:
        render(root, time.time(), width)
        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    sys.exit(main())

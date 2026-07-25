#!/usr/bin/env python3
"""Sidebar v3 — the projects that are active right now.

A project is present because its topic directory exists, and active because
that directory was touched inside the window. Nothing is inferred from
message traffic, so a project with a single lone session still shows.

    python3 tools/sidebar_v3.py            refresh until interrupted
    python3 tools/sidebar_v3.py --once     render one frame and exit
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

TOPIC_FAMILY = "repository"
ACTIVE_WINDOW_SECONDS = 60 * 60
REFRESH_SECONDS = 2

RESET = "\033[0m"
DIM = "\033[2m"


def topics_root() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        sys.exit("sidebar: XDG_RUNTIME_DIR is unset — no user-wide topic root")
    return Path(runtime) / "orchard" / "topics" / TOPIC_FAMILY


def projects(root: Path, now: float) -> list[tuple[str, float]]:
    if not root.is_dir():
        return []
    found = [(d.name, now - d.stat().st_mtime) for d in root.iterdir() if d.is_dir()]
    return sorted(
        (name, idle) for name, idle in found if idle < ACTIVE_WINDOW_SECONDS
    )


def idle_text(seconds: float) -> str:
    minutes = int(seconds // 60)
    return "now" if minutes < 1 else f"{minutes}m"


def frame(root: Path, now: float, width: int) -> list[str]:
    active = projects(root, now)
    if not active:
        return [f"{DIM}⋮ no active project ⋮{RESET}"]
    return [_row(name, idle, width) for name, idle in active]


def _row(name: str, idle: float, width: int) -> str:
    age = idle_text(idle)
    room = max(width - len(age) - 1, 1)
    label = name if len(name) <= room else name[: room - 1] + "…"
    return f"{label}{' ' * max(width - len(label) - len(age), 1)}{DIM}{age}{RESET}"


def render(root: Path, width: int) -> None:
    print("\033[H\033[2J", end="")
    print("\n".join(frame(root, time.time(), width)), flush=True)


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
        render(root, width)
        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    sys.exit(main())

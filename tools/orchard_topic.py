#!/usr/bin/env python3
"""Post activity to this repository's project topic.

A project shows in the sidebar because its topic directory exists and was
touched inside the active window (sidebar_v3). This script is the only
writer: it resolves the user-wide topic root, derives the project name from
the repository it runs in, and touches the topic directory. Callers pass
nothing — every piece of metadata is discovered.

    python3 tools/orchard_topic.py post
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

TOPIC_FAMILY = "repository"


def topics_root() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        sys.exit("orchard-topic: XDG_RUNTIME_DIR is unset — no user-wide topic root")
    return Path(runtime) / "orchard" / "topics" / TOPIC_FAMILY


def project_name() -> str:
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    name = top.stdout.strip()
    if top.returncode != 0 or not name:
        sys.exit("orchard-topic: not inside a repository — no project to post to")
    return Path(name).name


def post() -> None:
    topic = topics_root() / project_name()
    topic.mkdir(parents=True, exist_ok=True)
    os.utime(topic, None)
    print(topic)


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] != "post":
        sys.exit("usage: orchard_topic.py post")
    post()


if __name__ == "__main__":
    main()

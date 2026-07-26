#!/usr/bin/env bash
# Mount the orchard question-broker (sidebar-polish item 12) as a detached
# background process — one per tmux server, unlike sidebar-mount.sh's visible
# pinned pane, since there is nothing to look at until the broker pops a
# popup. Idempotent: does nothing if a broker is already running for this
# tmux server. Never errors a session launch — exits 0 even when tmux or
# pgrep are unavailable or the spawn fails.
set -euo pipefail

if ! command -v tmux >/dev/null 2>&1 || [ -z "${TMUX:-}" ]; then
  echo "orchard-question-broker-mount: not inside tmux, skipping" >&2
  exit 0
fi

# Resolve through the .claude/tools symlink to the real tools dir, so the
# co-located courier.py is found (same resolution as sidebar-mount.sh).
DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

if command -v pgrep >/dev/null 2>&1 \
   && pgrep -f "orchard-question-broker.py watch" >/dev/null 2>&1; then
  exit 0
fi

nohup python3 "$DIR/orchard-question-broker.py" watch >/dev/null 2>&1 &
disown 2>/dev/null || true

exit 0

#!/usr/bin/env bash
# Mount the orchid-sidebar renderer as a pinned left pane in a tmux window.
# Usage: sidebar-mount.sh [target-window]
#   target-window: tmux window id/name to mount into (default: current window)
# Idempotent: does nothing if the target window already has a sidebar pane
# (detected by its start command running sidebar.py — robust to the pane-title
# clobbering by status-glyph setters that made a title match unreliable).
# Never errors a session launch — exits 0 even when tmux is unavailable or the
# split fails.
set -euo pipefail

if ! command -v tmux >/dev/null 2>&1 || [ -z "${TMUX:-}" ]; then
  echo "sidebar-mount: not inside tmux, skipping sidebar mount" >&2
  exit 0
fi

# Resolve through the .claude/tools symlink to the real tools dir, so the
# co-located sidebar.py / sidebar_nav.py are found.
DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
window="${1:-$(tmux display-message -p '#{window_id}')}"

if tmux list-panes -t "$window" -F '#{pane_start_command}' 2>/dev/null | grep -q 'sidebar.py'; then
  exit 0
fi

if ! pane=$(tmux split-window -h -b -l '17%' -d -t "$window" -P -F '#{pane_id}' "python3 '$DIR/sidebar.py' || tmux display-message 'orchid-sidebar: failed to start'"); then
  echo "sidebar-mount: split failed, skipping sidebar mount" >&2
  exit 0
fi
tmux select-pane -t "$pane" -T 'orchid-sidebar' 2>/dev/null || true
tmux set-window-option -t "$pane" automatic-rename off 2>/dev/null || true  # pin the title: stop python3/bash clobbering it
tmux set-window-option -t "$pane" allow-rename off 2>/dev/null || true      # pin the title: stop python3/bash clobbering it

exit 0

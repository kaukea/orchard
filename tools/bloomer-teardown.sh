#!/usr/bin/env bash
# Bloomer pane teardown — run by the bloomer AGENT ITSELF as its last act.
# Returns focus to the pane that launched it (bloomer-launch.sh) and closes
# the bloomer's own pane. Pane-scoped counterpart to architect-teardown.sh's
# window-scoped close: same socket-aware tx wrapper, same .return-* contract,
# scaled down from a whole window to a single split pane (Decision-075).
#
# Usage: bloomer-teardown.sh <task-id>
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "usage: bloomer-teardown.sh <task-id>" >&2
  exit 1
fi

task_id="$1"

common_dir="$(git rev-parse --git-common-dir)"
common_dir="$(cd "$common_dir" && pwd)"
state_file="$common_dir/the-works/$task_id/.return-pane"

if [ ! -f "$state_file" ]; then
  echo "bloomer-teardown: no .return-pane for $task_id, nothing to do" >&2
  exit 0
fi

ret=$(sed -n 1p "$state_file")
sock=$(sed -n 2p "$state_file")
[ -n "$sock" ] || sock="${TMUX%%,*}"

if [ -z "$sock" ]; then
  echo "bloomer-teardown: no tmux socket available for $task_id" >&2
  exit 0
fi

tx(){ tmux -S "$sock" "$@" 2>/dev/null || true; }

# Resolve the bloomer's own pane: $TMUX_PANE when invoked from inside the
# bloomer pane itself (the normal case), else fall back to the stable
# bloom:<task-id> pane title set by bloomer-launch.sh.
bloom_pane="${TMUX_PANE:-}"
if [ -z "$bloom_pane" ]; then
  bloom_pane=$(tx list-panes -a -F '#{pane_id} #{pane_title}' | awk -v t="bloom:$task_id" '$2==t{print $1; exit}')
fi

if [ -z "$bloom_pane" ]; then
  echo "bloomer-teardown: could not resolve bloomer pane for $task_id, not closing anything" >&2
  exit 0
fi

# SAFETY: never kill the return pane.
if [ "$bloom_pane" = "$ret" ]; then
  echo "bloomer-teardown: bloomer pane equals return pane, refusing to close" >&2
  exit 0
fi

# Focus return — line 1 is a pane id %N (Decision-006).
ret_win=$(tx display-message -p -t "$ret" '#{window_id}')
tx switch-client -t "$ret"
[ -n "$ret_win" ] && tx select-window -t "$ret_win"
tx select-pane -t "$ret"

tx kill-pane -t "$bloom_pane"
rm -f "$state_file"

echo "bloomer-teardown: returned to $ret, closed $bloom_pane"

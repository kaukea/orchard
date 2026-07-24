#!/usr/bin/env bash
# Launch the bloomer as a tmux PANE split out of the orchestrator's current
# window (Decision-075's pane variant of the architect's window pattern): the
# bloomer pane gets the bottom 75% of the window's height, the calling
# (orchestrator) pane keeps the top 25% — both stay visible at once, and the
# operator converses with the bloomer directly in its pane.
#
# Companion to bloomer-teardown.sh, which the bloomer runs as its last act to
# close its own pane and hand focus back to the pane recorded here.
#
# Usage: bloomer-launch.sh <task-id>   (run FROM the orchestrator's pane)
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "usage: bloomer-launch.sh <task-id>" >&2
  exit 1
fi

task_id="$1"

if [ -z "${TMUX:-}" ]; then
  echo "bloomer-launch: not inside tmux, refusing to launch bloomer pane" >&2
  exit 1
fi

if [ -z "${TMUX_PANE:-}" ]; then
  echo "bloomer-launch: TMUX_PANE unset, cannot record a return pane" >&2
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel)"
sock="${TMUX%%,*}"

tx(){ tmux -S "$sock" "$@"; }

# State file lives under the git-common-dir so it is shared across worktrees,
# mirroring the architect's .return-window contract (Decision-006: line 1 is
# a pane id %N, line 2 is the tmux socket path).
common_dir="$(git rev-parse --git-common-dir)"
common_dir="$(cd "$common_dir" && pwd)"
state_dir="$common_dir/the-works/$task_id"
state_file="$state_dir/.return-pane"

mkdir -p "$state_dir"
{
  printf '%s\n' "$TMUX_PANE"
  printf '%s\n' "$sock"
} > "$state_file"

cmd="ORCHID_PARENT_SESSION='${CLAUDE_CODE_SESSION_ID:-}' claude --agent bloomer 'Boot: bloom task ${task_id}.'"

new_pane=$(tx split-window -v -l '75%' -c "$repo_root" -P -F '#{pane_id}' "$cmd")
tx select-pane -t "$new_pane" -T "bloom:$task_id"
tx set-window-option -t "$new_pane" automatic-rename off  # pin the title: stop claude/bash clobbering it
tx set-window-option -t "$new_pane" allow-rename off       # pin the title: stop claude/bash clobbering it
# Leave focus on the bloomer pane — split-window already activates the new
# pane, this makes the intent explicit and survives future flag changes.
tx select-pane -t "$new_pane"

echo "$new_pane"

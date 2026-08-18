#!/usr/bin/env bash
# Uniform subagent launch (operator ruling, 2026-08-10): EVERY agent, whatever
# it will become, starts the same way -- a hidden pane, a REAL claude process
# from the moment of launch (never a Task-tool subagent: that has no pty of
# its own and cannot promote or close itself -- see docs/tmux-topology.md).
# The dispatcher never decides whether the child gets a window or stays a
# pane; the child decides that for itself on boot (tools/pane-promote.sh).
#
# Usage: dispatch-agent.sh <agent-type> <name> <cwd> <prompt...>
# Prints the new pane id on stdout.
set -euo pipefail
[ "$#" -ge 4 ] || { echo "usage: dispatch-agent.sh <agent-type> <name> <cwd> <prompt...>" >&2; exit 2; }
agent="$1"; name="$2"; cwd="$3"; shift 3
if [ -n "${TMUX_PANE:-}" ]; then
  win=$(tmux display-message -p -t "$TMUX_PANE" '#{window_id}')
else
  win=$(tmux display-message -p '#{window_id}')
fi
cmd=$(printf 'env ORCHID_PARENT_SESSION=%q claude --agent %q --name %q %q' \
  "${CLAUDE_CODE_SESSION_ID:-}" "$agent" "$name" "$*")
pane=$(tmux split-window -d -c "$cwd" -t "$win" -P -F '#{pane_id}' "$cmd")
echo "$pane"

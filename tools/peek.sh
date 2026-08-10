#!/usr/bin/env bash
# RETIRED (operator ruling, 2026-08-10) -- never worked properly. Nothing in the
# fleet calls this today; kept in the tree only in case it's worth resurrecting
# once the messaging rewrite lands and agents have a solid footing under them.
# Do not wire this back in without a fresh decision.
#
# Peek into a hidden subagent (Decision-036): subagents are never named sessions,
# but hidden does not mean unpeekable — this opens a DISPOSABLE pane tailing a
# live transcript, in the current window's RIGHT COLUMN (first peek splits right,
# later peeks stack vertically in that column), capped at 4. Close it when done.
#
# Title (operator, 2026-08-10): TWO WORDS MAX, always -- a cute name for this
# specific task if the caller bothered to give one, else the bare agent name
# (e.g. "Explorer"). The "peek:" prefix stays underneath for this script's own
# bookkeeping (cap counting, column-anchor lookup below) -- it is mechanical,
# not part of the two-word budget, and is not load-bearing outside this script
# (docs/tmux-topology.md §4: cross-agent matches key off window user-options,
# never pane_title).
#
# Usage: peek.sh <transcript.jsonl> [tmux-window-target] [display-name]
set -eu
file=$1
[ -f "$file" ] || { echo "peek: no such file: $file" >&2; exit 1; }
win=${2:-$(tmux display-message -p '#{window_id}')}
name=${3:-$(basename "$file" .jsonl)}
name=$(echo "$name" | awk '{print $1, $2}' | sed 's/ *$//')  # enforce two words max
jqprog='fromjson? | .message.content? // empty | if type=="array" then .[] | (.text // empty) else . end'
cmd="tail -n 100 -f '$file' | jq -rR --unbuffered '$jqprog'"
peeks=$(tmux list-panes -t "$win" -F '#{pane_title}' | grep -c '^peek:' || true)
if [ "$peeks" -ge 4 ]; then
  echo "peek: cap reached (4) in $win — close one first" >&2; exit 1
fi
if [ "$peeks" -eq 0 ]; then
  pane=$(tmux split-window -h -l '33%' -t "$win" -P -F '#{pane_id}' "$cmd")
else
  col=$(tmux list-panes -t "$win" -F '#{pane_id} #{pane_title}' | awk '$2 ~ /^peek:/ {print $1; exit}')
  pane=$(tmux split-window -v -t "$col" -P -F '#{pane_id}' "$cmd")
fi
tmux select-pane -t "$pane" -T "peek:$name"
echo "$pane"

#!/usr/bin/env bash
# Peek into a hidden subagent (Decision-036): subagents are never named sessions,
# but hidden does not mean unpeekable — this opens a DISPOSABLE pane tailing a
# live transcript, in the current window's RIGHT COLUMN (first peek splits right,
# later peeks stack vertically in that column), capped at 4. Close it when done.
#
# Usage: peek.sh <transcript.jsonl> [tmux-window-target]
set -eu
file=$1
[ -f "$file" ] || { echo "peek: no such file: $file" >&2; exit 1; }
win=${2:-$(tmux display-message -p '#{window_id}')}
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
tmux select-pane -t "$pane" -T "peek:$(basename "$file" .jsonl)"
tmux set-window-option -t "$pane" automatic-rename off  # pin the title: stop tail/jq clobbering it
tmux set-window-option -t "$pane" allow-rename off       # pin the title: stop tail/jq clobbering it
echo "$pane"

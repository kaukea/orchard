#!/usr/bin/env bash
# An agent calls this on ITS OWN boot, by ITS OWN decision, to promote its
# current (hidden) pane into its own dedicated window -- never done by a
# parent (operator ruling, 2026-08-10: "the decision is completely up to the
# agent", decoupling launch from rendering). tmux break-pane relocates the
# EXISTING pane -- same process, same pty -- into a new window; nothing is
# restarted. An agent that decides to stay a pane never calls this at all.
#
# Usage: pane-promote.sh <window-name>
# Prints the new window id on stdout. The caller is responsible for
# recording it (e.g. as its own @landscaper_id-style handle) and for
# tearing this same window down itself, as its own last act, when it closes.
set -euo pipefail
[ "$#" -eq 1 ] || { echo "usage: pane-promote.sh <window-name>" >&2; exit 2; }
name="$1"
pane=$(tmux display-message -p '#{pane_id}')
win=$(tmux break-pane -s "$pane" -P -F '#{window_id}' -n "$name")
tmux set-option -w -t "$win" automatic-rename off
echo "$win"

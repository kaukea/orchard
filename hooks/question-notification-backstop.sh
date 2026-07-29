#!/usr/bin/env bash
# Notification hook — backstop for sidebar-polish item 12b: when the harness
# raises its OWN native notification/question (bypassing the courier ask/popup
# path in tools/orchard-question-broker.py), post the same status the ordinary
# done-gate wait uses (docs/courier-wire.md §2's four-channel ruling: waiting
# on an outstanding answer, the operator's included, is the status word
# `questioning`) — mechanical, independent of whether the model remembers to
# do it itself. This hook renders nothing on its own; the sidebar's answer-
# wait glyph is what shows it.
#
# Direct call, not through the courier subagent: this hook runs outside any
# model turn, so there is no parent session to ask — the same exception
# `courier-end.sh`'s self-wake send already takes.
set -eu

root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
for candidate in "$root/.claude/tools/orchard_topic.py" "$root/tools/orchard_topic.py"; do
  [ -f "$candidate" ] && topic="$candidate" && break
done
[ -n "${topic:-}" ] || exit 0

python3 "$topic" post status questioning >/dev/null 2>&1 || true
exit 0

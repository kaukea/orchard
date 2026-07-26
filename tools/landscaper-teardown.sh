#!/usr/bin/env bash
# window-kill + focus-return primitive; resolves by @landscaper_id/@gardener_id
# window user-options; callable by the groundskeeper (pass socket as $2) or
# self-called from within the landscaper's tmux; no .return-window.
#
# Pane titles are clobbered live by claude (Decision-048), so every load-bearing
# handle keys off a window user-option. The primitive returns the operator's tmux
# client to the gardener window (spec §3), then kills the landscaper's window —
# which also removes its sidebar pane. It refuses to kill an unresolved handle or
# the focus-return target itself (spec §7).
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "usage: landscaper-teardown.sh <landscaper-id> [socket]" >&2
  exit 2
fi

id="$1"
# Socket: explicit $2 wins; else the current tmux socket (self-call from inside the
# landscaper). ${TMUX} is <socket>,<pid>,<session> — take the socket field.
sock="${2:-${TMUX:-}}"
sock="${sock%%,*}"

die(){ echo "landscaper-teardown: $*" >&2; exit 1; }
[ -n "$sock" ] || die "no tmux socket available (pass as \$2 or run inside tmux)"

tx(){ tmux -S "$sock" "$@"; }

# LANDSCAPER window — matched on the stable @landscaper_id window user-option.
# Fields are '|'-delimited so a session name containing spaces (the current
# 'orchids ▸ <name>' form, pre-tmux-naming) cannot shift field positions.
land_win=$(tx list-windows -a -F '#{window_id}|#{@landscaper_id}' \
  | awk -F'|' -v id="$id" '$2==id{print $1; exit}')

# GARDENER window — the one carrying a non-empty @gardener_id. One gardener per
# session (Decision-032), so the first non-empty match is correct. @gardener_id is
# placed FIRST so an unset value is an empty leading field (skipped), never a
# shifted one; window id and session name follow, '|'-delimited for space-safety.
gard=$(tx list-windows -a -F '#{@gardener_id}|#{window_id}|#{session_name}' \
  | awk -F'|' '$1!=""{print $2"|"$3; exit}')
gard_win=${gard%%|*}
gard_sess=${gard#*|}

# Refuse: never act on an unresolved handle, and never kill the focus-return target.
[ -n "$land_win" ] || die "no landscaper window found for @landscaper_id=$id"
[ -n "$gard_win" ] || die "no gardener window found (@gardener_id unset)"
[ "$land_win" != "$gard_win" ] || \
  die "landscaper window $land_win is the gardener window; refusing to kill the focus-return target"

# Return focus to the gardener window, then release the landscaper window.
tx switch-client -t "$gard_sess"
tx select-window -t "$gard_win"
tx kill-window -t "$land_win"

echo "landscaper-teardown: returned focus to gardener $gard_sess:$gard_win, closed landscaper window $land_win"

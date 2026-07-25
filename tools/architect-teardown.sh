#!/usr/bin/env bash
# Message-bus choreography teardown action.
# Run by the ARCHITECT ITSELF as its very last act (self-teardown, Decision-041):
# returns the operator's tmux client to the orchestrator pane, then closes the
# architect's OWN window — the caller's session ends with it. Nobody runs this
# against another agent: supervision kills are removed (operator ruling, 2026-07-25).
# Replaces the retired Stop hook — no transcript reading, no stdin, no scratch-file logging.
# Best-effort: every tmux call is guarded, always exit 0.
set -u

if [ -z "${1:-}" ]; then
  echo "usage: architect-teardown.sh <feature-id>" >&2
  exit 0
fi

id="$1"
wt=".claude/worktrees/$id"
rw="$wt/.return-window"

if [ ! -f "$rw" ]; then
  echo "architect-teardown: no .return-window for $id"
  exit 0
fi

ret=$(sed -n 1p "$rw")
sock=$(sed -n 2p "$rw")
[ -n "$sock" ] || sock="${TMUX%%,*}"
if [ -z "$sock" ]; then
  echo "architect-teardown: no tmux socket available for $id"
  exit 0
fi

tx(){ tmux -S "$sock" "$@" 2>/dev/null || true; }

# architect window is found by the stable @arch_id window user-option — pane
# titles get clobbered live by claude, so they cannot be used as a handle.
arch_win=$(tx list-windows -a -F '#{window_id} #{@arch_id}' | awk -v id="$id" '$2==id{print $1; exit}')

# focus return — line 1 is a pane id %N (Decision-006) or legacy window id @N
case "$ret" in
  %*) ret_win=$(tx display-message -p -t "$ret" '#{window_id}'); tx switch-client -t "$ret"; [ -n "$ret_win" ] && tx select-window -t "$ret_win"; tx select-pane -t "$ret" ;;
  *)  ret_win="$ret"; tx switch-client -t "$ret" || tx select-window -t "$ret" ;;
esac

# SAFETY: never kill the return target. The architect's window mounts both the
# architect pane and its sidebar pane, so a window-level kill closes the whole
# handle in one shot. Refuse only when no window resolved, or when that window
# is (or contains) the return target — comparing against both the resolved
# return window and the raw return-target string (legacy @window match).
if [ -z "$arch_win" ]; then
  echo "architect-teardown: no architect window found for $id, not closing"
  exit 0
fi
if [ "$arch_win" = "$ret_win" ]; then
  echo "architect-teardown: architect window is the return target's window, not closing"
  exit 0
fi
if [ "$arch_win" = "$ret" ]; then
  echo "architect-teardown: architect window equals return target, not closing"
  exit 0
fi

tx kill-window -t "$arch_win"
echo "architect-teardown: returned to $ret, closed $arch_win"
exit 0

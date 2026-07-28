#!/usr/bin/env bash
# A live acceptance surface for a sidebar branch under development.
#
# Shows the renderer belonging to THIS branch and reloads it when a fix LANDS —
# that is, when the branch's HEAD moves. It deliberately does not watch the
# working tree: a half-saved file would otherwise reach the screen, and a running
# renderer goes blank when its own source changes underneath it, which reads as a
# rendering fault rather than as somebody mid-edit.
#
# Each reload runs a clean export of the exact commit, so the pane title names
# the code being judged and a verdict given here is a verdict on that commit.
#
# The renderer is not modified and knows nothing about this script.
#
# --- Scenario mode (SIDEBAR_LIVE_SCENARIO) ----------------------------------
# Unset (the default): everything above applies unchanged, byte-identical to
# before this knob existed — this is still the operator's real fleet, over
# his real $XDG_RUNTIME_DIR, and nothing here is any different.
#
# Set to a `tools/sidebar_sim.py --scenario` name (e.g. "major-scenarios"):
# the SAME commit-following/export loop still runs (so a fix to the renderer,
# or to the simulator itself, still lands on screen the moment it's
# committed), but each (re)start also regenerates that scenario into an
# ISOLATED runtime tree under this worktree — never the live one — using the
# just-exported commit's OWN copy of `tools/sidebar_sim.py`, and points the
# renderer at it via `XDG_RUNTIME_DIR` for that one child process only. `HOME`
# is overridden the same way, for one reason only: `sidebar_model.py`'s sole
# use of `Path.home()` is the project registry
# (`~/.config/orchids/sidebar-registry.json`), which would otherwise filter
# the simulator's made-up project names down to whatever the operator's real
# registry happens to list. Neither override touches the calling shell or
# any other process. The pane title is prefixed `SCENARIO <name>` instead of
# `LIVE` so a verdict on simulated data is never mistaken for a verdict on
# the real fleet (Decision-112).
#
# --- Variant mode (SIDEBAR_LIVE_VARIANT) ------------------------------------
# Purely a label this script shows in the pane title, so two panes started
# with different values are visibly distinguishable side by side for an A/B.
# It carries no meaning of its own and this script does not interpret it —
# any renderer-side env var a given feature actually reads (e.g. a header
# sower's own gradient-width knob) already reaches the child process by
# ordinary shell inheritance the moment the operator exports it before
# invoking this script; nothing here needs to know that variable's name.

set -u

source_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
branch="$(git -C "$source_repo" rev-parse --abbrev-ref HEAD 2>/dev/null || echo detached)"
surface="$source_repo/.claude/worktrees/.sidebar-live-surface"
log="$(git -C "$source_repo" rev-parse --git-common-dir)/the-works/sidebar-live.log"
mkdir -p "$(dirname "$log")"

scenario="${SIDEBAR_LIVE_SCENARIO:-}"
variant="${SIDEBAR_LIVE_VARIANT:-}"
scenario_runtime="$source_repo/.claude/worktrees/.sidebar-live-scenario-runtime"
scenario_home="$source_repo/.claude/worktrees/.sidebar-live-scenario-home"
# Fixed, not wall-clock: two panes started minutes apart on the same
# scenario must render identically for an A/B to mean anything.
scenario_base_ts="2026-07-27T09:00:00+00:00"

renderer_pid=""
shown_sha=""    # the commit actually exported and running, and named in the title
checked_sha=""  # the newest HEAD already judged for whether it changes the display

# Paths the displayed pane actually depends on: the renderer and its model, and
# the sidecars it reads feature names from. A commit touching only, say, the
# workstream notes must not interrupt a pane somebody is watching.
affects_display() {
  [ -n "$1" ] || return 0
  git -C "$source_repo" diff --name-only "$1" "$2" -- tools/ docs/TODO.md.d/ 2>/dev/null | grep -q .
}

head_sha() { git -C "$source_repo" rev-parse HEAD 2>/dev/null; }
short() { git -C "$source_repo" rev-parse --short "$1" 2>/dev/null; }
subject() { git -C "$source_repo" log -1 --format=%s "$1" 2>/dev/null; }

set_title() { printf '\033]2;%s\033\\' "$1"; }

# "LIVE branch @ sha" when scenario is unset — byte-identical to before this
# knob existed. "SCENARIO name branch @ sha" otherwise, so a verdict on
# simulated data can never be mistaken for one on the real fleet
# (Decision-112). A variant, when set, is appended to either form.
pane_title() {
  local sha="$1" title
  if [ -n "$scenario" ]; then
    title="SCENARIO $scenario $branch @ $(short "$sha")"
  else
    title="LIVE $branch @ $(short "$sha")"
  fi
  [ -n "$variant" ] && title="$title variant=$variant"
  printf '%s' "$title"
}

# "CRASHED branch @ sha" when scenario is unset — byte-identical to before
# this knob existed. "CRASHED SCENARIO name branch @ sha" otherwise.
crash_title() {
  local sha="$1"
  if [ -n "$scenario" ] || [ -n "$variant" ]; then
    printf 'CRASHED %s' "$(pane_title "$sha")"
  else
    printf 'CRASHED %s @ %s' "$branch" "$(short "$sha")"
  fi
}

# Lay down a clean tree at the requested commit. Exporting rather than checking
# out keeps this independent of the working tree the sowers are editing.
export_commit() {
  local sha="$1" staging="$surface.incoming"
  rm -rf "$staging" && mkdir -p "$staging" || return 1
  git -C "$source_repo" archive "$sha" | tar -x -C "$staging" || return 1
  rm -rf "$surface" && mv "$staging" "$surface"
}

# Regenerates the isolated scenario tree from the just-exported commit's own
# `tools/sidebar_sim.py` — so a commit that changes the simulator shows up
# the moment it lands, same as any renderer fix. Never touches
# $XDG_RUNTIME_DIR: the target is always under this worktree.
write_scenario_data() {
  rm -rf "$scenario_runtime" "$scenario_home"
  mkdir -p "$scenario_runtime/orchard/projects" "$scenario_home/.config/orchids" || return 1
  python3 "$surface/tools/sidebar_sim.py" "$scenario_runtime/orchard/projects" \
    --once --scenario "$scenario" --base-ts "$scenario_base_ts" >>"$log" 2>&1
}

start_renderer() {
  local sha="$1"
  clear
  set_title "$(pane_title "$sha")"
  : > "$log"
  if [ -n "$scenario" ]; then
    write_scenario_data
    XDG_RUNTIME_DIR="$scenario_runtime" HOME="$scenario_home" \
      python3 "$surface/tools/sidebar.py" 2>>"$log" &
  else
    python3 "$surface/tools/sidebar.py" 2>>"$log" &
  fi
  renderer_pid=$!
  shown_sha="$sha"
}

stop_renderer() {
  [ -n "$renderer_pid" ] || return 0
  kill "$renderer_pid" 2>/dev/null
  wait "$renderer_pid" 2>/dev/null
  renderer_pid=""
}

# A crash stays readable on screen instead of scrolling past in a retry loop, and
# clears itself the moment the next commit lands.
show_crash() {
  stop_renderer
  clear
  set_title "$(crash_title "$shown_sha")"
  printf 'The sidebar renderer stopped.\n\n'
  printf 'Commit on this pane: %s  %s\n' "$(short "$shown_sha")" "$(subject "$shown_sha")"
  printf 'It restarts by itself when the next commit lands.\n\n'
  tail -n 30 "$log" 2>/dev/null
}

trap 'stop_renderer; exit 0' INT TERM HUP

target="$(head_sha)"
if export_commit "$target"; then
  start_renderer "$target"
else
  clear
  printf 'Could not export %s for display.\n' "$(short "$target")"
fi

while :; do
  sleep 2
  target="$(head_sha)"

  if [ -n "$target" ] && [ "$target" != "$checked_sha" ] && [ "$target" != "$shown_sha" ]; then
    checked_sha="$target"
    if affects_display "$shown_sha" "$target"; then
      if export_commit "$target"; then
        stop_renderer
        start_renderer "$target"
      fi
    fi
    continue
  fi

  if [ -n "$renderer_pid" ] && ! kill -0 "$renderer_pid" 2>/dev/null; then
    show_crash
    while [ "$(head_sha)" = "$shown_sha" ]; do sleep 2; done
  fi
done

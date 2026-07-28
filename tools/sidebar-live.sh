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

set -u

source_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
branch="$(git -C "$source_repo" rev-parse --abbrev-ref HEAD 2>/dev/null || echo detached)"
surface="$source_repo/.claude/worktrees/.sidebar-live-surface"
log="$(git -C "$source_repo" rev-parse --git-common-dir)/the-works/sidebar-live.log"
mkdir -p "$(dirname "$log")"

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

# Lay down a clean tree at the requested commit. Exporting rather than checking
# out keeps this independent of the working tree the sowers are editing.
export_commit() {
  local sha="$1" staging="$surface.incoming"
  rm -rf "$staging" && mkdir -p "$staging" || return 1
  git -C "$source_repo" archive "$sha" | tar -x -C "$staging" || return 1
  rm -rf "$surface" && mv "$staging" "$surface"
}

start_renderer() {
  local sha="$1"
  clear
  set_title "LIVE $branch @ $(short "$sha")"
  : > "$log"
  python3 "$surface/tools/sidebar.py" 2>>"$log" &
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
  set_title "CRASHED $branch @ $(short "$shown_sha")"
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

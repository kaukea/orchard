#!/usr/bin/env python3
"""tmux navigation resolver for the fleet sidebar.

Resolves a tmux WINDOW by its `#{window_name}` and switches the operator's
client to it (session + window). Window name is the reliable handle —
pane titles get clobbered by a status-glyph setter, so matching is done on
window name, not pane title. Mirrors the resolve-by-title approach used by
tools/landscaper-teardown.sh, but runs on the AMBIENT tmux socket (the
sidebar lives inside the same tmux server it navigates), so plain `tmux`
is used rather than a `-S <socket>` target.

NAMING (operator ruling, 2026-08-10, docs/tmux-topology.md §1/§4):
session = the bare repository name, window = the bare feature name, and
the gardener's window is ALWAYS named literally "Gardener" — a fixed,
known value, never guessed. This replaces the earlier design, which had
no controlled name for the gardener window (whatever the terminal
happened to call it) and had to heuristically pick "whichever window in
the session carries no repo/feature separator" — a guess that never
reliably worked. There is now nothing to guess: a target is either a bare
repo name (-> that session's window named "Gardener") or
"repo<TARGET_SEPARATOR>feature" (-> that session's window named exactly
`feature`, no separator variants, no normalisation).

STDLIB ONLY.
"""
from __future__ import annotations

import subprocess
import sys

from sidebar_glyphs import TARGET_SEPARATOR

LIST_WINDOWS_FORMAT = "#{session_name}\t#{window_id}\t#{window_name}\t#{pane_current_command}"
LIST_PANES_FORMAT = "#{pane_id} #{pane_title}"

_SHELL_COMMANDS = {"bash", "sh", "zsh", "fish", "dash", "-bash", "-sh", "-zsh", "login", "tmux"}

GARDENER_WINDOW_NAME = "Gardener"


def _tmux(*args: str) -> str | None:
    """Run a tmux command, returning stripped stdout or None on any failure."""
    try:
        result = subprocess.run(
            ["tmux", *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _list_windows() -> list[tuple[str, str, str, str]]:
    """Return (session_name, window_id, window_name, active_cmd) for every window."""
    out = _tmux("list-windows", "-a", "-F", LIST_WINDOWS_FORMAT)
    if not out:
        return []
    windows = []
    for line in out.splitlines():
        # window names contain no tabs, so a maxsplit-3 split keeps them exact.
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        session_name, window_id, window_name, active_cmd = parts
        windows.append((session_name, window_id, window_name, active_cmd))
    return windows


def _prefer_live(matches: list[tuple[str, str, str, str]]) -> tuple[str, str]:
    """Among same-named window matches, prefer one whose active pane command
    is not a bare login shell (the live window rather than a blank launcher
    leftover). Falls back to the first match if all are shells."""
    for session_name, window_id, _window_name, active_cmd in matches:
        if active_cmd not in _SHELL_COMMANDS:
            return (session_name, window_id)
    session_name, window_id, _window_name, _active_cmd = matches[0]
    return (session_name, window_id)


def resolve_window(name: str) -> tuple[str, str] | None:
    """Return (session_name, window_id) for `name`.

    A repo-level target (bare name, no TARGET_SEPARATOR) resolves to that
    session's window named exactly "Gardener". A feature-level target
    ("repo<SEP>feature") resolves to that session's window named exactly
    `feature` — an EXACT match; window names carry no repo prefix and no
    separator, so there is nothing left to normalise. Returns None if no
    session or no matching window exists. When more than one window shares
    the name, prefers the live one (see _prefer_live)."""
    if TARGET_SEPARATOR in name:
        session_name, window_name = name.split(TARGET_SEPARATOR, 1)
    else:
        session_name, window_name = name, GARDENER_WINDOW_NAME

    windows = _list_windows()
    matches = [w for w in windows if w[0] == session_name and w[2] == window_name]
    if not matches:
        return None
    return _prefer_live(matches)


def resolve_pane(title: str) -> str | None:
    """Return the tmux pane id whose #{pane_title} equals `title`, or None.

    Kept for convenience/back-compat; NOT used by navigate_to() — pane titles
    are unreliable (clobbered by a status-glyph setter), so navigation
    matches on window name via resolve_window() instead.
    """
    out = _tmux("list-panes", "-a", "-F", LIST_PANES_FORMAT)
    if not out:
        return None
    for line in out.splitlines():
        pane_id, _, pane_title = line.partition(" ")
        if pane_title == title:
            return pane_id
    return None


def navigate_to(window_name: str) -> bool:
    """Switch the tmux client to the window whose #{window_name} is exactly
    `window_name`.

    Resolves the window via resolve_window() and, if found, switches the
    client to its session then selects the window (selecting the window
    focuses its active pane, which is sufficient). Returns True on success,
    False if no matching window was found (never raises, so a stale sidebar
    row can be ignored by the caller).
    """
    match = resolve_window(window_name)
    if match is None:
        return False
    session_name, window_id = match

    if _tmux("switch-client", "-t", session_name) is None:
        return False
    if _tmux("select-window", "-t", window_id) is None:
        return False
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: sidebar_nav.py <window-name>", file=sys.stderr)
        sys.exit(1)
    ok = navigate_to(sys.argv[1])
    print(ok)
    sys.exit(0 if ok else 1)

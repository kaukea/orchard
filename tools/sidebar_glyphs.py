"""Fixed glyph, emoji, and mock-canonical text vocabulary for the sidebar
renderer -- constants only, copied verbatim from the blessed mock
(`.git/the-works/bus-message-specifying/sidebar-mock.py`) where the module
docstring in `sidebar.py` says so, plus the handful of glyphs this branch
added on top of it (task bar, indent, header ramp halves). No logic here,
just the vocabulary every drawing/text module below imports by name.
"""
from __future__ import annotations


# PHASES/BRANCH_SEPARATOR live in sidebar_model.py (imported above) — both
# are model-layer vocabulary, not presentation.
PHASE_MARK = {"done": "●", "active": "⠧", "todo": "○"}

NBSP = "\xa0"

# Pending-operator-pick roles render as no emoji (None), not a placeholder —
# so a later pick drops in without a code change (bus-message-specifying B5
# item 8).
ROLE_EMOJI: dict[str, str | None] = {
    "gardener": "🌳",
    "landscaper": "🌿",
    "sower": "🌱",
    "groundskeeper": "🧹",
    "courier": "📮",
    "bloomer": "🌸",
}
LOCATION_BADGES = {"local": "💻", "cloud": "☁️"}

# Spinner frames — retained as the source of the single static "working"
# glyph (index 7 == mock's "⠧"); no longer cycled per-frame for a feature
# row (superseded by the band sweep, see module docstring).
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# Seven-state status vocabulary (sidebar-titling item 9, revised again by
# the mock's visual contract, and again by the retention ruling below):
# idle, waiting, awaiting_agent, and stale share the same hollow circle —
# there is no longer a separate operator-wait glyph variant (bus-message-
# specifying B5 item 7: "hollow circle only, no watch/timer glyphs anywhere
# in row status"). "waiting"/"awaiting_agent" are part of the full
# vocabulary the mock defines but are currently unreachable: the fleet
# model (below) only ever derives working/done/failed/idle/stale from the
# new event grammar, which has no blocked/notify_user signal to distinguish
# a wait — see the module docstring's "NOT ported" list. Kept here rather
# than pruned, since STATUS_EMOJI.get() is used defensively and a future
# data source may yet supply the signal.
#
# "stale" IS reachable (operator ruling, 2026-07-25, revised same day): a
# session with no event inside the ~1h ACTIVE_WINDOW and no terminal
# outcome renders gray rather than being dropped from the model — nothing
# is ever removed from the sidebar by staleness; only a session restart
# (the tmpfs projects tree clearing) resets what is shown. See
# `_status_for`.
STATUS_EMOJI = {
    "working": SPINNER_FRAMES[7],
    "waiting": "○",
    "idle": "○",
    "awaiting_agent": "○",
    "stale": "○",
    "done": "✓",
    "failed": "❌",
}

# Subagent presence glyph (sidebar-titling item 4). A subagent row has no
# state beyond "it currently exists in the model" — it appears the moment
# its delegation begins and vanishes the moment it ends or its own events
# age out (operator ruling, 2026-07-26: a subagent is live-only, never
# persisted). `_row_text` below still honours a terminal glyph here
# defensively, for a Row built directly rather than through the model (see
# TaskGlyphTests).
SUBAGENT_GLYPH = "●"

# Glyph for a subagent's own live state, keyed by the scheduled/doing/done
# vocabulary (`_DELEGATION_STATE` in sidebar_model.py) — "done" is handled
# by the shared STATUS_EMOJI/TERMINAL_TASK_STATUSES path instead (see
# `_row_text`), so only the one non-default live state needs an entry here.
_SUBAGENT_LIVE_GLYPH = {"scheduled": "○"}

# TERMINAL_TASK_STATUSES lives in sidebar_model.py (imported above).

# Bookend glyph is the file's own idle/waiting hollow circle
# (STATUS_EMOJI["idle"]/["waiting"]/["stale"]), not "⋮" (sidebar-teamwork
# defect 3: "⋮" doubled as both the identity line's field separator — see
# `compose_identity_line`'s `sep` — and this banner's bookend, an
# ambiguous reuse of one glyph for two meanings). "○" already means
# "nothing live here" everywhere else in this vocabulary, so it reads the
# same way framing an empty fleet.
NO_ACTIVITY_TEXT = "○ no activity ○"
ELLIPSIS = "…"

# Separator between repo name and feature name in a feature row's tmux
# window target ("<repo>/<name>", sidebar-titling item 2) — the DISPLAYED
# row text no longer carries this prefix (bus-message-specifying B5: a
# feature row shows only its own name, since the repo is already named by
# the header block above its group), but navigation targets still need it.
TARGET_SEPARATOR = "/"

def role_emoji(role: str | None) -> str | None:
    return ROLE_EMOJI.get(role) if role else None


# Per-step glyph — done/active carry a mark, todo is bare (small caps alone
# already reads as "not reached yet" next to a marked neighbour, and a bare
# glyph column would just add noise).
_ACCORDION_STEP_GLYPH = {"done": "✓", "active": "⠧", "todo": ""}

# 0..4 completed-of-five steps -> a quarter-fill circle (operator ruling,
# 2026-07-26): a task never shows index 5 — five-of-five is a terminal task,
# which collapses to its own one-line terminal glyph instead (see
# `_task_rows`), so the full circle and the terminal tick never compete for
# the same meaning. Index 0 still renders its own (emptiest) glyph rather
# than a blank column — a task at zero progress still exists.
_PROGRESS_CIRCLES = "○◔◑◕●"
_HEADER_RAMP_IN = "▐"   # left ramp (entering the core): glyph fg on the RIGHT half — nearer the core
_HEADER_RAMP_OUT = "▌"  # right ramp (leaving the core): glyph fg on the LEFT half — nearer the core

# The one-column task-related-row indent (operator ruling, 2026-07-28, item
# 11: "the indent s quarter or half block left, forgeground THURD
# background FOURTH") — HALF block, not quarter: quarter (`▎`) is already
# `_TASK_BAR_GLYPH`'s own glyph, and reusing it here would blur two markers
# with different meanings into one shape. Half block is also the exact
# technique the header's own ramp uses (one cell, two tones).
_INDENT_GLYPH = "▌"
_INDENT_WIDTH = 1

_TASK_BAR_GLYPH = "▎"

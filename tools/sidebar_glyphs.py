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

# Spinner frames. `STATUS_EMOJI["working"]` below stays pinned to a single
# frame (index 7 == mock's "⠧") for a status LOOKUP with no tick of its own
# to advance by; the row painters that DO have a tick (feature/task/step —
# `_feature_row_glyph`/`_task_row_glyph`/`_step_row_glyph`) instead index
# this alphabet directly by `tick % len(SPINNER_FRAMES)` for their own
# "working"/"active" mark, each fixing the same "the spinner doesn't spin"
# defect for its own row.
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# Seven-state status vocabulary (sidebar-titling item 9, revised again by
# the mock's visual contract, and again by the retention ruling below):
# idle, waiting, awaiting_agent, and stale share the same hollow circle —
# there is no longer a separate operator-wait glyph variant (bus-message-
# specifying B5 item 7: "hollow circle only, no watch/timer glyphs anywhere
# in row status"). Both wait states ARE reachable (M2 remap, ruled
# 2026-07-29 — "Questioning is not waiting: the two wait words",
# docs/TODO.md.d/bus-addressing.md §Decision entries): a status post of
# `questioning` reads as "waiting" (an answer this agent asked for is
# outstanding), a status post of `waiting` reads as "awaiting_agent" (this
# agent is waiting on another agent) — see `sidebar_model._status_for`.
# The two share this glyph by design; a curses colour pair distinguishes
# them instead (`sidebar_curses_colour.py`).
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

# Eighth-resolution LEFT block ladder (index 0 = empty/space .. 8 = full
# block) — lets ONE cell show up to 9 distinguishable fill levels of one
# colour over another via a single glyph (fg = the fraction filled from
# the left, bg = the remainder) — the header/feature "falling block"
# gradient's own sub-cell resolution (operator, 2026-07-28: "the
# block-element range gives you finer steps than you may think... the
# eighth-resolution ladder is available at both ends"). Only the LEFT
# series exists as literal Unicode glyphs; a RIGHT-hand step is
# synthesised by swapping a LEFT glyph's own fg/bg (a left three-quarters
# block with its colours reversed reads as a right one-quarter block) —
# not needed by this file's own single left-to-right fade (see
# `sidebar_paint_shared.falling_block_fade_colours`), but the reason the
# ladder works at both ends.
_LEFT_EIGHTHS = " ▏▎▍▌▋▊▉█"

# Feature row identity marker (operator, 2026-07-28, superseding an
# earlier "ƒ" draft the same day: "so 🧩/<human feature name>" — U+1F9E9
# JIGSAW PUZZLE PIECE, then a literal "/", then the feature's own name).
# The emoji carries its own colour already, so it needs no contrast
# treatment of its own against the row's background. TWO cells wide
# (`unicodedata.east_asian_width` reports "W", verified — not assumed,
# since a wide glyph in a leading position has already caused a row-merge
# bug in this file, see `_draw_feature_row`'s own `cell_col` comment in
# sidebar_paint_feature.py) plus one more for the literal "/" — three
# cells of chrome before the name, not two.
FEATURE_MARKER = "🧩"

# The one-column task-related-row indent (operator ruling, 2026-07-28, item
# 11: "the indent s quarter or half block left, forgeground THURD
# background FOURTH") — HALF block, not quarter: quarter (`▎`) is already
# `_TASK_BAR_GLYPH`'s own glyph, and reusing it here would blur two markers
# with different meanings into one shape. Half block is also the exact
# technique the header's own ramp uses (one cell, two tones).
_INDENT_GLYPH = "▌"
_INDENT_WIDTH = 1

_TASK_BAR_GLYPH = "▎"

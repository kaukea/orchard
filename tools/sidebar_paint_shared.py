"""Shared curses painting helpers for every row related to an open task --
step/agent/subagent rows all use these, so they live apart from any one of
those painters. The one-column GUTTER indent glyph (the task's own carrying
colour on FOURTH -- operator ruling 2026-07-28), a plain background fill for
a row that has one, the open step's own block background (`_open_block_bg`
-- FOURTH, the same tone as the step's own title, operator ruling 2026-07-28
-- supersedes the earlier FIFTH-toned `open_stage_colour` reading), and the
SELECTED-row colour lift used instead of `curses.A_REVERSE` (Decision-111
found `A_REVERSE`'s swap did too little work on this file's own truecolor
bands).
"""
from __future__ import annotations

from sidebar_colour import MUTED, WHITE, _CONTRAST_MIN_MARK, ensure_contrast, lerp, task_chain_roles  # noqa: E402
from sidebar_curses_colour import _ColourCache, _safe_addch, _safe_addstr  # noqa: E402
from sidebar_glyphs import _INDENT_GLYPH  # noqa: E402
from sidebar_rows import Row  # noqa: E402


# --------------------------------------------------------------------------
# Curses drawing — the generic row path (task/step/agent/subagent). These
# used to be decorations hanging off a "working" feature row (phase label,
# identity line, phase checklist, footer); the six-level tree (2026-07-26)
# makes each of them a real Row in its own right instead, so they draw
# through the same plain path as any other non-feature row below — no
# separate decoration mechanism is needed any more. `footer_lines()`/
# `done_footer_line()` remain as pure formatters (still exercised directly;
# build_model() has never populated a source for them) but nothing in the
# live draw path calls them.
# --------------------------------------------------------------------------

# A "block" background — set once a step is OPEN (its own line, plus every
# agent/subagent line nested inside it) — is threaded down to these three
# functions as `bg: tuple[int, int, int] | None`: None outside any open
# step (task/feature/repo rows never get one), the step's own FOURTH tone
# otherwise (operator ruling, 2026-07-28: "the background colour of the
# currently active items inside a stage is the same colour as the titles of
# the stages themselves" — supersedes the 2026-07-26/27 `open_stage_colour`
# reading, a separately-lightened FIFTH tone; that function stays defined
# and tested in `sidebar_colour_lineage.py`, just with no live caller now).
# The whole open region still reads as ONE contiguous block — it is now
# literally the same paint as its own section title, not merely a lighter
# relative of it.
# A constant, small breathing indent replaces the old depth-scaled one here
# (curses-only — depth is now colour, not columns; the plain-text path
# still uses `INDENT_UNIT * row.depth`, see `render_lines`, since it has no
# colour to carry structure with). The indent glyph itself and its width
# constant now live in `sidebar_glyphs.py` (`_INDENT_GLYPH`/`_INDENT_WIDTH`).
# --------------------------------------------------------------------------


def _draw_indent_cell(
    stdscr, y: int, colours: _ColourCache, gutter: tuple[int, int, int], fourth: tuple[int, int, int],
) -> None:
    """The one-column GUTTER glyph for every step/agent/subagent row —
    `gutter` (the task's own carrying colour, Ct — operator ruling,
    2026-07-28: "the task colour... becomes the half block on the left all
    the way for each of the steps, and for the content of each of the
    steps" — supersedes the earlier repo-wide THIRD reading) on the glyph's
    own half, FOURTH (every step row's and the indent's own background) on
    the rest of the cell. `fourth` is the caller's already selection-
    adjusted background — lifting only the glyph's own fg here would desync
    it from a lifted neighbour, so the caller decides the lift once and
    this just paints."""
    fg = ensure_contrast(gutter, fourth, _CONTRAST_MIN_MARK)
    _safe_addch(stdscr, y, 0, _INDENT_GLYPH, colours.pair(fg, fourth))


def _fill_row_bg(stdscr, y: int, width: int, bg: tuple[int, int, int], colours: _ColourCache) -> None:
    attr = colours.pair(MUTED, bg)
    _safe_addstr(stdscr, y, 0, " " * max(width - 1, 0), attr)
    if width > 0:
        _safe_addch(stdscr, y, width - 1, " ", attr)


def _open_block_bg(
    row: Row, hue: dict[str, tuple[int, int, int]],
) -> tuple[int, int, int] | None:
    """The open step's own block background this row (an agent/subagent
    line) sits inside — the SAME FOURTH tone the step's own title row sits
    on (`task_chain_roles(hue, row.feature_colour).fourth`), not a
    separately-derived tone of its own (operator ruling, 2026-07-28: "the
    background colour of the currently active items inside a stage is the
    same colour as the titles of the stages themselves... to avoid having
    colours just bleeding everywhere" — supersedes the earlier `open_stage_
    colour(content_colour_base(row.task_colour))` FIFTH tone, which is kept
    defined and tested in `sidebar_colour_lineage.py` but has no live caller
    left, same "reusable, not deleted" pattern this codebase already uses
    for other superseded geometry). None only for a row with no owning
    feature/task colour context at all (shouldn't happen for an agent/
    subagent in practice — they only ever render under an open step — but
    never crashes if it does)."""
    if row.task_colour is None:
        return None
    return task_chain_roles(hue, row.feature_colour).fourth

# The SELECTED row's own highlight (sidebar-teamwork defect 4, 2026-07-27):
# a further lift toward WHITE from whatever background the row already
# carries (plain black when it carries none of its own), rather than
# `curses.A_REVERSE` — a straight foreground/background swap did "very
# little work" on screen, because on this file's own truecolor bands two
# already-similar tones can swap onto each other and read as unchanged, and
# a swapped pair's OWN readability was never separately checked (only the
# un-swapped direction ever ran through `ensure_contrast`). A colour LIFT
# is checked exactly the same way every other derived colour in this file
# already is — every caller re-runs `ensure_contrast` against the LIFTED
# background it actually painted, so the guarantee holds by construction,
# not by assuming a swap preserves it. Paired with `curses.A_BOLD` for a
# second, colour-independent cue — safe over a custom background; Decision-
# 111 found the corruption specific to `A_DIM`, never bold.
_SELECTION_LIFT_FRACTION = 0.30


def _selection_highlight(bg: tuple[int, int, int] | None) -> tuple[int, int, int]:
    return lerp(bg if bg is not None else (0, 0, 0), WHITE, _SELECTION_LIFT_FRACTION)

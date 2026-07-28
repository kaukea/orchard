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
from sidebar_glyphs import _INDENT_GLYPH, _LEFT_EIGHTHS  # noqa: E402
from sidebar_rows import Row  # noqa: E402
from sidebar_text import _cell_width, _truncate  # noqa: E402


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


# --------------------------------------------------------------------------
# "Falling block" row: a solid PRIMARY core (the text) flush at the LEFT,
# falling away to SECONDARY toward the right edge — shared by the project
# header and the feature row (operator, 2026-07-28: "the feature should do
# exactly the same [as the project]... on the SAME BACKGROUND... A longer
# gradient using more block steps... Both for the project and for the
# feature" — replaces the earlier symmetric two/three-cell ramp entirely).
# The fade is TWO named colours only (no intermediate RGB lerp) dithered
# via the eighth-resolution block ladder (`_LEFT_EIGHTHS`), so it reads
# smoothly across however many columns the pane actually has past the
# core, however few or many that is.
# --------------------------------------------------------------------------

_FALLING_BLOCK_PAD = 1  # one space of padding each side of the core text


def falling_block_core_width(text: str) -> int:
    return _cell_width(text) + 2 * _FALLING_BLOCK_PAD


def _falling_block_core_text(text: str, core_width: int) -> str:
    """`text`, LEFT-aligned (not centred — the core anchors the pane's left
    edge, operator: "fold on the left"), padded with one space each side,
    truncated with an ellipsis if `core_width` can't hold it whole."""
    if core_width <= 0:
        return ""
    inner_width = max(core_width - 2 * _FALLING_BLOCK_PAD, 0)
    shown = _truncate(text, inner_width)
    pad = max(inner_width - _cell_width(shown), 0)
    body = (" " * _FALLING_BLOCK_PAD) + shown + (" " * pad) + (" " * _FALLING_BLOCK_PAD)
    return body[:core_width]


def falling_block_fade_colours(
    primary: tuple[int, int, int], secondary: tuple[int, int, int], fade_width: int,
) -> list[tuple[str, tuple[int, int, int], tuple[int, int, int]]]:
    """(glyph, fg, bg) for each of `fade_width` cells, left (adjacent to
    the core, mostly PRIMARY) to right (the pane edge, mostly SECONDARY) —
    eighth-resolution via `_LEFT_EIGHTHS`, using only the two named
    colours (operator, 2026-07-28: "the eighth-resolution ladder... gives
    you finer steps than you may think" — up to 9 distinguishable levels
    per cell from exactly two colours, rather than needing an intermediate
    RGB computed for every cell) — smooth across as few or as many cells
    as the pane actually affords past the core, which is what "reads as
    falling away toward the edge of the screen" needs: a long gradient
    where the pane is wide, still a legible one where it is narrow."""
    if fade_width <= 0:
        return []
    cells = []
    for i in range(fade_width):
        fraction = 1.0 - (i + 0.5) / fade_width
        k = max(0, min(8, round(fraction * 8)))
        if k <= 0:
            cells.append((" ", secondary, secondary))
        elif k >= 8:
            cells.append((" ", primary, primary))
        else:
            cells.append((_LEFT_EIGHTHS[k], primary, secondary))
    return cells


def _draw_falling_block_row(
    stdscr, y: int, width: int, text: str,
    primary: tuple[int, int, int], secondary: tuple[int, int, int], text_fg: tuple[int, int, int],
    colours: _ColourCache, extra_attr: int = 0,
) -> None:
    """Paints the shared header/feature-row layout: a solid `primary` core
    containing `text` (in `text_fg`), flush left, then a `falling_block_
    fade_colours` fade to `secondary` filling the rest of `width`. Every
    column gets an explicit `colours.pair(fg, bg)` — no column is ever left
    to inherit whatever a previous row painted (the correctness half of
    this redesign, not just its look)."""
    if width <= 0:
        return
    core_width = min(falling_block_core_width(text), width)
    core_text = _falling_block_core_text(text, core_width)
    core_attr = colours.pair(text_fg, primary) | extra_attr
    for i in range(core_width):
        ch = core_text[i] if i < len(core_text) else " "
        _safe_addch(stdscr, y, i, ch, core_attr)
    fade_width = width - core_width
    for i, (ch, fg, bg) in enumerate(falling_block_fade_colours(primary, secondary, fade_width)):
        _safe_addch(stdscr, y, core_width + i, ch, colours.pair(fg, bg) | extra_attr)

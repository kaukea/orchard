"""Paints one line of the task's five-step accordion: centred small caps
over a one-column indent (THIRD on FOURTH) plus the row's own FOURTH
background -- the same tone for every step regardless of done/active/todo
(operator ruling 2026-07-28). The ACTIVE+live step additionally carries the
moving KITT sweep, reusing sidebar_band.py's triangular-wave geometry.
"""
from __future__ import annotations

import curses

from sidebar_band import band_column_colour, band_position, band_span  # noqa: E402
from sidebar_colour import (  # noqa: E402
    GREEN_SOFT,
    MUTED,
    TEXT,
    _CONTRAST_MIN_TEXT,
    ensure_contrast,
    task_chain_roles,
)
from sidebar_curses_colour import _ColourCache, _safe_addch  # noqa: E402
from sidebar_glyphs import _ACCORDION_STEP_GLYPH, _INDENT_WIDTH  # noqa: E402
from sidebar_paint_shared import _draw_indent_cell, _selection_highlight  # noqa: E402
from sidebar_rows import Row  # noqa: E402
from sidebar_text import render_header_line  # noqa: E402


_STEP_LINE_COLOUR = {"done": GREEN_SOFT, "active": TEXT, "todo": MUTED}


def _step_row_name_and_mark(row: Row) -> tuple[str, str]:
    """(name_only, mark) split of an accordion Row's `label` — the model
    layer (`_step_row`) still bakes "{glyph} {small_caps(name)}" into
    `label` for the plain-text path (`_row_text`/`render_lines`, untouched
    by this curses-only realignment); this recovers the mark so the curses
    painter can pin it to a fixed column instead of leaving it embedded in
    the centred name."""
    mark = _ACCORDION_STEP_GLYPH.get(row.status, "")
    prefix = f"{mark} "
    if mark and row.label.startswith(prefix):
        return row.label[len(prefix):], mark
    return row.label, mark


def _step_row_display_text(row: Row, width: int) -> str:
    """The step row's full-width display text with its own mark pinned to
    a FIXED right-hand column, rather than riding the centred name
    (operator ruling, 2026-07-27: "the checkmarx or red markx next to the
    step shoujld be right aligned... the mark must not float in the middle
    next to a centred label of varying length" — a mark that drifts with
    the label reads ragged; a fixed column doesn't). The window's own
    literal last column is never safely writable (`_safe_addch`'s insch
    trap drops any character landed there), so "right-aligned" lands one
    column short of the true edge, at `width - 2`, with the true last
    column left blank."""
    name, mark = _step_row_name_and_mark(row)
    if width < 2:
        return render_header_line(row.label, width)
    name_width = width - 2
    centred = render_header_line(name, name_width)
    mark_ch = mark if mark else " "
    return (centred + mark_ch + " ")[:width]


def _draw_step_row(
    stdscr, y: int, width: int, row: Row, selected: bool, colours: _ColourCache, tick: int,
    hue: dict[str, tuple[int, int, int]],
) -> int:
    """One line of the task's five-step accordion (operator correction,
    2026-07-26: "collapse keeps the line" — every step gets its own row,
    always), CENTRED, small caps, over a one-column indent (THIRD on
    FOURTH, `_draw_indent_cell`) plus the row's own FOURTH background.

    EVERY step title — done, active, or todo alike — carries the SAME flat
    FOURTH colour (operator ruling 2026-07-28, item 11: "for whichi
    wederive the FOURTh... Then each step uses FOURTH" — supersedes the
    grade-3 `content_colour_base(row.task_colour)` reading this docstring
    previously described; a step row's background is now the repo/feature
    chain's FOURTH, same tone as the indent's own background, not a
    per-task tint). Being active is expressed by its mark, its sweep and
    by what appears beneath it, NOT by changing the title's own
    background (operator ruling 2026-07-27, still true). If the ACTIVE
    step is also LIVE (a genuinely "working" agent on it, not merely the
    furthest-along position — `row.live`, see `_step_row`/the model-layer
    function of the same name) it additionally carries the MOVING
    GRADIENT sweep — reusing the pre-existing lifted-band triangular-wave
    geometry (`band_position`/`band_span`/`band_column_colour`) across the
    row's own text width, brightening this SAME FOURTH colour rather than
    a separately-darkened one. No room/no motion just means a static (but
    still correctly coloured) block (ANIMATION CAVEAT: a missing animation
    must never mean a missing step). `selected` swaps in `_selection_
    highlight` for the step's own FOURTH colour (sidebar-teamwork defect
    4) rather than `curses.A_REVERSE` — every foreground below is already
    run through `ensure_contrast` against `content`/the sweep's own `bg`,
    so substituting the lifted colour before those calls keeps the
    guarantee automatically."""
    roles = task_chain_roles(hue, row.feature_colour)
    content = _selection_highlight(roles.fourth) if selected else roles.fourth
    attr_extra = curses.A_BOLD if selected else 0
    _draw_indent_cell(stdscr, y, colours, roles.third, content)
    text_width = max(width - _INDENT_WIDTH, 0)
    text = _step_row_display_text(row, text_width)

    if row.status != "active":
        fg = ensure_contrast(_STEP_LINE_COLOUR.get(row.status, MUTED), content, _CONTRAST_MIN_TEXT)
        for col, ch in enumerate(text):
            _safe_addch(stdscr, y, col + _INDENT_WIDTH, ch, colours.pair(fg, content) | attr_extra)
        return y + 1

    if row.live:
        span = band_span(max(text_width - 1, 1))
        pos = band_position(tick, span)
        for col, ch in enumerate(text):
            bg = band_column_colour(col, pos, text_width, content) or content
            fg = ensure_contrast(TEXT, bg, _CONTRAST_MIN_TEXT)
            _safe_addch(stdscr, y, col + _INDENT_WIDTH, ch, colours.pair(fg, bg) | attr_extra)
    else:
        fg = ensure_contrast(TEXT, content, _CONTRAST_MIN_TEXT)
        for col, ch in enumerate(text):
            _safe_addch(stdscr, y, col + _INDENT_WIDTH, ch, colours.pair(fg, content) | attr_extra)
    return y + 1

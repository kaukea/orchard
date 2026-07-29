"""Paints one line of the task's five-step accordion: a fixed-LEFT mark
(checkmark/spinner), centred small caps, and a reserved-but-currently-blank
right column for a per-step timer (operator ruling 2026-07-28 -- see
`_step_row_display_text`), over a one-column gutter indent (the FEATURE's
own carrying colour on FOURTH -- operator ruling, reversing the earlier
task-colour reading, see `_draw_step_row`) plus the row's own background.
DONE/TODO steps share ONE flat FOURTH tone -- unbroken across every step of
every task in the same feature (operator ruling 2026-07-28, item 11); the
ACTIVE stage alone gets a background of its own, derived from the task's
own colour (operator ruling, 2026-07-29 -- see `_draw_step_row`). The
ACTIVE+live step additionally carries the moving KITT sweep, reusing
sidebar_band.py's triangular-wave geometry, and its own mark CYCLES through
`SPINNER_FRAMES` by tick (operator ruling: "the spinner doesn't spin" --
the task/feature rows already carry this same fix, see `_task_row_glyph`/
`_feature_row_glyph`; the accordion's own mark was still pinned to a single
static frame despite `tick` already reaching `_draw_step_row` for the KITT
sweep).
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
from sidebar_colour_lineage import content_colour_base  # noqa: E402
from sidebar_curses_colour import _ColourCache, _safe_addch  # noqa: E402
from sidebar_glyphs import _ACCORDION_STEP_GLYPH, _INDENT_WIDTH, SPINNER_FRAMES  # noqa: E402
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


def _step_row_glyph(status: str | None, live: bool, tick: int) -> str:
    """The step row's own mark — CYCLES through `SPINNER_FRAMES` by `tick`
    while genuinely LIVE (`status == "active"` AND `live` — a real
    "working" agent on the step, not merely its furthest-along position;
    an idle/stopped session's step still reads `status == "active"` with
    `live == False`, see `Row.live`/`_step_row`'s own docstring, and MUST
    stay static — proven directly by SidebarEmulatorFrameTests'
    `test_active_step_kitt_sweep_animates_while_other_lines_stay_static`,
    which seeds exactly that idle case alongside a genuinely live one).
    Operator ruling: "the spinner doesn't spin" —
    `STATUS_EMOJI["working"]`/`_ACCORDION_STEP_GLYPH["active"]` were both
    pinned to the SAME single fixed `SPINNER_FRAMES[7]` frame;
    `_task_row_glyph`/`_feature_row_glyph` already carry this identical fix
    for their own rows, and `tick` already reaches `_draw_step_row` for the
    KITT sweep's own `band_position` call — it just never advanced the
    mark itself. Every other case keeps its existing static mark from
    `_ACCORDION_STEP_GLYPH`, unchanged."""
    if status == "active" and live:
        return SPINNER_FRAMES[tick % len(SPINNER_FRAMES)]
    return _ACCORDION_STEP_GLYPH.get(status, "")


def _step_row_display_text(row: Row, width: int, tick: int = 0) -> str:
    """The step row's full-width display text with its own mark pinned to
    a FIXED LEFT-hand column (operator ruling, 2026-07-28: "the checkmark
    goes to the left, not to the right. I changed my mind... the spinner
    goes to the left" — reverses the 2026-07-27 right-alignment below, but
    for the SAME reason: a mark that drifts with a centred label of varying
    length reads ragged, a fixed column doesn't, whichever side it sits on).
    A trailing column is reserved for a RIGHT-hand timer (2026-07-28: "on
    the right, you have your timer of how long things are going... when it
    closes, then it becomes the total time") — NOT implemented here: no
    per-step/per-task start timestamp exists anywhere in this model (`Step`/
    `Task`/`Agent` carry none; the closest thing on the bus, `_seen_ts`, is
    a per-SESSION last-activity marker used only for staleness, never a
    per-step "began at", and `context_tokens`/`spend` are magnitudes, not
    time) — flagged to the operator rather than invented, so the column is
    left blank pending that data. The window's own literal last column is
    never safely writable (`_safe_addch`'s insch trap drops any character
    landed there), so this still reserves it as blank, same as before.

    `tick` (default 0, curses-only callers pass the real frame counter)
    picks the LIVE active step's own cycling `SPINNER_FRAMES` frame via
    `_step_row_glyph` (gated on `row.live`, never on `row.status` alone —
    see that function's own docstring) — done/todo marks and the NAME
    split both still come from `_step_row_name_and_mark`'s static,
    model-baked reading, so a repeated call at `tick=0` (the plain-text/
    default path) stays exactly what it always was."""
    name, _static_mark = _step_row_name_and_mark(row)
    if width < 2:
        return render_header_line(row.label, width)
    name_width = max(width - 3, 0)
    centred = render_header_line(name, name_width)
    mark = _step_row_glyph(row.status, row.live, tick)
    mark_ch = mark if mark else " "
    return f"{mark_ch} {centred} "[:width]


def _draw_step_row(
    stdscr, y: int, width: int, row: Row, selected: bool, colours: _ColourCache, tick: int,
    hue: dict[str, tuple[int, int, int]],
) -> int:
    """One line of the task's five-step accordion (operator correction,
    2026-07-26: "collapse keeps the line" — every step gets its own row,
    always), mark fixed LEFT / name CENTRED / timer column reserved RIGHT
    (`_step_row_display_text`), over a one-column gutter indent (the
    FEATURE's own carrying colour on FOURTH, `_draw_indent_cell` —
    REVERSES the earlier task-colour reading this docstring described;
    the operator confirmed the reversal so the gutter reads as one
    unbroken band down the WHOLE feature, never breaking colour at a task
    boundary the way the task's own Ct did) plus the row's own background.

    DONE/TODO step titles carry the SAME flat FOURTH colour, unbroken
    across every step of every task in the feature (operator ruling
    2026-07-28, item 11: "for whichi wederive the FOURTh... Then each step
    uses FOURTH") — this is the "shared band" ruling 2026-07-29 below
    contrasts against. The ACTIVE stage row — and ONLY the active one —
    additionally paints its OWN distinct background (operator ruling,
    2026-07-29: reinstates the grade-3 `content_colour_base(row.task_
    colour)` tone, a step title's own background per that function's own
    docstring, for the active row alone rather than uniformly for every
    row the way the 2026-07-28 ruling above still reads for done/todo).
    Which step is "active" is `row.status`, already derived client-side
    from the agent's own role (Decision-107, `_step_row`/`sidebar_model.
    py`) — consumed here via the existing `row.status`/`row.live` fields,
    never re-derived. If the ACTIVE step is also LIVE (a genuinely
    "working" agent on it, not merely the furthest-along position —
    `row.live`, see `_step_row`/the model-layer function of the same
    name) it additionally carries the MOVING GRADIENT sweep — reusing the
    pre-existing lifted-band triangular-wave geometry (`band_position`/
    `band_span`/`band_column_colour`) across the row's own text width,
    brightening this SAME active-distinct colour rather than a
    separately-darkened one. No room/no motion just means a static (but
    still correctly coloured) block (ANIMATION CAVEAT: a missing animation
    must never mean a missing step). `selected` swaps in `_selection_
    highlight` for the step's own background (sidebar-teamwork defect
    4) rather than `curses.A_REVERSE` — every foreground below is already
    run through `ensure_contrast` against `content`/the sweep's own `bg`,
    so substituting the lifted colour before those calls keeps the
    guarantee automatically."""
    roles = task_chain_roles(hue, row.feature_colour)
    if row.status == "active" and row.task_colour is not None:
        base_bg = content_colour_base(row.task_colour)
    else:
        base_bg = roles.fourth
    content = _selection_highlight(base_bg) if selected else base_bg
    gutter = row.feature_colour or roles.third
    attr_extra = curses.A_BOLD if selected else 0
    _draw_indent_cell(stdscr, y, colours, gutter, content)
    text_width = max(width - _INDENT_WIDTH, 0)
    text = _step_row_display_text(row, text_width, tick)

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

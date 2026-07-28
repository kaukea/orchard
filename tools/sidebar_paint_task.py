"""Paints a task's own row: a full-width FLAT band in the task's own
carrying colour (Ct, `row.task_colour`) -- the most visible thing on the
board (operator ruling, 2026-07-28: "the task needs to be derived from
that colour scheme. It's probably the one you want to be the most
visible... it should be completely flat") -- glyph and name over it, no
gradient, no separate accent-bar cell, no progress-circle tail (see
`_draw_task_row`'s docstring for what those three used to be and why they
are gone). The status glyph cycles while "working" (operator ruling,
2026-07-27), static otherwise.
"""
from __future__ import annotations

import curses

from sidebar_colour import (  # noqa: E402
    MUTED,
    TEXT,
    _CONTRAST_MIN_TEXT,
    ensure_contrast,
)
from sidebar_curses_colour import _ColourCache, _safe_addch, _safe_addstr  # noqa: E402
from sidebar_glyphs import SPINNER_FRAMES, STATUS_EMOJI  # noqa: E402
from sidebar_paint_shared import _selection_highlight  # noqa: E402
from sidebar_render_text import compose_task_row_text  # noqa: E402
from sidebar_rows import Row  # noqa: E402
from sidebar_text import _truncate  # noqa: E402


def _task_row_glyph(status: str | None, tick: int) -> str:
    """The task row's own status glyph — a genuinely CYCLING spinner frame
    while `status == "working"` (operator ruling, 2026-07-27: "the spinner
    on the task doesn't spin" — a real defect, not styling; the row was
    drawing a fixed `STATUS_EMOJI["working"]` frame with no `tick` ever
    threaded into `_draw_task_row` to recompute it against, so it could
    never advance regardless of how long the frame loop ran). Every other
    status keeps its existing static glyph unchanged. This is curses-only,
    same as every other per-frame motion in this file — the plain-text
    path (`compose_task_row_text`/`_row_text`) still uses the static
    `STATUS_EMOJI["working"]` frame, since a repeated `render_lines` call
    must stay byte-identical."""
    if status == "working":
        return SPINNER_FRAMES[tick % len(SPINNER_FRAMES)]
    return STATUS_EMOJI.get(status, "○")


def _draw_task_row(
    stdscr, y: int, width: int, row: Row, selected: bool, colours: _ColourCache,
    hue: dict[str, tuple[int, int, int]], tick: int,
) -> int:
    """A task's own row: ONE flat full-width band in the task's own
    carrying colour (Ct, `row.task_colour` — grade 2, already allocated
    once per feature by `_assign_task_colours` within its feature's own hue
    range, so two open tasks are visually distinct by this colour alone),
    glyph and name drawn straight over it (operator ruling, 2026-07-28).

    THREE things this row used to carry are gone (operator ruling,
    2026-07-28, verbatim: "currently, it has a quarter block. It has a
    black block, which I don't understand, and it has the white bubble,
    which is not for it, it's for other systems"):

    1. The QUARTER BLOCK — `_TASK_BAR_GLYPH` ("▎"), the one-column accent
       bar this row used to draw at column 0.
    2. The BLACK BLOCK — that same bar cell's own background (`task_chain_
       roles(...).third`, a dark repo-chain tone) filling the rest of the
       character cell behind the thin quarter-glyph sliver.
       Both 1 and 2 were one glyph draw, at one cell — removed together,
       superseded by this row's own flat Ct band, which now carries the
       task's identity colour over the WHOLE row instead of one column.
    3. The WHITE BUBBLE — `row.progress_glyph`, the right-aligned "steps
       completed" circle (`_PROGRESS_CIRCLES`, "○◔◑◕●"). Its terminal glyph
       ("●", all five steps done) is the EXACT SAME character as
       `SUBAGENT_GLYPH`, the presence marker for a subagent elsewhere in
       this tree — a different system's own vocabulary bleeding onto this
       row, which is what read as "not for it". Dropped from this curses
       painter by passing `progress=None` to `compose_task_row_text`; the
       plain-text path and `Row.progress_glyph` itself are untouched (still
       used by the headless render/tests), since only the on-screen curses
       appearance was in scope here.

    A terminal task's own name text drops its green "done" colour (operator
    ruling, 2026-07-28: "the green is not green enough... I suggest we
    simply remove the green from that" — the same colour-as-status-carrier
    drop `_draw_subagent_row` already made): the row's own `✓` mark already
    carries done-ness, so its name reads in plain TEXT, same as any other
    status except "failed", which still keeps MUTED. The
    status glyph itself is `_task_row_glyph` (operator ruling, 2026-07-27)
    — cycling while working, static otherwise. `selected` swaps in
    `_selection_highlight` for the row's own background (sidebar-teamwork
    defect 4) rather than `curses.A_REVERSE` — every foreground below is
    already run through `ensure_contrast` against `bg`, so substituting the
    lifted background before those calls keeps the guarantee
    automatically.

    A TERMINAL task carries no `task_colour` of its own (`_assign_task_
    colours` skips it — its slot is simply freed for reuse, operator
    ruling 2026-07-26); this row's own fallback for that case is `hue
    ["fill"]` (SECONDARY), never `hue["accent"]` (PRIMARY) — found here:
    PRIMARY is now the header/feature row's own shared falling-block
    background (this step's Dracula/falling-block redesign), so a terminal
    task falling back to it would paint the EXACT SAME colour as its own
    feature row immediately above, reading as one merged band rather than
    two rows. SECONDARY was already the feature row's OWN background before
    this step and is unused by any row again now, so it is free to be this
    row's own distinct fallback tone instead."""
    bg = row.task_colour or hue["fill"]
    if selected:
        bg = _selection_highlight(bg)
    attr_extra = curses.A_BOLD if selected else 0
    glyph = _task_row_glyph(row.status, tick)
    # One column short of the window's TRUE last column (`width - 1`),
    # the same reservation `_step_row_display_text` and `_draw_feature_row`
    # already make — `_safe_addch` blanks whatever lands on the true last
    # column, so it is filled separately below rather than by `_safe_addstr`.
    text_width = max(width - 1, 0)
    body = _truncate(compose_task_row_text(glyph, row.label, None, text_width), text_width)
    text_fg = MUTED if row.status == "failed" else TEXT
    text_fg = ensure_contrast(text_fg, bg, _CONTRAST_MIN_TEXT)
    attr = colours.pair(text_fg, bg) | attr_extra
    _safe_addstr(stdscr, y, 0, body, attr)
    if width > 0:
        _safe_addch(stdscr, y, width - 1, " ", attr)
    return y + 1

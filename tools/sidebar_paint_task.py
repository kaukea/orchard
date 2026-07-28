"""Paints a task's own row: a single accent bar cell (background THIRD,
foreground the task's own grade-2 colour) followed by its name and
right-aligned progress circle as plain text, no background -- what keeps a
task row visibly distinct from a feature row's own full band. The status
glyph cycles while "working" (operator ruling, 2026-07-27), static
otherwise.
"""
from __future__ import annotations

import curses

from sidebar_colour import (  # noqa: E402
    GREEN,
    MUTED,
    TEXT,
    _CONTRAST_MIN_MARK,
    _CONTRAST_MIN_TEXT,
    ensure_contrast,
    task_chain_roles,
)
from sidebar_colour_lineage import feature_colour_base  # noqa: E402
from sidebar_curses_colour import _ColourCache, _safe_addstr  # noqa: E402
from sidebar_glyphs import SPINNER_FRAMES, STATUS_EMOJI, _TASK_BAR_GLYPH  # noqa: E402
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
    """A task's own row: a single accent BAR cell — background THIRD
    (`task_chain_roles(hue, row.feature_colour).third`, operator ruling
    2026-07-28: the task line's own background is derived FROM the repo's
    SECONDARY, one link down the chain, no longer equal to it — supersedes
    the earlier `hue["fill"]` reading, which was SECONDARY itself, the
    feature row's own tone), foreground Ct (grade 2, `row.task_colour`,
    already allocated once per feature by `_assign_task_colours` within
    its feature's own hue range, so two open tasks are told apart by bar
    colour alone) — followed by its name and right-aligned progress circle
    as PLAIN text, no background (operator spec, 2026-07-26: this is what
    keeps a task row visibly distinct from a feature row's own full solid
    band). A terminal task's own green/"failed" colour always wins over
    its Ct tint, same exclusivity rule as before. The status glyph itself
    is `_task_row_glyph` (operator ruling, 2026-07-27) — cycling while
    working, static otherwise. `selected` swaps in `_selection_highlight`
    for the row's own background (sidebar-teamwork defect 4) rather than
    `curses.A_REVERSE` — every foreground below is already run through
    `ensure_contrast` against `bg`, so substituting the lifted background
    before those calls keeps the guarantee automatically."""
    bg = task_chain_roles(hue, row.feature_colour).third
    if selected:
        bg = _selection_highlight(bg)
    attr_extra = curses.A_BOLD if selected else 0
    if row.status == "done":
        bar_fg = GREEN
    elif row.status == "failed":
        bar_fg = MUTED
    else:
        bar_fg = row.task_colour or feature_colour_base(hue)
    bar_fg = ensure_contrast(bar_fg, bg, _CONTRAST_MIN_MARK)
    _safe_addstr(stdscr, y, 0, _TASK_BAR_GLYPH, colours.pair(bar_fg, bg) | attr_extra)
    glyph = _task_row_glyph(row.status, tick)
    # One column short of the window's TRUE last column (`width - 1`),
    # never `width - 2` — the same reservation `_step_row_display_text`
    # and `_draw_feature_row` already make. `_safe_addstr` (unlike
    # `_safe_addch`) never special-cases that edge: a body long enough to
    # reach it would `addstr` straight onto it, and this build's terminal
    # auto-wraps the cursor off that write, desyncing the colour-pair
    # state for whatever draws on the ROW BELOW next — a row depending on
    # what was drawn before it, Decision-111's `A_DIM` bug reached through
    # a different attribute path (sidebar-teamwork defect (b)).
    avail = max(width - 3, 0)
    body = _truncate(compose_task_row_text(glyph, row.label, row.progress_glyph, avail), avail)
    text_fg = GREEN if row.status == "done" else MUTED if row.status == "failed" else TEXT
    text_fg = ensure_contrast(text_fg, bg, _CONTRAST_MIN_TEXT)
    _safe_addstr(stdscr, y, 2, body, colours.pair(text_fg, bg) | attr_extra)
    return y + 1

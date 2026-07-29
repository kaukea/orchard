"""Triangular-wave sweep and fill-bar column geometry -- pure integer/RGB
math, no curses, no Row. `band_position`/`band_span` still drive the
accordion's live KITT sweep (`_draw_step_row`); `fill_cols`/`band_travel_
end`/`progress_column_colour`/`lifted_fill_colour`/`band_column_colour` were
the feature row's own percentage-driven partial fill, superseded 2026-07-26
by its unconditional full-width band, but kept defined and tested rather
than deleted -- the geometry is exactly reusable if a percentage-driven
fill is ever wanted again.

Also home to the header/feature-row EDGE-TAPER BAND geometry (operator
ruling, area A, this step): a full-width band whose ends taper toward the
pane edges, the PRIMARY core filling and widening with whatever is left
between them (`band_gradient_fits`/`core_min_width`/`core_text`), and the
eighth-resolution taper itself on each side (`left_taper_cells`/
`right_taper_cells`). This corrects the previous "falling block" reading
(`sidebar_paint_shared._draw_falling_block_row`, title flush at column 0,
fading away to the RIGHT only) which the operator identified as the
opposite of what he asked: "the gradient should only be on the left... it
looks like it's folding towards the end of the screen" was misread as
"gradient trails right of a left-anchored title" when he meant the
gradient itself enters FROM the left edge, growing more intense as it
nears the title -- restated here as ruling 1, "the row reads as folding in
from the screen edge". `header_ramp_cells` is one narrow, deliberate
exception to this file's own purity: it reads `SIDEBAR_HEADER_RAMP_
VARIANT` from the environment when no explicit variant is passed, the
same fail-open pattern already used elsewhere in this renderer for
environment-sourced input, kept here rather than pushed to a caller so the
env var's name and default never need repeating.
"""
from __future__ import annotations

import os

from sidebar_colour import WHITE, lerp  # noqa: E402
from sidebar_glyphs import _LEFT_EIGHTHS  # noqa: E402
from sidebar_text import _cell_width, _truncate  # noqa: E402


# --------------------------------------------------------------------------
# Progress fill / band sweep geometry (pure). `band_position`/`band_span`
# are still live — the accordion's ACTIVE step KITT sweep reuses them
# (`_draw_step_row`). `fill_cols`/`band_travel_end`/`progress_column_colour`/
# `band_column_colour`/`lifted_fill_colour` were the feature row's own
# percentage-driven partial fill, superseded 2026-07-26 by its unconditional
# full-width band (a feature carries no percentage any more) — kept defined
# and exercised by their own tests (same "stays defined, no live caller"
# pattern as `footer_lines`/`done_footer_line`) rather than deleted, since
# the geometry is exactly reusable if a percentage-driven fill is ever
# wanted again.
# --------------------------------------------------------------------------


def fill_cols(pct: int, width: int) -> int:
    return round(width * pct / 100)


def band_travel_end(pct: int, width: int) -> int:
    return width - len(f"{pct}%")


def band_span(travel_end: int) -> int:
    return max(travel_end - 1, 1)


def band_position(tick: int, span: int) -> int:
    """Triangular wave over [0, span], period 2*span — the band's column
    offset at a given tick (bus-message-specifying B5 item 3: "triangular
    wave" bidirectional sweep)."""
    span = max(span, 1)
    phase = tick % (2 * span)
    return phase if phase <= span else 2 * span - phase


def lifted_fill_colour(fill_rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    return lerp(fill_rgb, WHITE, 0.18)


def progress_column_colour(
    col: int, fill_cols_count: int, fill_rgb: tuple[int, int, int],
) -> tuple[int, int, int] | None:
    return fill_rgb if col < fill_cols_count else None


def band_column_colour(
    col: int, pos: int, travel_end: int, fill_rgb: tuple[int, int, int],
) -> tuple[int, int, int] | None:
    if col >= travel_end:
        return None
    if abs(col - pos) <= 2:
        return lifted_fill_colour(fill_rgb)
    return fill_rgb


# --------------------------------------------------------------------------
# Header/feature-row edge-taper band (operator ruling, area A, this step):
# a full-width band whose two ends taper toward the pane edges, with a solid
# PRIMARY core -- the row's own text -- filling and widening with whatever
# width is left between the two tapers. Direction: the core is PRIMARY at
# full strength; each side TAMES it outward to SECONDARY as it nears its own
# pane edge ("we don't highlight, we tame with the gradient" -- the same
# primary->gradient->secondary pair `colour_ramp_steps` in sidebar_colour.py
# already names for reuse elsewhere, e.g. ownership tracking; this band uses
# the eighth-resolution block ladder instead of that function's flat steps,
# for a longer, finer-grained gradient than a few flat colour steps could
# give). Applies identically to the project header and to every feature row
# (ruling: not the first only) -- the two painters share this geometry and
# differ only in the text colour they hand in.
# --------------------------------------------------------------------------

_HEADER_RAMP_VARIANT_ENV = "SIDEBAR_HEADER_RAMP_VARIANT"
_HEADER_RAMP_CELLS_BY_VARIANT = {"two-cell": 2, "three-cell": 3}
_HEADER_RAMP_DEFAULT_VARIANT = "three-cell"


def header_ramp_cells(variant: str | None = None) -> int:
    """Ramp cells per side -- the SIDEBAR_HEADER_RAMP_VARIANT A/B switch,
    which survives this redesign (operator ruling). `variant` lets a unit
    test exercise both named variants directly; the live render path
    passes nothing and this reads the environment itself. `three-cell` is
    the default (he said three twice) -- an unset or unrecognised variant
    falls back to it rather than raising, this file's own fail-open rule
    for environment-sourced input."""
    if variant is None:
        variant = os.environ.get(_HEADER_RAMP_VARIANT_ENV, _HEADER_RAMP_DEFAULT_VARIANT)
    return _HEADER_RAMP_CELLS_BY_VARIANT.get(
        variant, _HEADER_RAMP_CELLS_BY_VARIANT[_HEADER_RAMP_DEFAULT_VARIANT],
    )


def _taper_k(distance_from_core: int, ramp_cells: int) -> int:
    """0..8 eighth-resolution fill level for a ramp cell `distance_from_
    core` cells away from the PRIMARY core (0 = adjacent to it) -- 8 (near-
    solid PRIMARY) closest to the core, 0 (near-solid SECONDARY) at the
    outermost cell, the pane edge."""
    fraction = 1.0 - (distance_from_core + 0.5) / ramp_cells
    return max(0, min(8, round(fraction * 8)))


def left_taper_cells(
    ramp_cells: int, primary: tuple[int, int, int], secondary: tuple[int, int, int],
) -> list[tuple[str, tuple[int, int, int], tuple[int, int, int]]]:
    """LEFT-edge taper, `ramp_cells` (glyph, fg, bg) cells in LEFT-TO-RIGHT
    screen order (pane edge -> core) -- eighth-resolution `_LEFT_EIGHTHS`
    glyphs used directly, fg=PRIMARY/bg=SECONDARY, so the row reads as
    folding IN from the left screen edge toward the core (ruling 1):
    near-secondary at column 0, near-primary at the cell touching the
    core."""
    if ramp_cells <= 0:
        return []
    cells = []
    for col in range(ramp_cells):
        distance_from_core = ramp_cells - 1 - col
        k = _taper_k(distance_from_core, ramp_cells)
        if k <= 0:
            cells.append((" ", secondary, secondary))
        elif k >= 8:
            cells.append((" ", primary, primary))
        else:
            cells.append((_LEFT_EIGHTHS[k], primary, secondary))
    return cells


def right_taper_cells(
    ramp_cells: int, primary: tuple[int, int, int], secondary: tuple[int, int, int],
) -> list[tuple[str, tuple[int, int, int], tuple[int, int, int]]]:
    """RIGHT-edge taper, `ramp_cells` (glyph, fg, bg) cells in LEFT-TO-RIGHT
    screen order (core -> pane edge) -- Unicode has no right-quarter block,
    so the mirror is faked the way the operator dictated: the LEFT taper's
    own cell sequence, reversed, with each cell's foreground and background
    swapped (ruling 2: "a right-hand mirror is made by swapping foreground/
    background on a left block")."""
    mirrored = list(reversed(left_taper_cells(ramp_cells, primary, secondary)))
    return [(glyph, bg, fg) for glyph, fg, bg in mirrored]


def core_min_width(text: str) -> int:
    """The core's own minimum width -- `text`'s cell width plus one space
    of padding each side. This is the ONE-sided (unpadded-to-pane) size
    used to decide whether a gradient fits at all; the core itself grows
    past this once it does (see `core_text`)."""
    return _cell_width(text) + 2


def band_gradient_fits(text: str, width: int, ramp_cells: int) -> bool:
    """True once `width` can hold `text`'s own minimum core PLUS a full
    taper of `ramp_cells` on each side. The one on/off switch (ruling 7:
    "no room for the gradient means no gradient; the title is never
    shortened to protect it") -- there is no partial taper, and this never
    feeds back into truncating `text`."""
    return width >= core_min_width(text) + 2 * ramp_cells


def core_text(text: str, core_width: int) -> str:
    """`text`, LEFT-aligned inside `core_width` cells with one leading
    space of padding, truncated with an ellipsis if it can't fit, and
    space-filled on the right to reach `core_width` exactly. The core
    widens with the pane by growing this TRAILING fill, never by
    re-centring or re-padding the text itself -- the text anchors the
    core's own left edge, immediately after the left taper, which is what
    lets the gradient read as folding in from the left toward it (ruling
    1) rather than trailing away from it."""
    if core_width <= 0:
        return ""
    inner_width = max(core_width - 1, 0)
    shown = _truncate(text, inner_width)
    pad = max(core_width - 1 - _cell_width(shown), 0)
    return " " + shown + (" " * pad)

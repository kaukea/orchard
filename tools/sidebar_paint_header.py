"""Paints the per-repo header block: a full-width ramp of gradient cells at
each pane edge, taming PRIMARY down toward SECONDARY, with the PRIMARY
core (the title, centred) filling everything between them -- the core
widens with the pane. `SIDEBAR_HEADER_RAMP_VARIANT` (two-cell/three-cell,
default three) is a temporary A/B knob, read once per call.
"""
from __future__ import annotations

import curses
import os

from sidebar_colour import (  # noqa: E402
    HEADER_FG,
    PAUSED_HEADER_GRAY,
    _CONTRAST_MIN_TEXT,
    _muted_toward,
    _repo_hue,
    colour_ramp_steps,
    ensure_contrast,
    repo_colour_roles,
)
from sidebar_curses_colour import _ColourCache, _safe_addch  # noqa: E402
from sidebar_glyphs import _HEADER_RAMP_IN, _HEADER_RAMP_OUT  # noqa: E402
from sidebar_text import _cell_width, render_header_line  # noqa: E402


# --------------------------------------------------------------------------
# Curses drawing — repo header
#
# FULL-WIDTH BLOCK layout (operator spec, 2026-07-28, reproducing the
# operator's own tmux `window-status-current-format` technique against the
# repo's own hue, restated 2026-07-28 in item 11: "the gradient cells...
# reach the sides of the pane"): `_header_ramp_cells()` gradient cells sit
# at EACH pane edge, taming PRIMARY down toward SECONDARY, with the CORE —
# filled with PRIMARY, the title centred within it — filling everything in
# between. The core therefore WIDENS with the pane; there is no flat
# secondary fill band any more (superseded the earlier fixed-size centred
# core + flat-fill-to-the-edges build, same day). Each ramp cell carries
# TWO interpolated tones at once via a half-block glyph (`▐`/`▌`) — one
# tone as the glyph's foreground (the half nearer the core), the other as
# its background (the half nearer the pane edge) — the same trick that
# lets tmux's own ramp read as more steps than it has cells. "No space for
# gradients, no gradient, easy" (operator, 2026-07-28): the title is NEVER
# shrunk to make room for the ramp — `_header_gradient_fits` is the one
# threshold that decides ramp-or-not, computed from the title's OWN
# untruncated width, never the reverse.
#
# TEMPORARY A/B SWITCH (operator, 2026-07-28: his own dictated "three
# cells" and the tmux reference he pointed at — which spends only TWO
# cells per side and reaches four perceptual steps via the half-block
# trick — are two different builds, and he was never asked to choose
# between them explicitly; he then ruled choices must never be buried in
# prose again). `_header_ramp_cells()` reads `SIDEBAR_HEADER_RAMP_VARIANT`
# so two panes can run side by side differing ONLY in this one knob:
# "two-cell" (the tmux reference's own proportions) or "three-cell" (his
# literal dictation, the default when unset — the closer reading of his
# actual words). A companion sower wires the env var through and shows the
# active variant in the pane title; this module only reads it. Narrow and
# obviously temporary: it exists purely for that A/B and comes back out
# once he picks.
# --------------------------------------------------------------------------

_HEADER_RAMP_VARIANT_ENV = "SIDEBAR_HEADER_RAMP_VARIANT"
_HEADER_RAMP_CELLS_BY_VARIANT = {"two-cell": 2, "three-cell": 3}
_HEADER_RAMP_DEFAULT_VARIANT = "three-cell"


def _header_ramp_cells() -> int:
    """Gradient cells per side, right now — see the A/B switch note above.
    An unrecognised or unset value falls back to the default variant
    rather than raising, the same fail-open rule this file uses
    everywhere else for environment-sourced input."""
    variant = os.environ.get(_HEADER_RAMP_VARIANT_ENV, _HEADER_RAMP_DEFAULT_VARIANT)
    return _HEADER_RAMP_CELLS_BY_VARIANT.get(
        variant, _HEADER_RAMP_CELLS_BY_VARIANT[_HEADER_RAMP_DEFAULT_VARIANT],
    )


def _header_core_width(title: str) -> int:
    """The core's own width — the title's cell width plus one space of
    padding each side — computed independently of the available row width,
    since the title is what decoration yields to, never the reverse."""
    return _cell_width(title) + 2


def _header_gradient_fits(title: str, width: int, ramp_cells: int) -> bool:
    """True once `width` can hold the title's own FULL core plus a FULL
    ramp of `ramp_cells` on each side. This is the one on/off switch
    (operator: "no space for gradients, no gradient, easy") — there is no
    partial ramp and the title is never truncated to manufacture room for
    one."""
    return width >= _header_core_width(title) + 2 * ramp_cells


def _header_ramp_tone(
    steps: list[tuple[int, int, int]], k: int,
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """(inner, outer) tones for ramp cell `k` (0 = adjacent to the core,
    the outermost cell = adjacent to the flat fill) — identical
    mapping on both sides of the core; only the glyph (and so which
    physical half of the cell "inner" lands on) differs between them."""
    return steps[2 * k], steps[2 * k + 1]


def _draw_header(
    stdscr, y: int, width: int, title: str, paused: bool, selected: bool,
    colours: _ColourCache,
) -> None:
    """Per-repo BLOCK header (operator spec, 2026-07-28 — supersedes the
    earlier monotonic left-to-right gradient: "brighter, intense... each
    side a 3 cell gradient to the first fade colour, block layout like the
    window name in the status bar", corrected same day to tame OUTWARD
    from the intense colour rather than highlight inward — see
    `colour_ramp_steps`). PAUSED stays flat light-gray, no gradient, exactly
    as before. `selected` means "the cursor is here AND the user has
    actually moved it" (see `_draw`'s `has_moved`) — A_REVERSE never
    appears merely because `selected == 0` is the resting default.

    The title's "thin" look is still `_muted_toward` (never `curses.A_DIM`,
    see that function's docstring), run through `ensure_contrast` against
    whatever it actually sits on (`PAUSED_HEADER_GRAY` or the primary) —
    the fixed crossover-aware helper, never an assumed black/white or a
    `luminance < 0.5` threshold (that was the bug, see `ensure_contrast`'s
    own docstring). The core's background is uniform, so — unlike the old
    per-column gradient — this is computed ONCE per row, not once per
    column.

    The paused/no-gradient flat branch reserves the row's own literal LAST
    column for background only, via `render_header_line(title, width - 1)`
    (never the title's own trailing glyph): `_safe_addch` blanks whatever
    character lands on that column to a plain space, and a multi-byte
    ellipsis landing there used to vanish silently rather than render (a
    long repo name truncating to "orc" with no "…" at width 4) — the same
    one-column reservation `_step_row_display_text`/`_draw_feature_row`/
    `_draw_task_row` already make. The gradient branch does not need the
    same reservation for its own ramp glyphs: the outermost ramp cell's
    "outer" tone is already exactly `secondary` (`_header_ramp_tone`), and
    now that the ramp reaches the pane edge, THAT outermost cell — not the
    core — is what can land on the last column; if it gets blanked to a
    plain space, what shows through is that same flat secondary tone —
    correct, not merely harmless."""
    reverse = curses.A_REVERSE if selected else 0
    if width <= 0:
        return

    def _draw_flat_block(bg: tuple[int, int, int]) -> None:
        text = render_header_line(title, max(width - 1, 0))
        fg = ensure_contrast(_muted_toward(HEADER_FG, bg), bg, _CONTRAST_MIN_TEXT)
        attr = colours.pair(fg, bg) | reverse
        for col in range(width):
            ch = text[col] if col < len(text) else " "
            _safe_addch(stdscr, y, col, ch, attr)

    if paused:
        _draw_flat_block(PAUSED_HEADER_GRAY)
        return

    hue = _repo_hue(title)
    roles = repo_colour_roles(hue)
    primary, secondary = roles.primary, roles.secondary
    ramp_cells = _header_ramp_cells()

    if not _header_gradient_fits(title, width, ramp_cells):
        _draw_flat_block(primary)
        return

    # FULL WIDTH: the ramp reaches both pane edges and the core fills
    # everything left over — the core WIDENS with the pane instead of a
    # flat secondary fill doing so (item 11's structural change).
    core_width = width - 2 * ramp_cells
    ramp = colour_ramp_steps(primary, secondary, ramp_cells * 2)
    core_text = render_header_line(title, core_width)
    core_fg = ensure_contrast(_muted_toward(HEADER_FG, primary), primary, _CONTRAST_MIN_TEXT)
    core_attr = colours.pair(core_fg, primary) | reverse

    col = 0
    for k in reversed(range(ramp_cells)):
        inner, outer = _header_ramp_tone(ramp, k)
        _safe_addch(stdscr, y, col, _HEADER_RAMP_IN, colours.pair(inner, outer) | reverse)
        col += 1
    for i in range(core_width):
        ch = core_text[i] if i < len(core_text) else " "
        _safe_addch(stdscr, y, col, ch, core_attr)
        col += 1
    for k in range(ramp_cells):
        inner, outer = _header_ramp_tone(ramp, k)
        _safe_addch(stdscr, y, col, _HEADER_RAMP_OUT, colours.pair(inner, outer) | reverse)
        col += 1

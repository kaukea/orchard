"""Paints the per-repo header block: a FULL-WIDTH band whose ends taper
toward the pane edges, with a solid PRIMARY core — the title — filling and
widening with whatever is left between them (`sidebar_band.left_taper_
cells`/`right_taper_cells`/`core_text`). The feature row shares this
identical band geometry (`_draw_edge_taper_row`, exported for
`sidebar_paint_feature` to import), differing only in text colour
(operator, 2026-07-28: "the feature should do exactly the same... but
maybe in a slightly different color for the font while keeping the same
background").
"""
from __future__ import annotations

import curses

from sidebar_band import (  # noqa: E402
    band_gradient_fits,
    core_text,
    header_ramp_cells,
    left_taper_cells,
    right_taper_cells,
)
from sidebar_colour import (  # noqa: E402
    HEADER_FG,
    PAUSED_HEADER_GRAY,
    _CONTRAST_MIN_TEXT,
    _muted_toward,
    _repo_hue,
    ensure_contrast,
    header_emphasis_colour,
    repo_colour_roles,
)
from sidebar_curses_colour import _ColourCache, _safe_addch  # noqa: E402
from sidebar_text import _cell_width, render_header_line  # noqa: E402


# --------------------------------------------------------------------------
# Curses drawing — repo header
#
# EDGE-TAPER BAND layout (operator spec, area A this step — corrects the
# previous "falling block" reading, which had the title's own core sit
# solid at column 0 and fade away to SECONDARY toward the right only: the
# operator identified that as the opposite of what he asked. "The gradient
# should only be on the left. So it looks like it's folding towards the end
# of the screen" means the gradient itself enters FROM the left screen
# edge, growing more intense as it nears the title — restated with more
# resolution the same day: "a longer gradient using more block steps...
# reads as falling away toward the edge of the screen. Both for the
# project and for the feature"). The row is now FULL WIDTH: a taper of
# `header_ramp_cells()` cells sits at EACH pane edge (`sidebar_band.left_
# taper_cells`/`right_taper_cells`, the SIDEBAR_HEADER_RAMP_VARIANT A/B
# switch survives, three cells by default), taming the repo's PRIMARY
# (`repo_colour_roles(hue).primary`, `hue["accent"]`, still resolved
# through the direct-colour terminfo path, never approximated away) down
# toward SECONDARY (`hue["fill"]`) as each taper nears its own edge, with
# the PRIMARY core — the title, left-anchored immediately after the left
# taper — filling and widening with whatever is left in between. No room
# for the full core-plus-both-tapers width means no gradient at all
# (`band_gradient_fits`) — a flat PRIMARY row instead; the title is never
# shortened to protect the gradient. PAUSED stays flat light-gray, no
# gradient, exactly as before.
# --------------------------------------------------------------------------


def _draw_edge_taper_row(
    stdscr, y: int, width: int, text: str,
    primary: tuple[int, int, int], secondary: tuple[int, int, int], text_fg: tuple[int, int, int],
    colours: _ColourCache, extra_attr: int = 0,
) -> None:
    """Shared band painter — the project header and every feature row draw
    through this one function (`sidebar_paint_feature` imports it), so the
    two layouts can never drift apart. Every column gets its own explicit
    `colours.pair(fg, bg)` — no column is ever left to inherit whatever a
    previous row painted (ruling 9). Advances by each character's own
    `_cell_width`, not by one, since the core's own text routinely carries
    two-cell East-Asian-Wide glyphs (`🧩`, `❌`)."""
    if width <= 0:
        return
    ramp_cells = header_ramp_cells()
    core_attr = colours.pair(text_fg, primary) | extra_attr

    if not band_gradient_fits(text, width, ramp_cells):
        rendered = core_text(text, width)
        col = 0
        for ch in rendered:
            if col >= width:
                break
            _safe_addch(stdscr, y, col, ch, core_attr)
            col += _cell_width(ch)
        while col < width:
            _safe_addch(stdscr, y, col, " ", core_attr)
            col += 1
        return

    core_width = width - 2 * ramp_cells
    col = 0
    for glyph, fg, bg in left_taper_cells(ramp_cells, primary, secondary):
        _safe_addch(stdscr, y, col, glyph, colours.pair(fg, bg) | extra_attr)
        col += 1
    core_start = col
    rendered = core_text(text, core_width)
    for ch in rendered:
        if col >= core_start + core_width:
            break
        _safe_addch(stdscr, y, col, ch, core_attr)
        col += _cell_width(ch)
    while col < core_start + core_width:
        _safe_addch(stdscr, y, col, " ", core_attr)
        col += 1
    for glyph, fg, bg in right_taper_cells(ramp_cells, primary, secondary):
        _safe_addch(stdscr, y, col, glyph, colours.pair(fg, bg) | extra_attr)
        col += 1


def _draw_header(
    stdscr, y: int, width: int, title: str, paused: bool, selected: bool,
    colours: _ColourCache,
) -> None:
    """Per-repo header row. `selected` means "the cursor is here AND the
    user has actually moved it" (see `_draw`'s `has_moved`) — A_REVERSE
    never appears merely because `selected == 0` is the resting default.

    The title is the MOST emphasized text in the sidebar, not the least
    (operator ruling, ruling 5, this step and 2026-07-28: "the project is
    rendered as the least readable, least emphasized text of the whole
    sidebar. It makes it hard to see parent child structure" — the
    opposite of what it did before): `header_emphasis_colour` runs `TEXT`
    straight through `ensure_contrast` at the higher `_CONTRAST_MIN_
    CONTENT` floor, never muted toward the background first (`_muted_
    toward` before the contrast check is what produced the original
    defect — a title that cleared the WCAG floor and still measured
    near-zero on APCA against a typical repo accent). PAUSED is a
    separate, unaffected state — flat light-gray, still muted, exactly as
    before (there is nothing to emphasize about a paused repo)."""
    reverse = curses.A_REVERSE if selected else 0
    if width <= 0:
        return

    if paused:
        text = render_header_line(title, max(width - 1, 0))
        fg = ensure_contrast(_muted_toward(HEADER_FG, PAUSED_HEADER_GRAY), PAUSED_HEADER_GRAY, _CONTRAST_MIN_TEXT)
        attr = colours.pair(fg, PAUSED_HEADER_GRAY) | reverse
        for col in range(width):
            ch = text[col] if col < len(text) else " "
            _safe_addch(stdscr, y, col, ch, attr)
        return

    hue = _repo_hue(title)
    roles = repo_colour_roles(hue)
    primary, secondary = roles.primary, roles.secondary
    text_fg = header_emphasis_colour(primary)
    _draw_edge_taper_row(stdscr, y, width, title, primary, secondary, text_fg, colours, reverse)

"""Paints the per-repo header block: a solid PRIMARY core (the title) flush
at the pane's LEFT edge, falling away to SECONDARY toward the right — the
same "falling block" layout the feature row now shares (`sidebar_paint_
shared._draw_falling_block_row`), differing only in text colour (operator,
2026-07-28: "the feature should do exactly the same... but maybe in a
slightly different color for the font while keeping the same background").
"""
from __future__ import annotations

import curses

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
from sidebar_paint_shared import _draw_falling_block_row  # noqa: E402
from sidebar_text import render_header_line  # noqa: E402


# --------------------------------------------------------------------------
# Curses drawing — repo header
#
# FALLING BLOCK layout (operator spec, 2026-07-28, superseding the earlier
# symmetric two/three-cell ramp reaching BOTH pane edges: "the gradient
# should only be on the left. So it looks like it's folding towards the end
# of the screen"; restated the same day with more resolution: "a longer
# gradient using more block steps... reads as falling away toward the edge
# of the screen. Both for the project and for the feature"). The title's
# own core sits solid at column 0 in PRIMARY (`repo_colour_roles(hue).
# primary`, `hue["accent"]`, still resolved through the direct-colour
# terminfo path, never approximated away); everything past it fades to
# SECONDARY (`hue["fill"]`) via `_draw_falling_block_row`'s eighth-
# resolution dithered block ladder — see that function's own docstring for
# the mechanics, shared verbatim with the feature row
# (`sidebar_paint_feature._draw_feature_row`) so the two can never drift
# apart. PAUSED stays flat light-gray, no gradient, exactly as before.
# --------------------------------------------------------------------------


def _draw_header(
    stdscr, y: int, width: int, title: str, paused: bool, selected: bool,
    colours: _ColourCache,
) -> None:
    """Per-repo header row. `selected` means "the cursor is here AND the
    user has actually moved it" (see `_draw`'s `has_moved`) — A_REVERSE
    never appears merely because `selected == 0` is the resting default.

    The title is now the MOST emphasized text in the sidebar, not the
    least (operator ruling, 2026-07-28: "the project is rendered as the
    least readable, least emphasized text of the whole sidebar. It makes
    it hard to see parent child structure" — the opposite of what it did
    before this step): `header_emphasis_colour` runs `TEXT` straight
    through `ensure_contrast` at the higher `_CONTRAST_MIN_CONTENT` floor,
    never muted toward the background first (`_muted_toward` before the
    contrast check is what produced the original defect — a title that
    cleared the WCAG floor and still measured near-zero on APCA against a
    typical repo accent). PAUSED is a separate, unaffected state — flat
    light-gray, still muted, exactly as before (there is nothing to
    emphasize about a paused repo)."""
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
    _draw_falling_block_row(stdscr, y, width, title, primary, secondary, text_fg, colours, reverse)

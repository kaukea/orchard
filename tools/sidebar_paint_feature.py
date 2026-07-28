"""Paints a feature's own row: glyph + name over a full-width dimmer
background band (SECONDARY, `hue["fill"]`) -- the load-bearing signal that
a feature row is NOT a task row (Decision-110), unconditional regardless of
status. Shares its column layout with the plain-text path via
`_feature_row_layout`/`compose_feature_row_text` (sidebar_render_text.py)
so the two can never disagree.
"""
from __future__ import annotations

import curses

from sidebar_colour import (  # noqa: E402
    AMBER,
    FILL_GREEN,
    GREEN,
    MUTED,
    TEXT,
    _CONTRAST_MIN_MARK,
    _CONTRAST_MIN_TEXT,
    _muted_toward,
    _repo_hue,
    ensure_contrast,
)
from sidebar_curses_colour import _ColourCache, _safe_addch  # noqa: E402
from sidebar_glyphs import STATUS_EMOJI  # noqa: E402
from sidebar_paint_shared import _selection_highlight  # noqa: E402
from sidebar_render_text import _feature_row_layout, compose_feature_row_text  # noqa: E402
from sidebar_rows import Row  # noqa: E402
from sidebar_text import _cell_width  # noqa: E402


# --------------------------------------------------------------------------
# Curses drawing — feature row (glyph + name over a full-width dimmer
# background band — no percentage, no per-status partial fill: this band is
# the load-bearing signal that a feature row is NOT a task row, operator
# ruling 2026-07-26, so it runs the row's entire width unconditionally)
# --------------------------------------------------------------------------

# "stale" and "failed" both fall through to MUTED here — MUTED IS the mock's
# gray (retention ruling, 2026-07-25: a stale row renders gray, never
# removed). "failed" has no dedicated RED entry in the mock-canonical
# palette at the top of this file (only GREEN exists for a terminal state);
# its own distinct ❌ glyph — inherently red in every terminal's emoji font —
# is what carries the red signal, same as the pre-existing done/failed glyph
# distinction (never re-derive a colour the mock doesn't define).


def _feature_glyph_colour(status: str | None, accent: tuple[int, int, int]) -> tuple[int, int, int]:
    if status == "done":
        return GREEN
    if status == "working":
        return accent
    return MUTED


def _feature_name_colour(status: str | None) -> tuple[int, int, int]:
    if status == "done":
        return GREEN
    if status == "working":
        return TEXT
    return MUTED


def _feature_fill_colour(status: str | None, hue: dict[str, tuple[int, int, int]]) -> tuple[int, int, int]:
    return FILL_GREEN if status == "done" else hue["fill"]


def _feature_row_cell_styles(
    layout: tuple[str, str, int, str, str], status: str | None, accent: tuple[int, int, int],
    fill_rgb: tuple[int, int, int],
) -> list[tuple[int, int, int]]:
    """[fg_rgb] per character of the row text `_feature_row_layout`
    composes — one entry per column, so the curses painter and
    `compose_feature_row_text` can never disagree on where a segment
    starts. A "muted" look (idle/stale body, the tail/badge) is
    `_muted_toward(colour, fill_rgb)` — never `curses.A_DIM` (see that
    function's docstring for why). Every colour returned is then run
    through `ensure_contrast` against `fill_rgb` (operator hard rule,
    2026-07-27: contrast is calculated, never eyeballed) — muting softens
    a colour toward the band first, as intended, but never past the point
    of actually being readable; `_draw_step_row` already did this and
    `_draw_feature_row` not doing the same was the proximate cause of a
    feature row reading as dark grey-purple text on a dark purple band, at
    the limit of legibility."""
    _glyph, shown_name, pad_width, badge_text, pct_text = layout
    muted_body = status not in ("working", "done")
    glyph_colour = _feature_glyph_colour(status, accent)
    name_colour = _feature_name_colour(status)
    if muted_body:
        glyph_colour = _muted_toward(glyph_colour, fill_rgb)
        name_colour = _muted_toward(name_colour, fill_rgb)
    tail_colour = _muted_toward(MUTED, fill_rgb)
    badge_colour = _muted_toward(AMBER, fill_rgb)
    glyph_colour = ensure_contrast(glyph_colour, fill_rgb, _CONTRAST_MIN_MARK)
    name_colour = ensure_contrast(name_colour, fill_rgb, _CONTRAST_MIN_TEXT)
    tail_colour = ensure_contrast(tail_colour, fill_rgb, _CONTRAST_MIN_MARK)
    badge_colour = ensure_contrast(badge_colour, fill_rgb, _CONTRAST_MIN_MARK)
    return (
        [glyph_colour]
        + [name_colour] * (1 + len(shown_name))
        + [tail_colour] * pad_width
        + [badge_colour] * len(badge_text)
        + [tail_colour] * len(pct_text)
    )


def _draw_feature_row(
    stdscr, y: int, width: int, row: Row, selected: bool, colours: _ColourCache,
) -> None:
    """`selected` swaps in `_selection_highlight` for the row's own band
    colour (sidebar-teamwork defect 4) rather than `curses.A_REVERSE` —
    `_feature_row_cell_styles` already runs every foreground it returns
    through `ensure_contrast` against `fill_rgb`, so substituting the
    lifted band before that call keeps every pair legible automatically.

    Layout is computed against `width - 1`, one short of the row's real
    width (sidebar-teamwork defect (d): a name long enough to need
    `_truncate`'s ellipsis was budgeted the FULL row width, landing that
    ellipsis on the window's own last column — exactly the column
    `_safe_addch`'s `insch` trap silently blanks to a plain space (see its
    docstring), so the cut read as bare with a column to spare. The same
    reservation already governs `_step_row_display_text`; the padding loop
    below still fills the true last column with background, so the band
    still reads edge-to-edge."""
    hue = _repo_hue(row.repo_name)
    status = row.status
    glyph = STATUS_EMOJI.get(status, "○")
    text_width = max(width - 1, 0)
    layout = _feature_row_layout(glyph, row.label, None, text_width, None)
    text = compose_feature_row_text(glyph, row.label, None, text_width)
    fill_rgb = _feature_fill_colour(status, hue)
    if selected:
        fill_rgb = _selection_highlight(fill_rgb)
    styles = _feature_row_cell_styles(layout, status, hue["accent"], fill_rgb)
    # Same tail treatment `_feature_row_cell_styles` already gives its OWN
    # `tail_colour` (`_muted_toward(MUTED, fill_rgb)`, then `ensure_contrast`
    # against the mark floor) -- this is the row's SEPARATE, redundant fill
    # for columns `_feature_row_cell_styles` never laid out at all (past its
    # returned `styles`, and past the composed text out to the pane edge).
    # Left uncontrasted, both fallbacks measured 2.62 resting / 1.36 selected
    # against `FILL_GREEN` (sidebar-teamwork contrast bug, 2026-07-28,
    # captured off real emitted bytes) -- `d249908`'s sweep never saw this
    # because it never covered a column `_feature_row_cell_styles` doesn't
    # itself return a colour for.
    beyond_styles_colour = ensure_contrast(_muted_toward(MUTED, fill_rgb), fill_rgb, _CONTRAST_MIN_MARK)

    attr_extra = curses.A_BOLD if selected else 0
    # `col` (the CHARACTER index into `text`/`styles`) and the true terminal
    # COLUMN are the same number only when every character drawn so far was
    # one cell wide. The status glyph (e.g. `❌`, East-Asian-Wide) is two --
    # writing it at column 0 and then, on the next loop iteration, EXPLICITLY
    # positioning the following space at column 1 (its character index)
    # lands that write on the glyph's own second, already-occupied cell.
    # ncurses does not silently ignore that: it re-flows the row from there,
    # which is what pushed this row's real content one column past the
    # pane's true edge and tripped the terminal's own line-wrap, merging this
    # row with the one below it (sidebar-teamwork defect, live pane capture
    # 2026-07-28, `major-scenarios` fixture, BRAVO-equivalent "Truncation
    # edge cases" — a wrap, not a truncation-rule miss, since the composed
    # string's own cell width was already correctly budgeted at `width - 1`).
    # `cell_col` is the real column, advanced by each character's OWN
    # `_cell_width` rather than by one; `styles`/`text` are still indexed by
    # character position, since `_feature_row_cell_styles` builds one entry
    # per character, not per cell.
    cell_col = 0
    for col, ch in enumerate(text[:width]):
        if cell_col >= width:
            break
        fg = styles[col] if col < len(styles) else beyond_styles_colour
        attr = colours.pair(fg, fill_rgb) | attr_extra
        _safe_addch(stdscr, y, cell_col, ch, attr)
        cell_col += _cell_width(ch)
    # The band covers the FULL row width, including any trailing columns
    # past the composed text (name shorter than the pane) — a feature row
    # reads as a solid band, not a highlighted word.
    for col in range(cell_col, width):
        _safe_addch(stdscr, y, col, " ", colours.pair(beyond_styles_colour, fill_rgb) | attr_extra)

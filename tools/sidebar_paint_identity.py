"""Paints an agent's quote-plus-citation and a subagent's presence-glyph
line, both on the owning open step's FIFTH-toned block background
(`_open_block_bg`) with the shared one-column indent glyph
(`_draw_indent_cell`) marking them as belonging to their task. Content
decisions (tight_line_parts/attribution_text/_quoted_activity) are shared
with the plain-text path via sidebar_citation.py, so the two can never
disagree -- only the per-segment colouring is curses-only here.
"""
from __future__ import annotations

import curses

from sidebar_citation import (  # noqa: E402
    _ATTRIBUTION_INDENT,
    _quoted_activity,
    attribution_text,
    tight_line_parts,
)
from sidebar_colour import (  # noqa: E402
    GREEN,
    MUTED,
    TEXT,
    _CONTRAST_MIN_TEXT,
    ensure_contrast,
    model_tier_colour,
    task_chain_roles,
)
from sidebar_curses_colour import _ColourCache, _safe_addstr  # noqa: E402
from sidebar_glyphs import (  # noqa: E402
    STATUS_EMOJI,
    SUBAGENT_GLYPH,
    _INDENT_WIDTH,
    _SUBAGENT_LIVE_GLYPH,
)
from sidebar_model import TERMINAL_TASK_STATUSES  # noqa: E402
from sidebar_paint_shared import (  # noqa: E402
    _draw_indent_cell,
    _fill_row_bg,
    _open_block_bg,
    _selection_highlight,
)
from sidebar_rows import Row  # noqa: E402
from sidebar_text import _cell_width, _truncate  # noqa: E402


def _draw_identity_block(
    stdscr, y: int, width: int, row: Row, selected: bool, expand: bool, colours: _ColourCache,
    hue: dict[str, tuple[int, int, int]],
) -> int:
    """Draws the agent's quote + subordinate attribution (see
    `identity_block`'s docstring for the exact ladder) — 1 or 2 curses rows
    depending on `expand`; returns the next unused y. Shares its content
    decisions (`attribution_text`/`tight_line_parts`) with the pure text
    path so the two can never disagree; only the per-segment colouring
    (quote plain ITALIC, role dim-italic, model tier-coloured) is
    curses-only. The owning step's open-block colour (`_open_block_bg`,
    FIFTH) is painted across the FULL row width first, then every
    foreground colour is contrast-checked against it (operator ruling,
    2026-07-26: legible text on the dimmed background is a hard
    requirement, achieved by adjusting the foreground, never by dimming
    the content itself — so the role/model text below drops its old
    A_DIM attribute in favour of an explicitly contrast-safe colour).
    `selected` swaps in `_selection_highlight` for the block's own
    background (sidebar-teamwork defect 4) rather than `curses.A_REVERSE`
    — always painted, even when this row had no open-block background of
    its own, so the pick is unmistakable whatever row kind it lands on.
    The one-column indent glyph (THIRD on FOURTH, `_draw_indent_cell`)
    marks this row as belonging to its task; content starts one column in."""
    bg = _open_block_bg(row)
    if selected:
        bg = _selection_highlight(bg)
    roles = task_chain_roles(hue, row.feature_colour)
    fourth = _selection_highlight(roles.fourth) if selected else roles.fourth
    content_width = max(width - _INDENT_WIDTH, 0)
    attr_extra = curses.A_BOLD if selected else 0
    block_bg = bg if bg is not None else (0, 0, 0)
    quote_fg = ensure_contrast(TEXT, block_bg, _CONTRAST_MIN_TEXT)
    role_fg = ensure_contrast(MUTED, block_bg, _CONTRAST_MIN_TEXT)

    if bg is not None:
        _fill_row_bg(stdscr, y, width, bg, colours)
        if expand:
            _fill_row_bg(stdscr, y + 1, width, bg, colours)
    _draw_indent_cell(stdscr, y, colours, roles.third, fourth)

    if not expand:
        shown_quote, tail = tight_line_parts(row.activity, row.role, content_width, row.model)
        _safe_addstr(stdscr, y, _INDENT_WIDTH, _truncate(shown_quote, content_width),
                     colours.pair(quote_fg, bg, italic=True) | attr_extra)
        if tail:
            x = _INDENT_WIDTH + _cell_width(shown_quote)
            _safe_addstr(stdscr, y, x, _truncate(tail, max(width - x, 0)),
                         colours.pair(role_fg, bg, italic=True) | attr_extra)
        return y + 1

    quote = _quoted_activity(row.activity)
    _safe_addstr(stdscr, y, _INDENT_WIDTH, _truncate(quote, content_width),
                 colours.pair(quote_fg, bg, italic=True) | attr_extra)
    if not row.role:
        return y + 1
    y += 1
    _draw_indent_cell(stdscr, y, colours, roles.third, fourth)
    # No dash on this rung (operator, 2026-07-28: "the citation is just
    # below the text itself either right alined or indented by a few
    # blans, no ash obviuouys") — indented, chosen over right-aligned
    # because `_ATTRIBUTION_INDENT` already existed for exactly this.
    attribution_width = max(content_width - len(_ATTRIBUTION_INDENT), 0)
    role_text, model_text = attribution_text(row.role, row.model, attribution_width)
    x = _INDENT_WIDTH + len(_ATTRIBUTION_INDENT)
    _safe_addstr(stdscr, y, x, role_text, colours.pair(role_fg, bg, italic=True) | attr_extra)
    x += _cell_width(role_text)
    if model_text:
        sep = " · "
        _safe_addstr(stdscr, y, x, sep, colours.pair(role_fg, bg) | attr_extra)
        x += len(sep)
        model_fg = ensure_contrast(model_tier_colour(row.model), block_bg, _CONTRAST_MIN_TEXT)
        _safe_addstr(stdscr, y, x, model_text, colours.pair(model_fg, bg, italic=True) | attr_extra)
    return y + 1

_SUBAGENT_TERMINAL_FG = {"done": GREEN, "failed": MUTED}


def _draw_subagent_row(
    stdscr, y: int, width: int, row: Row, selected: bool, colours: _ColourCache,
    hue: dict[str, tuple[int, int, int]],
) -> int:
    """A subagent's own line — presence glyph (`_row_text`'s existing
    scheduled/doing/done/failed vocabulary) + label, on the owning step's
    open-block background (see `_draw_identity_block`'s docstring for why),
    full width, contrast-checked. `selected` swaps in `_selection_highlight`
    for the block's own background (sidebar-teamwork defect 4), same as
    `_draw_identity_block`. Carries the same one-column indent glyph
    (THIRD on FOURTH) as every other row related to this task."""
    bg = _open_block_bg(row)
    if selected:
        bg = _selection_highlight(bg)
    roles = task_chain_roles(hue, row.feature_colour)
    fourth = _selection_highlight(roles.fourth) if selected else roles.fourth
    block_bg = bg if bg is not None else (0, 0, 0)
    fg = ensure_contrast(
        _SUBAGENT_TERMINAL_FG.get(row.status, TEXT), block_bg, _CONTRAST_MIN_TEXT,
    )
    attr_extra = curses.A_BOLD if selected else 0
    if bg is not None:
        _fill_row_bg(stdscr, y, width, bg, colours)
    _draw_indent_cell(stdscr, y, colours, roles.third, fourth)
    glyph = (STATUS_EMOJI[row.status] if row.status in TERMINAL_TASK_STATUSES
             else _SUBAGENT_LIVE_GLYPH.get(row.status, SUBAGENT_GLYPH))
    text = _truncate(f"{glyph} {row.label}", max(width - _INDENT_WIDTH, 0))
    _safe_addstr(stdscr, y, _INDENT_WIDTH, text, colours.pair(fg, bg) | attr_extra)
    return y + 1

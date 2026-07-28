"""Paints a feature's own row: shares the header's "falling block" layout
verbatim (`sidebar_paint_shared._draw_falling_block_row`) — the SAME
PRIMARY-core/SECONDARY-fade background as the repo header above it, differing
only in font colour (operator, 2026-07-28: "the feature should do exactly
the same, but maybe in a slightly different color for the font while
keeping the same background we chose for the project... That shared
background is deliberate: it is what ties feature to project visually, and
the font colour is what separates them. Do not give the feature row its own
background family"). A DONE feature keeps its own separate flat green band
(unchanged by this step — not part of the falling-block instruction).
"""
from __future__ import annotations

import curses

from sidebar_colour import (  # noqa: E402
    FILL_GREEN,
    GREEN,
    _CONTRAST_MIN_TEXT,
    _repo_hue,
    ensure_contrast,
    feature_emphasis_colour,
    repo_colour_roles,
)
from sidebar_curses_colour import _ColourCache, _safe_addch  # noqa: E402
from sidebar_glyphs import SPINNER_FRAMES, STATUS_EMOJI  # noqa: E402
from sidebar_paint_shared import _draw_falling_block_row, _selection_highlight  # noqa: E402
from sidebar_rows import Row  # noqa: E402
from sidebar_text import _truncate  # noqa: E402


def _feature_row_glyph(status: str | None, tick: int) -> str:
    """The feature row's own status glyph — CYCLING while `status ==
    "working"` (operator ruling, 2026-07-28: "the spinner doesn't spin" —
    `STATUS_EMOJI["working"]` was hardcoded to a single fixed `SPINNER_
    FRAMES` frame everywhere it was drawn; the task row already threads
    `tick` through for this, see `_task_row_glyph` — this row gets the
    same fix). Every other status keeps its existing static glyph. Curses-
    only, same split as `_task_row_glyph`: the plain-text/`--dump` path
    (`compose_feature_row_text`/`render_lines`) keeps the static frame, so
    a repeated `render_lines` call stays byte-identical."""
    if status == "working":
        return SPINNER_FRAMES[tick % len(SPINNER_FRAMES)]
    return STATUS_EMOJI.get(status, "○")


def _draw_feature_row(
    stdscr, y: int, width: int, row: Row, selected: bool, colours: _ColourCache, tick: int = 0,
) -> None:
    """A feature's own row. Content is `{glyph} {label}` — `label` already
    carries the `ƒ` identity prefix (operator, 2026-07-28: "the feature
    name could start with the f function emoji to mirror the f slash we
    usually use for branch names", applied once at the model layer in
    `sidebar_rows._feature_rows` so the plain-text and curses paths can
    never disagree on it).

    DONE is the one status that still gets its own separate flat band
    (`FILL_GREEN`, unchanged by this step — this branch predates and is
    orthogonal to the falling-block redesign, and nothing in the new
    instructions touches it). Every other status shares the repo header's
    own PRIMARY/SECONDARY falling block verbatim — `feature_emphasis_
    colour` is the "slightly different" font colour that ties this row to
    its header while still telling the two apart.

    `selected` lifts PRIMARY/SECONDARY toward white (`_selection_
    highlight`, Decision-111 — never `curses.A_REVERSE`) paired with
    `curses.A_BOLD`, same pattern as every other row painter in this
    file's own package."""
    hue = _repo_hue(row.repo_name)
    status = row.status
    glyph = _feature_row_glyph(status, tick)
    content = f"{glyph} {row.label}"
    attr_extra = curses.A_BOLD if selected else 0

    if status == "done":
        fill_rgb = _selection_highlight(FILL_GREEN) if selected else FILL_GREEN
        text_fg = ensure_contrast(GREEN, fill_rgb, _CONTRAST_MIN_TEXT)
        text = _truncate(content, max(width - 1, 0))
        attr = colours.pair(text_fg, fill_rgb) | attr_extra
        for col in range(width):
            ch = text[col] if col < len(text) else " "
            _safe_addch(stdscr, y, col, ch, attr)
        return

    roles = repo_colour_roles(hue)
    primary, secondary = roles.primary, roles.secondary
    if selected:
        primary = _selection_highlight(primary)
        secondary = _selection_highlight(secondary)
    text_fg = feature_emphasis_colour(primary)
    _draw_falling_block_row(stdscr, y, width, content, primary, secondary, text_fg, colours, attr_extra)

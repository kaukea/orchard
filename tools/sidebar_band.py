"""Triangular-wave sweep and fill-bar column geometry -- pure integer/RGB
math, no curses, no Row. `band_position`/`band_span` still drive the
accordion's live KITT sweep (`_draw_step_row`); `fill_cols`/`band_travel_
end`/`progress_column_colour`/`lifted_fill_colour`/`band_column_colour` were
the feature row's own percentage-driven partial fill, superseded 2026-07-26
by its unconditional full-width band, but kept defined and tested rather
than deleted -- the geometry is exactly reusable if a percentage-driven
fill is ever wanted again.
"""
from __future__ import annotations

from sidebar_colour import WHITE, lerp  # noqa: E402


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

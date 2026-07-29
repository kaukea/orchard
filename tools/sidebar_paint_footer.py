"""Paints a repo's own FOOTER — the block's LAST section (spec §3's `age⏱
vs worked + tokens⚡/dollars` grammar): drawn once, right after every row
belonging to that repo has already been drawn (`sidebar_paint._draw`
detects the repo boundary and calls `_draw_repo_footer` there), never as
its own `Row` — `sidebar_render_text.footer_lines()` stays the single
source of the actual text, so the curses path and the headless
`render_lines()` path can never disagree on its wording, only on whether
it currently has a live caller.

Same conventions as every other painter in this package: OWN background
(the repo's own SECONDARY/fill tone — the same band a terminal task row
already falls back to, `_draw_task_row`'s `hue["fill"]`), and a contrast
floor via `ensure_contrast` at the plain-TEXT threshold (this is body text,
not a mark). Never selectable — a summary line, not a navigation target,
same footing as the dead-space fill it sits just above.

Deliberately does NOT reach the window's true last column, unlike every
other full-width row in this package (`_fill_row_bg`/`_draw_task_row`'s own
`_safe_addch` reservation there). Empirically bisected, 2026-07-29: this
row sits immediately above the dead-space fill (`sidebar_paint._draw`), and
painting its own last column with a DIFFERENT colour pair right before that
fill begins reproduced the exact corruption `sidebar_curses_colour.
_safe_addch`'s own docstring already documents for the plain-`addstr`
case — except here even the documented `insch` mitigation did not prevent
it (no full-width row before this one ever sat directly above the
dead-space fill with a colour-pair change at the boundary, so that
combination was never exercised). Leaving the last column alone here — it
stays whatever `stdscr.erase()` left it, painted over by the very next
thing drawn there — costs one unpainted corner cell against a whole-screen
corruption; not itself a ruling, this function's own implementer choice,
flagged rather than asserted as a general fix.
"""
from __future__ import annotations

from sidebar_colour import TEXT, _CONTRAST_MIN_TEXT, ensure_contrast, repo_colour_roles  # noqa: E402
from sidebar_curses_colour import _ColourCache, _safe_addstr  # noqa: E402
from sidebar_model import Repo  # noqa: E402
from sidebar_render_text import footer_lines  # noqa: E402
from sidebar_text import _cell_width, _truncate  # noqa: E402


def _draw_repo_footer(
    stdscr, y: int, width: int, repo: Repo, colours: _ColourCache,
    hue: dict[str, tuple[int, int, int]],
) -> int:
    """Draws `footer_lines(repo)` starting at `y`, one physical line each,
    and returns the next free `y` — unchanged when `footer_lines` has
    nothing to show (a repo with no age/worked/tokens data at all, e.g. one
    with no live or marker-derived agent record yet)."""
    lines = footer_lines(repo)
    if not lines:
        return y
    bg = repo_colour_roles(hue).secondary
    text_fg = ensure_contrast(TEXT, bg, _CONTRAST_MIN_TEXT)
    attr = colours.pair(text_fg, bg)
    # One column short of the true edge (see module docstring) — never the
    # usual `_safe_addch` last-column reservation other full-width rows use.
    text_width = max(width - 1, 0)
    for line in lines:
        body = _truncate(line, text_width)
        body += " " * max(text_width - _cell_width(body), 0)
        _safe_addstr(stdscr, y, 0, body, attr)
        y += 1
    return y

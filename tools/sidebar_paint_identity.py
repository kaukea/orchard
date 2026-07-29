"""Paints an agent's quote-plus-citation and a subagent's presence-glyph
line, both on the owning open step's own block background (`_open_block_bg`
-- FOURTH, the SAME tone as the step's own title, operator ruling
2026-07-28: "the background colour of the currently active items inside a
stage is the same colour as the titles of the stages themselves", so
nothing here is a separately-derived FIFTH tone any more) with the shared
one-column indent glyph (`_draw_indent_cell`, the task's own carrying
colour -- the gutter, operator ruling 2026-07-28) marking them as belonging
to their task. Content decisions (tight_line_parts/attribution_text/
_quoted_activity) are shared with the plain-text path via
sidebar_citation.py, so the two can never disagree -- only the per-segment
colouring is curses-only here.
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
    ACTIVITY_ACCENT,
    MUTED,
    TEXT,
    _CONTRAST_MIN_CONTENT,
    ensure_contrast,
    model_tier_colour,
    task_chain_roles,
)
from sidebar_curses_colour import _ColourCache, _safe_addstr  # noqa: E402
from sidebar_glyphs import (  # noqa: E402
    SUBAGENT_GLYPH,
    _INDENT_WIDTH,
    _SUBAGENT_LIVE_GLYPH,
)
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
    hue: dict[str, tuple[int, int, int]], align: str = "indent",
) -> int:
    """Draws the agent's quote + subordinate attribution (see
    `identity_block`'s docstring for the exact ladder) — 1 or 2 curses rows
    depending on `expand`; returns the next unused y. Shares its content
    decisions (`attribution_text`/`tight_line_parts`) with the pure text
    path so the two can never disagree; only the per-segment colouring is
    curses-only.

    The quote is told apart from its surrounding step titles by HUE, not
    by style (operator ruling, 2026-07-28, choosing between four shown
    treatments: a distinct accent colour, plain — NOT italic, and NOT the
    same colour as the body text). A quote in plain `TEXT` — what an
    earlier fix did in the course of raising step-content contrast — reads
    as legible but loses the one thing that marked it as a different KIND
    of line from the stage names around it; italic recovers that
    distinction without a second colour to learn, but he ruled it out
    directly. `ACTIVITY_ACCENT` is the accent this settles on. The role/
    model attribution stays MUTED, plain (never italic either, same
    ruling). The owning step's open-block colour (`_open_block_bg`,
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
    The one-column indent glyph (the task's own gutter colour on FOURTH,
    `_draw_indent_cell`) marks this row as belonging to its task; content
    starts one column in.

    The quote drops its accent for MUTED when `row.status == "stale"`
    (operator ruling, 2026-07-29, Decision-094 — "staleness is a colour,
    not a removal"): DIAGNOSIS, same shape as `_draw_task_row`'s own —
    DISCARDED, not missing. `row.status` already carries "stale" all the
    way from `Agent.status` (sidebar_model.py's `_status_for`) through
    `Row.status` (sidebar_rows.py's `_agent_row` passes it through
    unchanged); this function simply never consulted it for colour before
    this step, so a stale agent's activity line read exactly as vivid as
    a live one. `role_fg` needs no equivalent change — it is already
    MUTED for every status.

    `align` ("indent", the default, or "right") picks which of `identity_
    block`'s two NORMAL-layout citation rungs this curses draw mirrors
    (operator ruling, 2026-07-29: both built for a real A/B, not just the
    indented rung a prior step settled on unilaterally) — affects only the
    `expand` branch's second line; the tight (non-`expand`) rung is
    unaffected, same as the plain-text `identity_block`."""
    bg = _open_block_bg(row, hue)
    if selected:
        bg = _selection_highlight(bg)
    roles = task_chain_roles(hue, row.feature_colour)
    fourth = _selection_highlight(roles.fourth) if selected else roles.fourth
    gutter = row.task_colour or roles.third
    content_width = max(width - _INDENT_WIDTH, 0)
    attr_extra = curses.A_BOLD if selected else 0
    block_bg = bg if bg is not None else (0, 0, 0)
    # `_CONTRAST_MIN_CONTENT` (7.0), not the step title's `_CONTRAST_MIN_
    # TEXT` (4.5, left untouched — operator ruling, 2026-07-28, "the title
    # is absolutely fine for contrast... the content of step" is what is
    # not): this is a step's own CONTENT.
    quote_source = MUTED if row.status == "stale" else ACTIVITY_ACCENT
    quote_fg = ensure_contrast(quote_source, block_bg, _CONTRAST_MIN_CONTENT)
    role_fg = ensure_contrast(MUTED, block_bg, _CONTRAST_MIN_CONTENT)

    if bg is not None:
        _fill_row_bg(stdscr, y, width, bg, colours)
        if expand:
            _fill_row_bg(stdscr, y + 1, width, bg, colours)
    _draw_indent_cell(stdscr, y, colours, gutter, fourth)

    if not expand:
        shown_quote, tail = tight_line_parts(row.activity, row.role, content_width, row.model)
        _safe_addstr(stdscr, y, _INDENT_WIDTH, _truncate(shown_quote, content_width),
                     colours.pair(quote_fg, bg) | attr_extra)
        if tail:
            x = _INDENT_WIDTH + _cell_width(shown_quote)
            _safe_addstr(stdscr, y, x, _truncate(tail, max(width - x, 0)),
                         colours.pair(role_fg, bg) | attr_extra)
        return y + 1

    quote = _quoted_activity(row.activity)
    _safe_addstr(stdscr, y, _INDENT_WIDTH, _truncate(quote, content_width),
                 colours.pair(quote_fg, bg) | attr_extra)
    if not row.role:
        return y + 1
    y += 1
    _draw_indent_cell(stdscr, y, colours, gutter, fourth)
    # No dash on this rung (operator, 2026-07-28: "the citation is just
    # below the text itself either right alined or indented by a few
    # blans, no ash obviuouys") — indented, chosen over right-aligned
    # because `_ATTRIBUTION_INDENT` already existed for exactly this.
    attribution_width = max(content_width - len(_ATTRIBUTION_INDENT), 0)
    role_text, model_text = attribution_text(row.role, row.model, attribution_width)
    x = _INDENT_WIDTH + len(_ATTRIBUTION_INDENT)
    _safe_addstr(stdscr, y, x, role_text, colours.pair(role_fg, bg) | attr_extra)
    x += _cell_width(role_text)
    if model_text:
        sep = " · "
        _safe_addstr(stdscr, y, x, sep, colours.pair(role_fg, bg) | attr_extra)
        x += len(sep)
        model_fg = ensure_contrast(model_tier_colour(row.model), block_bg, _CONTRAST_MIN_CONTENT)
        _safe_addstr(stdscr, y, x, model_text, colours.pair(model_fg, bg) | attr_extra)
    return y + 1

def _subagent_glyph(status: str | None, tick: int) -> str:
    """The subagent's own THREE-state presence glyph (operator ruling,
    2026-07-29: bubble glyphs belong to subagents ALONE — this is the one
    row kind that legitimately carries one): empty (`_SUBAGENT_LIVE_GLYPH
    ["scheduled"]`, "○") for "scheduled", BLINKING for "doing" (running),
    full (`SUBAGENT_GLYPH`, "●") for "done" (closed) — Decision-109's own
    exactly-scheduled/doing/done vocabulary, nothing borrowed from the
    task row's six-state `STATUS_EMOJI` (a subagent never carries "failed"
    at all). Blinking rides the SAME `tick` the spinner already advances
    on (operator: "the blink can ride the same tick the spinner uses") —
    alternating full/blank on tick parity, never full/empty, so a running
    subagent's blink is never momentarily confusable with a DIFFERENT
    subagent's still "scheduled" (empty) row. An unrecognized status
    (defensive only — Decision-109 leaves no fourth value) falls to the
    same "full" rung "done" uses, never back to a bubble borrowed from
    elsewhere."""
    if status == "scheduled":
        return _SUBAGENT_LIVE_GLYPH.get("scheduled", "○")
    if status == "doing":
        return SUBAGENT_GLYPH if tick % 2 == 0 else " "
    return SUBAGENT_GLYPH


def _draw_subagent_row(
    stdscr, y: int, width: int, row: Row, selected: bool, colours: _ColourCache,
    hue: dict[str, tuple[int, int, int]], tick: int = 0,
) -> int:
    """A subagent's own line — presence glyph (`_subagent_glyph`'s own
    empty/blinking/full three states) + label, on the owning step's
    open-block background (see `_draw_identity_block`'s docstring for why),
    full width, contrast-checked at `_CONTRAST_MIN_CONTENT` (this is a
    step's own content, same as the identity block above it). `selected`
    swaps in `_selection_highlight` for the block's own background
    (sidebar-teamwork defect 4), same as `_draw_identity_block`. Carries the
    same one-column indent glyph (the task's own gutter colour on FOURTH)
    as every other row related to this task.

    PLACEMENT (operator, 2026-07-29): this row sits beneath its owning
    agent's own identity-line row, which itself sits beneath its task —
    never injected between the five step rows. That nesting is
    `sidebar_rows.py`'s own job (`_agent_and_subagent_rows`/`_task_rows`),
    not this function's — this painter only ever draws whatever Row it is
    handed, at the y its caller (`sidebar_paint.py`'s dispatch loop)
    already placed it at. Verified empirically for this step (see
    `tests/test_sidebar_area_cd.py`'s `SubagentPlacementTests`): a fleet
    built directly from `Agent(subagents=[...])` flattens the subagent row
    immediately after its agent's row, both one depth below their step's
    own accordion row.

    `tick` (default 0, so an existing caller that has not been updated to
    thread a real one still renders — it simply never blinks) is
    `_subagent_glyph`'s own animation clock, threaded the same way
    `_draw_task_row`/`_draw_feature_row` already thread it for their own
    cycling spinners.

    ONE foreground colour regardless of `row.status` (operator ruling,
    2026-07-28: "because there's already a checkbox or checkmark, there is
    no reason to have a blue and a green... to avoid colours just bleeding
    everywhere" — restated 2026-07-28 as "the difference between a green
    and a white, even on an OLED screen at very high brightness, I can
    barely tell"). This row used to swap to GREEN for `done` and MUTED for
    `failed`, a distinction its own glyph already carries in full — the
    colour swap was pure redundant encoding of a state the glyph already
    names, and green-vs-white was precisely the pair he could not
    distinguish. No information is lost: status still reads off the glyph,
    unambiguously, for every state."""
    bg = _open_block_bg(row, hue)
    if selected:
        bg = _selection_highlight(bg)
    roles = task_chain_roles(hue, row.feature_colour)
    fourth = _selection_highlight(roles.fourth) if selected else roles.fourth
    gutter = row.task_colour or roles.third
    block_bg = bg if bg is not None else (0, 0, 0)
    fg = ensure_contrast(TEXT, block_bg, _CONTRAST_MIN_CONTENT)
    attr_extra = curses.A_BOLD if selected else 0
    if bg is not None:
        _fill_row_bg(stdscr, y, width, bg, colours)
    _draw_indent_cell(stdscr, y, colours, gutter, fourth)
    glyph = _subagent_glyph(row.status, tick)
    text = _truncate(f"{glyph} {row.label}", max(width - _INDENT_WIDTH, 0))
    _safe_addstr(stdscr, y, _INDENT_WIDTH, text, colours.pair(fg, bg) | attr_extra)
    return y + 1

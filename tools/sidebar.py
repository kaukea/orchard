#!/usr/bin/env python3
"""Curses fleet sidebar — reads the fleet model, renders it, navigates via
sidebar_nav. The ONLY sidebar (bus-finishing): the old courier-inbox reader
and the plain-text prototype reader (tools/sidebar_v3.py) are both retired.

The MODEL layer — data classes, event folding, registry reading, tree
assembly (`build_model()`/`watch()`) — lives in `tools/sidebar_model.py`
and is owned by that module's own docstring, which is the specification to
read first. This module owns everything downstream of a `Fleet`: the
pure-text Row/render pipeline (`flatten()`/`render_lines()`) and the curses
draw layer, plus the CLI.

SEVEN-LEVEL HIERARCHY (Decision-105, 2026-07-26 — supersedes the earlier
three-level repo/feature/subagent model, which minted one Feature row PER
SESSION and could draw one feature twice; area/component are the taxonomy
context the renderer doesn't itself draw a row for): project (repo header)
-> feature -> task -> step -> agent -> subagent.

  - A SESSION IS NOT A ROW: an agent is identified by the triple
    `(session_id, parent, agent_name)`, never by session id alone — see
    `sidebar_model.py`'s module docstring for why. Two agents on the same
    feature/task fold into ONE Feature/Task, each carrying a LIST of agents
    (`Step.agents`) — never a single-slot field.
  - THE ACTIVE STEP IS DERIVED CLIENT-SIDE from each agent's own announced
    role, via `resolve_step()`/`load_role_step_map()` — nothing on the bus
    ever names a step. The map is a FALLBACK only (an explicit `phase` on a
    record would win, were one ever posted) and FAILS OPEN: a missing or
    unmapped role still renders, just without a step (`Task.
    unstepped_agents`). A task's five steps render as FIVE LINES, the
    ACCORDION (`_step_row`, always small caps) — a collapse keeps its own
    line rather than folding into the previous one (operator correction,
    2026-07-26: "collapse keeps the line, it doesn't go to the previous
    one"), so done/todo steps each stay a single bare line and only the
    currently active step's agents (and their subagents) nest beneath it,
    one level deeper.
  - AN AGENT WITH EVENTS ALWAYS RENDERS SOMETHING (operator ruling,
    2026-07-26): missing identity, unknown/unmapped role, absent feature or
    task — none of these drop an agent or orphan the subagents registered
    under it. The repo header comes from whichever ONE agent is
    identifiable as the root — an explicit `agent: "gardener"` identity, or
    failing that the root of the parent chain (a session named as some
    other session's `parent` that names no parent of its own — covers a
    resumed root session, which can no longer announce its own role). That
    one session is excluded from the feature/task loop so it never also
    draws a duplicate row for itself; every other agent does. The COURIER
    is never an agent, whatever session it rides (operator ruling,
    2026-07-27) — see `sidebar_model.py`.
  - THREE COLLAPSES, nothing else is ever hidden: a TASK folds to one row
    once it reaches a terminal state (done/failed — `TERMINAL_TASK_
    STATUSES`); a FEATURE folds to one row once ALL its tasks are done — a
    single failed or still-open task holds it expanded.
  - REVIVAL: a TASK is terminal and never reopened (new work is a new
    task); a FEATURE is neither terminal nor idempotent — a new task
    revives a collapsed feature, and its completed sibling tasks come back
    alongside it (see `_combine_status`, `flatten`).
  - SUBAGENTS carry no model, no status text, no identity of their own —
    a label plus exactly one of three states (scheduled/doing/done, ALL
    three rendered — a pending "scheduled" bubble is never omitted),
    sourced from `orchard:agent:delegation:schedule/begin/end` and hung
    under the STEP their parent agent is on (registered under the parent's
    session id). Live-only; they fold away with their task.

PRESENTATION IS "VERY COMPACT FORM" BY DEFAULT (operator ruling, 2026-07-26,
supersedes an earlier, roomier draft): 2 columns of indent per tree level
(`INDENT_UNIT`); an agent's identity renders as a quote with its role riding
the SAME line by default (`identity_block`'s "tight" rung) — the quote
NEVER drops, and now nor does the role once it has any: the ACTIVITY text is
what shrinks first (ellipsised) to make room for it (`tight_line_parts`),
role/model still degrade before a second line is ever spent (see
`_agent_expansion_fits`); a task row's progress is a single right-aligned
quarter-fill circle (`_task_progress_glyph`, `○ ◔ ◑ ◕ ●` for 0-4 of 5 steps
done — 5-of-5 is a terminal task and collapses instead), never a column-
hungry percentage — the numeric-percentage variant stays deliberately
unbuilt (operator ruling, 2026-07-26: "the circle is unconditional") — and
the task NAME is what ellipsises under width pressure, never the circle. A
FEATURE carries no percentage of its own any more either (progress is the
task's alone) — its own row is instead set apart from a task's by a
full-width dimmer background band (curses-only, `_draw_feature_row`), which
is the load-bearing fix for a feature and its sole same-named task
otherwise reading as identical text; that same task row also drops its own
name when it is the feature's only task and shares its exact name, showing
its progress circle and accordion instead of repeating the string.

NOT ported (no source in the new event grammar — orchard_topic.py's `post`
verbs are lifecycle/status/delegation/outcome/task only — so nothing below
fabricates a value for them): courier rows (the old model's collapsed
inbox-sidecar row — the new grammar has no announce/inbox concept to
collapse into one); open questions/question badges (routed through the
`:session:operator` broker instead); tokens/dollars/age/worked (the
`footer_lines()`/`done_footer_line()` formatters that would show them stay
defined and tested, but build_model() never populates a source for them).

Presentation is deliberately split from curses: `flatten()` turns a Fleet
into a flat list of Row objects, and `render_lines()` turns those into plain
text with NO curses calls at all — that pure function is what tests assert
on. The curses app (`main`, run through `curses.wrapper`) is a thin loop that
polls a background `watch()` thread and draws each line with its status
colour.

VISUAL CONTRACT (bus-message-specifying B5, operator-approved, non-
negotiable — SUPERSEDES the older sidebar-titling glyph/colour vocabulary):
the mock at `.git/the-works/bus-message-specifying/sidebar-mock.py` and its
blessed `approved-frame.ans` are the source of truth for every glyph, RGB
constant, spacing and animation rule below. Every constant named after the
mock (REPO_HUES, MODEL_TIERS, HEADER_FG/TEXT/MUTED/GREEN/GREEN_SOFT/AMBER/
FILL_GREEN, PHASES, ROLE_EMOJI, LOCATION_BADGES, NBSP) is copied from it
verbatim, not re-derived.

The project header is a FULL-WIDTH BLOCK (operator spec, 2026-07-28,
superseding the earlier monotonic left-to-right gradient, then again the
same day's centred-badge build once the ramp was corrected to reach the
pane edges): `_header_ramp_cells()` cells of gradient sit at EACH pane
edge (a temporary A/B knob, see `_draw_header`'s own comment) taming the
repo's PRIMARY colour (`repo_colour_roles(hue).primary`, i.e.
`hue["accent"]`, still resolved through the direct-colour terminfo path,
never approximated away) down toward SECONDARY (`hue["fill"]`), mirrored,
with the PRIMARY-filled core — the title, centred, one space of padding
each side at minimum — filling everything left over, so the core WIDENS
with the pane rather than a flat fill band doing so. No new palette,
every tone is built from the triple the repo already owns (see
`_draw_header`). The title is never shrunk to make room for the ramp: a
pane too narrow for the full title AND the full ramp drops the ramp
entirely and renders a flat primary block instead.

PRIMARY and SECONDARY are the first two links of a five-role chain
(operator ruling, 2026-07-28, verbatim: "primay -> gradient -> secondary.
we reuse that later for ownership tracking" then "from the SECONDARY we
derive a THIRD... FOURTH... FIFTH"), named and derived in exactly one
place (`repo_colour_roles`/`task_chain_roles`) so a later ownership-
tracking feature can reuse it: PRIMARY is the header core; SECONDARY is
where the ramp lands, and unconditionally IS the feature row's own
full-width dimmer background band (`hue["fill"]`, every feature row, any
status — what makes a feature visibly not a task, see
`_draw_feature_row`); THIRD is the task row's own background and the
one-column INDENT glyph's foreground; FOURTH is the indent glyph's
background and every step row's own background; FIFTH is the open-stage
block's background exactly as it already was (`open_stage_colour`,
per-task, unchanged by this chain). The indent — one column, a left
half-block glyph, THIRD on FOURTH — is what marks every step/agent/
subagent row as belonging to its task, replacing a plain blank-space
indent. Whether THIRD/FOURTH root at the REPO's own hue (one chain per
repo, the default) or re-root per FEATURE is `SIDEBAR_COLOUR_SCOPE`
(`repo`/`feature`, unresolved by the operator — both are built, neither is
picked, see `task_chain_roles`). The accordion's ACTIVE step
carries the KITT sweep — a bright cell with a two-column fading tail,
sweeping the same bidirectional triangular wave (`band_position`/
`band_span`, reused from the pre-existing lifted-band geometry) across a
small fixed-width dot strip beside its label (`_draw_step_row`) — the
liveness signal for "this is the step actually moving right now". Known
licensed deviation (recorded debt): true per-pixel gradient fade on the
KITT core, beyond the 3-step bright/soft/muted banding implemented here.

ANIMATION IS STATE-DRIVEN, curses-only: the pure text path (`render_lines`)
never animates — a repeated render of the same Fleet is byte-identical. In
curses, the accordion's ACTIVE step line carries the KITT sweep described
above, and a "working" TASK row's own status glyph cycles through
`SPINNER_FRAMES` (`_task_row_glyph`, operator ruling 2026-07-27: a frozen
task spinner is a defect, not a styling choice — it was drawing a fixed
frame because `tick` was never threaded into `_draw_task_row` to recompute
it against) — both driven by the same tick counter from the main loop's
getch cadence. A missing/impossible frame (no width for the strip) never
costs the step line itself: it still renders its label statically and
legibly, same as any other row (ANIMATION CAVEAT). The feature row's own
status glyph remains a STATIC accent-coloured member of the spinner family
(`STATUS_EMOJI["working"]`), never cycled — that non-cycling is specific to
the feature row, not a blanket rule for every "working" glyph in the file.

Every other row (repo header text, done/todo feature glyph, subagent,
courier) stays a single fixed-width character, unconditionally the same on
every frame.

CLI:
  python3 tools/sidebar.py          run the interactive curses UI
  python3 tools/sidebar.py --dump   print one frame as plain text and exit 0
                                    (headless — no TTY required)
  python3 tools/sidebar.py --once   paint one real curses frame (same
                                    terminal/colour/draw path as the live
                                    UI) and exit 0 — no input loop, no watch
                                    thread. Requires a real terminal; exits
                                    non-zero with a message otherwise.

STDLIB ONLY.
"""
from __future__ import annotations

import colorsys
import curses
import os
import re
import sys
import threading
import unicodedata
import zlib
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sidebar_nav  # noqa: E402
from sidebar_glyphs import (  # noqa: E402
    ELLIPSIS,
    LOCATION_BADGES,
    NBSP,
    NO_ACTIVITY_TEXT,
    PHASE_MARK,
    ROLE_EMOJI,
    SPINNER_FRAMES,
    STATUS_EMOJI,
    SUBAGENT_GLYPH,
    TARGET_SEPARATOR,
    _ACCORDION_STEP_GLYPH,
    _HEADER_RAMP_IN,
    _HEADER_RAMP_OUT,
    _INDENT_GLYPH,
    _INDENT_WIDTH,
    _PROGRESS_CIRCLES,
    _SUBAGENT_LIVE_GLYPH,
    _TASK_BAR_GLYPH,
    role_emoji,
)
from sidebar_colour import (  # noqa: E402
    AMBER,
    FALLBACK_HEADER_HUES,
    FILL_GREEN,
    GREEN,
    GREEN_SOFT,
    HEADER_FG,
    MODEL_TIERS,
    MUTED,
    PAUSED_HEADER_GRAY,
    REPO_HUES,
    TEXT,
    WHITE,
    ColourRoles,
    _chain_step,
    _colour_scope,
    _derive_fallback_hue,
    _muted_toward,
    _repo_hue,
    _srgb_channel_linear,
    _CONTRAST_MIN_MARK,
    _CONTRAST_MIN_TEXT,
    colour_ramp_steps,
    contrast_ratio,
    ensure_contrast,
    lerp,
    model_tier_colour,
    relative_luminance,
    repo_colour_roles,
    task_chain_roles,
)
from sidebar_colour_lineage import (  # noqa: E402
    content_colour_base,
    feature_colour_base,
    open_stage_colour,
    task_colour_base,
    _hls_jitter_point,
    _perceptual_distance,
    _TASK_COLOUR_MAX_REROLLS,
    _TASK_HUE_JITTER_DEGREES,
    _TASK_LIGHTNESS_JITTER,
    _TASK_MIN_PERCEPTUAL_DISTANCE,
    _TASK_SATURATION_JITTER,
)
from sidebar_band import (  # noqa: E402
    band_column_colour,
    band_position,
    band_span,
    band_travel_end,
    fill_cols,
    lifted_fill_colour,
    progress_column_colour,
)
from sidebar_text import (  # noqa: E402
    _cell_width,
    _truncate,
    render_header_line,
    small_caps,
)
from sidebar_citation import (  # noqa: E402
    _ATTRIBUTION_INDENT,
    _MIN_TIGHT_QUOTE_WIDTH,
    _agent_expansion_fits,
    _quoted_activity,
    _tight_quote_floor,
    attribution_text,
    compose_identity_line,
    identity_block,
    identity_line_text,
    tight_line,
    tight_line_parts,
)
from sidebar_rows import (  # noqa: E402
    INDENT_UNIT,
    Row,
    _step_row,
    flatten,
)
from sidebar_render_text import (  # noqa: E402
    _feature_row_layout,
    _row_text,
    clamp_scroll_offset,
    compose_feature_row_text,
    compose_task_row_text,
    done_footer_line,
    footer_lines,
    phase_dot_suffix,
    phase_mark,
    render_lines,
)
from sidebar_curses_colour import (  # noqa: E402
    _ColourCache,
    _direct_term_name,
    _init_agent_colours,
    _init_colours,
    _rgb_to_direct_colour_id,
    _rgb_to_xterm256,
    _safe_addch,
    _safe_addstr,
    _select_display_term,
    _terminfo_has_direct_colour,
    _truecolor_advertised,
)
from sidebar_paint_shared import (  # noqa: E402
    _SELECTION_LIFT_FRACTION,
    _draw_indent_cell,
    _fill_row_bg,
    _open_block_bg,
    _selection_highlight,
)
from sidebar_paint_header import (  # noqa: E402
    _draw_header,
    _header_gradient_fits,
    _header_ramp_cells,
)
from sidebar_model import (  # noqa: E402
    ACTIVE_WINDOW_SECONDS,
    BRANCH_SEPARATOR,
    NO_LIVE_ACTIVITY,
    PHASES,
    TERMINAL_TASK_STATUSES,
    Agent,
    Feature,
    Fleet,
    Repo,
    Step,
    Subagent,
    Task,
    _fold_sessions,
    _is_bare_uuid,
    _parse_frontmatter,
    _repo_display_name,
    build_model,
    load_role_step_map,
    load_watched_repo_names,
    phase_states,
    watch,
)


# --------------------------------------------------------------------------
# Phase checklist
# --------------------------------------------------------------------------

# `phase_states` is NOT redefined here (found during this round's module
# split, 2026-07-28): a byte-identical copy used to sit in this exact spot,
# shadowing the one already imported from `sidebar_model` above -- a wart
# from whenever this file absorbed sidebar_model.py, never noticed since
# both bodies agreed. Pruned; the imported name is the only one now.


# --------------------------------------------------------------------------
# Shared fleet state (written by the watch thread, read by the main loop)
# --------------------------------------------------------------------------

class _SharedFleet:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fleet = Fleet()

    def set(self, fleet: Fleet) -> None:
        with self._lock:
            self._fleet = fleet

    def get(self) -> Fleet:
        with self._lock:
            return self._fleet


def _watch_thread(shared: _SharedFleet) -> None:
    try:
        watch(shared.set, watched_names=load_watched_repo_names())
    except Exception:
        pass  # keep the UI alive on the last snapshot even if the watch dies


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


def _task_row_glyph(status: str | None, tick: int) -> str:
    """The task row's own status glyph — a genuinely CYCLING spinner frame
    while `status == "working"` (operator ruling, 2026-07-27: "the spinner
    on the task doesn't spin" — a real defect, not styling; the row was
    drawing a fixed `STATUS_EMOJI["working"]` frame with no `tick` ever
    threaded into `_draw_task_row` to recompute it against, so it could
    never advance regardless of how long the frame loop ran). Every other
    status keeps its existing static glyph unchanged. This is curses-only,
    same as every other per-frame motion in this file — the plain-text
    path (`compose_task_row_text`/`_row_text`) still uses the static
    `STATUS_EMOJI["working"]` frame, since a repeated `render_lines` call
    must stay byte-identical."""
    if status == "working":
        return SPINNER_FRAMES[tick % len(SPINNER_FRAMES)]
    return STATUS_EMOJI.get(status, "○")


def _draw_task_row(
    stdscr, y: int, width: int, row: Row, selected: bool, colours: _ColourCache,
    hue: dict[str, tuple[int, int, int]], tick: int,
) -> int:
    """A task's own row: a single accent BAR cell — background THIRD
    (`task_chain_roles(hue, row.feature_colour).third`, operator ruling
    2026-07-28: the task line's own background is derived FROM the repo's
    SECONDARY, one link down the chain, no longer equal to it — supersedes
    the earlier `hue["fill"]` reading, which was SECONDARY itself, the
    feature row's own tone), foreground Ct (grade 2, `row.task_colour`,
    already allocated once per feature by `_assign_task_colours` within
    its feature's own hue range, so two open tasks are told apart by bar
    colour alone) — followed by its name and right-aligned progress circle
    as PLAIN text, no background (operator spec, 2026-07-26: this is what
    keeps a task row visibly distinct from a feature row's own full solid
    band). A terminal task's own green/"failed" colour always wins over
    its Ct tint, same exclusivity rule as before. The status glyph itself
    is `_task_row_glyph` (operator ruling, 2026-07-27) — cycling while
    working, static otherwise. `selected` swaps in `_selection_highlight`
    for the row's own background (sidebar-teamwork defect 4) rather than
    `curses.A_REVERSE` — every foreground below is already run through
    `ensure_contrast` against `bg`, so substituting the lifted background
    before those calls keeps the guarantee automatically."""
    bg = task_chain_roles(hue, row.feature_colour).third
    if selected:
        bg = _selection_highlight(bg)
    attr_extra = curses.A_BOLD if selected else 0
    if row.status == "done":
        bar_fg = GREEN
    elif row.status == "failed":
        bar_fg = MUTED
    else:
        bar_fg = row.task_colour or feature_colour_base(hue)
    bar_fg = ensure_contrast(bar_fg, bg, _CONTRAST_MIN_MARK)
    _safe_addstr(stdscr, y, 0, _TASK_BAR_GLYPH, colours.pair(bar_fg, bg) | attr_extra)
    glyph = _task_row_glyph(row.status, tick)
    # One column short of the window's TRUE last column (`width - 1`),
    # never `width - 2` — the same reservation `_step_row_display_text`
    # and `_draw_feature_row` already make. `_safe_addstr` (unlike
    # `_safe_addch`) never special-cases that edge: a body long enough to
    # reach it would `addstr` straight onto it, and this build's terminal
    # auto-wraps the cursor off that write, desyncing the colour-pair
    # state for whatever draws on the ROW BELOW next — a row depending on
    # what was drawn before it, Decision-111's `A_DIM` bug reached through
    # a different attribute path (sidebar-teamwork defect (b)).
    avail = max(width - 3, 0)
    body = _truncate(compose_task_row_text(glyph, row.label, row.progress_glyph, avail), avail)
    text_fg = GREEN if row.status == "done" else MUTED if row.status == "failed" else TEXT
    text_fg = ensure_contrast(text_fg, bg, _CONTRAST_MIN_TEXT)
    _safe_addstr(stdscr, y, 2, body, colours.pair(text_fg, bg) | attr_extra)
    return y + 1


_STEP_LINE_COLOUR = {"done": GREEN_SOFT, "active": TEXT, "todo": MUTED}


def _step_row_name_and_mark(row: Row) -> tuple[str, str]:
    """(name_only, mark) split of an accordion Row's `label` — the model
    layer (`_step_row`) still bakes "{glyph} {small_caps(name)}" into
    `label` for the plain-text path (`_row_text`/`render_lines`, untouched
    by this curses-only realignment); this recovers the mark so the curses
    painter can pin it to a fixed column instead of leaving it embedded in
    the centred name."""
    mark = _ACCORDION_STEP_GLYPH.get(row.status, "")
    prefix = f"{mark} "
    if mark and row.label.startswith(prefix):
        return row.label[len(prefix):], mark
    return row.label, mark


def _step_row_display_text(row: Row, width: int) -> str:
    """The step row's full-width display text with its own mark pinned to
    a FIXED right-hand column, rather than riding the centred name
    (operator ruling, 2026-07-27: "the checkmarx or red markx next to the
    step shoujld be right aligned... the mark must not float in the middle
    next to a centred label of varying length" — a mark that drifts with
    the label reads ragged; a fixed column doesn't). The window's own
    literal last column is never safely writable (`_safe_addch`'s insch
    trap drops any character landed there), so "right-aligned" lands one
    column short of the true edge, at `width - 2`, with the true last
    column left blank."""
    name, mark = _step_row_name_and_mark(row)
    if width < 2:
        return render_header_line(row.label, width)
    name_width = width - 2
    centred = render_header_line(name, name_width)
    mark_ch = mark if mark else " "
    return (centred + mark_ch + " ")[:width]


def _draw_step_row(
    stdscr, y: int, width: int, row: Row, selected: bool, colours: _ColourCache, tick: int,
    hue: dict[str, tuple[int, int, int]],
) -> int:
    """One line of the task's five-step accordion (operator correction,
    2026-07-26: "collapse keeps the line" — every step gets its own row,
    always), CENTRED, small caps, over a one-column indent (THIRD on
    FOURTH, `_draw_indent_cell`) plus the row's own FOURTH background.

    EVERY step title — done, active, or todo alike — carries the SAME flat
    FOURTH colour (operator ruling 2026-07-28, item 11: "for whichi
    wederive the FOURTh... Then each step uses FOURTH" — supersedes the
    grade-3 `content_colour_base(row.task_colour)` reading this docstring
    previously described; a step row's background is now the repo/feature
    chain's FOURTH, same tone as the indent's own background, not a
    per-task tint). Being active is expressed by its mark, its sweep and
    by what appears beneath it, NOT by changing the title's own
    background (operator ruling 2026-07-27, still true). If the ACTIVE
    step is also LIVE (a genuinely "working" agent on it, not merely the
    furthest-along position — `row.live`, see `_step_row`/the model-layer
    function of the same name) it additionally carries the MOVING
    GRADIENT sweep — reusing the pre-existing lifted-band triangular-wave
    geometry (`band_position`/`band_span`/`band_column_colour`) across the
    row's own text width, brightening this SAME FOURTH colour rather than
    a separately-darkened one. No room/no motion just means a static (but
    still correctly coloured) block (ANIMATION CAVEAT: a missing animation
    must never mean a missing step). `selected` swaps in `_selection_
    highlight` for the step's own FOURTH colour (sidebar-teamwork defect
    4) rather than `curses.A_REVERSE` — every foreground below is already
    run through `ensure_contrast` against `content`/the sweep's own `bg`,
    so substituting the lifted colour before those calls keeps the
    guarantee automatically."""
    roles = task_chain_roles(hue, row.feature_colour)
    content = _selection_highlight(roles.fourth) if selected else roles.fourth
    attr_extra = curses.A_BOLD if selected else 0
    _draw_indent_cell(stdscr, y, colours, roles.third, content)
    text_width = max(width - _INDENT_WIDTH, 0)
    text = _step_row_display_text(row, text_width)

    if row.status != "active":
        fg = ensure_contrast(_STEP_LINE_COLOUR.get(row.status, MUTED), content, _CONTRAST_MIN_TEXT)
        for col, ch in enumerate(text):
            _safe_addch(stdscr, y, col + _INDENT_WIDTH, ch, colours.pair(fg, content) | attr_extra)
        return y + 1

    if row.live:
        span = band_span(max(text_width - 1, 1))
        pos = band_position(tick, span)
        for col, ch in enumerate(text):
            bg = band_column_colour(col, pos, text_width, content) or content
            fg = ensure_contrast(TEXT, bg, _CONTRAST_MIN_TEXT)
            _safe_addch(stdscr, y, col + _INDENT_WIDTH, ch, colours.pair(fg, bg) | attr_extra)
    else:
        fg = ensure_contrast(TEXT, content, _CONTRAST_MIN_TEXT)
        for col, ch in enumerate(text):
            _safe_addch(stdscr, y, col + _INDENT_WIDTH, ch, colours.pair(fg, content) | attr_extra)
    return y + 1


def _draw(
    stdscr, rows: list[Row], selected: int, offset: int,
    colour_pairs: dict[str, int], agent_colours: list[int] | None,
    colours: _ColourCache, tick: int, has_moved: bool = False,
) -> None:
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    if not rows:
        _safe_addstr(stdscr, 0, 0, _truncate(NO_ACTIVITY_TEXT, max_x), curses.A_DIM)
        stdscr.refresh()
        return

    expand = _agent_expansion_fits(rows, max_y)
    y = 0
    # The current repo's hue triple — updated on every "repo" row, reused
    # by every "task"/"accordion"/"agent"/"subagent" row until the next one
    # (each resolves its own THIRD/FOURTH from this via `task_chain_roles`;
    # feature rows carry everything colour-related they need directly on
    # the Row already, see `task_colour`/`feature_colour`/`_open_block_bg`).
    hue = _repo_hue("")
    for i, row in enumerate(rows[offset:offset + max_y], start=offset):
        if y >= max_y:
            break
        if row.kind == "repo":
            hue = _repo_hue(row.label)
            _draw_header(stdscr, y, max_x, row.label, row.paused, i == selected and has_moved, colours)
            y += 1
            continue
        if row.kind == "feature":
            _draw_feature_row(stdscr, y, max_x, row, i == selected, colours)
            y += 1
            continue
        if row.kind == "task":
            y = _draw_task_row(stdscr, y, max_x, row, i == selected, colours, hue, tick)
            continue
        if row.kind == "accordion":
            y = _draw_step_row(stdscr, y, max_x, row, i == selected, colours, tick, hue)
            continue
        if row.kind == "agent":
            y = _draw_identity_block(stdscr, y, max_x, row, i == selected, expand, colours, hue)
            continue
        if row.kind == "subagent":
            y = _draw_subagent_row(stdscr, y, max_x, row, i == selected, colours, hue)
            continue

        text = _truncate(_row_text(row), max_x)
        attr = colour_pairs.get(row.status, 0)
        if i == selected:
            attr |= curses.A_REVERSE
        _safe_addstr(stdscr, y, 0, text, attr)
        y += 1

    # DEAD-SPACE FILL (sidebar-teamwork defect 1): the loop above only ever
    # stops short of `max_y` once `rows` itself has run out — the slice
    # `rows[offset:offset + max_y]` already claims every row the viewport
    # can hold, so reaching here with `y < max_y` means there is genuinely
    # nothing further to show, never a row scrolled past. `stdscr.erase()`
    # already blanked those remaining rows to nothing; paint them in the
    # current repo's own dim FILL hue instead (the same tone a feature row's
    # band and a task row's own bar background already use) so the pane's
    # surface claims the full height it was granted rather than stopping in
    # a bare, unstyled void the moment its content does.
    for fill_y in range(y, max_y):
        _fill_row_bg(stdscr, fill_y, max_x, hue["fill"], colours)

    stdscr.refresh()


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------

def _navigate_selected(rows: list[Row], selected: int) -> None:
    if not rows or not (0 <= selected < len(rows)):
        return
    row = rows[selected]
    sidebar_nav.navigate_to(row.target)


def _clamp_selected(selected: int, count: int) -> int:
    if count == 0:
        return 0
    return max(0, min(selected, count - 1))


def _init_draw_state(stdscr) -> tuple[dict[str, int], list[int] | None, _ColourCache]:
    curses.curs_set(0)
    # ~125ms/frame target (bus-message-specifying B5 item 3, matching the
    # mock's FPS=8) — the band sweep rides this loop's tick, same as the
    # spinner used to; a slower actual cadence is accepted (geometry over
    # framerate) rather than tightened with extra timers.
    stdscr.timeout(125)
    return _init_colours(), _init_agent_colours(), _ColourCache()


def _draw_frame(
    stdscr, fleet: Fleet, selected: int, scroll_offset: int,
    colour_pairs: dict[str, int], agent_colours: list[int] | None,
    colours: _ColourCache, tick: int, has_moved: bool,
) -> tuple[list[Row], int, int]:
    rows = flatten(fleet)
    selected = _clamp_selected(selected, len(rows))
    max_y, _max_x = stdscr.getmaxyx()
    scroll_offset = clamp_scroll_offset(scroll_offset, selected, len(rows), max_y)
    _draw(stdscr, rows, selected, scroll_offset, colour_pairs, agent_colours, colours, tick, has_moved)
    return rows, selected, scroll_offset


def main(stdscr) -> None:
    colour_pairs, agent_colours, colours = _init_draw_state(stdscr)

    shared = _SharedFleet()
    thread = threading.Thread(target=_watch_thread, args=(shared,), daemon=True)
    thread.start()

    selected = 0
    scroll_offset = 0
    tick = 0
    has_moved = False  # header A_REVERSE stays off until the operator navigates

    while True:
        rows, selected, scroll_offset = _draw_frame(
            stdscr, shared.get(), selected, scroll_offset,
            colour_pairs, agent_colours, colours, tick, has_moved,
        )

        key = stdscr.getch()
        tick += 1

        if key in (curses.KEY_UP, ord("k")):
            selected = max(0, selected - 1)
            has_moved = True
        elif key in (curses.KEY_DOWN, ord("j")):
            selected = min(len(rows) - 1, selected + 1) if rows else 0
            has_moved = True
        elif key in (10, 13, curses.KEY_ENTER):
            _navigate_selected(rows, selected)
        elif key in (ord("q"), ord("Q")):
            return
        elif key == curses.KEY_RESIZE:
            # `update_lines_cols()` alone only refreshes the `curses.LINES`/
            # `curses.COLS` convenience globals -- it does NOT reliably
            # resize `stdscr` itself (whether ncurses' own internal SIGWINCH
            # handler already resized `stdscr` before `KEY_RESIZE` reached
            # here is a build/version detail, not something this app can
            # assume). Confirmed the hard way: a real resize left every
            # subsequent `stdscr.getmaxyx()` reporting the OLD geometry
            # forever, so the app kept redrawing at the old width while
            # tmux's own pane grid silently cropped the oversized output to
            # the new, smaller viewport -- a name cut mid-word with no
            # ellipsis, because the renderer never even saw the narrower
            # width to truncate against. `resizeterm()` is the explicit,
            # version-independent call that actually reallocates `stdscr`
            # (and any subwindows) to the just-refreshed `curses.LINES`/
            # `curses.COLS`.
            curses.update_lines_cols()
            curses.resizeterm(curses.LINES, curses.COLS)
        # any other key (including -1 on timeout) is ignored


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _run_dump() -> int:
    fleet = build_model(watched_names=load_watched_repo_names())
    for line in render_lines(fleet):
        print(line)
    return 0


def _paint_once(stdscr) -> None:
    colour_pairs, agent_colours, colours = _init_draw_state(stdscr)
    fleet = build_model(watched_names=load_watched_repo_names())
    _draw_frame(stdscr, fleet, 0, 0, colour_pairs, agent_colours, colours, tick=0, has_moved=False)


def _run_once() -> int:
    try:
        curses.wrapper(_paint_once)
    except curses.error as exc:
        print(f"sidebar --once: no terminal available ({exc})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if "--dump" in sys.argv[1:]:
        sys.exit(_run_dump())
    os.environ["TERM"] = _select_display_term(os.environ.get("TERM", ""))
    # `LINES`/`COLUMNS`, when present in the environment, are what ncurses
    # consults FIRST for the screen size -- ahead of the real pty geometry
    # -- so a shell that exported them once (bash's own `checkwinsize`,
    # `/etc/bash.bashrc`, does this for every interactive shell) freezes
    # this process at whatever size the pane happened to be at launch.
    # Confirmed the hard way: after a real resize, `curses.update_lines_
    # cols()`/`resizeterm()` kept recomputing the SAME stale launch-time
    # size forever, because they were reading these two variables rather
    # than the pty's live `TIOCGWINSZ` -- the renderer kept drawing at the
    # old width while tmux's own pane grid silently cropped the output to
    # the new, narrower one, which is indistinguishable on screen from a
    # truncation bug (no ellipsis, cut exactly at the new edge) but has
    # nothing to do with the truncation rule itself. Dropping both here,
    # once, before curses ever starts, is what every KEY_RESIZE afterward
    # needs to actually see the terminal's real size.
    os.environ.pop("LINES", None)
    os.environ.pop("COLUMNS", None)
    if "--once" in sys.argv[1:]:
        sys.exit(_run_once())
    curses.wrapper(main)

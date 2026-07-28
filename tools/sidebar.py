#!/usr/bin/env python3
"""Curses fleet sidebar — reads the fleet model, renders it, navigates via
sidebar_nav. The ONLY sidebar (bus-finishing): the old courier-inbox reader
and the plain-text prototype reader (tools/sidebar_v3.py) are both retired.

The MODEL layer — data classes, event folding, registry reading, tree
assembly (`build_model()`/`watch()`) — lives in `tools/sidebar_model.py`
and is owned by that module's own docstring, which is the specification to
read first. THIS file is now a thin CLI/main-loop shim (2026-07-28 module
split, discovery pass: "colour ~36 functions, model building ~32, text
composition ~21, curses I/O ~20, pure-text render pipeline ~13, glyphs
~12" against a 3,086-line/~130-function monolith) — it wires the watch
thread to the curses draw loop and re-imports every name the rest of this
codebase (and its tests) reach by `sidebar.X`, but no longer DEFINES most
of them. Read in dependency order (each only imports from the ones before
it — colour before text composition before model building before the
render pipeline before curses I/O, never the reverse):
`sidebar_glyphs.py` (every fixed emoji/glyph constant) →
`sidebar_colour.py` (RGB math, repo hue, the PRIMARY..FOURTH chain,
contrast) → `sidebar_colour_lineage.py` (per-feature/task identity colour)
→ `sidebar_band.py` (sweep/fill-bar geometry) → `sidebar_text.py`
(cell-width-aware string primitives) → `sidebar_citation.py` (the agent
quote + attribution ladder) → `sidebar_rows.py` (Fleet -> Row assembly) →
`sidebar_render_text.py` (Row -> plain text, no curses) →
`sidebar_curses_colour.py` (terminal colour management) →
`sidebar_paint_shared.py`/`sidebar_paint_header.py`/`sidebar_paint_
feature.py`/`sidebar_paint_task.py`/`sidebar_paint_step.py`/`sidebar_paint_
identity.py` (one painter per row kind) → `sidebar_paint.py` (the
per-frame dispatcher, `_draw()`). This file owns only what's left: the
watch-thread supervisor (`_SharedFleet`/`_watch_thread`) and the curses
event loop/CLI (`main`/`_run_dump`/`_run_once`).

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

import colorsys  # noqa: F401 -- re-exported: a test reaches `sidebar.colorsys` directly
import curses
import os
import sys
import threading

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
from sidebar_paint_feature import (  # noqa: E402
    _draw_feature_row,
    _feature_fill_colour,
    _feature_name_colour,
    _feature_row_cell_styles,
)
from sidebar_paint_task import (  # noqa: E402
    _draw_task_row,
    _task_row_glyph,
)
from sidebar_paint_step import (  # noqa: E402
    _draw_step_row,
    _step_row_display_text,
    _step_row_name_and_mark,
)
from sidebar_paint_identity import (  # noqa: E402
    _draw_identity_block,
    _draw_subagent_row,
)
from sidebar_paint import _draw  # noqa: E402
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

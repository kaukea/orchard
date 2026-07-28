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

The project header is a centred BLOCK (operator spec, 2026-07-28,
superseding the earlier monotonic left-to-right gradient): a fixed-size
core — the title, one space of padding each side — filled with the repo's
PRIMARY colour (`repo_colour_roles(hue).primary`, i.e. `hue["accent"]`,
still resolved through the direct-colour terminfo path, never
approximated away), flanked by `_header_ramp_cells()` cells of gradient
EACH side (a temporary A/B knob, see `_draw_header`'s own comment) that
tame the primary down toward the SECONDARY (`hue["fill"]`), mirrored, with
flat secondary fill beyond that to the row's edges — no new palette, every
tone is built from the triple the repo already owns (see `_draw_header`).
The title is never shrunk to make room for the ramp: a pane too narrow for
the full title AND the full ramp drops the ramp entirely and renders a
flat primary block instead. A feature row's
full-width dimmer background band uses that same `"fill"` hue,
unconditionally (every feature row, any status — it is what makes a feature
visibly not a task, see `_draw_feature_row`). The accordion's ACTIVE step
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
# Mock-canonical palette and glyph vocabulary (bus-message-specifying B5) —
# copied verbatim from sidebar-mock.py; never re-derived.
# --------------------------------------------------------------------------

HEADER_FG = (0xB6, 0xBA, 0xC6)
TEXT = (0xD0, 0xD5, 0xDF)
MUTED = (0x84, 0x89, 0x94)
GREEN = (0x76, 0xC8, 0x8E)
GREEN_SOFT = (0x60, 0x9E, 0x72)
AMBER = (0xC6, 0x98, 0x54)
FILL_GREEN = (0x17, 0x2B, 0x1F)
WHITE = (0xFF, 0xFF, 0xFF)

# Per-repo hue triple (header/fill/accent). `orchids`/`signmc` are pinned to
# the mock's exact RGBs (case-insensitive lookup, see `_repo_hue`); any other
# repo gets a triple derived — deterministically, by a stable hash of its
# lowercased name — from `FALLBACK_HEADER_HUES` (see `_derive_fallback_hue`).
REPO_HUES: dict[str, dict[str, tuple[int, int, int]]] = {
    "orchids": {
        "header": (0x2C, 0x18, 0x3E),
        "fill": (0x28, 0x1F, 0x36),
        "accent": (0xAC, 0x88, 0xD6),
    },
    "signmc": {
        "header": (0x09, 0x2A, 0x2D),
        "fill": (0x16, 0x2A, 0x2E),
        "accent": (0x6E, 0xB4, 0xB0),
    },
}
FALLBACK_HEADER_HUES = [
    (0x1C, 0x2E, 0x4A),  # dark blue
    (0x4A, 0x3A, 0x1C),  # dark olive
    (0x1C, 0x4A, 0x2E),  # dark green
    (0x4A, 0x1C, 0x2E),  # dark maroon
]
PAUSED_HEADER_GRAY = (0xD9, 0xD9, 0xD9)

MODEL_TIERS = {
    "haiku": (0x6C, 0xB2, 0xAA),
    "sonnet": (0x7C, 0x98, 0xC4),
    "opus": (0xA4, 0x82, 0xDC),
    "fable": (0xD6, 0xAC, 0x60),
}

# PHASES/BRANCH_SEPARATOR live in sidebar_model.py (imported above) — both
# are model-layer vocabulary, not presentation.
PHASE_MARK = {"done": "●", "active": "⠧", "todo": "○"}

NBSP = "\xa0"

# Pending-operator-pick roles render as no emoji (None), not a placeholder —
# so a later pick drops in without a code change (bus-message-specifying B5
# item 8).
ROLE_EMOJI: dict[str, str | None] = {
    "gardener": "🌳",
    "landscaper": "🌿",
    "sower": "🌱",
    "groundskeeper": "🧹",
    "courier": "📮",
    "bloomer": "🌸",
}
LOCATION_BADGES = {"local": "💻", "cloud": "☁️"}

# Spinner frames — retained as the source of the single static "working"
# glyph (index 7 == mock's "⠧"); no longer cycled per-frame for a feature
# row (superseded by the band sweep, see module docstring).
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# Seven-state status vocabulary (sidebar-titling item 9, revised again by
# the mock's visual contract, and again by the retention ruling below):
# idle, waiting, awaiting_agent, and stale share the same hollow circle —
# there is no longer a separate operator-wait glyph variant (bus-message-
# specifying B5 item 7: "hollow circle only, no watch/timer glyphs anywhere
# in row status"). "waiting"/"awaiting_agent" are part of the full
# vocabulary the mock defines but are currently unreachable: the fleet
# model (below) only ever derives working/done/failed/idle/stale from the
# new event grammar, which has no blocked/notify_user signal to distinguish
# a wait — see the module docstring's "NOT ported" list. Kept here rather
# than pruned, since STATUS_EMOJI.get() is used defensively and a future
# data source may yet supply the signal.
#
# "stale" IS reachable (operator ruling, 2026-07-25, revised same day): a
# session with no event inside the ~1h ACTIVE_WINDOW and no terminal
# outcome renders gray rather than being dropped from the model — nothing
# is ever removed from the sidebar by staleness; only a session restart
# (the tmpfs projects tree clearing) resets what is shown. See
# `_status_for`.
STATUS_EMOJI = {
    "working": SPINNER_FRAMES[7],
    "waiting": "○",
    "idle": "○",
    "awaiting_agent": "○",
    "stale": "○",
    "done": "✓",
    "failed": "❌",
}

# Subagent presence glyph (sidebar-titling item 4). A subagent row has no
# state beyond "it currently exists in the model" — it appears the moment
# its delegation begins and vanishes the moment it ends or its own events
# age out (operator ruling, 2026-07-26: a subagent is live-only, never
# persisted). `_row_text` below still honours a terminal glyph here
# defensively, for a Row built directly rather than through the model (see
# TaskGlyphTests).
SUBAGENT_GLYPH = "●"

# Glyph for a subagent's own live state, keyed by the scheduled/doing/done
# vocabulary (`_DELEGATION_STATE` in sidebar_model.py) — "done" is handled
# by the shared STATUS_EMOJI/TERMINAL_TASK_STATUSES path instead (see
# `_row_text`), so only the one non-default live state needs an entry here.
_SUBAGENT_LIVE_GLYPH = {"scheduled": "○"}

# TERMINAL_TASK_STATUSES lives in sidebar_model.py (imported above).

# Bookend glyph is the file's own idle/waiting hollow circle
# (STATUS_EMOJI["idle"]/["waiting"]/["stale"]), not "⋮" (sidebar-teamwork
# defect 3: "⋮" doubled as both the identity line's field separator — see
# `compose_identity_line`'s `sep` — and this banner's bookend, an
# ambiguous reuse of one glyph for two meanings). "○" already means
# "nothing live here" everywhere else in this vocabulary, so it reads the
# same way framing an empty fleet.
NO_ACTIVITY_TEXT = "○ no activity ○"
ELLIPSIS = "…"

# Separator between repo name and feature name in a feature row's tmux
# window target ("<repo>/<name>", sidebar-titling item 2) — the DISPLAYED
# row text no longer carries this prefix (bus-message-specifying B5: a
# feature row shows only its own name, since the repo is already named by
# the header block above its group), but navigation targets still need it.
TARGET_SEPARATOR = "/"

# Per-agent colour palette (sidebar-polish item 4, unchanged by this step) —
# still used for subagent/courier row tinting, which this step does not rebuild
# (bus-message-specifying B5 item 9).
ORCHID_PALETTE = [
    ("white",   (0xF5, 0xF0, 0xF6), curses.COLOR_WHITE),
    ("pink",    (0xF4, 0xA6, 0xC6), curses.COLOR_MAGENTA),
    ("purple",  (0x9B, 0x59, 0xB6), curses.COLOR_MAGENTA),
    ("magenta", (0xC7, 0x1F, 0xA0), curses.COLOR_MAGENTA),
    ("yellow",  (0xF5, 0xD6, 0x42), curses.COLOR_YELLOW),
    ("orange",  (0xE8, 0x8A, 0x2E), curses.COLOR_YELLOW),
    ("green",   (0x6A, 0xB0, 0x4F), curses.COLOR_GREEN),
    ("blue",    (0x4A, 0x7B, 0xC8), curses.COLOR_BLUE),
]


def lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _muted_toward(
    fg: tuple[int, int, int], bg: tuple[int, int, int], amount: float = 0.35,
) -> tuple[int, int, int]:
    """A visually "thinner"/less prominent variant of `fg` against `bg`,
    blended in RGB space — NEVER via `curses.A_DIM`. Verified against a
    real capture (2026-07-26): combining `A_DIM` with a custom truecolor
    pair, followed by ANOTHER custom-pair draw on a later row, silently
    drops that later row's own background on this tmux+ncurses build
    (reproduced in isolation — a bare two-line repro with `A_DIM` on row 0
    corrupted row 1's background even though row 1 never used `A_DIM`
    itself). No code path in this file combines `A_DIM` with a non-default
    background any more; every "muted" look below is this function
    instead."""
    return lerp(fg, bg, amount)


def _derive_fallback_hue(header: tuple[int, int, int]) -> dict[str, tuple[int, int, int]]:
    """A repo not in `REPO_HUES` still needs a fill/accent, not just a
    header — derived deterministically from its fallback header colour so
    the whole triple stays a pure function of the repo name."""
    return {
        "header": header,
        "fill": lerp(header, WHITE, 0.08),
        "accent": lerp(header, WHITE, 0.55),
    }


def _repo_hue(repo_name: str) -> dict[str, tuple[int, int, int]]:
    """Stable per-repo hue triple. Case-insensitive match against
    `REPO_HUES`; any other repo name is assigned one of
    `FALLBACK_HEADER_HUES` by a stable hash (zlib.crc32) of its lowercased
    name, so a given repo always gets the same triple."""
    key = repo_name.lower()
    if key in REPO_HUES:
        return REPO_HUES[key]
    index = zlib.crc32(key.encode("utf-8")) % len(FALLBACK_HEADER_HUES)
    return _derive_fallback_hue(FALLBACK_HEADER_HUES[index])


# --------------------------------------------------------------------------
# Repo colour ROLES (operator ruling, 2026-07-28: "primay -> gradient ->
# secondary. we reuse that later for ownership tracking") — a repo hue's
# PRIMARY (its own intense, saturated identity colour — the same
# `hue["accent"]` `feature_colour_base` already uses as a feature's grade-1
# base) and SECONDARY (the dimmer tone every fill/background band already
# lands on — `hue["fill"]`), named and derived in exactly ONE place. The
# header below is the FIRST consumer, not the owner: a later
# ownership-tracking feature is expected to reuse this identical pair for a
# different purpose, so nothing about deriving primary/secondary may live
# inside `_draw_header` itself, and `colour_ramp_steps`'s step COUNT is a
# parameter precisely so that future caller can ask for its own number of
# steps over the same pair without this function changing.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ColourRoles:
    primary: tuple[int, int, int]
    secondary: tuple[int, int, int]


def repo_colour_roles(hue: dict[str, tuple[int, int, int]]) -> ColourRoles:
    """A repo hue's PRIMARY/SECONDARY pair — no new palette, both are
    fields the hue triple already carries (`"accent"`/`"fill"`)."""
    return ColourRoles(primary=hue["accent"], secondary=hue["fill"])


def colour_ramp_steps(
    primary: tuple[int, int, int], secondary: tuple[int, int, int], steps: int,
) -> list[tuple[int, int, int]]:
    """`steps` tones taming FROM `primary` TOWARD `secondary` (operator
    correction, 2026-07-28: "In our cse the colour step are inverted" /
    "we dont highlight, we tame with the gradient" — interpolate OUTWARD
    from the intense colour toward the fade colour; never derive a ramp by
    brightening FROM the fade colour INTO a highlight, which is what a
    literal reading of a tmux-style highlight ramp would give). Step `i`
    (0-based) is `lerp(primary, secondary, (i + 1) / steps)`, so the LAST
    tone lands exactly on `secondary` and `primary` itself is never
    restated — the caller's own core block already owns that exact tone
    verbatim. The step count is the only per-caller knob, never
    hardcoded — see the module comment above."""
    if steps <= 0:
        return []
    return [lerp(primary, secondary, (i + 1) / steps) for i in range(steps)]


# --------------------------------------------------------------------------
# Three-grade colour lineage (operator spec, 2026-07-26): FEATURE colour
# base (grade 1, the project's own hue) -> TASK colour base (grade 2, Ct —
# each task its OWN colour, allocated within its feature's hue RANGE, never
# the global palette) -> CONTENT colour base (grade 3, derived in turn from
# the task's own colour — the step bands and the open-stage block a level
# below them).
#
# "Dimmer" throughout this lineage NEVER means darker (operator correction,
# 2026-07-27: "dimmer fr me meant lighter / more subdued / less of the
# colour or a color that matches on the color wheel the container" — the
# darker reading was an agent inference, not his). A CONTAINED grade is a
# SUBDUED variant of its container — desaturated and/or lightened toward
# it, never pushed toward black — so it visibly reads as belonging to its
# container rather than as a different band: darkening breaks that
# reading, lightening/desaturating/hue-harmonising preserve it. See
# `content_colour_base`/`open_stage_colour`.
#
# Colour therefore encodes lineage: which feature a task belongs to, and
# which task a block of content belongs to, readable without a word.
#
# Contrast is COMPUTED (WCAG 2.x relative-luminance ratio), never
# hardcoded/eyeballed — `ensure_contrast` pushes a foreground toward
# white/black until it clears the guideline minimum against whatever
# background it actually landed on, since the feature hue (and everything
# derived from it) varies per project/task. This runs BEFORE the RGB
# reaches `_ColourCache`, so a low-colour terminal's own xterm-256/
# attribute-only degradation (already handled there) still applies on top
# of an already-readable pair — contrast compliance takes precedence over
# fidelity to the derived hue, never abandoned by discarding the
# background instead (the background carries the structural/lineage
# meaning; the foreground is what yields).
# --------------------------------------------------------------------------

_CONTRAST_MIN_TEXT = 4.5  # WCAG "normal text"
_CONTRAST_MIN_MARK = 3.0  # WCAG "large/bold text" and meaningful non-text marks


def _srgb_channel_linear(c: int) -> float:
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_srgb_channel_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def ensure_contrast(
    fg: tuple[int, int, int], bg: tuple[int, int, int], min_ratio: float,
    *, step: float = 0.06, max_steps: int = 24,
) -> tuple[int, int, int]:
    """`fg`, pushed toward WHITE or BLACK — whichever one can actually
    reach a HIGHER ratio against `bg` — in small steps until it clears
    `min_ratio` (never raises, never abandons `bg`: operator ruling,
    2026-07-26, the derived background carries structural meaning — fix
    the foreground, not the background). Best-effort (near-white/
    near-black) if `max_steps` isn't enough, rather than shipping
    something unreadable.

    The target extreme is picked by comparing `contrast_ratio(WHITE, bg)`
    against `contrast_ratio(BLACK, bg)` directly — NOT by a `relative_
    luminance(bg) < 0.5` threshold, which was the bug (found here,
    2026-07-27): the WCAG ratio formula's own `+0.05` offset makes
    darkening buy more headroom against a MID-toned background than
    lightening does, so the true crossover sits near luminance ~0.18, not
    0.5. Any background between those two — most of this file's derived
    content/open-stage backgrounds land there — picked WHITE under the old
    threshold when BLACK was the only extreme that could ever clear a
    normal-text ratio; the loop then ran its full budget and returned an
    already-near-white candidate that STILL failed contrast. That silent
    failure is what read on screen as "the brightest thing in the pane,
    near-white" — text pushed toward the wrong extreme, not merely too
    subtle.

    A second, smaller bug travelled with the first: when the loop's
    `max_steps` budget ran out before reaching `min_ratio`, it used to
    return whatever PARTIALLY-blended candidate it had reached — visibly
    short of the promised "near-white/near-black" best effort, and short
    of `min_ratio` for real (a `TEXT`-family foreground against this
    file's own open-stage backgrounds needed 17-18 steps at the default
    6% to actually clear 4.5:1; the old default of 16 fell one or two
    steps short every time). `max_steps` is raised to comfortably cover
    that real case, and lerp-ing straight toward `target` only ever moves
    EVERY channel monotonically closer to it, so if the budget somehow
    still runs out, `target` itself is provably the best ratio either
    extreme can reach against `bg` — the fallback below, not a partial
    step, is what "best-effort" actually means."""
    if contrast_ratio(fg, bg) >= min_ratio:
        return fg
    target = WHITE if contrast_ratio(WHITE, bg) >= contrast_ratio((0, 0, 0), bg) else (0, 0, 0)
    candidate = fg
    for _ in range(max_steps):
        candidate = lerp(candidate, target, step)
        if contrast_ratio(candidate, bg) >= min_ratio:
            return candidate
    return target


# A feature's own assigned base colour, when one has been decided at
# feature-creation time and persisted to its sidecar (operator spec,
# 2026-07-26: "feature base colours can be decided in advance... kept in
# repo and synchronized with github") — READ side only; assigning and
# writing one is board/board_gh.py territory, a separate task, never this
# module. `docs/TODO.md.d/<feature_id>.md`'s frontmatter is the same
# `---\nkey: value\n---` shape `_parse_frontmatter` already reads for
# agent charters (`load_role_step_map`) — reused, not reinvented. Only
# reachable for the repo this tool itself runs from (same limitation
# `_AGENTS_DIR` already has for `agents/*.md`): a sidebar rendering
# ANOTHER repo's features has no path to that repo's own checkout, so it
# always falls back for them — the correct, honest "absent" state, not a
# broken promise.
_FEATURE_SIDECAR_DIR = Path(__file__).resolve().parent.parent / "docs" / "TODO.md.d"
_HEX_COLOUR_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


def _parse_hex_colour(text: str | None) -> tuple[int, int, int] | None:
    """A plain hex string ("#AC88D6" or "AC88D6") -> RGB — the minimum
    form a human assigning a colour by hand would write (operator spec,
    2026-07-26). None for anything else, never a raise — malformed is the
    same as absent."""
    if not text:
        return None
    match = _HEX_COLOUR_RE.match(text.strip())
    if not match:
        return None
    hex6 = match.group(1)
    return (int(hex6[0:2], 16), int(hex6[2:4], 16), int(hex6[4:6], 16))


def _read_feature_base_colour(
    feature_id: str, sidecar_dir: Path | None = None,
) -> tuple[int, int, int] | None:
    """A feature's own base colour from its sidecar's frontmatter
    (`colour:`/`color:`, either spelling), or None — missing file,
    missing key, or an unparseable value are all the SAME "absent" result
    (fail-open, same rule as everywhere else in this module): the caller
    then derives grade 1 from the project hue exactly as when no colour
    was ever assigned, never a raise, never a blank row."""
    sidecar_dir = sidecar_dir or _FEATURE_SIDECAR_DIR
    try:
        text = (sidecar_dir / f"{feature_id}.md").read_text(encoding="utf-8")
    except OSError:
        return None
    fields = _parse_frontmatter(text)
    return _parse_hex_colour(fields.get("colour") or fields.get("color"))


def _hash_unit(key: str, salt: int = 0) -> float:
    """A stable [0, 1) pseudo-random value from `key` (+ `salt`, so a
    perceptual collision can be deterministically re-rolled) — crc32, the
    same stable-hash primitive already used elsewhere in this file
    (`_repo_hue`/`_agent_colour_index`), never `random`: a task's colour
    must be identical across every redraw, a restart, and two panes
    rendering the same tree at once, not merely "look random once"."""
    return (zlib.crc32(f"{key}:{salt}".encode("utf-8")) % 10_000) / 10_000


def _hls_jitter_point(
    base: tuple[int, int, int], key: str, salt: int,
    hue_degrees: float, lightness_jitter: float, saturation_jitter: float,
) -> tuple[int, int, int]:
    """A deterministic, UNORDERED point in HLS space near `base` — hashed
    from `key` (+ `salt`, for a rejection-test reroll), never `random`
    (see `_hash_unit`). Shared by every grade of the colour lineage that
    needs "belongs to its container, but not identical to it, and not on a
    ramp": `feature_colour_base`'s fallback (grade 1 jittered from the
    project hue) and `task_colour_base` (grade 2 jittered from grade 1)
    both go through this one formula, so "which grade" only changes WHAT
    is jittered and by how much, never the jitter mechanics themselves."""
    r0, g0, b0 = (c / 255 for c in base)
    h0, l0, s0 = colorsys.rgb_to_hls(r0, g0, b0)
    h = (h0 + (_hash_unit(key, salt) - 0.5) * (hue_degrees / 360.0)) % 1.0
    l = min(max(l0 + (_hash_unit(f"{key}:l", salt) - 0.5) * lightness_jitter, 0.0), 1.0)
    s = min(max(s0 + (_hash_unit(f"{key}:s", salt) - 0.5) * saturation_jitter, 0.0), 1.0)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (round(r * 255), round(g * 255), round(b * 255))


# A feature's own FALLBACK point (grade 1, no assigned sidecar colour yet —
# true for every feature today) is jittered from the project's own hue,
# keyed by `feature_id`, exactly the way a task's own colour is jittered
# from ITS feature's base (see `task_colour_base` below) — never the
# project hue verbatim. Decision-110: "derives one from the project hue"
# when a feature has no colour of its own, not "reuses the project hue" —
# every unassigned feature in the SAME repo returning the literal same RGB
# was the direct cause of "both features render their step bands in the
# identical lavender" (two features share a repo far more often than they
# share an assigned colour). Wider than the task jitter below: a FEATURE is
# the top division within a repo's hue and needs more headroom than a task
# needs within its feature's own, narrower range.
_FEATURE_HUE_JITTER_DEGREES = 130.0
_FEATURE_LIGHTNESS_JITTER = 0.12
_FEATURE_SATURATION_JITTER = 0.16


def _fallback_feature_colour(
    hue: dict[str, tuple[int, int, int]], feature_id: str,
) -> tuple[int, int, int]:
    return _hls_jitter_point(
        hue["accent"], feature_id, 0,
        _FEATURE_HUE_JITTER_DEGREES, _FEATURE_LIGHTNESS_JITTER, _FEATURE_SATURATION_JITTER,
    )


def feature_colour_base(
    hue: dict[str, tuple[int, int, int]], feature_id: str | None = None,
    sidecar_dir: Path | None = None,
) -> tuple[int, int, int]:
    """Grade 1 — a feature's own ASSIGNED base colour when its sidecar has
    one (`_read_feature_base_colour`); otherwise a point jittered from the
    project's own hue (`_repo_hue`'s `"accent"`), keyed by `feature_id`
    (`_fallback_feature_colour`) so sibling features in the same repo don't
    collapse onto the identical RGB — the fallback is not a stopgap: every
    feature renders sensibly whether or not a colour has been assigned
    (true for all of them today, since nothing writes one yet). With no
    `feature_id` to key on at all, the project's own hue is returned
    verbatim (the one caller that can reach this — `_draw_task_row`'s own
    last-resort fallback for a task with no `task_colour` — has no feature
    identity to jitter from either). The orchid palette is the starting
    point, not a closed set — any repo's own hue (pinned or hash-derived,
    see `_repo_hue`), or any feature's own assigned colour, works here
    identically."""
    if feature_id is not None:
        assigned = _read_feature_base_colour(feature_id, sidecar_dir)
        if assigned is not None:
            return assigned
        return _fallback_feature_colour(hue, feature_id)
    return hue["accent"]


# "Goes with purple, not ordered by it" (operator, 2026-07-26): a task's
# colour carries identity only, never sequence/age/progress — so it is a
# deterministic-but-unordered point within a hue/lightness/saturation
# JITTER around the feature's own accent, not a ramp or an evenly-spaced
# rotation. Wide enough to read as "randomly its own", tight enough to
# still sit in the same family as the feature's hue.
_TASK_HUE_JITTER_DEGREES = 70.0
_TASK_LIGHTNESS_JITTER = 0.08
_TASK_SATURATION_JITTER = 0.12

# The rejection test's "too close to an already-assigned sibling" floor
# (Euclidean, see `_perceptual_distance`) and how many deterministic
# re-rolls (hash salted 1, 2, 3…) are tried before just accepting the best
# candidate seen. This bounds a loop, not an allocation — 16.7M colours is
# never actually short on room (operator ruling, 2026-07-26: tasks never
# reopen, so a completed task's colour is simply available for reuse by no
# longer appearing in `sibling_colours`; no eviction/recycling bookkeeping).
_TASK_MIN_PERCEPTUAL_DISTANCE = 40.0
_TASK_COLOUR_MAX_REROLLS = 8


def _perceptual_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """A cheap, good-enough Euclidean distance in sRGB space for the
    rejection test — not a full CIEDE2000 delta-E (out of scope for a test
    that only needs "close enough to collide" vs. "clearly different"),
    weighted with the same luma emphasis WCAG's own coefficients use so a
    green/red difference isn't under-counted relative to blue."""
    dr, dg, db = (a[i] - b[i] for i in range(3))
    return (0.30 * dr ** 2 + 0.59 * dg ** 2 + 0.11 * db ** 2) ** 0.5


def task_colour_base(
    hue: dict[str, tuple[int, int, int]], feature_id: str, task_id: str,
    sibling_colours: list[tuple[int, int, int]] = (),
    sidecar_dir: Path | None = None,
) -> tuple[int, int, int]:
    """Grade 2 — this task's own colour (Ct): a deterministic, UNORDERED
    point drawn from within its feature's own harmonious range around
    grade 1 (`feature_colour_base(hue, feature_id)` — the feature's own
    assigned sidecar colour when it has one, else derived from the
    project hue) (operator ruling, 2026-07-26: "they have different
    colours randomly selected not ordered... whatever falls off the tree
    that goes with purple" — no ramp, no ordinal meaning). Hashed from the
    task's own id (`_hash_unit`) so it is STABLE for the task's whole
    life. Rejected and deterministically re-rolled against
    `sibling_colours` — every OTHER currently-open task's own already-
    assigned Ct in the same feature — until `_TASK_MIN_PERCEPTUAL_
    DISTANCE` is cleared or `_TASK_COLOUR_MAX_REROLLS` is spent (accepts
    the least-close candidate tried rather than looping forever)."""
    feature_base = feature_colour_base(hue, feature_id, sidecar_dir)

    best_candidate, best_distance = None, -1.0
    for salt in range(_TASK_COLOUR_MAX_REROLLS):
        candidate = _hls_jitter_point(
            feature_base, task_id, salt,
            _TASK_HUE_JITTER_DEGREES, _TASK_LIGHTNESS_JITTER, _TASK_SATURATION_JITTER,
        )
        distance = min(
            (_perceptual_distance(candidate, sib) for sib in sibling_colours), default=float("inf"),
        )
        if distance >= _TASK_MIN_PERCEPTUAL_DISTANCE:
            return candidate
        if distance > best_distance:
            best_candidate, best_distance = candidate, distance
    return best_candidate


# Grade 3/open-stage "subdued" tuning (operator ruling, 2026-07-27 — see
# the lineage section docstring above for why this is desaturate+lighten,
# never darken). Content keeps the task colour's own lightness and only
# quiets its saturation; the open stage goes a further step lighter AND
# quieter still, so it reads as visibly derived from — and lighter than —
# the section title it sits under, never the plain background.
_CONTENT_SATURATION_FACTOR = 0.4
# PROPORTIONAL, not additive/subtractive (bug found 2026-07-27, defect 2's
# second half): a fixed "+0.16 lightness" compounds on top of a content
# colour whose own lightness already sits around 0.6-0.65 for most of this
# palette (grade 2/3 inherit the task's own lightness unchanged, see
# `content_colour_base`), landing the open-stage block at L~0.79-0.85 —
# visually near-white regardless of which task/feature it belongs to, and
# an absolute "-0.12 saturation" on top of content's ALREADY-reduced
# saturation routinely hit the floor of 0 — a flat, hue-less gray. Together
# these were the on-screen "agent identity line and empty rows are the
# brightest things in the pane, near-white... pulling the eye" and the
# loss of lineage at exactly the most space-consuming, most-read level (an
# agent's own line). A FRACTION of the remaining headroom to white, and a
# FACTOR (not a flat subtraction) on saturation — the same multiplicative
# shape `_CONTENT_SATURATION_FACTOR` above already uses — keeps the "always
# lighter, never darker" invariant (Decision-110) while landing consistently
# around L~0.70-0.78 with enough saturation left to still read as tinted,
# not gray, whatever the starting lightness/saturation happened to be.
_OPEN_STAGE_LIGHTNESS_LIFT_FRACTION = 0.30
_OPEN_STAGE_SATURATION_FACTOR = 0.75


def content_colour_base(task_colour: tuple[int, int, int]) -> tuple[int, int, int]:
    """Grade 3 — a step title's own background (C), a SUBDUED variant of
    the TASK's own colour (grade 2) — desaturated at the SAME lightness,
    never darkened toward black (operator ruling, 2026-07-27: "dimmer"
    meant lighter/less-saturated/harmonising, never darker — darkening
    reads as a different band, not a quieter one). Content visibly
    belongs to its task the same way a task visibly belongs to its
    feature — through reduced saturation, not reduced lightness."""
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in task_colour))
    r, g, b = colorsys.hls_to_rgb(h, l, s * _CONTENT_SATURATION_FACTOR)
    return (round(r * 255), round(g * 255), round(b * 255))


def open_stage_colour(content_colour: tuple[int, int, int]) -> tuple[int, int, int]:
    """The OPEN step's own block background — LIGHTER than the section
    title's own `content_colour_base` (operator ruling, 2026-07-27,
    supersedes the earlier "dimmer means darker" reading: "inside the step
    shuld be lighter or the color implicitness of inheritnce breaks" — a
    child must read as visibly DERIVED from its parent; reverting to a
    darker or plain background says the opposite). Computed straight FROM
    `content_colour` — never an unrelated source, never independently
    re-derived from the task colour or anywhere else — lightened and
    desaturated a further step past it, so the block an agent/subagent
    line sits in is always painted from the background of the section
    title it is nested under (the same "parented FROM the line above"
    relationship the operator separately named for the accent beside a
    delegated line — the child's colour input is its parent's own
    rendered colour, not an unrelated one), and the whole open region
    still reads as one contiguous, findable block against that title."""
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in content_colour))
    l = l + (1.0 - l) * _OPEN_STAGE_LIGHTNESS_LIFT_FRACTION
    s = s * _OPEN_STAGE_SATURATION_FACTOR
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (round(r * 255), round(g * 255), round(b * 255))


# --------------------------------------------------------------------------
# Small caps (phase label, e.g. "building" -> "ʙᴜɪʟᴅɪɴɢ")
# --------------------------------------------------------------------------

_SMALL_CAPS_MAP = {
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ",
    "f": "ꜰ", "g": "ɢ", "h": "ʜ", "i": "ɪ", "j": "ᴊ",
    "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ", "o": "ᴏ",
    "p": "ᴘ", "q": "ꞯ", "r": "ʀ", "s": "ꜱ", "t": "ᴛ",
    "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x",       "y": "ʏ",
    "z": "ᴢ",
}


def small_caps(text: str) -> str:
    return "".join(_SMALL_CAPS_MAP.get(ch, ch) for ch in text)


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


# --------------------------------------------------------------------------
# Identity line ("<doing> ⋮ <role> ⋮ <model>", NBSP-glued, model truncated)
# --------------------------------------------------------------------------

def model_tier_colour(model: str | None) -> tuple[int, int, int]:
    if not model:
        return TEXT
    return MODEL_TIERS.get(model.split("-")[0], TEXT)


def _cell_width(text: str) -> int:
    """Terminal column width of `text`: East-Asian Wide/Fullwidth characters
    (which include the role emoji) occupy two cells, everything else one."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def compose_identity_line(
    doing: str, role: str | None, model: str | None, width: int,
) -> tuple[str, str, str]:
    """(doing, role_text, model_text) — role_text is '' when `role` is None;
    otherwise it is `role_emoji(role)` glued to the role text with an NBSP
    (no leading space when there is no glyph for the role). model_text is
    `model` truncated (never wrapped) to whatever room is left after
    doing+role, '' if none is left or `model` is None."""
    sep = NBSP + "⋮" + NBSP
    emoji = role_emoji(role)
    role_text = (emoji + NBSP + role) if (role and emoji) else (role or "")
    used = _cell_width(doing) + (len(sep) + _cell_width(role_text) if role_text else 0)
    room = width - used - (len(sep) if model else 0)
    model_text = (model or "")[:max(room, 0)] if model else ""
    return doing, role_text, model_text


def identity_line_text(doing: str, role: str | None, model: str | None, width: int) -> str:
    doing_t, role_t, model_t = compose_identity_line(doing, role, model, width)
    sep = NBSP + "⋮" + NBSP
    parts = [doing_t]
    if role_t:
        parts.append(role_t)
    if model_t:
        parts.append(model_t)
    return sep.join(parts)


# --------------------------------------------------------------------------
# Identity BLOCK — a quote with a subordinate attribution beneath it, book-
# epigraph style (operator ruling, 2026-07-26, SUPERSEDES the single-line
# `identity_line_text` above as the agent row's live render; that function
# stays defined/tested but nothing in the draw path calls it any more).
#
# The status is volatile and is the thing being scanned for, so it carries
# the news as the quote; role/model are stable context, subordinate and
# rendered smaller/later. Degrades in this exact order as room shrinks:
#   full    "activity"                  (2 lines, full model string)
#           — role · model
#   abbrev  "activity"                  (2 lines, model's short/version-
#           — role · shortmodel          less form — WIDTH-driven: the full
#                                         string didn't fit)
#   tight   "activity" — role           (1 line, model dropped entirely —
#                                         HEIGHT-driven: no room for a
#                                         second line this frame)
#   none    "activity"                  (1 line, attribution dropped too —
#                                         WIDTH-driven: even "quote — role"
#                                         didn't fit)
# The quote itself never drops. 2-vs-1-line (expand) is a single per-frame
# decision from real available height (`_agent_expansion_fits`), never a
# per-row guess; full-vs-abbrev-vs-none is purely about whether the text
# fits the row's own column width.
# --------------------------------------------------------------------------

_ATTRIBUTION_INDENT = "    "


def _role_text(role: str | None) -> str:
    emoji = role_emoji(role)
    return (emoji + NBSP + role) if (role and emoji) else (role or "")


def short_model_name(model: str | None) -> str | None:
    """The version-elided short form of a model string ("claude-opus-5" ->
    "opus5", "claude-sonnet-5-20260101" -> "sonnet5") — family name plus
    its leading numeric version component, dropping any "claude-" prefix
    and any later date/build suffix. None when there's nothing to shorten
    to (an empty or unparseable string)."""
    if not model:
        return None
    parts = model.split("-")
    if parts and parts[0] == "claude":
        parts = parts[1:]
    if not parts:
        return None
    family = parts[0]
    version = next((p for p in parts[1:] if p.isdigit()), "")
    return f"{family}{version}"


def attribution_text(role: str | None, model: str | None, width: int) -> tuple[str, str]:
    """(role_text, model_text) for the attribution line at `width` columns
    — role_text never empties (callers only reach this once `role` is
    truthy); model_text is the full model string, its short form, or ''
    once neither fits — the model degrades, role never does, in the
    2-line (expand) form."""
    role_text = _role_text(role)
    if not model:
        return role_text, ""
    room = width - _cell_width("— ") - _cell_width(role_text) - _cell_width(" · ")
    if _cell_width(model) <= max(room, 0):
        return role_text, model
    short = short_model_name(model)
    if short and _cell_width(short) <= max(room, 0):
        return role_text, short
    return role_text, ""


def _attribution_line(role: str | None, model: str | None, width: int) -> str:
    role_text, model_text = attribution_text(role, model, width)
    tail = f" · {model_text}" if model_text else ""
    return f"— {role_text}{tail}"


def _quoted_activity(activity: str) -> str:
    """The agent's activity, quoted for display — an empty string renders
    as the words "no activity" rather than a bare pair of smart quotes
    (sidebar-teamwork defect 5: idle is a legitimate state, Decision-058,
    not a blank to paper over). The model layer already substitutes
    `NO_LIVE_ACTIVITY` for every `Agent.activity` it builds, so this is
    defensive rather than the primary guard — but it is the ONE place
    every quote-building call site goes through, so the render side never
    depends on the model never slipping one through."""
    return f"“{activity or NO_LIVE_ACTIVITY}”"


# The floor a squeezed quote is still allowed to shrink to in the tight
# rung (`tight_line_parts`) before the ROLE is given up on instead
# (sidebar-teamwork defect 2, 2026-07-27: at 29 columns an agent's activity
# was truncating to almost nothing — "no ac… — 🌿 landscaper" — because the
# role's emoji+NBSP+word took a fixed share off the top and the quote got
# whatever was left, unconditionally, down to a near-useless sliver. The
# quote is the one genuinely LIVE piece of information on the line; the
# role is stable context already visible via the row's own colour lineage
# (Decision-110) — so the floor is no longer a bare few cells, it is
# `_TIGHT_QUOTE_FLOOR`, at least half of the row's own budget. Below that
# floor the role tail drops instead, same "none" rung `identity_block`'s
# own docstring already names — this raises how EASILY that rung is
# reached, it does not invent it.
_MIN_TIGHT_QUOTE_WIDTH = 8


def _tight_quote_floor(width: int) -> int:
    """The minimum cell budget the quote must keep before the role tail is
    even considered — half of this row's own width, floored at
    `_MIN_TIGHT_QUOTE_WIDTH` so a very narrow row still asks for something
    (never zero, never a single character)."""
    return max(width // 2, _MIN_TIGHT_QUOTE_WIDTH)


def tight_line_parts(activity: str, role: str | None, width: int) -> tuple[str, str]:
    """(shown_quote, tail) for the tight (1-line) rung — `tail` is
    " — <role>" once the quote can keep at least `_tight_quote_floor(width)`
    cells alongside it, "" once giving the role room would crush the quote
    below that floor (sidebar-teamwork defect 2: the quote is what a reader
    scans this line for, so it is the role that yields when both can't fit
    comfortably, not the other way round). `shown_quote` alone is never
    truncated below the plain quote unless making room for the role
    actually requires it."""
    quote = _quoted_activity(activity)
    if not role:
        return _truncate(quote, width), ""
    role_text = _role_text(role)
    tail = f" — {role_text}"
    quote_budget = width - _cell_width(tail)
    if quote_budget >= _tight_quote_floor(width):
        shown_quote = quote if _cell_width(quote) <= quote_budget else _truncate(quote, quote_budget)
        return shown_quote, tail
    return _truncate(quote, width), ""


def tight_line(activity: str, role: str | None, width: int) -> str:
    quote, tail = tight_line_parts(activity, role, width)
    return f"{quote}{tail}"


def identity_block(activity: str, role: str | None, model: str | None,
                    width: int, expand: bool) -> list[str]:
    """[quote] or [quote, attribution] — see the module section docstring
    above for the exact degradation ladder. `expand` is the caller's real-
    height decision (`_agent_expansion_fits`); `width` is this row's own
    column budget. Lines are returned WITHOUT the row's own depth indent —
    callers prepend that uniformly; the attribution line's extra
    `_ATTRIBUTION_INDENT` beneath the quote is already baked in."""
    if not role:
        return [_quoted_activity(activity)]
    if expand:
        quote = _quoted_activity(activity)
        attribution_width = max(width - len(_ATTRIBUTION_INDENT), 0)
        return [quote, _ATTRIBUTION_INDENT + _attribution_line(role, model, attribution_width)]
    return [tight_line(activity, role, width)]


def _agent_expansion_fits(rows: list[Row], height: int | None) -> bool:
    """Whether there is genuine room to give an agent row its own
    attribution line, rather than folding it onto the quote line.

    "Very compact form" (operator ruling, 2026-07-26) supersedes the
    original bare-fits check: compactness wins at EVERY choice point, so
    the tight 1-line form (role riding the quote line) is the DEFAULT, and
    2-line expansion is reserved for a frame with real slack to spare —
    never "just doesn't overflow". In practice that makes the 2-line form
    unreachable through today's callers; it stays defined (and `height`/
    `rows` kept as parameters) as a seam for a future roomier/wide-pane
    mode rather than deleted, per `identity_block`'s own degradation
    ladder, which a caller may still drive directly."""
    return False


# --------------------------------------------------------------------------
# Phase checklist
# --------------------------------------------------------------------------

def phase_states(active_phase: str | None) -> list[tuple[str, str]]:
    """[(phase_word, state)] for every `PHASES` entry, state in
    {done, active, todo}, given the current active phase name (an unknown or
    absent phase renders every entry as `todo` — nothing claimed done or
    active without a signal)."""
    if active_phase not in PHASES:
        return [(p, "todo") for p in PHASES]
    active_index = PHASES.index(active_phase)
    return [
        (p, "done" if i < active_index else "active" if i == active_index else "todo")
        for i, p in enumerate(PHASES)
    ]


def phase_mark(state: str) -> str:
    return PHASE_MARK.get(state, PHASE_MARK["todo"])


def phase_dot_suffix(running: int, queued: int) -> str:
    return "●" * running + "○" * queued


# --------------------------------------------------------------------------
# Footer stats — omitted entirely when the model doesn't (yet) expose them;
# a later integration step wires the source, this step invents none of it.
# --------------------------------------------------------------------------

def _tokens_dollars_text(tokens: str | None, dollars: str | None) -> str | None:
    return f"⚡ {tokens} ⋮ ${dollars}" if tokens is not None and dollars is not None else None


def footer_lines(source: object) -> list[str]:
    age = getattr(source, "age", None)
    worked = getattr(source, "worked", None)
    tokens = getattr(source, "tokens", None)
    dollars = getattr(source, "dollars", None)
    lines = []
    if age is not None and worked is not None:
        lines.append(f"⏱ {age} ⋮ worked {worked}")
    stats = _tokens_dollars_text(tokens, dollars)
    if stats is not None:
        lines.append(stats)
    return lines


def done_footer_line(source: object) -> str | None:
    """The collapsed one-line footer under a DONE feature row ("⚡ 384k ⋮
    $7.90 ⋮ 6h02", mock frame) — tokens/dollars pair like footer_lines'
    second line; age (no "worked" companion — the collapsed form drops it)
    stands alone. None when neither has anything to show."""
    if source is None:
        return None
    tokens = getattr(source, "tokens", None)
    dollars = getattr(source, "dollars", None)
    age = getattr(source, "age", None)
    parts = [p for p in (_tokens_dollars_text(tokens, dollars), age) if p is not None]
    return " ⋮ ".join(parts) if parts else None


def role_emoji(role: str | None) -> str | None:
    return ROLE_EMOJI.get(role) if role else None


# --------------------------------------------------------------------------
# Presentation model (pure, no curses)
# --------------------------------------------------------------------------

# Indent unit for the six-level tree (repo/feature/task/accordion/agent/
# subagent), one unit per `Row.depth` — 2 columns per level (operator
# ruling, 2026-07-26, "very compact form": on a narrow pane, indentation
# competes directly with content, so it is the minimum that keeps a level
# legible, not the earlier 4-space draft).
INDENT_UNIT = "  "


@dataclass
class Row:
    depth: int
    kind: str  # "repo" | "feature" | "task" | "accordion" | "agent" | "subagent"
    target: str  # exact tmux window name to navigate to on Enter
    label: str
    status: str | None
    paused: bool = field(default=False)  # only meaningful for kind == "repo"
    repo_name: str = field(default="")  # owning repo's name; only meaningful for kind == "feature"
    progress_pct: int | None = field(default=None)  # kind == "feature" only; no source in this grammar
    progress_glyph: str | None = field(default=None)  # kind == "task" only — see `_task_progress_glyph`
    activity: str = field(default="")  # kind == "agent" only — the "doing" text
    role: str | None = field(default=None)  # kind == "agent" only
    model: str | None = field(default=None)  # kind == "agent" only
    # kind == "accordion" only — the ACTIVE step's own KITT sweep gate: true
    # only when it also has a genuinely "working" agent, not merely the
    # furthest-along position (an idle/stale/stopped agent's step is still
    # positionally "active" but has nothing live to signal — see
    # `_step_row`/`_draw_step_row`).
    live: bool = field(default=False)
    # kind in {"task", "accordion", "agent", "subagent"} only — this row's
    # owning OPEN task's own already-allocated colour (Ct, grade 2,
    # `task_colour_base`, computed once per feature by `_assign_task_
    # colours` so every row under the same task agrees on it). None for a
    # terminal task's own row (it uses a fixed done/failed colour instead,
    # see `_draw_task_row`) and for repo/feature rows (not applicable).
    task_colour: tuple[int, int, int] | None = field(default=None)


def _agent_row(agent: Agent, target: str, depth: int, task_colour: tuple[int, int, int] | None) -> Row:
    return Row(depth=depth, kind="agent", target=target, label=agent.role or agent.session_id,
               task_colour=task_colour,
               status=agent.status, activity=agent.activity, role=agent.role, model=agent.model)


def _subagent_row(
    sub: Subagent, target: str, depth: int, task_colour: tuple[int, int, int] | None,
) -> Row:
    return Row(depth=depth, kind="subagent", target=target, label=sub.label, status=sub.state,
               task_colour=task_colour)


def _agent_and_subagent_rows(
    agent: Agent, target: str, depth: int, task_colour: tuple[int, int, int] | None,
) -> list[Row]:
    """An agent's identity-line row, followed by its own subagent rows at
    the SAME depth (rule 6, 2026-07-26: a subagent hangs under the STEP its
    parent agent is on, not one level deeper than its parent) — both carry
    the owning task's own colour (`task_colour`, Ct), so the curses draw
    path can paint them on the same open-block background as their step
    without any further lookup."""
    return [_agent_row(agent, target, depth, task_colour), *(
        _subagent_row(sub, target, depth, task_colour) for sub in agent.subagents
    )]


# Per-step glyph — done/active carry a mark, todo is bare (small caps alone
# already reads as "not reached yet" next to a marked neighbour, and a bare
# glyph column would just add noise).
_ACCORDION_STEP_GLYPH = {"done": "✓", "active": "⠧", "todo": ""}


def _step_row(
    step: Step, target: str, depth: int, task_colour: tuple[int, int, int] | None,
) -> Row:
    """One line of the task's five-step accordion — a COLLAPSE KEEPS ITS
    OWN LINE (operator correction, 2026-07-26: "collapse keeps the line,
    it doesn't go to the previous one"), so every one of the five states
    (done/active/todo) gets its own row, always small caps, keeping its
    place among the five rather than folding into a shared summary line.
    The active step's agents (and their subagents) are the caller's job to
    nest beneath this row, one level deeper (see `_task_rows`) — this row
    itself only ever carries the step's own name and mark, plus the owning
    task's own colour (`task_colour`, Ct) its grade-3 content colour is
    derived from (`content_colour_base`, curses-only)."""
    glyph = _ACCORDION_STEP_GLYPH[step.state]
    label = f"{glyph} {small_caps(step.name)}" if glyph else small_caps(step.name)
    live = step.state == "active" and any(a.status == "working" for a in step.agents)
    return Row(depth=depth, kind="accordion", target=target, label=label, status=step.state,
               live=live, task_colour=task_colour)


# 0..4 completed-of-five steps -> a quarter-fill circle (operator ruling,
# 2026-07-26): a task never shows index 5 — five-of-five is a terminal task,
# which collapses to its own one-line terminal glyph instead (see
# `_task_rows`), so the full circle and the terminal tick never compete for
# the same meaning. Index 0 still renders its own (emptiest) glyph rather
# than a blank column — a task at zero progress still exists.
_PROGRESS_CIRCLES = "○◔◑◕●"


def _task_progress_glyph(task: Task) -> str | None:
    """The task row's right-aligned progress cell — completed steps out of
    five, computed client-side from `task.steps` (never a wire/marker
    field: step state is a display concern, per the role->step map ruling
    already governing it). None for a task with no steps at all (nothing
    to show progress through — e.g. every agent on it is role-unmapped)."""
    if not task.steps:
        return None
    done = sum(1 for step in task.steps if step.state == "done")
    return _PROGRESS_CIRCLES[min(done, len(_PROGRESS_CIRCLES) - 1)]


def _task_rows(
    task: Task, target: str, depth: int,
    task_colour: tuple[int, int, int] | None = None,
) -> list[Row]:
    """A task's own row (name left-aligned, its progress circle right-
    aligned — `_task_progress_glyph`); `task_colour` is
    this task's own already-allocated Ct, grade 2, computed once per
    feature by `_assign_task_colours` — None for a terminal task, which
    uses a fixed done/failed colour instead, curses-only), plus — while it
    is still open — its five-line step accordion (`_step_row`, one row per
    `PHASES` entry, each keeping its own place whether done/active/todo),
    the active step's agents (and their subagents) nested one level deeper
    than that step's own row, and any role-unmapped agent (fails open,
    rendered directly under the task, no step to nest it in). A terminal
    task (`TERMINAL_TASK_STATUSES`) folds: its own row is all that shows."""
    name = task.name
    rows = [Row(depth=depth, kind="task", target=target, label=name, status=task.status,
                 progress_glyph=_task_progress_glyph(task), task_colour=task_colour)]
    if task.status in TERMINAL_TASK_STATUSES:
        return rows
    for step in task.steps:
        rows.append(_step_row(step, target, depth + 1, task_colour))
        if step.state == "active":
            for agent in step.agents:
                rows.extend(_agent_and_subagent_rows(agent, target, depth + 2, task_colour))
    for agent in task.unstepped_agents:
        rows.extend(_agent_and_subagent_rows(agent, target, depth + 1, task_colour))
    return rows


def _feature_collapsed(feature: Feature) -> bool:
    """A feature folds to its own single row once EVERY task is done — a
    still-open or failed task holds it expanded (operator ruling, 2026-07-
    26: a failed task is never quietly absorbed into a "complete" feature).
    An empty task list is never collapsed — there is nothing to have
    finished."""
    return bool(feature.tasks) and all(t.status == "done" for t in feature.tasks)


def _assign_task_colours(
    hue: dict[str, tuple[int, int, int]], feature_id: str, tasks: list[Task],
) -> dict[str, tuple[int, int, int]]:
    """One Ct (grade 2, `task_colour_base`) per OPEN task in `tasks`,
    keyed by `task_id` — computed together, in order, so each new task's
    rejection test sees every sibling already assigned so far (a terminal
    task never enters or occupies this: it uses its own fixed done/failed
    colour instead, and freeing up its slot for reuse needs no bookkeeping
    beyond simply not being in this dict, operator ruling 2026-07-26)."""
    assigned: dict[str, tuple[int, int, int]] = {}
    for task in tasks:
        if task.status in TERMINAL_TASK_STATUSES:
            continue
        assigned[task.task_id] = task_colour_base(
            hue, feature_id, task.task_id, list(assigned.values()),
        )
    return assigned


def _sole_same_named_task(feature: Feature) -> Task | None:
    """The feature's one task, when it is the ONLY task and shares the
    feature's exact name — the case a name-drop applies to (sidebar-
    teamwork defect 4: with one task of the same name, the feature's own
    band and the task row directly beneath it repeated the identical
    string). None otherwise, including when the feature simply has no
    tasks yet."""
    if len(feature.tasks) == 1 and feature.tasks[0].name == feature.name:
        return feature.tasks[0]
    return None


def _feature_rows(feature: Feature, repo_name: str, depth: int) -> list[Row]:
    target = f"{repo_name}{TARGET_SEPARATOR}{feature.name}"
    rows = [Row(depth=depth, kind="feature", target=target, label=feature.name,
                 status=feature.status, repo_name=repo_name)]
    if _feature_collapsed(feature):
        return rows
    task_colours = _assign_task_colours(_repo_hue(repo_name), feature.feature_id, feature.tasks)
    dropped_name_task = _sole_same_named_task(feature)
    for task in feature.tasks:
        task_rows = _task_rows(task, target, depth + 1,
                                task_colour=task_colours.get(task.task_id))
        if task is dropped_name_task:
            # NAME-DROP, not a row-drop (Decision-106: nothing is hidden
            # except by the two collapses) — the task row still carries
            # its own glyph, progress circle and accordion; only the
            # string identical to the feature's own name above it drops.
            #
            # sidebar-teamwork defect (c): dropping straight to "" left a
            # row with a marker, a status glyph and nothing else -- the
            # feature band above already carries the shared name (it has
            # nothing else to show, and stays real per operator ruling even
            # unpopulated), so it keeps the name; this row falls back to
            # its own status word instead of going blank, which is real,
            # own information (Decision-098: the task is what persists and
            # carries the terminal state) and never a repeat of the string
            # already on the band above.
            task_rows[0].label = task.status.replace("_", " ")
        rows.extend(task_rows)
    return rows


def flatten(fleet: Fleet) -> list[Row]:
    """Fleet -> flat list of Row, depth-first: repo, its features, each
    feature's open tasks, each open task's steps (or unmapped agents), each
    active step's agents and their own subagents.

    A repo with no live session (`not repo.has_session`) is skipped entirely
    — header AND group — an empty project has nothing to show (sidebar-
    titling item 3).

    Within a repo's features, `done` features sort FIRST (stable sort,
    done-first), ahead of everything still live — sidebar-titling item 7.
    Tasks/steps/agents/subagents keep their model order (see
    `_assemble_repo`/`_live_subagents`)."""
    rows: list[Row] = []
    for repo in fleet.repos:
        if not repo.has_session:
            continue
        rows.append(Row(depth=0, kind="repo", target=repo.name, label=repo.name,
                          status=repo.status, paused=repo.paused))
        features = sorted(repo.features, key=lambda f: f.status != "done")
        for feature in features:
            rows.extend(_feature_rows(feature, repo.name, depth=1))
    return rows


def _agent_row_lines(row: Row, width: int, expand: bool) -> list[str]:
    """The agent row's 1-2 output lines (see `identity_block`), each
    prefixed with the row's own depth indent — `width` MUST be the row's
    real available column budget: the degradation ladder trims the model,
    then folds/drops the attribution to fit it, so a caller that instead
    hands this a generous sentinel and hard-truncates the composed string
    afterward can silently lose the role text on a deeply-indented row
    (regression, 2026-07-26 — the "writing ⋮ 🌿 ⋮" empty-role frame)."""
    indent = INDENT_UNIT * row.depth
    content_width = max(width - len(indent), 0)
    return [indent + line for line in
            identity_block(row.activity, row.role, row.model, content_width, expand)]


def _row_text(row: Row) -> str:
    indent = INDENT_UNIT * row.depth
    if row.kind == "subagent":
        # A task/subagent that has reached a terminal state carries its own
        # STATUS_EMOJI glyph, so a completed row visibly reads as completed
        # (sidebar-titling item 4, Decision-058); otherwise its own
        # scheduled/doing glyph (rule 6, 2026-07-26).
        glyph = (STATUS_EMOJI[row.status] if row.status in TERMINAL_TASK_STATUSES
                 else _SUBAGENT_LIVE_GLYPH.get(row.status, SUBAGENT_GLYPH))
        return f"{indent}{glyph} {row.label}"
    if row.kind == "agent":
        return _agent_row_lines(row, width=200, expand=False)[0]  # defensive fallback only
    if row.kind == "repo" or row.kind == "accordion":
        # an accordion row is one step's own line — `label` is already the
        # fully composed glyph+small-caps text (`_step_row`), nothing more
        # to add; the curses draw path (`_draw_step_row`) additionally
        # layers the ACTIVE step's KITT sweep, which the plain-text path
        # never does (curses-only animation).
        return f"{indent}{row.label}"
    if row.kind == "task":
        return f"{indent}{compose_task_row_text(STATUS_EMOJI.get(row.status, '○'), row.label, row.progress_glyph, 200)}"
    # feature carries no progress cell of its own — see `_task_progress_glyph`.
    return f"{indent}{STATUS_EMOJI.get(row.status, '○')} {row.label}"


def _truncate(text: str, width: int) -> str:
    """THE single truncation rule for every row kind (feature, task,
    subagent, header, quote alike — sidebar-teamwork defect 1: a feature
    row and a task row used to disagree, one cutting bare and one with an
    ellipsis; every caller now goes through this one function instead).

    `width` is TERMINAL CELLS, not characters — measured via `_cell_width`,
    never `len()`, because these strings carry role emoji and other
    East-Asian-Wide glyphs (the ❌ failed glyph is one) that occupy two
    cells apiece; slicing by character count alone can both overflow the
    pane edge and land the cut mid-glyph. A string that already fits is
    returned unchanged; one that doesn't is cut and ends with an ellipsis,
    which itself counts toward the budget so the result never overflows."""
    if width <= 0:
        return ""
    if _cell_width(text) <= width:
        return text
    ellipsis_width = _cell_width(ELLIPSIS)
    budget = max(width - ellipsis_width, 0)
    kept: list[str] = []
    used = 0
    for ch in text:
        ch_width = _cell_width(ch)
        if used + ch_width > budget:
            break
        kept.append(ch)
        used += ch_width
    return "".join(kept) + ELLIPSIS


def _feature_row_layout(
    glyph: str, name: str, pct: int | None, width: int, badge: str | None,
) -> tuple[str, str, int, str, str]:
    """(glyph, shown_name, pad_width, badge_text, pct_text) for a feature row
    at `width` columns — the single source of truth for BOTH the plain-text
    dump path (`compose_feature_row_text`) and the curses per-column
    painter (`_draw_feature_row`), so their layouts can never drift apart
    (the same sharing pattern the file already used for
    `_feature_row_segments` before this step).

    `pct` is `None` for every live caller (operator ruling, 2026-07-26: a
    feature carries no percentage of its own — progress belongs to the
    task alone, drawn there as its fill circle) — `pct_text` is then "",
    the same as an absent badge. The parameter itself stays (rather than
    being deleted) purely so `FeatureRowLayoutTests` can keep asserting on
    the tail-composition math directly; nothing in the live render path
    ever passes an int here any more.

    Every measurement here is `_cell_width`, not `len()` — `glyph` is
    often a status emoji (e.g. the failed ❌, East-Asian-Wide, two cells
    for one character) and undercounting it by one cell is exactly what
    let a feature row overflow the pane edge (sidebar-teamwork defect 1)."""
    pct_text = f"{pct}%" if pct is not None else ""
    badge_text = f"{badge} " if badge else ""
    tail_len = _cell_width(badge_text) + _cell_width(pct_text)
    budget_for_name = max(width - _cell_width(glyph) - 1 - tail_len, 0)
    shown_name = name if _cell_width(name) <= budget_for_name else _truncate(name, budget_for_name)
    used = _cell_width(glyph) + 1 + _cell_width(shown_name) + tail_len
    pad_width = max(width - used, 0)
    return glyph, shown_name, pad_width, badge_text, pct_text


def compose_feature_row_text(
    glyph: str, name: str, pct: int | None, width: int, badge: str | None = None,
) -> str:
    glyph, shown_name, pad_width, badge_text, pct_text = _feature_row_layout(
        glyph, name, pct, width, badge,
    )
    return f"{glyph} {shown_name}{' ' * pad_width}{badge_text}{pct_text}"


def _task_row_layout(
    glyph: str, name: str, progress: str | None, width: int,
) -> tuple[str, str, int, str]:
    """(glyph, shown_name, pad_width, tail) for a task row at `width`
    columns — the progress cell (if any) is a SHORT, FIXED tail that
    always survives truncation intact; the NAME is what ellipsises when
    the row is too narrow (operator ruling, 2026-07-26: "a truncated name
    still reads, a truncated number misleads" — the same holds for the
    progress circle).

    Measured in `_cell_width`, not `len()` — same reasoning as
    `_feature_row_layout`, whose glyph vocabulary (STATUS_EMOJI) this row
    shares."""
    tail = f" {progress}" if progress else ""
    budget_for_name = max(width - _cell_width(glyph) - 1 - _cell_width(tail), 0)
    shown_name = name if _cell_width(name) <= budget_for_name else _truncate(name, budget_for_name)
    used = _cell_width(glyph) + 1 + _cell_width(shown_name) + _cell_width(tail)
    pad_width = max(width - used, 0)
    return glyph, shown_name, pad_width, tail


def compose_task_row_text(glyph: str, name: str, progress: str | None, width: int) -> str:
    glyph, shown_name, pad_width, tail = _task_row_layout(glyph, name, progress, width)
    return f"{glyph} {shown_name}{' ' * pad_width}{tail}"


def clamp_scroll_offset(offset: int, selected: int, count: int, height: int) -> int:
    """Keep-cursor-visible viewport clamp (sidebar-polish item 3 resolution).

    Given the CURRENT scroll `offset` (top row index shown), the `selected`
    row, the total `count` of rows, and the viewport `height`, returns the
    offset shifted the minimum amount needed so `selected` stays within
    `[offset, offset + height)` — it does not recentre. Never negative,
    never scrolls past what's needed to show the last row, and is a no-op
    (0) whenever every row already fits in the viewport."""
    if height <= 0 or count <= height:
        return 0
    if selected < 0:
        selected = 0
    if selected >= offset + height:
        offset = selected - height + 1
    if selected < offset:
        offset = selected
    max_offset = count - height
    return max(0, min(offset, max_offset))


def render_lines(
    fleet: Fleet,
    selected: int = -1,
    width: int = 32,
    offset: int = 0,
    height: int | None = None,
) -> list[str]:
    """Pure text rendering of one frame — exactly what gets drawn, no curses.

    `offset`/`height` are an optional viewport window mirroring the curses
    draw loop's scroll-follows-selection behaviour (sidebar-polish item 3),
    so tests can assert on scrolled output without a curses TTY. Omitting
    `height` (the default) renders every row, unwindowed — the original
    behaviour.

    No animation, curses-only (bus-message-specifying B5, same "curses-only"
    split as the pre-existing spinner/blink animation): a repeated render of
    the same Fleet is byte-identical. Most rows render one line; an "agent"
    row renders 1 or 2 (quote, then its subordinate attribution line) per
    `identity_block` — `_agent_expansion_fits` decides once, for the whole
    frame, whether there's real room for the second line, so the extra
    lines are a property of the actual available height, never a per-row
    guess (operator ruling, 2026-07-26). The extra attribution line carries
    no selection marker of its own — it is not a separate Row."""
    rows = flatten(fleet)
    if not rows:
        return [_truncate(NO_ACTIVITY_TEXT, width)]

    expand = _agent_expansion_fits(rows, height)
    if height is None:
        window, start = rows, 0
    else:
        offset = clamp_scroll_offset(offset, selected, len(rows), height)
        window, start = rows[offset:offset + height], offset

    lines = []
    for i, row in enumerate(window, start=start):
        marker = ">" if i == selected else " "
        if row.kind == "feature":
            indent = INDENT_UNIT * row.depth
            avail = max(width - len(marker) - len(indent), 0)
            glyph = STATUS_EMOJI.get(row.status, "○")
            # A feature carries no percentage of its own (operator ruling,
            # 2026-07-26) — pct=None, so compose_feature_row_text's tail is
            # empty; the pane's own dimmer background band (curses-only,
            # `_draw_feature_row`) is what sets a feature row apart from a
            # task row, not a number.
            body = compose_feature_row_text(glyph, row.label, None, avail)
            lines.append(_truncate(f"{marker}{indent}{body}", width))
        elif row.kind == "task":
            indent = INDENT_UNIT * row.depth
            avail = max(width - len(marker) - len(indent), 0)
            glyph = STATUS_EMOJI.get(row.status, "○")
            body = compose_task_row_text(glyph, row.label, row.progress_glyph, avail)
            lines.append(_truncate(f"{marker}{indent}{body}", width))
        elif row.kind == "agent":
            body_lines = _agent_row_lines(row, max(width - len(marker), 0), expand)
            lines.append(_truncate(marker + body_lines[0], width))
            lines.extend(_truncate(" " * len(marker) + extra, width) for extra in body_lines[1:])
        else:
            lines.append(_truncate(marker + _row_text(row), width))
    return lines


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
# Project header text (pure) — sidebar-titling OVERRIDE 1
# --------------------------------------------------------------------------

def render_header_line(title: str, width: int) -> str:
    """Title centred over `width` columns, space-padded both sides — the
    text drawn on top of the curses solid-hue header block."""
    if width <= 0:
        return ""
    text = _truncate(title, width)
    pad = width - len(text)
    left = pad // 2
    return (" " * left) + text + (" " * (pad - left))


# --------------------------------------------------------------------------
# Curses colour management
# --------------------------------------------------------------------------

def _init_colours() -> dict[str, int]:
    """Colour-pair attrs per status, used ONLY by the still-unrebuilt
    subagent/courier rows (bus-message-specifying B5 item 9 — "verify, don't
    rebuild"); empty dict (attr 0 everywhere) if the terminal has no colour
    support. Feature/repo-header rows use `_ColourCache` instead (below)."""
    if not curses.has_colors():
        return {}
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK

    curses.init_pair(1, curses.COLOR_YELLOW, bg)   # working
    curses.init_pair(2, curses.COLOR_CYAN, bg)     # waiting
    curses.init_pair(3, curses.COLOR_WHITE, bg)    # idle
    curses.init_pair(4, curses.COLOR_WHITE, bg)    # awaiting_agent (dim white)
    curses.init_pair(5, curses.COLOR_GREEN, bg)    # done
    curses.init_pair(6, curses.COLOR_RED, bg)      # failed — never shares done's pair

    return {
        "working": curses.color_pair(1),
        "waiting": curses.color_pair(2),
        "idle": curses.color_pair(3) | curses.A_DIM,
        "awaiting_agent": curses.color_pair(4) | curses.A_DIM,
        "done": curses.color_pair(5) | curses.A_BOLD,
        "failed": curses.color_pair(6) | curses.A_BOLD,
    }


def _rgb_to_curses(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """0-255 RGB -> curses' 0-1000 init_color scale."""
    return tuple(round(c * 1000 / 255) for c in rgb)


# curses.COLORS reported by a `*-direct` terminfo entry (colors#0x1000000).
_DIRECT_COLOUR_THRESHOLD = 1 << 24


def _has_direct_colour() -> bool:
    """True once the active terminfo entry is a direct-colour one (`*-direct`,
    selected at process start by `_select_display_term`) — `curses.COLORS`
    is the tell, since that's the one fact `setupterm`/`initscr` computes
    from the terminfo `colors#` capability. Under direct colour there is no
    palette to redefine, so `curses.can_change_color()` stops being
    relevant and is never consulted."""
    return curses.has_colors() and curses.COLORS >= _DIRECT_COLOUR_THRESHOLD


def _rgb_to_direct_colour_id(rgb: tuple[int, int, int]) -> int:
    """Packed-RGB colour id a direct-colour terminfo entry expects: its
    `setaf`/`setb` decode any colour number >= 8 as r*65536 + g*256 + b
    (confirmed against tmux-direct/xterm-direct's terminfo source) — exact,
    no palette allocation and no `_rgb_to_xterm256` approximation."""
    r, g, b = rgb
    return (r << 16) | (g << 8) | b


# The 6 steps (0-5) of the xterm-256 colour cube map to these 0-255 values.
_XTERM256_CUBE_STEPS = (0, 95, 135, 175, 215, 255)


def _nearest_cube_step(v: int) -> int:
    return min(range(6), key=lambda i: abs(v - _XTERM256_CUBE_STEPS[i]))


# Above this max-minus-min channel spread, an RGB triple carries real hue
# and must never be approximated away onto the grayscale ramp — chosen
# below the orchids header purple's spread (38) and above the muted
# near-grays (HEADER_FG/MUTED, 16) that are meant to fall through to gray.
_NEAR_NEUTRAL_CHROMA = 24


def _rgb_to_xterm256(rgb: tuple[int, int, int]) -> int:
    """Nearest xterm-256 palette index for a 0-255 RGB triple — sidebar-
    titling item 1: lets a colour render on a terminal that reports 256
    colours but not `can_change_color()` (no custom RGB), by picking a fixed
    palette slot instead. Only searches the machine-computable ranges: the
    6x6x6 colour cube (indices 16-231) and the 24-step grayscale ramp
    (232-255) — never the 16 standard colours, whose actual RGBs vary per
    terminal theme and so cannot be matched reliably.

    A chromatic colour (chroma above `_NEAR_NEUTRAL_CHROMA`) always maps
    into the cube: the ramp's coarse 10-unit steps can sit numerically
    closer than the cube's own coarse 40-95-unit steps for a dark,
    desaturated-but-still-hued colour, which silently erases its hue (the
    orchids header purple used to land in the gray ramp this way). Only a
    genuinely near-neutral triple is left to the distance comparison."""
    r, g, b = rgb
    ri, gi, bi = _nearest_cube_step(r), _nearest_cube_step(g), _nearest_cube_step(b)
    cube_index = 16 + 36 * ri + 6 * gi + bi
    if max(r, g, b) - min(r, g, b) > _NEAR_NEUTRAL_CHROMA:
        return cube_index

    cube_rgb = (_XTERM256_CUBE_STEPS[ri], _XTERM256_CUBE_STEPS[gi], _XTERM256_CUBE_STEPS[bi])
    gray_index = max(0, min(23, round(((r + g + b) / 3 - 8) / 10)))
    gray_value = 8 + gray_index * 10
    gray_rgb = (gray_value, gray_value, gray_value)

    def _dist2(a: tuple[int, int, int], b_: tuple[int, int, int]) -> int:
        return sum((a[i] - b_[i]) ** 2 for i in range(3))

    if _dist2(cube_rgb, rgb) <= _dist2(gray_rgb, rgb):
        return cube_index
    return 232 + gray_index


# Colour-pair ids reserved for per-agent tint (sidebar-polish item 4, still
# used for subagent/courier rows) — kept clear of the 1-6 status pairs above and
# of `_ColourCache`'s lazily-allocated range (see its _FIRST_* constants).
_AGENT_PAIR_BASE = 10


def _init_agent_colours() -> list[int] | None:
    """One colour-pair attr per ORCHID_PALETTE entry, or None if the
    terminal can't support it — callers must fall back to no per-agent
    colour (default text colour) rather than crash."""
    if not curses.has_colors():
        return None
    try:
        direct = _has_direct_colour()
        can_custom = not direct and curses.COLORS >= 256 and curses.can_change_color()
        pairs = []
        for i, (_name, rgb, ansi_fallback) in enumerate(ORCHID_PALETTE):
            pair_id = _AGENT_PAIR_BASE + i
            if direct:
                curses.init_pair(pair_id, _rgb_to_direct_colour_id(rgb), -1)
            elif can_custom:
                colour_id = 64 + i  # arbitrary custom slot, above the 16 standard ones
                r, g, b = _rgb_to_curses(rgb)
                curses.init_color(colour_id, r, g, b)
                curses.init_pair(pair_id, colour_id, -1)
            else:
                curses.init_pair(pair_id, ansi_fallback, -1)
            pairs.append(curses.color_pair(pair_id))
        return pairs
    except curses.error:
        return None  # limited terminal — no per-agent colour, not a crash


def _agent_colour_key(row: Row) -> str:
    """A stable identity per live agent row: repo/feature rows are unique by
    target; sibling subagent rows share a target, so label joins in."""
    if row.kind == "subagent":
        return f"{row.target}/{row.label}"
    return row.target


def _agent_colour_index(key: str) -> int:
    return zlib.crc32(key.encode("utf-8")) % len(ORCHID_PALETTE)


class _ColourCache:
    """Lazily allocates curses colour pairs for arbitrary (fg_rgb, bg_rgb)
    combinations — the mock's palette is far richer than a fixed small set
    of pre-declared pairs, so pairs/colours are registered on first use
    instead (bus-message-specifying B5 item 10: "extend the existing
    mechanism to the mock's palette", generalising the pattern the old
    `_init_header_colours`/`_init_agent_colours` used for one hue set each).

    Exact RGB via `_rgb_to_direct_colour_id` when the active terminfo entry
    is direct-colour (`_has_direct_colour()`, set up by
    `_select_display_term` at process start); otherwise 24-bit via
    `curses.init_color` when the terminal reports `can_change_color()`;
    otherwise each RGB maps to its nearest xterm-256 palette index via
    `_rgb_to_xterm256` — the same fallback the header/agent colours already
    used. Silently degrades to attribute-only styling (dim/italic/bold, no
    colour) once the colour-pair or custom-colour budget runs out, or on a
    colourless terminal — never raises."""

    _FIRST_COLOUR_ID = 128  # clear of agent (64+) and status-pair ranges
    _FIRST_PAIR_ID = 50     # clear of status pairs (1-6) and agent pairs (10-17)

    def __init__(self) -> None:
        self.enabled = curses.has_colors()
        self._direct = self.enabled and _has_direct_colour()
        self._can_custom = (
            self.enabled and not self._direct
            and curses.COLORS >= 256 and curses.can_change_color()
        )
        self._colour_ids: dict[tuple[int, int, int], int] = {}
        self._pair_ids: dict[tuple[tuple[int, int, int], tuple[int, int, int] | None], int] = {}
        self._next_colour_id = self._FIRST_COLOUR_ID
        self._next_pair_id = self._FIRST_PAIR_ID

    def _colour_id(self, rgb: tuple[int, int, int]) -> int:
        if rgb in self._colour_ids:
            return self._colour_ids[rgb]
        if self._direct:
            colour_id = _rgb_to_direct_colour_id(rgb)
        else:
            colour_id = _rgb_to_xterm256(rgb)
            if self._can_custom and self._next_colour_id < curses.COLORS:
                candidate = self._next_colour_id
                self._next_colour_id += 1
                try:
                    r, g, b = _rgb_to_curses(rgb)
                    curses.init_color(candidate, r, g, b)
                    colour_id = candidate
                except curses.error:
                    pass
        self._colour_ids[rgb] = colour_id
        return colour_id

    def _pair_id(self, fg: tuple[int, int, int], bg: tuple[int, int, int] | None) -> int:
        key = (fg, bg)
        if key in self._pair_ids:
            return self._pair_ids[key]
        if not self.enabled or self._next_pair_id >= curses.COLOR_PAIRS:
            return 0
        pair_id = self._next_pair_id
        fg_id = self._colour_id(fg)
        bg_id = self._colour_id(bg) if bg is not None else -1
        try:
            curses.init_pair(pair_id, fg_id, bg_id)
        except curses.error:
            return 0
        self._next_pair_id += 1
        self._pair_ids[key] = pair_id
        return pair_id

    def pair(
        self, fg: tuple[int, int, int], bg: tuple[int, int, int] | None = None,
        dim: bool = False, italic: bool = False, bold: bool = False,
    ) -> int:
        attr = 0
        pair_id = self._pair_id(fg, bg)
        if pair_id:
            attr = curses.color_pair(pair_id)
        if dim:
            attr |= curses.A_DIM
        if italic:
            attr |= curses.A_ITALIC
        if bold:
            attr |= curses.A_BOLD
        return attr


# --------------------------------------------------------------------------
# Terminal setup — TERM upgrade to a direct-colour terminfo entry, applied
# once at process start (before curses ever calls setupterm/initscr).
# --------------------------------------------------------------------------

def _truecolor_advertised() -> bool:
    return os.environ.get("COLORTERM", "").strip().lower() in ("truecolor", "24bit")


def _direct_term_name(term: str) -> str | None:
    if not term.endswith("-256color"):
        return None
    return term[: -len("-256color")] + "-direct"


def _terminfo_has_direct_colour(term: str) -> bool:
    try:
        fd = sys.__stdout__.fileno() if sys.__stdout__ else 1
        curses.setupterm(term, fd)
        return curses.tigetnum("colors") >= _DIRECT_COLOUR_THRESHOLD
    except Exception:
        return False  # missing entry, no fd, or any other terminfo failure


def _select_display_term(term: str) -> str:
    """Upgrades TERM to its `*-direct` terminfo counterpart (tmux-256color
    -> tmux-direct, xterm-256color -> xterm-direct, matching the actual TERM
    family) when the outer terminal advertises truecolor (COLORTERM) and
    that entry actually exists on this machine — so ncurses accepts exact
    RGB values as colour numbers and no approximation (`_rgb_to_xterm256`)
    ever runs. Falls back to the original TERM, unchanged, when either
    condition fails."""
    if not _truecolor_advertised():
        return term
    candidate = _direct_term_name(term)
    if candidate and _terminfo_has_direct_colour(candidate):
        return candidate
    return term


def _safe_addstr(stdscr, y: int, x: int, text: str, attr: int) -> None:
    if not text:
        return
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass  # bottom-right cell write raises; harmless, just skip it


def _safe_addch(stdscr, y: int, x: int, ch: str, attr: int) -> None:
    """Single-cell-safe write for a row painted edge-to-edge (a header/
    feature/step full-width band, or an open-block background fill). The
    window's own LAST column needs `insch`, never `addstr` — verified
    against a real capture (2026-07-26, this tmux+ncurses build):
    `addstr`ing the rightmost column triggers the terminal's auto-wrap
    cursor advance, which then desyncs the colour-pair state for whatever
    gets drawn on the NEXT row — that row's own background silently
    vanishes even though it never touched the corrupted column itself
    (reproduced in isolation, bisected down to exactly `x == width - 1`).
    `insch` inserts without moving the cursor past the edge, avoiding that
    corruption — but ncurses' legacy narrow `insch` cannot safely carry an
    arbitrary (possibly multi-byte) Unicode character (verified the same
    way: a truncation ellipsis landing on that exact column came out as
    mojibake), so the true content character is dropped in favour of a
    plain space there — the row's BACKGROUND still reaches this cell
    edge-to-edge, only the text glyph doesn't, an acceptable one-column
    trade against a real corruption bug. Uses the window's OWN reported
    width (`getmaxyx`), not a caller-supplied one, so every call site gets
    this for free without having to track the real edge itself."""
    _, max_x = stdscr.getmaxyx()
    if x == max_x - 1:
        try:
            stdscr.insch(y, x, ord(" "), attr)
        except curses.error:
            pass
        return
    _safe_addstr(stdscr, y, x, ch, attr)


# --------------------------------------------------------------------------
# Curses drawing — repo header
#
# BLOCK layout (operator spec, 2026-07-28, reproducing the operator's own
# tmux `window-status-current-format` technique against the repo's own
# hue): a fixed-size CORE (" TITLE ", filled with PRIMARY) sits centred in
# the row, flanked by `_header_ramp_cells()` gradient cells each side that
# TAME the primary down toward SECONDARY (mirrored), with flat secondary
# fill beyond that to the row's edges. Each ramp cell carries TWO
# interpolated tones at once via a half-block glyph (`▐`/`▌`) — one tone as
# the glyph's foreground (the half nearer the core), the other as its
# background (the half nearer the fill) — the same trick that lets tmux's
# own ramp read as more steps than it has cells. "No space for gradients,
# no gradient, easy" (operator, 2026-07-28): the title is NEVER shrunk to
# make room for the ramp — `_header_gradient_fits` is the one threshold
# that decides ramp-or-not, computed from the title's OWN untruncated
# width, never the reverse.
#
# TEMPORARY A/B SWITCH (operator, 2026-07-28: his own dictated "three
# cells" and the tmux reference he pointed at — which spends only TWO
# cells per side and reaches four perceptual steps via the half-block
# trick — are two different builds, and he was never asked to choose
# between them explicitly; he then ruled choices must never be buried in
# prose again). `_header_ramp_cells()` reads `SIDEBAR_HEADER_RAMP_VARIANT`
# so two panes can run side by side differing ONLY in this one knob:
# "two-cell" (the tmux reference's own proportions) or "three-cell" (his
# literal dictation, the default when unset — the closer reading of his
# actual words). A companion sower wires the env var through and shows the
# active variant in the pane title; this module only reads it. Narrow and
# obviously temporary: it exists purely for that A/B and comes back out
# once he picks.
# --------------------------------------------------------------------------

_HEADER_RAMP_VARIANT_ENV = "SIDEBAR_HEADER_RAMP_VARIANT"
_HEADER_RAMP_CELLS_BY_VARIANT = {"two-cell": 2, "three-cell": 3}
_HEADER_RAMP_DEFAULT_VARIANT = "three-cell"
_HEADER_RAMP_IN = "▐"   # left ramp (entering the core): glyph fg on the RIGHT half — nearer the core
_HEADER_RAMP_OUT = "▌"  # right ramp (leaving the core): glyph fg on the LEFT half — nearer the core


def _header_ramp_cells() -> int:
    """Gradient cells per side, right now — see the A/B switch note above.
    An unrecognised or unset value falls back to the default variant
    rather than raising, the same fail-open rule this file uses
    everywhere else for environment-sourced input."""
    variant = os.environ.get(_HEADER_RAMP_VARIANT_ENV, _HEADER_RAMP_DEFAULT_VARIANT)
    return _HEADER_RAMP_CELLS_BY_VARIANT.get(
        variant, _HEADER_RAMP_CELLS_BY_VARIANT[_HEADER_RAMP_DEFAULT_VARIANT],
    )


def _header_core_width(title: str) -> int:
    """The core's own width — the title's cell width plus one space of
    padding each side — computed independently of the available row width,
    since the title is what decoration yields to, never the reverse."""
    return _cell_width(title) + 2


def _header_gradient_fits(title: str, width: int, ramp_cells: int) -> bool:
    """True once `width` can hold the title's own FULL core plus a FULL
    ramp of `ramp_cells` on each side. This is the one on/off switch
    (operator: "no space for gradients, no gradient, easy") — there is no
    partial ramp and the title is never truncated to manufacture room for
    one."""
    return width >= _header_core_width(title) + 2 * ramp_cells


def _header_ramp_tone(
    steps: list[tuple[int, int, int]], k: int,
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """(inner, outer) tones for ramp cell `k` (0 = adjacent to the core,
    the outermost cell = adjacent to the flat fill) — identical
    mapping on both sides of the core; only the glyph (and so which
    physical half of the cell "inner" lands on) differs between them."""
    return steps[2 * k], steps[2 * k + 1]


def _draw_header(
    stdscr, y: int, width: int, title: str, paused: bool, selected: bool,
    colours: _ColourCache,
) -> None:
    """Per-repo BLOCK header (operator spec, 2026-07-28 — supersedes the
    earlier monotonic left-to-right gradient: "brighter, intense... each
    side a 3 cell gradient to the first fade colour, block layout like the
    window name in the status bar", corrected same day to tame OUTWARD
    from the intense colour rather than highlight inward — see
    `colour_ramp_steps`). PAUSED stays flat light-gray, no gradient, exactly
    as before. `selected` means "the cursor is here AND the user has
    actually moved it" (see `_draw`'s `has_moved`) — A_REVERSE never
    appears merely because `selected == 0` is the resting default.

    The title's "thin" look is still `_muted_toward` (never `curses.A_DIM`,
    see that function's docstring), run through `ensure_contrast` against
    whatever it actually sits on (`PAUSED_HEADER_GRAY` or the primary) —
    the fixed crossover-aware helper, never an assumed black/white or a
    `luminance < 0.5` threshold (that was the bug, see `ensure_contrast`'s
    own docstring). The core's background is uniform, so — unlike the old
    per-column gradient — this is computed ONCE per row, not once per
    column.

    Both non-paused branches below reserve the row's own literal LAST
    column for background only, via `render_header_line(title, width - 1)`
    (never the title's own trailing glyph): `_safe_addch` blanks whatever
    character lands on that column to a plain space, and a multi-byte
    ellipsis landing there used to vanish silently rather than render (a
    long repo name truncating to "orc" with no "…" at width 4) — the same
    one-column reservation `_step_row_display_text`/`_draw_feature_row`/
    `_draw_task_row` already make. The gradient branch does not need the
    same reservation for its own ramp glyphs: the outermost ramp cell's
    "outer" tone is already exactly `secondary` (`_header_ramp_tone`), so
    if that glyph happens to land on the last column and gets blanked to a
    plain space, what shows through is that same flat secondary tone —
    correct, not merely harmless."""
    reverse = curses.A_REVERSE if selected else 0
    if width <= 0:
        return

    def _draw_flat_block(bg: tuple[int, int, int]) -> None:
        text = render_header_line(title, max(width - 1, 0))
        fg = ensure_contrast(_muted_toward(HEADER_FG, bg), bg, _CONTRAST_MIN_TEXT)
        attr = colours.pair(fg, bg) | reverse
        for col in range(width):
            ch = text[col] if col < len(text) else " "
            _safe_addch(stdscr, y, col, ch, attr)

    if paused:
        _draw_flat_block(PAUSED_HEADER_GRAY)
        return

    hue = _repo_hue(title)
    roles = repo_colour_roles(hue)
    primary, secondary = roles.primary, roles.secondary
    ramp_cells = _header_ramp_cells()

    if not _header_gradient_fits(title, width, ramp_cells):
        _draw_flat_block(primary)
        return

    core_width = _header_core_width(title)
    decorated_width = core_width + 2 * ramp_cells
    left_fill = (width - decorated_width) // 2
    right_fill = (width - decorated_width) - left_fill

    ramp = colour_ramp_steps(primary, secondary, ramp_cells * 2)
    core_fg = ensure_contrast(_muted_toward(HEADER_FG, primary), primary, _CONTRAST_MIN_TEXT)
    core_attr = colours.pair(core_fg, primary) | reverse
    fill_attr = colours.pair(MUTED, secondary) | reverse

    col = 0
    for _ in range(left_fill):
        _safe_addch(stdscr, y, col, " ", fill_attr)
        col += 1
    for k in reversed(range(ramp_cells)):
        inner, outer = _header_ramp_tone(ramp, k)
        _safe_addch(stdscr, y, col, _HEADER_RAMP_IN, colours.pair(inner, outer) | reverse)
        col += 1
    for ch in f" {title} ":
        _safe_addch(stdscr, y, col, ch, core_attr)
        col += 1
    for k in range(ramp_cells):
        inner, outer = _header_ramp_tone(ramp, k)
        _safe_addch(stdscr, y, col, _HEADER_RAMP_OUT, colours.pair(inner, outer) | reverse)
        col += 1
    for _ in range(right_fill):
        _safe_addch(stdscr, y, col, " ", fill_attr)
        col += 1


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

    attr_extra = curses.A_BOLD if selected else 0
    for col, ch in enumerate(text[:width]):
        fg = styles[col] if col < len(styles) else _muted_toward(MUTED, fill_rgb)
        attr = colours.pair(fg, fill_rgb) | attr_extra
        _safe_addch(stdscr, y, col, ch, attr)
    # The band covers the FULL row width, including any trailing columns
    # past the composed text (name shorter than the pane) — a feature row
    # reads as a solid band, not a highlighted word.
    for col in range(len(text), width):
        _safe_addch(stdscr, y, col, " ", colours.pair(_muted_toward(MUTED, fill_rgb), fill_rgb) | attr_extra)


# --------------------------------------------------------------------------
# Curses drawing — the generic row path (task/step/agent/subagent). These
# used to be decorations hanging off a "working" feature row (phase label,
# identity line, phase checklist, footer); the six-level tree (2026-07-26)
# makes each of them a real Row in its own right instead, so they draw
# through the same plain path as any other non-feature row below — no
# separate decoration mechanism is needed any more. `footer_lines()`/
# `done_footer_line()` remain as pure formatters (still exercised directly;
# build_model() has never populated a source for them) but nothing in the
# live draw path calls them.
# --------------------------------------------------------------------------

# A "block" background — set once a step is OPEN (its own line, plus every
# agent/subagent line nested inside it) — is threaded down to these three
# functions as `bg: tuple[int, int, int] | None`: None outside any open
# step (task/feature/repo rows never get one), the step's own
# `open_stage_colour(...)` otherwise (operator ruling, 2026-07-26, colour
# direction corrected 2026-07-27: "the agent and subagent lines do sit on
# the step's background... specifically the [subdued] variant, and
# specifically so that the block has visible bounds" — the whole open
# region reads as ONE contiguous block, LIGHTER than its own section
# title, never darker or the plain background — see `open_stage_colour`).
# A constant, small breathing indent replaces the old depth-scaled one here
# (curses-only — depth is now colour, not columns; the plain-text path
# still uses `INDENT_UNIT * row.depth`, see `render_lines`, since it has no
# colour to carry structure with).
_BLOCK_CONTENT_INDENT = "  "


def _fill_row_bg(stdscr, y: int, width: int, bg: tuple[int, int, int], colours: _ColourCache) -> None:
    attr = colours.pair(MUTED, bg)
    _safe_addstr(stdscr, y, 0, " " * max(width - 1, 0), attr)
    if width > 0:
        _safe_addch(stdscr, y, width - 1, " ", attr)


def _open_block_bg(row: Row) -> tuple[int, int, int] | None:
    """The open step's own block background this row sits inside —
    derived straight from `row.task_colour` (Ct, grade 2, threaded onto
    every row under an open task at model-build time — see `_task_rows`),
    so no separate state needs tracking across `_draw`'s row loop. None
    only for a row with no owning task at all (shouldn't happen for an
    agent/subagent in practice — they only ever render under an open
    step — but never crashes if it does)."""
    if row.task_colour is None:
        return None
    return open_stage_colour(content_colour_base(row.task_colour))


# The SELECTED row's own highlight (sidebar-teamwork defect 4, 2026-07-27):
# a further lift toward WHITE from whatever background the row already
# carries (plain black when it carries none of its own), rather than
# `curses.A_REVERSE` — a straight foreground/background swap did "very
# little work" on screen, because on this file's own truecolor bands two
# already-similar tones can swap onto each other and read as unchanged, and
# a swapped pair's OWN readability was never separately checked (only the
# un-swapped direction ever ran through `ensure_contrast`). A colour LIFT
# is checked exactly the same way every other derived colour in this file
# already is — every caller re-runs `ensure_contrast` against the LIFTED
# background it actually painted, so the guarantee holds by construction,
# not by assuming a swap preserves it. Paired with `curses.A_BOLD` for a
# second, colour-independent cue — safe over a custom background; Decision-
# 111 found the corruption specific to `A_DIM`, never bold.
_SELECTION_LIFT_FRACTION = 0.30


def _selection_highlight(bg: tuple[int, int, int] | None) -> tuple[int, int, int]:
    return lerp(bg if bg is not None else (0, 0, 0), WHITE, _SELECTION_LIFT_FRACTION)


def _draw_identity_block(
    stdscr, y: int, width: int, row: Row, selected: bool, expand: bool, colours: _ColourCache,
) -> int:
    """Draws the agent's quote + subordinate attribution (see
    `identity_block`'s docstring for the exact ladder) — 1 or 2 curses rows
    depending on `expand`; returns the next unused y. Shares its content
    decisions (`attribution_text`/`tight_line_parts`) with the pure text
    path so the two can never disagree; only the per-segment colouring
    (quote plain ITALIC, role dim-italic, model tier-coloured) is
    curses-only. The owning step's open-block colour (`_open_block_bg`) is
    painted across the FULL row width first, then every foreground colour
    is contrast-checked against it (operator ruling, 2026-07-26: legible
    text on the dimmed background is a hard requirement, achieved by
    adjusting the foreground, never by dimming the content itself — so the
    role/model text below drops its old A_DIM attribute in favour of an
    explicitly contrast-safe colour). `selected` swaps in `_selection_
    highlight` for the block's own background (sidebar-teamwork defect 4)
    rather than `curses.A_REVERSE` — always painted, even when this row had
    no open-block background of its own, so the pick is unmistakable
    whatever row kind it lands on."""
    bg = _open_block_bg(row)
    if selected:
        bg = _selection_highlight(bg)
    indent = _BLOCK_CONTENT_INDENT
    content_width = max(width - len(indent), 0)
    attr_extra = curses.A_BOLD if selected else 0
    block_bg = bg if bg is not None else (0, 0, 0)
    quote_fg = ensure_contrast(TEXT, block_bg, _CONTRAST_MIN_TEXT)
    role_fg = ensure_contrast(MUTED, block_bg, _CONTRAST_MIN_TEXT)

    if bg is not None:
        _fill_row_bg(stdscr, y, width, bg, colours)
        if expand:
            _fill_row_bg(stdscr, y + 1, width, bg, colours)

    if not expand:
        shown_quote, tail = tight_line_parts(row.activity, row.role, content_width)
        _safe_addstr(stdscr, y, 0, _truncate(indent + shown_quote, width),
                     colours.pair(quote_fg, bg, italic=True) | attr_extra)
        if tail:
            x = len(indent) + _cell_width(shown_quote)
            _safe_addstr(stdscr, y, x, _truncate(tail, max(width - x, 0)),
                         colours.pair(role_fg, bg, italic=True) | attr_extra)
        return y + 1

    quote = _quoted_activity(row.activity)
    _safe_addstr(stdscr, y, 0, _truncate(indent + quote, width),
                 colours.pair(quote_fg, bg, italic=True) | attr_extra)
    if not row.role:
        return y + 1
    y += 1
    attribution_width = max(content_width - len(_ATTRIBUTION_INDENT), 0)
    role_text, model_text = attribution_text(row.role, row.model, attribution_width)
    x = 0
    x += len(indent) + len(_ATTRIBUTION_INDENT)
    prefix = "— "
    _safe_addstr(stdscr, y, x, prefix, colours.pair(role_fg, bg) | attr_extra)
    x += len(prefix)
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
) -> int:
    """A subagent's own line — presence glyph (`_row_text`'s existing
    scheduled/doing/done/failed vocabulary) + label, on the owning step's
    open-block background (see `_draw_identity_block`'s docstring for why),
    full width, contrast-checked. `selected` swaps in `_selection_highlight`
    for the block's own background (sidebar-teamwork defect 4), same as
    `_draw_identity_block`."""
    bg = _open_block_bg(row)
    if selected:
        bg = _selection_highlight(bg)
    block_bg = bg if bg is not None else (0, 0, 0)
    fg = ensure_contrast(
        _SUBAGENT_TERMINAL_FG.get(row.status, TEXT), block_bg, _CONTRAST_MIN_TEXT,
    )
    attr_extra = curses.A_BOLD if selected else 0
    if bg is not None:
        _fill_row_bg(stdscr, y, width, bg, colours)
    glyph = (STATUS_EMOJI[row.status] if row.status in TERMINAL_TASK_STATUSES
             else _SUBAGENT_LIVE_GLYPH.get(row.status, SUBAGENT_GLYPH))
    text = _truncate(f"{_BLOCK_CONTENT_INDENT}{glyph} {row.label}", width)
    _safe_addstr(stdscr, y, 0, text, colours.pair(fg, bg) | attr_extra)
    return y + 1


_TASK_BAR_GLYPH = "▎"


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
    """A task's own row: a single accent BAR cell — background B
    (`hue["fill"]`, grade 1), foreground Ct (grade 2, `row.task_colour`,
    already allocated once per feature by `_assign_task_colours` within
    its feature's own hue range, so two open tasks are told apart by bar
    colour alone) — followed by its name and right-aligned progress circle
    as PLAIN text, no background (operator spec, 2026-07-26: this is what
    keeps a task row visibly distinct from a feature row's own full solid
    band). A terminal task's own green/"failed" colour always wins over
    its Ct tint, same exclusivity rule as before. The status glyph itself
    is `_task_row_glyph` (operator ruling, 2026-07-27) — cycling while
    working, static otherwise. `selected` swaps in `_selection_highlight`
    for the row's own background B (sidebar-teamwork defect 4) rather than
    `curses.A_REVERSE` — every foreground below is already run through
    `ensure_contrast` against `bg`, so substituting the lifted background
    before those calls keeps the guarantee automatically."""
    bg = hue["fill"]
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
) -> int:
    """One line of the task's five-step accordion (operator correction,
    2026-07-26: "collapse keeps the line" — every step gets its own row,
    always), FULL WIDTH from cell 1, CENTRED, small caps.

    EVERY step title — done, active, or todo alike — carries the SAME flat
    CONTENT colour (grade 3, `content_colour_base(row.task_colour)`,
    operator ruling 2026-07-27: "every step title carries the same
    section-title background... being active is expressed by its mark,
    its sweep and by what appears beneath it, NOT by changing the title's
    own background" — supersedes the earlier reading where the active
    title itself sat on a separately-darkened `open_stage_colour`). If the
    ACTIVE step is also LIVE (a genuinely "working" agent on it, not
    merely the furthest-along position — `row.live`, see `_step_row`/the
    model-layer function of the same name) it additionally carries the
    MOVING GRADIENT sweep — reusing the pre-existing lifted-band
    triangular-wave geometry (`band_position`/`band_span`/
    `band_column_colour`) at the row's own full width, brightening this
    SAME content colour rather than a separately-darkened one. No room/no
    motion just means a static (but still correctly coloured) block
    (ANIMATION CAVEAT: a missing animation must never mean a missing
    step). `selected` swaps in `_selection_highlight` for the step's own
    content colour (sidebar-teamwork defect 4) rather than `curses.
    A_REVERSE` — every foreground below is already run through `ensure_
    contrast` against `content`/the sweep's own `bg`, so substituting the
    lifted colour before those calls keeps the guarantee automatically."""
    content = content_colour_base(row.task_colour or MUTED)
    if selected:
        content = _selection_highlight(content)
    attr_extra = curses.A_BOLD if selected else 0
    text = _step_row_display_text(row, width)

    if row.status != "active":
        fg = ensure_contrast(_STEP_LINE_COLOUR.get(row.status, MUTED), content, _CONTRAST_MIN_TEXT)
        for col, ch in enumerate(text):
            _safe_addch(stdscr, y, col, ch, colours.pair(fg, content) | attr_extra)
        return y + 1

    if row.live:
        span = band_span(max(width - 1, 1))
        pos = band_position(tick, span)
        for col, ch in enumerate(text):
            bg = band_column_colour(col, pos, width, content) or content
            fg = ensure_contrast(TEXT, bg, _CONTRAST_MIN_TEXT)
            _safe_addch(stdscr, y, col, ch, colours.pair(fg, bg) | attr_extra)
    else:
        fg = ensure_contrast(TEXT, content, _CONTRAST_MIN_TEXT)
        for col, ch in enumerate(text):
            _safe_addch(stdscr, y, col, ch, colours.pair(fg, content) | attr_extra)
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
    # by every "task" row until the next one (a task row needs grade 1's
    # "B" for its bar's background; feature/step/agent/subagent rows carry
    # everything colour-related they need directly on the Row already, see
    # `task_colour`/`_open_block_bg`).
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
            y = _draw_step_row(stdscr, y, max_x, row, i == selected, colours, tick)
            continue
        if row.kind == "agent":
            y = _draw_identity_block(stdscr, y, max_x, row, i == selected, expand, colours)
            continue
        if row.kind == "subagent":
            y = _draw_subagent_row(stdscr, y, max_x, row, i == selected, colours)
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
    if "--once" in sys.argv[1:]:
        sys.exit(_run_once())
    curses.wrapper(main)

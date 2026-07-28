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
# Identity BLOCK — a quote with a subordinate attribution, book-epigraph
# style (operator ruling, 2026-07-26, SUPERSEDES the single-line `identity_
# line_text` above as the agent row's live render; that function stays
# defined/tested but nothing in the draw path calls it any more). Citation
# punctuation restored 2026-07-28 (operator, verbatim: "the rulestays (or
# comes back): middle dot between then, full odel name (minus Claude) and
# version, if clipping use abreviatiob, if stil clipping remove model, if
# stilll clipping usual ellipsis rule" — a RESTORATION, not an invention).
#
# The status is volatile and is the thing being scanned for, so it carries
# the news as the quote; role/model are stable context, subordinate. TWO
# layouts (operator: "one line citation style if space... otherwise the
# citation is just below the text"), chosen by `expand` — the caller's
# real-available-height decision (`_agent_expansion_fits`), unchanged by
# this step:
#
#   tight (expand=False, the row's own WIDTH-driven ladder — the common
#   case, since a 1-line row costs no extra height):
#     "activity" — role · model            (full model, the rare case:
#                                            "It's all relative" — Albert
#                                            Einstein · Opus 14.2)
#     "activity" — role · shortmodel        (model doesn't fit -> abbreviate)
#     "activity" — role                    (still doesn't fit -> drop model
#                                            entirely — never a dangling
#                                            middle dot)
#     "activ…"                              (even quote+role doesn't fit ->
#                                            role drops too, ordinary
#                                            ellipsis rule on the quote
#                                            alone, ``_truncate``)
#   expand (2 lines, HEIGHT-permitting only):
#     "activity"
#         role · model                      (full, then short, then no
#                                            model — same ladder, NO dash:
#                                            "no ash obviuouys" once the
#                                            citation is its own line —
#                                            indented a few blanks, chosen
#                                            over right-aligned because the
#                                            indent already existed here)
#
# The quote itself never drops in either layout. Which LAYOUT applies
# (tight vs expand) is HEIGHT-driven and untouched by this step; which RUNG
# within a layout applies is purely WIDTH-driven.
# --------------------------------------------------------------------------

_ATTRIBUTION_INDENT = "    "


def _role_text(role: str | None) -> str:
    emoji = role_emoji(role)
    return (emoji + NBSP + role) if (role and emoji) else (role or "")


def _strip_claude_prefix(model: str) -> str:
    """The model string exactly as it arrives on the bus, minus a leading
    "claude"/"claude-" (operator, 2026-07-28: "full odel name (minus
    Claude) and version" — the FULL citation rung is the bus string
    verbatim otherwise, never re-cased or re-punctuated; that transform is
    `short_model_name`'s job, one rung further down the ladder)."""
    lowered = model.lower()
    if lowered.startswith("claude-"):
        return model[len("claude-"):]
    if lowered.startswith("claude"):
        return model[len("claude"):].lstrip("-")
    return model


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
    """(role_text, model_text) for the BELOW-QUOTE citation at `width`
    columns — role_text never empties (callers only reach this once
    `role` is truthy); model_text is the full model string (minus its
    "Claude" prefix, `_strip_claude_prefix` — operator: "full odel name
    (minus Claude) and version"), its short form, or '' once neither fits
    — the model degrades, role never does, in the 2-line (expand) form.
    `width` here is the room for "role · model" — no dash, this rung sits
    on its own line (see the module section docstring)."""
    role_text = _role_text(role)
    if not model:
        return role_text, ""
    model = _strip_claude_prefix(model)
    room = width - _cell_width(role_text) - _cell_width(" · ")
    if _cell_width(model) <= max(room, 0):
        return role_text, model
    short = short_model_name(model)
    if short and _cell_width(short) <= max(room, 0):
        return role_text, short
    return role_text, ""


def _citation_line(role: str | None, model: str | None, width: int) -> str:
    """The below-quote citation (the expand layout's second line) — role
    then model, middle-dot separated, NO leading dash (operator: "no ash
    obviuouys" — the dash marks an INLINE attribution; once the citation
    is its own, positioned line, it is redundant). Falls through `_truncate`
    as the final safety net if even the role alone overruns `width` (the
    ordinary ellipsis rule, same as every other rung)."""
    role_text, model_text = attribution_text(role, model, width)
    text = f"{role_text} · {model_text}" if model_text else role_text
    return _truncate(text, width)


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


def _model_rungs(model: str | None) -> list[str | None]:
    """Model candidates for the ONE-LINE citation, widest first: the full
    string (minus "Claude", `_strip_claude_prefix`), its abbreviated form
    (`short_model_name`, skipped if identical), then None (dropped
    entirely) — operator: "if clipping use abreviatiob, if stil clipping
    remove model". Always ends in None so a caller's loop always has a
    final candidate to fall back to."""
    if not model:
        return [None]
    full = _strip_claude_prefix(model)
    candidates: list[str | None] = [full]
    short = short_model_name(full)
    if short and short != full:
        candidates.append(short)
    candidates.append(None)
    return candidates


def tight_line_parts(
    activity: str, role: str | None, width: int, model: str | None = None,
) -> tuple[str, str]:
    """(shown_quote, tail) for the tight (1-line) rung — the ONE-LINE
    citation's home (operator: "one line citation style if space" — rare,
    since it costs the most width, but tried FIRST, widest candidate
    first). `tail` is ` — role · model` (full), ` — role · shortmodel`
    (abbreviated), ` — role` (model dropped — never a dangling middle dot,
    since the dot is only ever emitted alongside a model string), or ""
    (role dropped too) — whichever is the WIDEST one that still keeps the
    quote at or above `_tight_quote_floor(width)` (sidebar-teamwork defect
    2: the quote is what a reader scans this line for, so IT is the last
    thing to yield, not the first). `shown_quote` alone is never truncated
    below the plain quote unless making room for a tail actually requires
    it."""
    quote = _quoted_activity(activity)
    if not role:
        return _truncate(quote, width), ""
    role_text = _role_text(role)
    floor = _tight_quote_floor(width)

    for candidate_model in _model_rungs(model):
        tail = f" — {role_text} · {candidate_model}" if candidate_model else f" — {role_text}"
        quote_budget = width - _cell_width(tail)
        if quote_budget >= floor:
            shown_quote = quote if _cell_width(quote) <= quote_budget else _truncate(quote, quote_budget)
            return shown_quote, tail
    return _truncate(quote, width), ""


def tight_line(activity: str, role: str | None, width: int, model: str | None = None) -> str:
    quote, tail = tight_line_parts(activity, role, width, model)
    return f"{quote}{tail}"


def identity_block(activity: str, role: str | None, model: str | None,
                    width: int, expand: bool) -> list[str]:
    """[quote] or [quote, citation] — see the module section docstring
    above for the exact two-layout, per-layout-ladder degradation.
    `expand` is the caller's real-height decision (`_agent_expansion_
    fits`); `width` is this row's own column budget. Lines are returned
    WITHOUT the row's own depth indent — callers prepend that uniformly;
    the citation line's extra `_ATTRIBUTION_INDENT` beneath the quote is
    already baked in."""
    if not role:
        return [_quoted_activity(activity)]
    if expand:
        quote = _quoted_activity(activity)
        attribution_width = max(width - len(_ATTRIBUTION_INDENT), 0)
        return [quote, _ATTRIBUTION_INDENT + _citation_line(role, model, attribution_width)]
    return [tight_line(activity, role, width, model)]


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
    # kind in {"task", "accordion", "agent", "subagent"} only — this row's
    # owning FEATURE's own grade-1 colour (`feature_colour_base`, computed
    # once per feature by `_feature_rows`), threaded the same way `task_
    # colour` already is. Only consumed when `SIDEBAR_COLOUR_SCOPE=feature`
    # re-roots the THIRD/FOURTH chain at the feature rather than the repo
    # (see `task_chain_roles`) — None otherwise (repo scope) and for
    # repo/feature rows (not applicable).
    feature_colour: tuple[int, int, int] | None = field(default=None)


def _agent_row(
    agent: Agent, target: str, depth: int, task_colour: tuple[int, int, int] | None,
    feature_colour: tuple[int, int, int] | None,
) -> Row:
    return Row(depth=depth, kind="agent", target=target, label=agent.role or agent.session_id,
               task_colour=task_colour, feature_colour=feature_colour,
               status=agent.status, activity=agent.activity, role=agent.role, model=agent.model)


def _subagent_row(
    sub: Subagent, target: str, depth: int, task_colour: tuple[int, int, int] | None,
    feature_colour: tuple[int, int, int] | None,
) -> Row:
    return Row(depth=depth, kind="subagent", target=target, label=sub.label, status=sub.state,
               task_colour=task_colour, feature_colour=feature_colour)


def _agent_and_subagent_rows(
    agent: Agent, target: str, depth: int, task_colour: tuple[int, int, int] | None,
    feature_colour: tuple[int, int, int] | None,
) -> list[Row]:
    """An agent's identity-line row, followed by its own subagent rows at
    the SAME depth (rule 6, 2026-07-26: a subagent hangs under the STEP its
    parent agent is on, not one level deeper than its parent) — both carry
    the owning task's own colour (`task_colour`, Ct) and the owning
    feature's own colour (`feature_colour`), so the curses draw path can
    paint them on the same open-block background as their step, and
    resolve the THIRD/FOURTH chain in either colour scope, without any
    further lookup."""
    return [_agent_row(agent, target, depth, task_colour, feature_colour), *(
        _subagent_row(sub, target, depth, task_colour, feature_colour) for sub in agent.subagents
    )]


def _step_row(
    step: Step, target: str, depth: int, task_colour: tuple[int, int, int] | None,
    feature_colour: tuple[int, int, int] | None,
) -> Row:
    """One line of the task's five-step accordion — a COLLAPSE KEEPS ITS
    OWN LINE (operator correction, 2026-07-26: "collapse keeps the line,
    it doesn't go to the previous one"), so every one of the five states
    (done/active/todo) gets its own row, always small caps, keeping its
    place among the five rather than folding into a shared summary line.
    The active step's agents (and their subagents) are the caller's job to
    nest beneath this row, one level deeper (see `_task_rows`) — this row
    itself only ever carries the step's own name and mark, plus the owning
    task's colour (`task_colour`) and feature's colour (`feature_colour`),
    which `_draw_step_row` resolves through `task_chain_roles` into its own
    FOURTH background (operator ruling, 2026-07-28 — supersedes the
    grade-3 `content_colour_base(task_colour)` reading this docstring
    previously described)."""
    glyph = _ACCORDION_STEP_GLYPH[step.state]
    label = f"{glyph} {small_caps(step.name)}" if glyph else small_caps(step.name)
    live = step.state == "active" and any(a.status == "working" for a in step.agents)
    return Row(depth=depth, kind="accordion", target=target, label=label, status=step.state,
               live=live, task_colour=task_colour, feature_colour=feature_colour)


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
    feature_colour: tuple[int, int, int] | None = None,
) -> list[Row]:
    """A task's own row (name left-aligned, its progress circle right-
    aligned — `_task_progress_glyph`); `task_colour` is
    this task's own already-allocated Ct, grade 2, computed once per
    feature by `_assign_task_colours` — None for a terminal task, which
    uses a fixed done/failed colour instead, curses-only); `feature_colour`
    is the owning feature's own grade-1 colour, threaded the same way for
    the `SIDEBAR_COLOUR_SCOPE=feature` chain re-rooting (`task_chain_
    roles`). Plus — while it is still open — its five-line step accordion
    (`_step_row`, one row per `PHASES` entry, each keeping its own place
    whether done/active/todo), the active step's agents (and their
    subagents) nested one level deeper than that step's own row, and any
    role-unmapped agent (fails open, rendered directly under the task, no
    step to nest it in). A terminal task (`TERMINAL_TASK_STATUSES`) folds:
    its own row is all that shows."""
    name = task.name
    rows = [Row(depth=depth, kind="task", target=target, label=name, status=task.status,
                 progress_glyph=_task_progress_glyph(task), task_colour=task_colour,
                 feature_colour=feature_colour)]
    if task.status in TERMINAL_TASK_STATUSES:
        return rows
    for step in task.steps:
        rows.append(_step_row(step, target, depth + 1, task_colour, feature_colour))
        if step.state == "active":
            for agent in step.agents:
                rows.extend(_agent_and_subagent_rows(
                    agent, target, depth + 2, task_colour, feature_colour,
                ))
    for agent in task.unstepped_agents:
        rows.extend(_agent_and_subagent_rows(agent, target, depth + 1, task_colour, feature_colour))
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
    hue = _repo_hue(repo_name)
    task_colours = _assign_task_colours(hue, feature.feature_id, feature.tasks)
    # This feature's own grade-1 colour — computed once here (mirrors `task_
    # colours` above) and threaded onto every row below so `task_chain_
    # roles` can re-root the THIRD/FOURTH chain on it when `SIDEBAR_COLOUR_
    # SCOPE=feature`; unused (but harmless to carry) in the default "repo"
    # scope.
    feature_colour = feature_colour_base(hue, feature.feature_id)
    dropped_name_task = _sole_same_named_task(feature)
    for task in feature.tasks:
        task_rows = _task_rows(task, target, depth + 1,
                                task_colour=task_colours.get(task.task_id),
                                feature_colour=feature_colour)
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
# FULL-WIDTH BLOCK layout (operator spec, 2026-07-28, reproducing the
# operator's own tmux `window-status-current-format` technique against the
# repo's own hue, restated 2026-07-28 in item 11: "the gradient cells...
# reach the sides of the pane"): `_header_ramp_cells()` gradient cells sit
# at EACH pane edge, taming PRIMARY down toward SECONDARY, with the CORE —
# filled with PRIMARY, the title centred within it — filling everything in
# between. The core therefore WIDENS with the pane; there is no flat
# secondary fill band any more (superseded the earlier fixed-size centred
# core + flat-fill-to-the-edges build, same day). Each ramp cell carries
# TWO interpolated tones at once via a half-block glyph (`▐`/`▌`) — one
# tone as the glyph's foreground (the half nearer the core), the other as
# its background (the half nearer the pane edge) — the same trick that
# lets tmux's own ramp read as more steps than it has cells. "No space for
# gradients, no gradient, easy" (operator, 2026-07-28): the title is NEVER
# shrunk to make room for the ramp — `_header_gradient_fits` is the one
# threshold that decides ramp-or-not, computed from the title's OWN
# untruncated width, never the reverse.
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

    The paused/no-gradient flat branch reserves the row's own literal LAST
    column for background only, via `render_header_line(title, width - 1)`
    (never the title's own trailing glyph): `_safe_addch` blanks whatever
    character lands on that column to a plain space, and a multi-byte
    ellipsis landing there used to vanish silently rather than render (a
    long repo name truncating to "orc" with no "…" at width 4) — the same
    one-column reservation `_step_row_display_text`/`_draw_feature_row`/
    `_draw_task_row` already make. The gradient branch does not need the
    same reservation for its own ramp glyphs: the outermost ramp cell's
    "outer" tone is already exactly `secondary` (`_header_ramp_tone`), and
    now that the ramp reaches the pane edge, THAT outermost cell — not the
    core — is what can land on the last column; if it gets blanked to a
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

    # FULL WIDTH: the ramp reaches both pane edges and the core fills
    # everything left over — the core WIDENS with the pane instead of a
    # flat secondary fill doing so (item 11's structural change).
    core_width = width - 2 * ramp_cells
    ramp = colour_ramp_steps(primary, secondary, ramp_cells * 2)
    core_text = render_header_line(title, core_width)
    core_fg = ensure_contrast(_muted_toward(HEADER_FG, primary), primary, _CONTRAST_MIN_TEXT)
    core_attr = colours.pair(core_fg, primary) | reverse

    col = 0
    for k in reversed(range(ramp_cells)):
        inner, outer = _header_ramp_tone(ramp, k)
        _safe_addch(stdscr, y, col, _HEADER_RAMP_IN, colours.pair(inner, outer) | reverse)
        col += 1
    for i in range(core_width):
        ch = core_text[i] if i < len(core_text) else " "
        _safe_addch(stdscr, y, col, ch, core_attr)
        col += 1
    for k in range(ramp_cells):
        inner, outer = _header_ramp_tone(ramp, k)
        _safe_addch(stdscr, y, col, _HEADER_RAMP_OUT, colours.pair(inner, outer) | reverse)
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
# colour to carry structure with). The indent glyph itself and its width
# constant now live in `sidebar_glyphs.py` (`_INDENT_GLYPH`/`_INDENT_WIDTH`).
# --------------------------------------------------------------------------

def _draw_indent_cell(
    stdscr, y: int, colours: _ColourCache, third: tuple[int, int, int], fourth: tuple[int, int, int],
) -> None:
    """The one-column boundary glyph for every step/agent/subagent row —
    THIRD (the task's own line colour) on the glyph's own half, FOURTH
    (every step row's and the indent's own background) on the rest of the
    cell. `fourth` is the caller's already selection-adjusted background —
    lifting only the glyph's own fg here would desync it from a lifted
    neighbour, so the caller decides the lift once and this just paints."""
    fg = ensure_contrast(third, fourth, _CONTRAST_MIN_MARK)
    _safe_addch(stdscr, y, 0, _INDENT_GLYPH, colours.pair(fg, fourth))


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

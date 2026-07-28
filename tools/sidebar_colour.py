"""RGB colour math for the sidebar renderer: the mock-canonical palette,
per-repo hue derivation, the PRIMARY->SECONDARY->THIRD->FOURTH colour-role
chain (operator ruling, 2026-07-28), and WCAG contrast enforcement. Pure
functions throughout -- no curses, no Row, no model types; every colour
another module draws with is computed here first.
"""
from __future__ import annotations

import colorsys
import os
import zlib
from dataclasses import dataclass


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
    third: tuple[int, int, int]
    fourth: tuple[int, int, int]

def repo_colour_roles(hue: dict[str, tuple[int, int, int]]) -> ColourRoles:
    """A repo hue's five-role chain (operator ruling, 2026-07-28, verbatim:
    "from the SECONDARY we derive a THIRD... for whichi wederive the
    FOURTh"): PRIMARY/SECONDARY are no new palette, both fields the hue
    triple already carries (`"accent"`/`"fill"`); THIRD and FOURTH are each
    one `_chain_step` further down the SAME chain — never independent
    lookups. FIFTH is deliberately NOT a field here: he calls it "the stage
    as today", i.e. the existing per-TASK `open_stage_colour(content_
    colour_base(task_colour))` value, unchanged by this chain — a repo-wide
    dataclass has no way to carry a per-task tone, and none was asked for."""
    secondary = hue["fill"]
    third = _chain_step(secondary)
    fourth = _chain_step(third)
    return ColourRoles(primary=hue["accent"], secondary=secondary, third=third, fourth=fourth)

# Fixed, never hashed (operator, 2026-07-28: "a given identity always
# resolves to the same colour, so nothing shifts as the pane repaints" —
# every field of `ColourRoles` is a pure function of the repo's own hue). A
# bare lightness lerp alone would leave THIRD/FOURTH sitting in exactly
# SECONDARY's own hue, which is what his separate ruling rules out ("dont
# stay in he same tones... an adjacent colour tone" — not the SAME family,
# not a disconnected one either): each link below rotates the hue by a
# small fixed amount as well as lightening/desaturating, so successive
# links buy contrast headroom from an adjacent hue rather than from
# lightness alone — the tension he flagged, since each link sits closer to
# its neighbour and the 4.5/3.0 floors get harder to clear every step.
_CHAIN_HUE_STEP_DEGREES = 18.0
_CHAIN_LIGHTNESS_STEP = 0.09
_CHAIN_SATURATION_FACTOR = 0.92

def _chain_step(base: tuple[int, int, int]) -> tuple[int, int, int]:
    """One link of the PRIMARY -> SECONDARY -> THIRD -> FOURTH -> FIFTH
    chain: a fixed hue rotation plus a lightening/desaturating nudge (see
    the constants above) — deterministic, same input always yields the
    same output."""
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in base))
    h = (h + _CHAIN_HUE_STEP_DEGREES / 360.0) % 1.0
    l = min(l + _CHAIN_LIGHTNESS_STEP, 1.0)
    s = max(s * _CHAIN_SATURATION_FACTOR, 0.0)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (round(r * 255), round(g * 255), round(b * 255))

# The one open choice this step builds BOTH sides of rather than picks
# (operator: "the axis is repository-uniform versus per-feature" — never
# per-task): whether the THIRD/FOURTH half of the chain (task row
# background, indent glyph, every step row background) is rooted at the
# REPO's own SECONDARY (one chain shared by every feature under it — the
# only behaviour that has ever existed here, and the default) or re-rooted
# at each FEATURE's own colour (`feature_colour_base`), so sibling features
# in the same repo get visually distinct task/step palettes. PRIMARY/
# SECONDARY themselves never move with this switch: the header and the
# feature row's own band stay repo-wide in both scopes — he pinned
# SECONDARY to the feature row's existing background unconditionally, and
# nothing about that is in play here.
_COLOUR_SCOPE_ENV = "SIDEBAR_COLOUR_SCOPE"
_COLOUR_SCOPE_VALUES = {"repo", "feature"}
_COLOUR_SCOPE_DEFAULT = "repo"

def _colour_scope() -> str:
    """`repo` (default, unset, or unrecognised — same fail-open rule this
    file uses everywhere for environment-sourced input) or `feature`."""
    value = os.environ.get(_COLOUR_SCOPE_ENV, _COLOUR_SCOPE_DEFAULT)
    return value if value in _COLOUR_SCOPE_VALUES else _COLOUR_SCOPE_DEFAULT

def task_chain_roles(
    hue: dict[str, tuple[int, int, int]], feature_colour: tuple[int, int, int] | None,
) -> ColourRoles:
    """THIRD/FOURTH for a task/step/indent row: `repo_colour_roles(hue)`
    unchanged in "repo" scope (the default), or re-rooted at `feature_
    colour` (this row's owning feature's own grade-1 colour) in "feature"
    scope — two more `_chain_step` links from the feature's own colour,
    the same distance SECONDARY sits from THIRD/FOURTH in the repo-scope
    chain, so the two scopes are structurally comparable. Falls back to
    the repo scope when a row has no feature colour to re-root on (should
    not happen in practice — every task-bearing row carries one — but
    never crashes if it does)."""
    roles = repo_colour_roles(hue)
    if _colour_scope() != "feature" or feature_colour is None:
        return roles
    third = _chain_step(feature_colour)
    fourth = _chain_step(third)
    return ColourRoles(primary=roles.primary, secondary=roles.secondary, third=third, fourth=fourth)

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

# A step's own TITLE text stays at `_CONTRAST_MIN_TEXT` (operator ruling,
# 2026-07-28: "the text itself for the title of stages is absolutely fine
# for contrast... it is not exactly fine for the content of step" — he
# read it on a large-screen TV from across a room and judged the title
# legible at 4.5; do not raise it, that reading was explicit and is not
# this constant's job). A step's own CONTENT — the agent/subagent identity
# lines nested under it, painted by `sidebar_paint_identity.py` — is the
# marginal case he flagged, and the room-distance viewing condition (his
# own words, not assumed) argues for materially more headroom there than
# the 4.5 floor gives, not a token bump: 7.0 is WCAG's own AAA "enhanced"
# threshold, the established name for "clears comfortably at a distance",
# not a number invented for this step.
_CONTRAST_MIN_CONTENT = 7.0

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

# --------------------------------------------------------------------------
# Identity line ("<doing> ⋮ <role> ⋮ <model>", NBSP-glued, model truncated)
# --------------------------------------------------------------------------

def model_tier_colour(model: str | None) -> tuple[int, int, int]:
    if not model:
        return TEXT
    return MODEL_TIERS.get(model.split("-")[0], TEXT)

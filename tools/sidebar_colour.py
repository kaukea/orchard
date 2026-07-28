"""RGB colour math for the sidebar renderer: the Dracula surface/text
palette, per-repo hue derivation, the PRIMARY->SECONDARY->THIRD->FOURTH
colour-role chain (operator ruling, 2026-07-28), and WCAG contrast
enforcement. Pure functions throughout -- no curses, no Row, no model
types; every colour another module draws with is computed here first.
"""
from __future__ import annotations

import colorsys
import zlib
from dataclasses import dataclass


def lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


# --------------------------------------------------------------------------
# Dracula palette (operator ruling, 2026-07-28: "we start with Dracula, and
# we will provide a theme functionality later to choose another color set" —
# theme SWITCHING is a later feature; adopting this one palette is this
# step's own scope). MIT licence — https://github.com/dracula/dracula-theme,
# (c) Zeno Rocha and contributors; vendored verbatim as eleven fixed RGB
# triples. `tools/palette-probe.py` prints and measures this exact set.
#
# This REPLACES the old derived-hue chain: every render colour used to be
# COMPUTED — `_chain_step` (now retired, see git history) rotated a hue and
# nudged its lightness/saturation, applied twice in a row from an already-
# dark base (SECONDARY). Measured, that produced adjacent surfaces at APCA/
# WCAG contrasts around 1.37 and 1.47 — roughly half of distinguishable —
# which is why the pre-Dracula render read as one dark mass. Colours below
# are CHOSEN from this designed set instead, never computed; identity is
# carried by PRIMARY (`_repo_hue`'s own per-repo accent, untouched by this
# adoption) and by each task's own jittered colour (`task_colour_base` in
# `sidebar_colour_lineage.py`, also untouched) — this file's own THIRD/
# FOURTH (`repo_colour_roles`) are now just the palette's two neutral
# surface tones, fixed, never varying by repo or feature.
#
# Readability here is judged by APCA (`tools/colour-probe.py`'s `apca_lc`),
# not the WCAG ratio this file's own `ensure_contrast` still enforces as a
# floor — the WCAG ratio is unreliable on dark backgrounds (its `+0.05`
# additive term flatters low-luminance pairs), which is how text used to
# clear that floor and still be unreadable. APCA is a judgement tool for
# CHOOSING these values, not a replacement for the floor `ensure_contrast`
# enforces everywhere below (that WCAG-ratio enforcement mechanism itself
# is unchanged by this step — a separate, larger piece of work). Never
# maximised: white scores highest of anything against a dark background
# and is the brightest thing a screen emits, which is not the goal.
# --------------------------------------------------------------------------

DRACULA_BASE = (0x28, 0x2A, 0x36)
DRACULA_LINE = (0x44, 0x47, 0x5A)
DRACULA_FG = (0xF8, 0xF8, 0xF2)
DRACULA_COMMENT = (0x62, 0x72, 0xA4)
DRACULA_CYAN = (0x8B, 0xE9, 0xFD)
DRACULA_GREEN = (0x50, 0xFA, 0x7B)
DRACULA_ORANGE = (0xFF, 0xB8, 0x6C)
DRACULA_PINK = (0xFF, 0x79, 0xC6)
DRACULA_PURPLE = (0xBD, 0x93, 0xF9)
DRACULA_RED = (0xFF, 0x55, 0x55)
DRACULA_YELLOW = (0xF1, 0xFA, 0x8C)

# Role mapping chosen for this step (recorded here, not just in the
# changelog, since every later reader of this file needs to know WHICH
# Dracula colour plays which part): FG is the sidebar's one body-text tone
# (`TEXT`/`HEADER_FG` — the mock used two near-white greys for these, which
# Dracula's own single designed foreground now replaces); COMMENT is the
# recede/muted tone AND the gutter/indent-glyph foreground (`MUTED`/THIRD);
# BASE is the deepest neutral surface (FOURTH — a step row's own
# background); GREEN/ORANGE are still the done/badge accents (`GREEN`/
# `AMBER`); CYAN is the activity line's own distinct accent (`ACTIVITY_
# ACCENT`, see `sidebar_paint_identity.py`) — chosen because it is neither
# the body-text tone nor a status colour already in use elsewhere on the
# same row. `GREEN_SOFT`/`FILL_GREEN` are blends toward the palette's own
# neutral tones rather than new hand-picked RGBs, so they still read as
# "the same green, quieter" rather than an unrelated colour.
HEADER_FG = DRACULA_FG
TEXT = DRACULA_FG
MUTED = DRACULA_COMMENT
GREEN = DRACULA_GREEN
GREEN_SOFT = lerp(DRACULA_GREEN, DRACULA_COMMENT, 0.5)
AMBER = DRACULA_ORANGE
FILL_GREEN = lerp(DRACULA_BASE, DRACULA_GREEN, 0.12)
ACTIVITY_ACCENT = DRACULA_CYAN
WHITE = (0xFF, 0xFF, 0xFF)  # ensure_contrast's/selection-lift's extreme target — a mechanism, not a body-text colour; never used to maximise readability for its own sake

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
    """A repo hue's four-role chain: PRIMARY/SECONDARY are no new palette,
    both fields the hue triple already carries (`"accent"`/`"fill"`).

    THIRD and FOURTH used to be each one `_chain_step` further down the
    same chain — a fixed hue rotation plus a lightening/desaturating nudge,
    applied twice in a row from SECONDARY (an already-dark tone). Retired
    (operator ruling, 2026-07-28, adopting Dracula: "colours are chosen
    from a designed palette, not computed" — see the module docstring's
    Dracula section for the measured adjacent-surface contrast that made):
    THIRD/FOURTH are now the palette's own two neutral surface tones,
    MUTED (Dracula COMMENT — the gutter/indent-glyph foreground) and
    DRACULA_BASE (the deepest surface — every step row's own background),
    fixed and never varying by repo or feature. Repo/feature identity is
    unaffected — it is still carried by PRIMARY/SECONDARY above (unchanged
    by this) and by each task's own jittered colour (`task_colour_base` in
    `sidebar_colour_lineage.py`, also unchanged).

    FIFTH is deliberately NOT a field here: he calls it "the stage as
    today", i.e. the existing per-TASK `open_stage_colour(content_colour_
    base(task_colour))` value — a repo-wide dataclass has no way to carry
    a per-task tone, and none was asked for."""
    return ColourRoles(primary=hue["accent"], secondary=hue["fill"], third=MUTED, fourth=DRACULA_BASE)

# Retired along with `_chain_step` (operator ruling, 2026-07-28, adopting
# Dracula): `SIDEBAR_COLOUR_SCOPE=feature` used to re-root THIRD/FOURTH at
# each feature's own colour instead of the repo's, by running the SAME
# computed chain from a different starting point — a way of choosing
# between two BUILT-but-unpicked options over a mechanism that no longer
# exists now that THIRD/FOURTH are fixed designed tones rather than
# anything computed from a base. There is nothing left to re-root.

def task_chain_roles(
    hue: dict[str, tuple[int, int, int]], feature_colour: tuple[int, int, int] | None,
) -> ColourRoles:
    """THIRD/FOURTH for a task/step/indent row — always `repo_colour_
    roles(hue)` (see that function's docstring: both are fixed Dracula
    surface tones now, not a computed chain). `feature_colour` is accepted
    but unused, kept only so every existing call site (`_draw_step_row`/
    `_draw_identity_block`/`_draw_subagent_row`/`_open_block_bg`) stays
    unchanged — the per-feature re-rooting this parameter used to enable
    is retired along with `_chain_step`, its only reason to exist."""
    return repo_colour_roles(hue)

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
# Header/feature "falling block" core text colour (operator, 2026-07-28:
# "the project is rendered as the least readable, least emphasized text of
# the whole sidebar... I think that the project header's text should
# become the MOST emphasized" — the opposite of what `_muted_toward`
# against the background used to produce). Judged by APCA, not the WCAG
# ratio (see the Dracula section above) — but `ensure_contrast`'s own
# WHITE-vs-BLACK extreme selection already picks the higher-APCA polarity
# here in practice (verified against every `REPO_HUES`/`FALLBACK_HEADER_
# HUES` accent), so no separate APCA-driven branch is needed: the higher
# `_CONTRAST_MIN_CONTENT` floor (7.0, the same "clears comfortably at a
# distance" tier already used for step content) is what actually pushes it
# to the stronger extreme rather than stopping the moment 4.5 clears.
# --------------------------------------------------------------------------

def header_emphasis_colour(bg: tuple[int, int, int]) -> tuple[int, int, int]:
    """The project header's own falling-block core text colour — run
    through `ensure_contrast` directly (never `_muted_toward` first, which
    is what produced the original defect: APCA near zero against a typical
    repo accent, because the text was dimmed toward the background BEFORE
    ever being contrast-checked)."""
    return ensure_contrast(TEXT, bg, _CONTRAST_MIN_CONTENT)

# A fixed fraction, not a re-hash or a different starting hue (operator,
# 2026-07-28: "the feature should do exactly the same [gradient/
# background]... maybe in a slightly different color for the font" — same
# background family, differing only in font colour). Blending the
# header's OWN resolved colour a small fraction toward the shared
# background guarantees a real, visible difference from the header
# regardless of which extreme (black/white) that background favours —
# picking a different STARTING hue does not: `ensure_contrast` converges
# to the exact same pure black/white once a background demands the full
# push, which erases any "slightly different" starting point.
_FEATURE_FONT_BLEND_TOWARD_BG = 0.22

def feature_emphasis_colour(bg: tuple[int, int, int]) -> tuple[int, int, int]:
    """The feature row's own falling-block core text colour — the header's
    resolved colour, blended toward the (shared) background and re-clamped
    at the PLAIN text floor (`_CONTRAST_MIN_TEXT`, not the header's higher
    one — the header is deliberately the MORE emphasized of the two, per
    the ruling above)."""
    header_fg = header_emphasis_colour(bg)
    return ensure_contrast(lerp(header_fg, bg, _FEATURE_FONT_BLEND_TOWARD_BG), bg, _CONTRAST_MIN_TEXT)

# --------------------------------------------------------------------------
# Identity line ("<doing> ⋮ <role> ⋮ <model>", NBSP-glued, model truncated)
# --------------------------------------------------------------------------

def model_tier_colour(model: str | None) -> tuple[int, int, int]:
    if not model:
        return TEXT
    return MODEL_TIERS.get(model.split("-")[0], TEXT)

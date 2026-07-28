"""Per-feature and per-task identity colour: a feature's own colour, read
from its sidecar frontmatter or jittered deterministically from the repo's
hue; a task's own colour, jittered in turn from its feature's; and the
subdued (lighter, less saturated -- never darker, Decision-110) content and
open-stage tones derived from a task's own colour. This is the OTHER colour
lineage -- per-identity, hashed and jittered -- as distinct from
`sidebar_colour.py`'s repo-wide PRIMARY..FOURTH chain, which never hashes.
"""
from __future__ import annotations

import colorsys
import re
import zlib
from pathlib import Path

from sidebar_model import _parse_frontmatter  # noqa: E402


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

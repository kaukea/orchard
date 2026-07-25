#!/usr/bin/env python3
"""Curses fleet sidebar — renders the tree built by sidebar_model, navigates
via sidebar_nav.

Presentation is deliberately split from curses: `flatten()` turns a Fleet
into a flat list of Row objects, and `render_lines()` turns those into plain
text with NO curses calls at all — that pure function is what tests assert
on. The curses app (`main`, run through `curses.wrapper`) is a thin loop that
polls a background `sidebar_model.watch()` thread and draws each line with
its status colour.

VISUAL CONTRACT (bus-message-specifying B5, operator-approved, non-
negotiable — SUPERSEDES the older sidebar-titling glyph/colour vocabulary):
the mock at `.git/the-works/bus-message-specifying/sidebar-mock.py` and its
blessed `approved-frame.ans` are the source of truth for every glyph, RGB
constant, spacing and animation rule below. Every constant named after the
mock (REPO_HUES, MODEL_TIERS, HEADER_FG/TEXT/MUTED/GREEN/GREEN_SOFT/AMBER/
FILL_GREEN, PHASES, ROLE_EMOJI, LOCATION_BADGES, NBSP) is copied from it
verbatim, not re-derived. Known licensed deviation (recorded debt, out of
scope for this step): the KITT-scanner bright-core-with-trailing-fade polish
— this port implements the mock's lifted-band sweep as-is, un-polished.

ANIMATION IS STATE-DRIVEN, curses-only: the pure text path (`render_lines`)
never animates — a repeated render of the same Fleet is byte-identical. In
curses, a "working" feature row carries the frame's ONE per-frame motion —
the bidirectional lifted-band sweep under its name (mock docstring: "only
the live feature line animates in place") — driven by a tick counter from
the main loop's getch cadence. The row's own status glyph is a STATIC
accent-coloured member of the spinner family (`STATUS_EMOJI["working"]`),
deliberately not cycled any more: cycling it too would be a second, redundant
motion the mock never shows.

Every other row (repo header, done/todo feature, subagent, courier) stays a
single fixed-width character, unconditionally the same on every frame.

CLI:
  python3 tools/sidebar.py          run the interactive curses UI
  python3 tools/sidebar.py --dump   print one frame as plain text and exit 0
                                    (headless — no TTY required)

STDLIB ONLY.
"""
from __future__ import annotations

import curses
import os
import sys
import threading
import unicodedata
import zlib
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sidebar_model  # noqa: E402
import sidebar_nav  # noqa: E402

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

# Canonical five-phase order (bus-message-specifying B3's phase vocabulary).
PHASES = ("ideation", "scoping", "designing", "building", "releasing")
PHASE_MARK = {"done": "●", "active": "⠧", "todo": "○"}

GUIDE_CHAR = "│"
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

# Six-state status vocabulary (final, settled — sidebar-titling item 9,
# revised again by the mock's visual contract): idle, waiting, and
# awaiting_agent share the same hollow circle — there is no longer a
# separate operator-wait glyph variant (superseded by the amber "?N" badge
# and the question-detail lines, see `question_badge`/`_draw_question_detail`
# — bus-message-specifying B5 item 7: "hollow circle only, no watch/timer
# glyphs anywhere in row status").
STATUS_EMOJI = {
    "working": SPINNER_FRAMES[7],
    "waiting": "○",
    "idle": "○",
    "awaiting_agent": "○",
    "done": "✓",
    "failed": "❌",
}

# Subagent presence glyph (sidebar-titling item 4, unchanged by this step): a
# subagent row has no verifiable state beyond "it currently exists in the
# model" — it disappears the moment it's done — so it is never rendered
# "working" and has no "idle" counterpart glyph.
SUBAGENT_GLYPH = "●"

COURIER_GLYPH = "📬"
NO_ACTIVITY_TEXT = "⋮ no activity ⋮"
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
# Progress fill / band sweep geometry (pure — the curses draw path is the
# only caller that turns these into actual screen colour)
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
# Question badge / detail
# --------------------------------------------------------------------------

def question_badge(question_count: int) -> str | None:
    return f"?{question_count}" if question_count > 0 else None


def question_count_text(count: int) -> str:
    return f"{count} question" + ("" if count == 1 else "s")


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

@dataclass
class Row:
    depth: int
    kind: str  # "repo" | "feature" | "subagent" | "courier"
    target: str  # exact tmux window name to navigate to on Enter
    label: str
    status: str | None
    waiting_on_operator: bool
    is_subagent: bool
    activity: str = field(default="")
    paused: bool = field(default=False)  # only meaningful for kind == "repo"
    repo_name: str = field(default="")  # owning repo's name; only meaningful for kind == "feature"
    # Display-grammar fields (bus-message-specifying B5) — only populated for
    # kind == "feature"; carried on Row so the curses draw path never has to
    # reach back into the model.
    phase: str | None = field(default=None)
    progress_pct: int | None = field(default=None)
    subagents_running: int = field(default=0)
    subagents_queued: int = field(default=0)
    question_count: int = field(default=0)
    first_question_subject: str | None = field(default=None)
    status_word: str = field(default="")
    # The originating Feature, kept for optional fields the model doesn't
    # guarantee yet (role, model, age, worked, tokens, dollars) — accessed
    # via getattr with a None default, never assumed present.
    source: object = field(default=None, repr=False)


def _courier_row(depth: int, target: str, courier: sidebar_model.Courier) -> Row:
    return Row(
        depth=depth, kind="courier", target=target, label=courier.label,
        status=None, waiting_on_operator=False, is_subagent=False,
    )


def flatten(fleet: sidebar_model.Fleet) -> list[Row]:
    """Fleet -> flat list of Row, depth-first (repo, its features, their
    subagents). A live parent's collapsed courier row (sidebar-polish item 5), if
    any, is the FIRST row in that parent's group — before its features or
    subagents.

    A repo with no live session (`not repo.has_session`) is skipped entirely
    — header AND group — an empty project has nothing to show (sidebar-
    titling item 3).

    Within a repo's features, `done` features sort FIRST (stable sort,
    done-first), ahead of everything still live — sidebar-titling item 7;
    subagent rows are exempt (they never persist past their own completion,
    so there is nothing to sort or retain)."""
    rows: list[Row] = []
    for repo in fleet.repos:
        if not repo.has_session:
            continue
        rows.append(Row(
            depth=0, kind="repo", target=repo.name, label=repo.name,
            status=repo.status, waiting_on_operator=repo.waiting_on_operator,
            is_subagent=False, paused=repo.paused,
        ))
        if repo.courier is not None:
            rows.append(_courier_row(1, repo.name, repo.courier))
        features = sorted(repo.features, key=lambda f: f.status != "done")
        for feature in features:
            feature_target = f"{repo.name}{TARGET_SEPARATOR}{feature.name}"
            rows.append(Row(
                depth=1, kind="feature", target=feature_target, label=feature.name,
                status=feature.status, waiting_on_operator=feature.waiting_on_operator,
                is_subagent=False, activity=feature.activity, repo_name=repo.name,
                phase=feature.phase, progress_pct=feature.progress_pct,
                subagents_running=feature.subagents_running,
                subagents_queued=feature.subagents_queued,
                question_count=feature.question_count,
                first_question_subject=feature.first_question_subject,
                status_word=feature.status_word, source=feature,
            ))
            if feature.courier is not None:
                rows.append(_courier_row(2, feature_target, feature.courier))
            for sub in feature.subagents:
                rows.append(Row(
                    depth=2, kind="subagent", target=feature_target, label=sub.label,
                    status="working", waiting_on_operator=False, is_subagent=True,
                ))
    return rows


def _row_text(row: Row) -> str:
    indent = "  " * row.depth
    if row.kind == "courier":
        return f"{indent}{COURIER_GLYPH} {row.label}"
    if row.kind == "subagent":
        # presence in the model IS the only verifiable subagent state — no
        # "idle" counterpart glyph exists (sidebar-titling item 4).
        return f"{indent}{SUBAGENT_GLYPH} {row.label}"
    # repo headers carry no leading status glyph in EITHER path — curses
    # already draws none (via _draw_header); the pure path matches
    # (sidebar-titling item 4). Feature rows never reach this function — see
    # render_lines(), which composes them via compose_feature_row_text.
    return f"{indent}{row.label}"


def _truncate(text: str, width: int) -> str:
    """Hard-slice to `width`, but a truncated string ends with an ellipsis
    (sidebar-polish item 8) rather than a hard cut — the ellipsis itself
    counts toward the width budget, never overflowing it."""
    if width <= 0 or len(text) <= width:
        return text[:width] if width > 0 else text
    return text[:width - 1] + ELLIPSIS


def _feature_row_layout(
    glyph: str, name: str, pct: int, width: int, badge: str | None,
) -> tuple[str, str, int, str, str]:
    """(glyph, shown_name, pad_width, badge_text, pct_text) for a feature row
    at `width` columns — the single source of truth for BOTH the plain-text
    dump path (`compose_feature_row_text`) and the curses per-column
    painter (`_draw_feature_row`), so their layouts can never drift apart
    (the same sharing pattern the file already used for
    `_feature_row_segments` before this step)."""
    pct_text = f"{pct}%"
    badge_text = f"{badge} " if badge else ""
    tail_len = len(badge_text) + len(pct_text)
    budget_for_name = max(width - len(glyph) - 1 - tail_len, 0)
    shown_name = name if len(name) <= budget_for_name else _truncate(name, budget_for_name)
    used = len(glyph) + 1 + len(shown_name) + tail_len
    pad_width = max(width - used, 0)
    return glyph, shown_name, pad_width, badge_text, pct_text


def compose_feature_row_text(
    glyph: str, name: str, pct: int, width: int, badge: str | None = None,
) -> str:
    glyph, shown_name, pad_width, badge_text, pct_text = _feature_row_layout(
        glyph, name, pct, width, badge,
    )
    return f"{glyph} {shown_name}{' ' * pad_width}{badge_text}{pct_text}"


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
    fleet: sidebar_model.Fleet,
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

    No animation and no decoration lines (band sweep, phase label, identity
    line, checklist, footer, question detail) — those are curses-only
    additions layered around a feature row (bus-message-specifying B5,
    same "curses-only" split as the pre-existing spinner/blink animation);
    this path renders exactly one line per Row, deterministically."""
    rows = flatten(fleet)
    if not rows:
        return [_truncate(NO_ACTIVITY_TEXT, width)]

    if height is None:
        window, start = rows, 0
    else:
        offset = clamp_scroll_offset(offset, selected, len(rows), height)
        window, start = rows[offset:offset + height], offset

    lines = []
    for i, row in enumerate(window, start=start):
        marker = ">" if i == selected else " "
        if row.kind == "feature":
            indent = "  " * row.depth
            avail = max(width - len(marker) - len(indent), 0)
            glyph = STATUS_EMOJI.get(row.status, "○")
            pct = row.progress_pct if row.progress_pct is not None else 0
            badge = question_badge(row.question_count)
            body = compose_feature_row_text(glyph, row.label, pct, avail, badge)
            lines.append(_truncate(f"{marker}{indent}{body}", width))
        else:
            lines.append(_truncate(marker + _row_text(row), width))
    return lines


# --------------------------------------------------------------------------
# Shared fleet state (written by the watch thread, read by the main loop)
# --------------------------------------------------------------------------

class _SharedFleet:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fleet = sidebar_model.Fleet()

    def set(self, fleet: sidebar_model.Fleet) -> None:
        with self._lock:
            self._fleet = fleet

    def get(self) -> sidebar_model.Fleet:
        with self._lock:
            return self._fleet


def _watch_thread(shared: _SharedFleet) -> None:
    try:
        sidebar_model.watch(shared.set)
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


# The 6 steps (0-5) of the xterm-256 colour cube map to these 0-255 values.
_XTERM256_CUBE_STEPS = (0, 95, 135, 175, 215, 255)


def _nearest_cube_step(v: int) -> int:
    return min(range(6), key=lambda i: abs(v - _XTERM256_CUBE_STEPS[i]))


def _rgb_to_xterm256(rgb: tuple[int, int, int]) -> int:
    """Nearest xterm-256 palette index for a 0-255 RGB triple — sidebar-
    titling item 1: lets a colour render on a terminal that reports 256
    colours but not `can_change_color()` (no custom RGB), by picking a fixed
    palette slot instead. Only searches the machine-computable ranges: the
    6x6x6 colour cube (indices 16-231) and the 24-step grayscale ramp
    (232-255) — never the 16 standard colours, whose actual RGBs vary per
    terminal theme and so cannot be matched reliably."""
    r, g, b = rgb
    ri, gi, bi = _nearest_cube_step(r), _nearest_cube_step(g), _nearest_cube_step(b)
    cube_rgb = (_XTERM256_CUBE_STEPS[ri], _XTERM256_CUBE_STEPS[gi], _XTERM256_CUBE_STEPS[bi])
    cube_index = 16 + 36 * ri + 6 * gi + bi

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
        can_custom = curses.COLORS >= 256 and curses.can_change_color()
        pairs = []
        for i, (_name, rgb, ansi_fallback) in enumerate(ORCHID_PALETTE):
            pair_id = _AGENT_PAIR_BASE + i
            if can_custom:
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
    target; sibling subagents/courier rows share a target, so label joins in."""
    if row.kind in ("subagent", "courier"):
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

    24-bit via `curses.init_color` when the terminal reports
    `can_change_color()`; otherwise each RGB maps to its nearest xterm-256
    palette index via `_rgb_to_xterm256` — the same fallback the header/agent
    colours already used. Silently degrades to attribute-only styling
    (dim/italic/bold, no colour) once the colour-pair or custom-colour budget
    runs out, or on a colourless terminal — never raises."""

    _FIRST_COLOUR_ID = 128  # clear of agent (64+) and status-pair ranges
    _FIRST_PAIR_ID = 50     # clear of status pairs (1-6) and agent pairs (10-17)

    def __init__(self) -> None:
        self.enabled = curses.has_colors()
        self._can_custom = (
            self.enabled and curses.COLORS >= 256 and curses.can_change_color()
        )
        self._colour_ids: dict[tuple[int, int, int], int] = {}
        self._pair_ids: dict[tuple[tuple[int, int, int], tuple[int, int, int] | None], int] = {}
        self._next_colour_id = self._FIRST_COLOUR_ID
        self._next_pair_id = self._FIRST_PAIR_ID

    def _colour_id(self, rgb: tuple[int, int, int]) -> int:
        if rgb in self._colour_ids:
            return self._colour_ids[rgb]
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


def _safe_addstr(stdscr, y: int, x: int, text: str, attr: int) -> None:
    if not text:
        return
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass  # bottom-right cell write raises; harmless, just skip it


# --------------------------------------------------------------------------
# Curses drawing — repo header
# --------------------------------------------------------------------------

def _draw_header(
    stdscr, y: int, width: int, title: str, paused: bool, selected: bool,
    colours: _ColourCache,
) -> None:
    """SOLID per-repo hue block (sidebar-titling OVERRIDE 1, hue now sourced
    from `_repo_hue(title)["header"]`) with the centred title drawn on top,
    thin/DIM and never bold — STATIC, no per-frame movement. PAUSED stays
    flat light-gray. A selected header keeps a visible A_REVERSE on the
    title."""
    bg_rgb = PAUSED_HEADER_GRAY if paused else _repo_hue(title)["header"]
    text = render_header_line(title, width)
    fill_attr = colours.pair(HEADER_FG, bg_rgb)
    text_attr = colours.pair(HEADER_FG, bg_rgb, dim=True) | (curses.A_REVERSE if selected else 0)
    _safe_addstr(stdscr, y, 0, " " * width, fill_attr)
    _safe_addstr(stdscr, y, 0, text, text_attr)


# --------------------------------------------------------------------------
# Curses drawing — feature row (glyph + name-over-progress-fill + badge/pct,
# with the band sweep layered on top for a "working" row)
# --------------------------------------------------------------------------

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
) -> list[tuple[tuple[int, int, int], bool]]:
    """[(fg_rgb, dim)] per character of the row text `_feature_row_layout`
    composes — one entry per column, so the curses painter and
    `compose_feature_row_text` can never disagree on where a segment
    starts."""
    _glyph, shown_name, pad_width, badge_text, pct_text = layout
    dim_body = status not in ("working", "done")
    glyph_style = (_feature_glyph_colour(status, accent), dim_body)
    name_style = (_feature_name_colour(status), dim_body)
    tail_style = (MUTED, True)
    badge_style = (AMBER, True)
    return (
        [glyph_style]
        + [name_style] * (1 + len(shown_name))
        + [tail_style] * pad_width
        + [badge_style] * len(badge_text)
        + [tail_style] * len(pct_text)
    )


def _draw_feature_row(
    stdscr, y: int, width: int, row: Row, selected: bool, colours: _ColourCache, tick: int,
) -> None:
    hue = _repo_hue(row.repo_name)
    status = row.status
    glyph = STATUS_EMOJI.get(status, "○")
    pct = row.progress_pct if row.progress_pct is not None else 0
    badge = question_badge(row.question_count)
    layout = _feature_row_layout(glyph, row.label, pct, width, badge)
    text = compose_feature_row_text(glyph, row.label, pct, width, badge)
    styles = _feature_row_cell_styles(layout, status, hue["accent"])
    fill_rgb = _feature_fill_colour(status, hue)

    if status == "working":
        travel_end = band_travel_end(pct, width)
        span = band_span(travel_end)
        pos = band_position(tick, span)
        bg_at = lambda col: band_column_colour(col, pos, travel_end, fill_rgb)  # noqa: E731
    else:
        cols = fill_cols(pct, width)
        bg_at = lambda col: progress_column_colour(col, cols, fill_rgb)  # noqa: E731

    reverse = curses.A_REVERSE if selected else 0
    for col, ch in enumerate(text[:width]):
        fg, dim = styles[col] if col < len(styles) else (MUTED, True)
        attr = colours.pair(fg, bg_at(col), dim=dim) | reverse
        _safe_addstr(stdscr, y, col, ch, attr)


# --------------------------------------------------------------------------
# Curses drawing — decoration lines under a "working" feature row (phase
# label, identity line, phase checklist, footer) and under any feature row
# carrying open questions (question-count + why lines). Curses-only, exactly
# like the pre-existing spinner/blink split — render_lines() never emits
# these.
# --------------------------------------------------------------------------

def _draw_guide_line(
    stdscr, y: int, width: int, text: str, colours: _ColourCache,
    fg: tuple[int, int, int] = MUTED,
) -> None:
    prefix = GUIDE_CHAR + " "
    body = _truncate(text, max(width - len(prefix), 0))
    _safe_addstr(stdscr, y, 0, prefix, colours.pair(MUTED, dim=True))
    _safe_addstr(stdscr, y, len(prefix), body, colours.pair(fg, dim=True))


def _draw_gap_line(stdscr, y: int, colours: _ColourCache) -> None:
    _safe_addstr(stdscr, y, 0, GUIDE_CHAR, colours.pair(MUTED, dim=True))


def _draw_identity_line(
    stdscr, y: int, width: int, doing: str, role: str | None, model: str | None,
    colours: _ColourCache,
) -> None:
    prefix = GUIDE_CHAR + " "
    content_width = max(width - len(prefix), 0)
    doing_t, role_t, model_t = compose_identity_line(doing, role, model, content_width)
    sep = NBSP + "⋮" + NBSP

    x = 0
    _safe_addstr(stdscr, y, x, prefix, colours.pair(MUTED, dim=True))
    x += len(prefix)
    _safe_addstr(stdscr, y, x, doing_t, colours.pair(TEXT))
    x += _cell_width(doing_t)
    if role_t:
        _safe_addstr(stdscr, y, x, sep, colours.pair(MUTED, dim=True))
        x += len(sep)
        _safe_addstr(stdscr, y, x, role_t, colours.pair(MUTED, dim=True, italic=True))
        x += _cell_width(role_t)
    if model_t:
        _safe_addstr(stdscr, y, x, sep, colours.pair(MUTED, dim=True))
        x += len(sep)
        _safe_addstr(stdscr, y, x, model_t, colours.pair(model_tier_colour(model), italic=True))


def _draw_phase_checklist(
    stdscr, y: int, width: int, active_phase: str | None,
    hue: dict[str, tuple[int, int, int]], running: int, queued: int, colours: _ColourCache,
) -> int:
    prefix = GUIDE_CHAR + "   "
    for word, state in phase_states(active_phase):
        is_active = state == "active"
        mark = phase_mark(state)
        mark_colour = GREEN_SOFT if state == "done" else (hue["accent"] if is_active else MUTED)
        word_colour = hue["accent"] if is_active else MUTED

        _safe_addstr(stdscr, y, 0, prefix, colours.pair(MUTED, dim=True))
        x = len(prefix)
        _safe_addstr(stdscr, y, x, mark, colours.pair(mark_colour, dim=not is_active))
        x += len(mark) + 1
        word_shown = _truncate(word, max(width - x, 0))
        _safe_addstr(stdscr, y, x, word_shown, colours.pair(word_colour, dim=not is_active))
        x += len(word_shown)

        if is_active:
            dots = phase_dot_suffix(running, queued)
            if dots:
                dots_shown = _truncate(" " + dots, max(width - x, 0))
                _safe_addstr(stdscr, y, x, dots_shown, colours.pair(MUTED, dim=True))
        y += 1
    return y


def _draw_footer(stdscr, y: int, width: int, source: object, colours: _ColourCache) -> int:
    for line in footer_lines(source):
        _draw_guide_line(stdscr, y, width, line, colours)
        y += 1
    return y


def _draw_done_footer(stdscr, y: int, width: int, row: Row, colours: _ColourCache) -> int:
    """Collapsed one-line footer under a DONE feature row — no guide char
    (the mock indents it with two plain spaces, unlike the live footer's
    "│ " lines), single dim/muted style throughout."""
    text = done_footer_line(row.source)
    if text is None:
        return y
    prefix = "  "
    body = _truncate(text, max(width - len(prefix), 0))
    _safe_addstr(stdscr, y, 0, prefix + body, colours.pair(MUTED, dim=True))
    return y + 1


def _draw_working_decorations(stdscr, y: int, width: int, row: Row, colours: _ColourCache) -> int:
    _draw_guide_line(stdscr, y, width, small_caps(row.phase) if row.phase else "", colours)
    y += 1
    _draw_gap_line(stdscr, y, colours)
    y += 1
    _draw_identity_line(
        stdscr, y, width, row.status_word,
        getattr(row.source, "role", None), getattr(row.source, "model", None), colours,
    )
    y += 1
    _draw_gap_line(stdscr, y, colours)
    y += 1
    hue = _repo_hue(row.repo_name)
    y = _draw_phase_checklist(
        stdscr, y, width, row.phase, hue, row.subagents_running, row.subagents_queued, colours,
    )
    _draw_gap_line(stdscr, y, colours)
    y += 1
    return _draw_footer(stdscr, y, width, row.source, colours)


def _draw_question_detail(stdscr, y: int, width: int, row: Row, colours: _ColourCache) -> int:
    if row.question_count <= 0:
        return y
    _draw_guide_line(stdscr, y, width, question_count_text(row.question_count), colours, fg=AMBER)
    y += 1
    if row.first_question_subject:
        prefix = GUIDE_CHAR + "   "
        body = _truncate(f"⋮ why: {row.first_question_subject}", max(width - len(prefix), 0))
        _safe_addstr(stdscr, y, 0, prefix, colours.pair(MUTED, dim=True))
        _safe_addstr(stdscr, y, len(prefix), body, colours.pair(AMBER, dim=True))
        y += 1
    return y


def _draw(
    stdscr, rows: list[Row], selected: int, offset: int,
    colour_pairs: dict[str, int], agent_colours: list[int] | None,
    colours: _ColourCache, tick: int,
) -> None:
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    if not rows:
        _safe_addstr(stdscr, 0, 0, _truncate(NO_ACTIVITY_TEXT, max_x), curses.A_DIM)
        stdscr.refresh()
        return

    y = 0
    for i, row in enumerate(rows[offset:offset + max_y], start=offset):
        if y >= max_y:
            break
        if row.kind == "repo":
            _draw_header(stdscr, y, max_x, row.label, row.paused, i == selected, colours)
            y += 1
            continue
        if row.kind == "feature":
            _draw_feature_row(stdscr, y, max_x, row, i == selected, colours, tick)
            y += 1
            if row.status == "working" and y < max_y:
                y = _draw_working_decorations(stdscr, y, max_x, row, colours)
            elif row.status == "done" and y < max_y:
                y = _draw_done_footer(stdscr, y, max_x, row, colours)
            if row.question_count > 0 and y < max_y:
                y = _draw_question_detail(stdscr, y, max_x, row, colours)
            continue

        text = _truncate(_row_text(row), max_x)
        attr = colour_pairs.get(row.status, 0)
        if row.kind == "courier":
            attr |= curses.A_ITALIC | curses.A_DIM
        if agent_colours:
            attr |= agent_colours[_agent_colour_index(_agent_colour_key(row))]
        if row.status == "waiting" and row.waiting_on_operator:
            attr |= curses.A_BLINK
        if i == selected:
            attr |= curses.A_REVERSE
        _safe_addstr(stdscr, y, 0, text, attr)
        y += 1
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


def main(stdscr) -> None:
    curses.curs_set(0)
    # ~125ms/frame target (bus-message-specifying B5 item 3, matching the
    # mock's FPS=8) — the band sweep rides this loop's tick, same as the
    # spinner used to; a slower actual cadence is accepted (geometry over
    # framerate) rather than tightened with extra timers.
    stdscr.timeout(125)
    colour_pairs = _init_colours()
    agent_colours = _init_agent_colours()
    colours = _ColourCache()

    shared = _SharedFleet()
    thread = threading.Thread(target=_watch_thread, args=(shared,), daemon=True)
    thread.start()

    selected = 0
    scroll_offset = 0
    tick = 0

    while True:
        rows = flatten(shared.get())
        selected = _clamp_selected(selected, len(rows))
        max_y, _max_x = stdscr.getmaxyx()
        scroll_offset = clamp_scroll_offset(scroll_offset, selected, len(rows), max_y)
        _draw(stdscr, rows, selected, scroll_offset, colour_pairs, agent_colours, colours, tick)

        key = stdscr.getch()
        tick += 1

        if key in (curses.KEY_UP, ord("k")):
            selected = max(0, selected - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            selected = min(len(rows) - 1, selected + 1) if rows else 0
        elif key in (10, 13, curses.KEY_ENTER):
            _navigate_selected(rows, selected)
        elif key in (ord("q"), ord("Q")):
            return
        elif key == curses.KEY_RESIZE:
            curses.update_lines_cols()
        # any other key (including -1 on timeout) is ignored


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _run_dump() -> int:
    fleet = sidebar_model.build_model()
    for line in render_lines(fleet):
        print(line)
    return 0


if __name__ == "__main__":
    if "--dump" in sys.argv[1:]:
        sys.exit(_run_dump())
    curses.wrapper(main)

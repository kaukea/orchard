#!/usr/bin/env python3
"""Curses fleet sidebar — reads the fleet, renders it, navigates via
sidebar_nav. The ONLY sidebar (bus-finishing): the old courier-inbox reader
(tools/sidebar_model.py) and the plain-text prototype reader
(tools/sidebar_v3.py) are both retired and folded in here.

The fleet model is read straight off the per-session event layout
orchard_topic.py writes: `$XDG_RUNTIME_DIR/orchard/projects/<repo>.<project>/
<sessionid>.<ts>.json`, one file per event, folded into one record per
session (latest of each kind wins) — see `_fold_sessions()`, ported from
sidebar_v3.py's `sessions()`. `build_model()`/`watch()` are this module's own
now; there is no other backing store.

NOT ported (no source in the new event grammar — orchard_topic.py's `post`
verbs are lifecycle/status/delegation/outcome/task only — so nothing below
fabricates a value for them):
  - courier rows (the old model's collapsed inbox-sidecar row) — the new
    grammar has no announce/inbox concept to collapse into one.
  - open questions / question badges — a question now flows through the
    :session:operator broker (tools/orchard-question-broker.py), not a
    courier-observed WIRE GRAMMAR v1 message.
  - phase ticks, waiting_on_operator, tokens/dollars, age/worked — the
    corresponding Feature/Repo fields stay present (so the render code needs
    no special-casing) but are always None/False; render_lines() and the
    curses painters already degrade gracefully on an absent value — that was
    true even under the old model, before its first orchid:phase/etc.
    message arrived.

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
  python3 tools/sidebar.py --once   paint one real curses frame (same
                                    terminal/colour/draw path as the live
                                    UI) and exit 0 — no input loop, no watch
                                    thread. Requires a real terminal; exits
                                    non-zero with a message otherwise.

STDLIB ONLY.
"""
from __future__ import annotations

import curses
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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

# Subagent presence glyph (sidebar-titling item 4). A subagent row once had no
# state beyond "it currently exists in the model", because it vanished the
# moment it finished; a completed task now persists from its feature marker,
# so the row carries its own working/done/failed state.
SUBAGENT_GLYPH = "●"

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
# Fleet model — reads $XDG_RUNTIME_DIR/orchard/projects/<repo>.<project>/
# <sessionid>.<ts>.json (see module docstring for what is and isn't ported).
# --------------------------------------------------------------------------

# A session with no event inside this window, and no terminal outcome,
# renders "stale" (gray) rather than "working"/"idle" — it is NOT dropped
# from the model (retention ruling, 2026-07-25, revised same day: nothing
# ever leaves the sidebar due to staleness; only a session restart, which
# clears the tmpfs projects tree, resets what is shown). See `_status_for`.
ACTIVE_WINDOW_SECONDS = 60 * 60
# schedule = queued, begin = active, end = inactive. `schedule` was briefly
# retired then restored (operator ruling, 2026-07-25): it is a member of
# the closed orchard subject corpus (courier.py's ORCHARD_VALID_SUBJECTS),
# so Feature.subagents_queued has a real source again.
_DELEGATION_STATE = {"schedule": "scheduled", "begin": "active", "end": "inactive"}

_SESSION_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _is_bare_uuid(text: str | None) -> bool:
    return bool(text) and bool(_SESSION_UUID_RE.match(text))


@dataclass
class Subagent:
    label: str
    # working/done/failed — same vocabulary _status_for() derives for a
    # Feature, sourced either from live delegation traffic (always
    # "working", the only state `_merge_subagents` derives from it) or from
    # the feature marker's persisted `tasks` entry once live events age out.
    status: str = "working"


@dataclass
class Feature:
    name: str
    activity: str
    status: str
    waiting_on_operator: bool
    subagents: list[Subagent] = field(default_factory=list)
    status_word: str = ""
    phase: str | None = None
    progress_pct: int | None = None
    subagents_running: int = 0
    subagents_queued: int = 0
    # role/model come straight off the identity/status snapshot every
    # orchard_topic.py event carries; tokens/dollars/age/worked have no
    # source in this grammar and stay None (see module docstring).
    role: str | None = None
    model: str | None = None
    tokens: str | None = None
    dollars: str | None = None
    age: str | None = None
    worked: str | None = None


@dataclass
class Repo:
    name: str
    activity: str
    status: str
    waiting_on_operator: bool
    paused: bool = False
    # True when the repo has at least one live session (a gardener session
    # or any feature). A repo with no live session is skipped by flatten().
    has_session: bool = True
    features: list[Feature] = field(default_factory=list)
    status_word: str = ""
    phase: str | None = None
    progress_pct: int | None = None
    subagents_running: int = 0
    subagents_queued: int = 0
    role: str | None = None
    model: str | None = None
    tokens: str | None = None
    dollars: str | None = None


@dataclass
class Fleet:
    repos: list[Repo] = field(default_factory=list)


def projects_root() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        return Path("/nonexistent")  # build_model()/watch() just see nothing
    return Path(runtime) / "orchard" / "projects"


def _repo_display_name(slug: str) -> str:
    """`<owner>.<repo>` (courier.py's project_slug() format) -> `<repo>` —
    the bare name sidebar_nav's gardener-window match expects. A slug with
    no owner component (no git remote at post time) has no dot to split on
    and is shown as-is."""
    _owner, sep, repo = slug.partition(".")
    return repo if sep else slug


def _latest(rec: dict, key: str, ts: float) -> bool:
    """True (and records ts) when this event is the newest of its kind for a session."""
    if ts < rec.get(key, -1.0):
        return False
    rec[key] = ts
    return True


_MARKER_ARCHIVE_DIR = "_archived"
_MARKER_STATE_OUTCOME = {"done": "success", "failed": "fail"}


def _parse_iso_ts(text: str | None) -> float:
    """ISO-8601 UTC (courier.py's `datetime.now(timezone.utc).isoformat()`
    shape) -> epoch seconds; 0.0 — maximally stale, never a crash — on
    anything unparsable or missing."""
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0


def _iter_marker_sessions(project_dir: Path):
    """Yield (feature_id, marker, sid, session) for every identity-bearing
    session an on-disk feature-node marker (frozen schema v1,
    `<feature-id>.marker`) still remembers — the structural source a
    Feature row survives on even once the archiver has removed its event
    files (retention ruling, 2026-07-25: a finished node persists until
    restart). `_archived/` is never scanned; a legacy zero-byte
    `<session-id>.marker` heartbeat (courier.py's mailbox touch) has no
    JSON to parse and is skipped; a session entry with no `agent` (a
    mailbox that never carried an identity, e.g. operator's) is skipped
    too."""
    for f in project_dir.iterdir():
        if f.name == _MARKER_ARCHIVE_DIR or not f.is_file():
            continue
        if not f.name.endswith(".marker") or f.stat().st_size == 0:
            continue
        try:
            marker = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        feature_id = f.name.removesuffix(".marker")
        for sid, session in (marker.get("sessions") or {}).items():
            if session.get("agent"):
                yield feature_id, marker, sid, session


def _apply_marker_session(rec: dict, feature_id: str, marker: dict, session: dict) -> None:
    """Seed a session record's structural baseline off its marker entry —
    identity plus a status a plain `_status_for` read already understands,
    so a session with no surviving events still renders correctly. The
    marker's `tasks` list (label/state/updated, merged in place by
    courier.py and never truncated) rides along on the record too, so a
    task stays available for `_merge_subagents` even once the delegation
    events that first reported it are archived away."""
    rec["identity"] = {
        "agent": session.get("agent"),
        "name": session.get("name") or marker.get("name"),
        "feature": marker.get("feature") or feature_id,
    }
    rec["marker_tasks"] = marker.get("tasks") or []
    rec["_seen_ts"] = max(rec.get("_seen_ts", 0.0), _parse_iso_ts(session.get("last_seen")))
    state = session.get("state")
    outcome = _MARKER_STATE_OUTCOME.get(state)
    if outcome:
        rec["outcome"] = outcome
    elif state == "working":
        rec["state"] = "starting"


def _fold_sessions(project_dir: Path) -> dict[str, dict]:
    """Fold one project's feature-node markers and event files into one
    record per session. Markers (`_iter_marker_sessions()`) seed the
    structural baseline first; event files then layer live state on top,
    latest of each kind winning — folded from the retired sidebar_v3.py's
    sessions(), unchanged: per-session event files are
    `<sessionid>.<ts>.json`."""
    found: dict[str, dict] = {}
    for feature_id, marker, sid, session in _iter_marker_sessions(project_dir):
        rec = found.setdefault(sid, {"sid": sid, "subs": {}})
        _apply_marker_session(rec, feature_id, marker, session)
    for f in project_dir.iterdir():
        if f.name.startswith(".") or not f.name.endswith(".json") or not f.is_file():
            continue
        try:
            env = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        sid = env.get("from", "").removeprefix(":session:")
        if not sid:
            continue
        ts = f.stat().st_mtime
        rec = found.setdefault(sid, {"sid": sid, "subs": {}})
        # The overall last-heard-from timestamp for this session, independent
        # of the per-kind "latest wins" bookkeeping below — this is what
        # `_status_for` compares against ACTIVE_WINDOW_SECONDS to decide
        # "stale", so it advances on ANY event, recognised or not.
        rec["_seen_ts"] = max(rec.get("_seen_ts", 0.0), ts)
        if _latest(rec, "_snap", ts):
            rec["identity"] = env.get("identity", rec.get("identity", {}))
            rec["status"] = env.get("status", rec.get("status", {}))
        subject = env.get("subject", "")
        if subject.startswith("orchard:agent:lifecycle:") and _latest(rec, "_life", ts):
            rec["state"] = subject.rsplit(":", 1)[-1]
        elif subject == "orchard:agent:status" and _latest(rec, "_stat", ts):
            rec["activity"] = env.get("body", "")
        elif subject.startswith("orchard:agent:outcome:") and _latest(rec, "_out", ts):
            rec["outcome"] = subject.rsplit(":", 1)[-1]
        elif subject.startswith("orchard:task:outcome:") and _latest(rec, "_task", ts):
            rec["task_outcome"] = subject.rsplit(":", 1)[-1]
        elif subject in ("orchard:agent:delegation:schedule",
                          "orchard:agent:delegation:begin",
                          "orchard:agent:delegation:end"):
            # EXACT subject match — the subagent id is no longer derived from
            # the subject tail (there is none any more): it rides the body.
            action = subject.removeprefix("orchard:agent:delegation:")
            sub = (env.get("body") or {}).get("subagent")
            state = _DELEGATION_STATE.get(action)
            if sub and state and _latest(rec, f"_sub_{sub}", ts):
                rec["subs"][sub] = state
    return found


def _status_for(rec: dict, now: float) -> str:
    """working/done/failed/idle/stale, derived from the lifecycle+outcome
    signals this grammar actually carries, plus `now` for the staleness
    check. No waiting/awaiting_agent variant exists (no blocked/notify_user
    post verb), so those STATUS_EMOJI entries are simply never produced
    here.

    A terminal outcome (done/failed) always wins — it is never demoted to
    stale, no matter how old (retention ruling, 2026-07-25 revision: a
    finished task is a permanent green/red one-liner). Absent a terminal
    outcome, a session with no event inside ACTIVE_WINDOW_SECONDS reads
    stale (gray) rather than working/idle — checked before the
    working/idle split, since staleness overrides even a stuck "starting"
    lifecycle state that never followed up."""
    if rec.get("outcome") == "fail" or rec.get("task_outcome") == "failed":
        return "failed"
    if rec.get("outcome") == "success" or rec.get("task_outcome") == "completed":
        return "done"
    if now - rec.get("_seen_ts", 0.0) >= ACTIVE_WINDOW_SECONDS:
        return "stale"
    if rec.get("state") in ("starting", "started", "stopping"):
        return "working"
    return "idle"


def _row_label(rec: dict) -> str | None:
    """The identity name/feature to show, or None if there is nothing
    operator-facing yet (a bare session-UUID with no announced name or
    feature is never rendered — sidebar-polish item 2)."""
    identity = rec.get("identity") or {}
    label = identity.get("name") or identity.get("feature")
    if label:
        return label
    return None if _is_bare_uuid(rec["sid"]) else rec["sid"]


def _apply_common(row: Feature | Repo, rec: dict, now: float) -> None:
    """Copy the fields a session record and a Feature/Repo row share —
    both dataclasses carry this exact field set, so one function serves
    either (duck-typed on purpose)."""
    identity = rec.get("identity") or {}
    status = rec.get("status") or {}
    row.activity = rec.get("activity", "")
    row.status_word = row.activity
    row.status = _status_for(rec, now)
    row.waiting_on_operator = False  # no source in this grammar
    row.role = identity.get("agent")
    row.model = status.get("model")
    subs = rec.get("subs", {})
    row.subagents_running = sum(1 for s in subs.values() if s == "active")
    row.subagents_queued = sum(1 for s in subs.values() if s == "scheduled")


_SUBAGENT_TASK_SORT_RANK = {"working": 0, "done": 1, "failed": 1}


def _merge_subagents(subs: dict[str, str], marker_tasks: list[dict]) -> list[Subagent]:
    """One Subagent row per label, unioning this session's live delegation
    traffic (`subs`, from `orchard:agent:delegation:begin|end`) with the
    owning feature marker's persisted `tasks` — the structural source a
    completed task survives on once the archiver removes the events that
    reported it (retention ruling, 2026-07-26). A label present in both
    renders once; live wins, since only a still-open delegation can produce
    "active" here at all. Working tasks sort ahead of done/failed ones so a
    growing pile of finished work never crowds the still-running rows out
    of view."""
    merged = {
        task["label"]: task["state"]
        for task in marker_tasks
        if task.get("label") and task.get("state")
    }
    for sub_label, state in subs.items():
        if state == "active":
            merged[sub_label] = "working"
    return sorted(
        (Subagent(label=label, status=status) for label, status in merged.items()),
        key=lambda sub: (_SUBAGENT_TASK_SORT_RANK.get(sub.status, 1), sub.label),
    )


def _assemble_repo(dir_name: str, sess: dict[str, dict], now: float) -> Repo:
    repo = Repo(name=_repo_display_name(dir_name), activity="", status="idle",
                waiting_on_operator=False)

    gardener = next(
        (sess[sid] for sid in sorted(sess)
         if (sess[sid].get("identity") or {}).get("agent") == "gardener"),
        None,
    )
    if gardener is not None:
        _apply_common(repo, gardener, now)

    for sid in sorted(sess):
        rec = sess[sid]
        agent = (rec.get("identity") or {}).get("agent")
        # Any identity earns a row, whatever its role — the gardener alone
        # is excluded (it already supplied the repo header above); a
        # session never seen with an identity at all contributes nothing
        # (ruling: any-role rows, 2026-07-26).
        if not agent or agent == "gardener":
            continue
        label = _row_label(rec)
        if label is None:
            continue
        feature = Feature(name=label, activity="", status="idle",
                           waiting_on_operator=False)
        _apply_common(feature, rec, now)
        # subagents: this session's own live delegation traffic
        # (orchard:agent:delegation:begin/end) merged with its owning
        # feature marker's persisted tasks (see module docstring: a child
        # session that announces itself without a delegation:begin from
        # its parent is still not shown — only a labelled task is).
        feature.subagents = _merge_subagents(rec.get("subs", {}), rec.get("marker_tasks", []))
        repo.features.append(feature)

    repo.has_session = gardener is not None or bool(repo.features)
    return repo


def build_model(root: Path | None = None) -> Fleet:
    """One snapshot of the fleet: every project directory is folded and
    assembled into one Repo, unconditionally — nothing is ever excluded by
    staleness (retention ruling, 2026-07-25 revision: a row leaves the
    sidebar only when the process restarts and the tmpfs projects tree
    clears with it). ACTIVE_WINDOW_SECONDS still matters — it is what
    `_status_for` compares `now` against to decide whether an
    unfinished session reads "stale" (gray) rather than "working"/"idle" —
    but it no longer removes anything from this snapshot."""
    root = root or projects_root()
    fleet = Fleet()
    if not root.is_dir():
        return fleet
    now = time.time()
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        fleet.repos.append(_assemble_repo(d.name, _fold_sessions(d), now))
    return fleet


_WATCH_RESTART_BACKOFF_SECONDS = 1.0


def watch(on_change, root: Path | None = None) -> None:
    """Call on_change(fleet) whenever the projects root changes. Never
    returns while the process lives.

    Prefers `inotifywait -m -r` on the root, supervised for the whole
    lifetime of the call: a dying inotifywait child is reaped and, as long
    as the binary is installed, restarted — with a short backoff if it
    keeps exiting immediately, so a crash loop never busy-spins. While the
    root doesn't exist (or inotifywait isn't installed at all) this falls
    back to a 2s re-scan, matching the retired sidebar_model.watch()
    shape; a root that later reappears is picked back up by inotifywait on
    the next iteration. build_model() on a missing root is just an empty
    Fleet, never a crash.
    """
    root = root or projects_root()
    has_inotifywait = shutil.which("inotifywait") is not None

    def rescan_and_notify() -> None:
        on_change(build_model(root))

    def run_inotify_until_exit() -> None:
        cmd = [
            "inotifywait", "-m", "-r",
            "-e", "create", "-e", "moved_to", "-e", "modify", "-e", "delete",
            "--format", "%f", str(root),
        ]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        try:
            for _ in proc.stdout:
                rescan_and_notify()
        finally:
            proc.terminate()
            proc.wait()

    while True:
        rescan_and_notify()
        if has_inotifywait and root.is_dir():
            started_at = time.monotonic()
            run_inotify_until_exit()
            if time.monotonic() - started_at < _WATCH_RESTART_BACKOFF_SECONDS:
                time.sleep(_WATCH_RESTART_BACKOFF_SECONDS)
        else:
            time.sleep(2)


# --------------------------------------------------------------------------
# Presentation model (pure, no curses)
# --------------------------------------------------------------------------

@dataclass
class Row:
    depth: int
    kind: str  # "repo" | "feature" | "subagent"
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
    status_word: str = field(default="")
    # The originating Feature, kept for optional fields the model doesn't
    # guarantee yet (role, model, age, worked, tokens, dollars) — accessed
    # via getattr with a None default, never assumed present.
    source: object = field(default=None, repr=False)


def flatten(fleet: Fleet) -> list[Row]:
    """Fleet -> flat list of Row, depth-first (repo, its features, their
    subagents).

    A repo with no live session (`not repo.has_session`) is skipped entirely
    — header AND group — an empty project has nothing to show (sidebar-
    titling item 3).

    Within a repo's features, `done` features sort FIRST (stable sort,
    done-first), ahead of everything still live — sidebar-titling item 7.
    A feature's own subagent rows keep `_merge_subagents`' order instead
    (working-first, so a persisted done/failed task never crowds the
    still-running ones out of view — the opposite priority from the
    feature sort above, deliberately: a feature list is scanned for what
    finished, a task list for what's still moving)."""
    rows: list[Row] = []
    for repo in fleet.repos:
        if not repo.has_session:
            continue
        rows.append(Row(
            depth=0, kind="repo", target=repo.name, label=repo.name,
            status=repo.status, waiting_on_operator=repo.waiting_on_operator,
            is_subagent=False, paused=repo.paused,
        ))
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
                status_word=feature.status_word, source=feature,
            ))
            for sub in feature.subagents:
                rows.append(Row(
                    depth=2, kind="subagent", target=feature_target, label=sub.label,
                    status=sub.status, waiting_on_operator=False, is_subagent=True,
                ))
    return rows


def _row_text(row: Row) -> str:
    indent = "  " * row.depth
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
            body = compose_feature_row_text(glyph, row.label, pct, avail)
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
        self._fleet = Fleet()

    def set(self, fleet: Fleet) -> None:
        with self._lock:
            self._fleet = fleet

    def get(self) -> Fleet:
        with self._lock:
            return self._fleet


def _watch_thread(shared: _SharedFleet) -> None:
    try:
        watch(shared.set)
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
    flat light-gray. `selected` here means "the cursor is here AND the user
    has actually moved it" (see `_draw`'s `has_moved`/`main`'s tracking of
    it) — the resting first frame never inverts a header merely because
    `selected == 0` happens to default there; A_REVERSE only appears once
    the operator has genuinely navigated."""
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
    layout = _feature_row_layout(glyph, row.label, pct, width, None)
    text = compose_feature_row_text(glyph, row.label, pct, width)
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

    y = 0
    for i, row in enumerate(rows[offset:offset + max_y], start=offset):
        if y >= max_y:
            break
        if row.kind == "repo":
            _draw_header(stdscr, y, max_x, row.label, row.paused, i == selected and has_moved, colours)
            y += 1
            continue
        if row.kind == "feature":
            _draw_feature_row(stdscr, y, max_x, row, i == selected, colours, tick)
            y += 1
            if row.status == "working" and y < max_y:
                y = _draw_working_decorations(stdscr, y, max_x, row, colours)
            elif row.status == "done" and y < max_y:
                y = _draw_done_footer(stdscr, y, max_x, row, colours)
            continue

        text = _truncate(_row_text(row), max_x)
        attr = colour_pairs.get(row.status, 0)
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
            curses.update_lines_cols()
        # any other key (including -1 on timeout) is ignored


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _run_dump() -> int:
    fleet = build_model()
    for line in render_lines(fleet):
        print(line)
    return 0


def _paint_once(stdscr) -> None:
    colour_pairs, agent_colours, colours = _init_draw_state(stdscr)
    _draw_frame(stdscr, build_model(), 0, 0, colour_pairs, agent_colours, colours, tick=0, has_moved=False)


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

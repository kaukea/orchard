#!/usr/bin/env python3
"""Curses fleet sidebar — renders the tree built by sidebar_model, navigates
via sidebar_nav.

Presentation is deliberately split from curses: `flatten()` turns a Fleet
into a flat list of Row objects, and `render_lines()` turns those into plain
text with NO curses calls at all — that pure function is what tests assert
on. The curses app (`main`, run through `curses.wrapper`) is a thin loop that
polls a background `sidebar_model.watch()` thread and draws each line with
its status colour.

ANIMATION IS STATE-DRIVEN, curses-only (sidebar-titling item 6, revising the
old blanket "no animation" invariant): an actively-working FEATURE row's
glyph cycles through a spinner (SPINNER_FRAMES), and a waiting-on-operator
row blinks (curses.A_BLINK) — driven purely by the row's current status,
never by message arrival. Every OTHER row stays a single fixed-width
character, unconditionally the same on every frame. The pure text path
(`render_lines`) never animates at all — it renders the static glyph
(🚧) for a working row regardless — so tests stay deterministic. Row layout
never shifts because a glyph disappeared or reappeared.

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
import zlib
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sidebar_model  # noqa: E402
import sidebar_nav  # noqa: E402

# Six-state status vocabulary (final, settled — sidebar-polish item 9,
# revised: NOT the old "three plus one" framing). Each glyph is fixed text —
# in the pure path (render_lines) it is unconditionally the same on every
# frame; in curses only, the "working" glyph may be replaced by a spinner
# frame (see SPINNER_FRAMES / _status_emoji's spinner_char param) — every
# other glyph is still never swapped per-tick, never blank-on-odd-frame.
STATUS_EMOJI = {
    "working": "🚧",
    "waiting": "⌚",
    "idle": "⚪",
    "awaiting_agent": "🪷",
    "done": "✅",
    "failed": "❌",
}
# ❓ VARIANT of "waiting" specifically when the wait is on the OPERATOR
# (row.waiting_on_operator) rather than an external component.
WAITING_ON_OPERATOR_EMOJI = "❓"

# Subagent presence glyph (sidebar-titling item 4): a subagent row has no
# verifiable state beyond "it currently exists in the model" — it disappears
# from the tree the moment it's done — so it is never rendered "working" (an
# unverifiable claim) and there is deliberately no "idle" counterpart glyph.
SUBAGENT_GLYPH = "●"

# Spinner frames (sidebar-titling item 6) for an actively-working FEATURE row,
# curses-only — cycled by a tick counter in main(); the pure text path never
# receives a frame and always renders the static STATUS_EMOJI["working"].
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

BUS_GLYPH = "📬"
NO_ACTIVITY_TEXT = "· no activity ·"
ELLIPSIS = "…"

# Separator between repo name and feature name in BOTH a feature row's
# display text ("<repo>/<name>", sidebar-titling item 2) and its tmux window
# target name — tmux window names are produced by the session-naming scheme
# as "<repo>/<name>" to match exactly.
TARGET_SEPARATOR = "/"

# Per-agent colour palette (sidebar-polish item 4): the 8 most popular
# orchid-species colours (operator ruling, Decision — sidebar-polish
# Questions), NOT the ANSI set. Each entry is (name, 256-colour RGB 0-255,
# nearest-ANSI fallback curses.COLOR_*) so a limited terminal still gets a
# reasonable, if less precise, per-agent hue instead of crashing or going
# colourless.
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

# Project header gradient (sidebar-polish item 10): classic orchid colour
# family (#DA70D6-ish), STATIC — no per-frame movement. PAUSED projects get a
# flat, very light gray instead (no gradient at all).
ORCHID_GRADIENT_DARK = (0x9B, 0x30, 0x93)
ORCHID_GRADIENT_LIGHT = (0xF0, 0xC6, 0xEE)
PAUSED_HEADER_GRAY = (0xD9, 0xD9, 0xD9)


# --------------------------------------------------------------------------
# Presentation model (pure, no curses)
# --------------------------------------------------------------------------

@dataclass
class Row:
    depth: int
    kind: str  # "repo" | "feature" | "subagent" | "bus"
    target: str  # exact tmux window name to navigate to on Enter
    label: str
    status: str | None
    waiting_on_operator: bool
    is_subagent: bool
    activity: str = field(default="")
    paused: bool = field(default=False)  # only meaningful for kind == "repo"
    repo_name: str = field(default="")  # owning repo's name; only meaningful for kind == "feature"


def _bus_row(depth: int, target: str, bus: sidebar_model.Bus) -> Row:
    return Row(
        depth=depth, kind="bus", target=target, label=bus.label,
        status=None, waiting_on_operator=False, is_subagent=False,
    )


def flatten(fleet: sidebar_model.Fleet) -> list[Row]:
    """Fleet -> flat list of Row, depth-first (repo, its features, their
    subagents). A live parent's collapsed bus row (sidebar-polish item 5), if
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
        if repo.bus is not None:
            rows.append(_bus_row(1, repo.name, repo.bus))
        features = sorted(repo.features, key=lambda f: f.status != "done")
        for feature in features:
            feature_target = f"{repo.name}{TARGET_SEPARATOR}{feature.name}"
            rows.append(Row(
                depth=1, kind="feature", target=feature_target, label=feature.name,
                status=feature.status, waiting_on_operator=feature.waiting_on_operator,
                is_subagent=False, activity=feature.activity, repo_name=repo.name,
            ))
            if feature.bus is not None:
                rows.append(_bus_row(2, feature_target, feature.bus))
            for sub in feature.subagents:
                rows.append(Row(
                    depth=2, kind="subagent", target=feature_target, label=sub.label,
                    status="working", waiting_on_operator=False, is_subagent=True,
                ))
    return rows


def _status_emoji(row: Row, spinner_char: str | None = None) -> str:
    """`spinner_char`, when given, replaces the static "working" glyph — used
    ONLY by the curses draw path (sidebar-titling item 6); the pure text path
    never passes it, so render_lines stays static."""
    if row.status == "waiting" and row.waiting_on_operator:
        return WAITING_ON_OPERATOR_EMOJI
    if row.status == "working" and spinner_char is not None:
        return spinner_char
    return STATUS_EMOJI.get(row.status, " ")


def _row_text(row: Row, spinner_char: str | None = None) -> str:
    indent = "  " * row.depth
    if row.kind == "bus":
        return f"{indent}{BUS_GLYPH} {row.label}"
    if row.kind == "subagent":
        # presence in the model IS the only verifiable subagent state — no
        # "idle" counterpart glyph exists (sidebar-titling item 4).
        return f"{indent}{SUBAGENT_GLYPH} {row.label}"
    if row.kind == "repo":
        # repo headers carry no leading status glyph in EITHER path — curses
        # already drew none (via _draw_header); the pure path now matches
        # (sidebar-titling item 4).
        return f"{indent}{row.label}"

    name = f"{row.repo_name}/{row.label}" if row.repo_name else row.label
    text = f"{indent}{_status_emoji(row, spinner_char)} {name}"
    if row.activity:
        text = f"{text} {row.activity}"
    return text


def _truncate(text: str, width: int) -> str:
    """Hard-slice to `width`, but a truncated string ends with an ellipsis
    (sidebar-polish item 8) rather than a hard cut — the ellipsis itself
    counts toward the width budget, never overflowing it."""
    if width <= 0 or len(text) <= width:
        return text[:width] if width > 0 else text
    return text[:width - 1] + ELLIPSIS


def _truncate_keep_name(repo_name: str, name: str, width: int) -> str:
    """Compose "<repo>/<name>" (or just `name` when `repo_name` is empty),
    truncated to `width` while KEEPING THE NAME side intact (sidebar-titling
    item 2) — the repo side is elided from the LEFT with a leading ELLIPSIS,
    e.g. "…ids/fleet sidebar". If `name` alone still exceeds `width`, falls
    back to `_truncate`'s normal right-cut-with-trailing-ellipsis on the name
    alone (there is nothing left to elide from the repo side)."""
    full = f"{repo_name}/{name}" if repo_name else name
    if width <= 0:
        return ""
    if len(full) <= width:
        return full
    if len(name) > width:
        return _truncate(name, width)
    tail_len = max(width - len(ELLIPSIS), 0)
    tail = full[-tail_len:] if tail_len > 0 else ""
    return ELLIPSIS + tail


def _feature_row_segments(
    row: Row, width: int, spinner_char: str | None = None,
) -> tuple[str, str, str, str, str]:
    """(indent, glyph, repo_part, name_part, suffix) for a feature row at
    `width` columns (a leading selection marker, if any, is NOT included in
    `width` — callers account for it separately). `repo_part` includes its
    trailing '/' when present; `name_part` is never truncated ahead of
    `repo_part` (see `_truncate_keep_name`). Shared by the pure text path
    (render_lines) and the curses draw path so the dim/bold segment
    boundaries always match the plain-text composition exactly."""
    indent = "  " * row.depth
    glyph = _status_emoji(row, spinner_char)
    avail = width - len(indent) - len(glyph) - 1  # +1 for the space after glyph
    if avail <= 0:
        return indent, glyph, "", "", ""
    # The name gets FIRST claim on the width (item 2: the name dominates, the
    # repo recedes). The activity is strictly secondary — it only fills space
    # left AFTER the composed <repo>/<name>, so a long activity can never
    # starve the repo prefix or truncate the name.
    composed = _truncate_keep_name(row.repo_name, row.label, avail)
    slash_idx = composed.find("/") if row.repo_name else -1
    if slash_idx == -1:
        repo_part, name_part = "", composed
    else:
        repo_part, name_part = composed[:slash_idx + 1], composed[slash_idx + 1:]
    remaining = avail - len(composed)
    suffix = _truncate(f" {row.activity}", remaining) if row.activity and remaining > 1 else ""
    return indent, glyph, repo_part, name_part, suffix


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

    No animation-related parameters (spinner_char/flash_on) — this path never
    animates, regardless of state; the curses draw path is the only one that
    ever passes a spinner_char (sidebar-titling item 6), so a render_lines
    frame depends only on the fleet's current state."""
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
            indent, glyph, repo_part, name_part, suffix = _feature_row_segments(
                row, max(width - len(marker), 0),
            )
            line = f"{marker}{indent}{glyph} {repo_part}{name_part}{suffix}"
            lines.append(_truncate(line, width))
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
# Project header gradient (pure) — sidebar-polish item 10
# --------------------------------------------------------------------------

def _lerp_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def header_gradient(width: int, paused: bool = False) -> list[tuple[int, int, int]]:
    """One RGB tuple per column, STATIC (same input -> same output, always —
    no frame/tick parameter exists to animate it). PAUSED is a flat, very
    light gray; otherwise a smooth interpolation across the classic orchid
    colour family (#DA70D6-ish)."""
    if width <= 0:
        return []
    if paused:
        return [PAUSED_HEADER_GRAY] * width
    if width == 1:
        return [_lerp_rgb(ORCHID_GRADIENT_DARK, ORCHID_GRADIENT_LIGHT, 0.5)]
    return [
        _lerp_rgb(ORCHID_GRADIENT_DARK, ORCHID_GRADIENT_LIGHT, i / (width - 1))
        for i in range(width)
    ]


def render_header_line(title: str, width: int) -> str:
    """Title centred over `width` columns, space-padded both sides — the
    text drawn on top of the curses gradient bevel."""
    if width <= 0:
        return ""
    text = _truncate(title, width)
    pad = width - len(text)
    left = pad // 2
    return (" " * left) + text + (" " * (pad - left))


# --------------------------------------------------------------------------
# Curses drawing
# --------------------------------------------------------------------------

def _init_colours() -> dict[str, int]:
    """Colour-pair attrs per status; empty dict (attr 0 everywhere) if the
    terminal has no colour support."""
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
    titling item 1: lets the header gradient render on a terminal that
    reports 256 colours but not `can_change_color()` (no custom RGB), by
    picking a fixed palette slot instead. Only searches the machine-
    computable ranges: the 6x6x6 colour cube (indices 16-231) and the 24-step
    grayscale ramp (232-255) — never the 16 standard colours, whose actual
    RGBs vary per terminal theme and so cannot be matched reliably."""
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


# Colour-pair ids reserved for per-agent tint (item 4) and the header
# gradient (item 10) — kept clear of the 1-6 status pairs above.
_AGENT_PAIR_BASE = 10
_HEADER_PAIR_BASE = 30
_HEADER_STEPS = 8
_HEADER_PAUSED_PAIR = _HEADER_PAIR_BASE + _HEADER_STEPS


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
    target; sibling subagents/bus rows share a target, so label joins in."""
    if row.kind in ("subagent", "bus"):
        return f"{row.target}/{row.label}"
    return row.target


def _agent_colour_index(key: str) -> int:
    return zlib.crc32(key.encode("utf-8")) % len(ORCHID_PALETTE)


def _init_header_colours() -> tuple[list[int], int] | tuple[None, None]:
    """(gradient step pairs, paused pair), or (None, None) on a terminal that
    can't render the gradient at all — callers fall back to plain text.

    sidebar-titling item 1: a terminal with `curses.COLORS >= 256` but no
    `can_change_color()` (no custom RGB — the common case on the live
    tmux/xterm-256color the sidebar actually runs in) still gets the
    gradient, by mapping each step's RGB to its NEAREST xterm-256 palette
    index (`_rgb_to_xterm256`) instead of defining a custom colour. Only a
    genuinely <256-colour or colourless terminal falls back to plain text."""
    if not curses.has_colors():
        return None, None
    try:
        if curses.COLORS < 256:
            return None, None
        can_custom = curses.can_change_color()
        steps = header_gradient(_HEADER_STEPS, paused=False)
        pairs = []
        for i, rgb in enumerate(steps):
            pair_id = _HEADER_PAIR_BASE + i
            if can_custom:
                colour_id = 96 + i
                r, g, b = _rgb_to_curses(rgb)
                curses.init_color(colour_id, r, g, b)
                curses.init_pair(pair_id, curses.COLOR_BLACK, colour_id)
            else:
                curses.init_pair(pair_id, curses.COLOR_BLACK, _rgb_to_xterm256(rgb))
            pairs.append(curses.color_pair(pair_id))
        if can_custom:
            paused_colour_id = 96 + _HEADER_STEPS
            r, g, b = _rgb_to_curses(PAUSED_HEADER_GRAY)
            curses.init_color(paused_colour_id, r, g, b)
            curses.init_pair(_HEADER_PAUSED_PAIR, curses.COLOR_BLACK, paused_colour_id)
        else:
            curses.init_pair(
                _HEADER_PAUSED_PAIR, curses.COLOR_BLACK, _rgb_to_xterm256(PAUSED_HEADER_GRAY),
            )
        return pairs, curses.color_pair(_HEADER_PAUSED_PAIR)
    except curses.error:
        return None, None


def _safe_addstr(stdscr, y: int, x: int, text: str, attr: int) -> None:
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass  # bottom-right cell write raises; harmless, just skip it


def _draw_header(stdscr, y: int, width: int, title: str, paused: bool, selected: bool,
                  header_pairs: list[int] | None, paused_pair: int | None) -> None:
    """Half-block (▀) gradient bevel with the centred title drawn on top —
    STATIC, no per-frame movement. Falls back to a plain centred line with
    no colour on a terminal that can't support the custom gradient pairs."""
    text = render_header_line(title, width)
    text_attr = curses.A_BOLD | (curses.A_REVERSE if selected else 0)

    if header_pairs is None:
        _safe_addstr(stdscr, y, 0, text, text_attr if not paused else curses.A_DIM)
        return

    for x in range(width):
        attr = paused_pair if paused else header_pairs[x % len(header_pairs)]
        _safe_addstr(stdscr, y, x, "▀", attr)
    _safe_addstr(stdscr, y, 0, text, text_attr)


def _draw_feature_row(stdscr, y: int, width: int, row: Row, selected: bool,
                       colour_pairs: dict[str, int], agent_colours: list[int] | None,
                       spinner_char: str | None) -> None:
    """<repo>/<name> with the repo segment DIM and the name segment BOLD
    (sidebar-titling item 2) so the name dominates and the repo recedes; the
    status glyph keeps its own status colour. The working glyph animates via
    `spinner_char` (item 6) — curses-only, never the pure text path."""
    indent, glyph, repo_part, name_part, suffix = _feature_row_segments(row, width, spinner_char)

    base_attr = 0
    if agent_colours:
        base_attr |= agent_colours[_agent_colour_index(_agent_colour_key(row))]
    if row.status == "waiting" and row.waiting_on_operator:
        base_attr |= curses.A_BLINK
    if selected:
        base_attr |= curses.A_REVERSE

    x = 0
    _safe_addstr(stdscr, y, x, indent, base_attr)
    x += len(indent)
    _safe_addstr(stdscr, y, x, glyph, base_attr | colour_pairs.get(row.status, 0))
    x += len(glyph)
    _safe_addstr(stdscr, y, x, " ", base_attr)
    x += 1
    _safe_addstr(stdscr, y, x, repo_part, base_attr | curses.A_DIM)
    x += len(repo_part)
    _safe_addstr(stdscr, y, x, name_part, base_attr | curses.A_BOLD)
    x += len(name_part)
    if suffix:
        _safe_addstr(stdscr, y, x, suffix, base_attr)


def _draw(stdscr, rows: list[Row], selected: int, offset: int,
          colour_pairs: dict[str, int], agent_colours: list[int] | None,
          header_pairs: list[int] | None, paused_pair: int | None,
          spinner_char: str | None = None) -> None:
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
            _draw_header(stdscr, y, max_x, row.label, row.paused, i == selected,
                         header_pairs, paused_pair)
            y += 1
            continue
        if row.kind == "feature":
            _draw_feature_row(stdscr, y, max_x, row, i == selected,
                              colour_pairs, agent_colours, spinner_char)
            y += 1
            continue

        text = _truncate(_row_text(row), max_x)
        attr = colour_pairs.get(row.status, 0)
        if row.kind == "bus":
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
    stdscr.timeout(150)
    colour_pairs = _init_colours()
    agent_colours = _init_agent_colours()
    header_pairs, paused_pair = _init_header_colours()

    shared = _SharedFleet()
    thread = threading.Thread(target=_watch_thread, args=(shared,), daemon=True)
    thread.start()

    selected = 0
    scroll_offset = 0
    # Spinner tick counter (sidebar-titling item 6): stdscr.timeout(150) above
    # means one loop iteration is ~150ms per getch(); advancing the frame
    # every 2 ticks is ~300ms per frame. Curses-only — render_lines never
    # sees this.
    tick = 0
    spinner_index = 0

    while True:
        rows = flatten(shared.get())
        selected = _clamp_selected(selected, len(rows))
        max_y, _max_x = stdscr.getmaxyx()
        scroll_offset = clamp_scroll_offset(scroll_offset, selected, len(rows), max_y)
        spinner_char = SPINNER_FRAMES[spinner_index % len(SPINNER_FRAMES)]
        _draw(stdscr, rows, selected, scroll_offset, colour_pairs, agent_colours,
              header_pairs, paused_pair, spinner_char)

        key = stdscr.getch()
        tick += 1
        if tick % 2 == 0:
            spinner_index += 1

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

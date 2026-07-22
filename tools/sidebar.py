#!/usr/bin/env python3
"""Curses fleet sidebar — renders the tree built by sidebar_model, navigates
via sidebar_nav.

Presentation is deliberately split from curses: `flatten()` turns a Fleet
into a flat list of Row objects, and `render_lines()` turns those into plain
text with NO curses calls at all — that pure function is what tests assert
on. The curses app (`main`, run through `curses.wrapper`) is a thin loop that
polls a background `sidebar_model.watch()` thread and draws each line with
its status colour.

NO ANIMATION (sidebar-polish item 1 + revised item 9): every status glyph is
a single fixed-width character, unconditionally the same on every frame for
unchanged state — no spinner, no flash. Row layout never shifts because a
glyph disappeared or reappeared.

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
# revised: NOT the old "three plus one" framing). Every glyph is static —
# never swapped per-tick, never blank-on-odd-frame.
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

BUS_GLYPH = "📬"
NO_ACTIVITY_TEXT = "· no activity ·"
ELLIPSIS = "…"

# Separator between repo name and feature human name in a feature/architect
# window's target name, e.g. "orchids ▸ fleet sidebar". Must match the real
# tmux window names produced by the session-naming scheme exactly: U+25B8
# with one space on each side.
TARGET_SEPARATOR = " ▸ "

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


def _bus_row(depth: int, target: str, bus: sidebar_model.Bus) -> Row:
    return Row(
        depth=depth, kind="bus", target=target, label=bus.label,
        status=None, waiting_on_operator=False, is_subagent=False,
    )


def flatten(fleet: sidebar_model.Fleet) -> list[Row]:
    """Fleet -> flat list of Row, depth-first (repo, its features, their
    subagents). A live parent's collapsed bus row (sidebar-polish item 5), if
    any, is the FIRST row in that parent's group — before its features or
    subagents."""
    rows: list[Row] = []
    for repo in fleet.repos:
        rows.append(Row(
            depth=0, kind="repo", target=repo.name, label=repo.name,
            status=repo.status, waiting_on_operator=repo.waiting_on_operator,
            is_subagent=False, paused=repo.paused,
        ))
        if repo.bus is not None:
            rows.append(_bus_row(1, repo.name, repo.bus))
        for feature in repo.features:
            feature_target = f"{repo.name}{TARGET_SEPARATOR}{feature.name}"
            rows.append(Row(
                depth=1, kind="feature", target=feature_target, label=feature.name,
                status=feature.status, waiting_on_operator=feature.waiting_on_operator,
                is_subagent=False, activity=feature.activity,
            ))
            if feature.bus is not None:
                rows.append(_bus_row(2, feature_target, feature.bus))
            for sub in feature.subagents:
                rows.append(Row(
                    depth=2, kind="subagent", target=feature_target, label=sub.label,
                    status="working", waiting_on_operator=False, is_subagent=True,
                ))
    return rows


def _status_emoji(row: Row) -> str:
    if row.status == "waiting" and row.waiting_on_operator:
        return WAITING_ON_OPERATOR_EMOJI
    return STATUS_EMOJI.get(row.status, " ")


def _row_text(row: Row) -> str:
    indent = "  " * row.depth
    if row.kind == "bus":
        return f"{indent}{BUS_GLYPH} {row.label}"

    text = f"{indent}{_status_emoji(row)} {row.label}"
    if row.kind == "feature" and row.activity:
        text = f"{text} {row.activity}"
    return text


def _truncate(text: str, width: int) -> str:
    """Hard-slice to `width`, but a truncated string ends with an ellipsis
    (sidebar-polish item 8) rather than a hard cut — the ellipsis itself
    counts toward the width budget, never overflowing it."""
    if width <= 0 or len(text) <= width:
        return text[:width] if width > 0 else text
    return text[:width - 1] + ELLIPSIS


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

    No animation-related parameters (spinner_frame/flash_on) — every status
    glyph is static, so a frame depends only on the fleet's current state."""
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
    can't support custom colours — callers fall back to plain text."""
    if not curses.has_colors():
        return None, None
    try:
        can_custom = curses.COLORS >= 256 and curses.can_change_color()
        if not can_custom:
            return None, None
        steps = header_gradient(_HEADER_STEPS, paused=False)
        pairs = []
        for i, rgb in enumerate(steps):
            colour_id = 96 + i
            r, g, b = _rgb_to_curses(rgb)
            curses.init_color(colour_id, r, g, b)
            pair_id = _HEADER_PAIR_BASE + i
            curses.init_pair(pair_id, curses.COLOR_BLACK, colour_id)
            pairs.append(curses.color_pair(pair_id))
        paused_colour_id = 96 + _HEADER_STEPS
        r, g, b = _rgb_to_curses(PAUSED_HEADER_GRAY)
        curses.init_color(paused_colour_id, r, g, b)
        curses.init_pair(_HEADER_PAUSED_PAIR, curses.COLOR_BLACK, paused_colour_id)
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


def _draw(stdscr, rows: list[Row], selected: int, offset: int,
          colour_pairs: dict[str, int], agent_colours: list[int] | None,
          header_pairs: list[int] | None, paused_pair: int | None) -> None:
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

        text = _truncate(_row_text(row), max_x)
        attr = colour_pairs.get(row.status, 0)
        if row.kind == "bus":
            attr |= curses.A_ITALIC | curses.A_DIM
        if agent_colours:
            attr |= agent_colours[_agent_colour_index(_agent_colour_key(row))]
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

    while True:
        rows = flatten(shared.get())
        selected = _clamp_selected(selected, len(rows))
        max_y, _max_x = stdscr.getmaxyx()
        scroll_offset = clamp_scroll_offset(scroll_offset, selected, len(rows), max_y)
        _draw(stdscr, rows, selected, scroll_offset, colour_pairs, agent_colours,
              header_pairs, paused_pair)

        key = stdscr.getch()

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

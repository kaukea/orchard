"""Curses terminal colour management: direct-colour terminfo detection and
selection (applied once at process start, before curses ever calls
setupterm), RGB->xterm256/direct-colour-id conversion, the per-agent
ORCHID_PALETTE colour-pair init, `_ColourCache` (lazy colour-pair allocation
for arbitrary RGB fg/bg pairs), and the two safe single-cell/string curses
writes every row painter uses to dodge this build's cursor-autowrap
corruption on the window's own last column.
"""
from __future__ import annotations

import curses
import os
import zlib


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

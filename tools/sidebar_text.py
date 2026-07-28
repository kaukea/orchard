"""Cell-width-aware plain string primitives -- small caps, truncation with
the ellipsis rule, header-line centring -- with no colour or model
dependency. `unicodedata`-based `_cell_width` (East-Asian Wide/Fullwidth
glyphs occupy two terminal columns) is the one thing nearly every other
module in this renderer needs, which is why it lives in its own small,
foundational file rather than the colour or citation modules that use it.
"""
from __future__ import annotations

import unicodedata

from sidebar_glyphs import ELLIPSIS


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

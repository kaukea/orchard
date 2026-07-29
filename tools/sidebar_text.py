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

# --------------------------------------------------------------------------
# Compact numeric formatting — shared by the repo footer (age/worked/tokens,
# sidebar_model.py's `_repo_time_and_tokens`) and the task row's own metrics
# text (sidebar_rows.py's `_task_metrics_text`). Lives here rather than in
# sidebar_rows.py so sidebar_model.py can use it too without importing
# sidebar_rows.py, which itself imports FROM sidebar_model.py (that import
# would be circular the other way around).
# --------------------------------------------------------------------------


def _format_running_time(seconds: float) -> str:
    """Seconds -> compact human text — `Xs` under a minute, `Xm` under an
    hour, `XhMM` (zero-padded minutes, no unit on the minutes half) from an
    hour up, echoing the footer mock's own "6h02" shape
    (`sidebar_render_text.done_footer_line`'s docstring) so the footer and
    any per-row running-time figure read as one family rather than two
    invented conventions. Not itself a ruling — the exact text shape is
    unruled by the spec and is this function's own implementer choice,
    flagged as such rather than asserted as settled design."""
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h{minutes:02d}"
    if minutes:
        return f"{minutes}m"
    return f"{secs}s"


def _format_token_count(n: int) -> str:
    """A raw token count -> compact human text — bare digits under 1000,
    then a `k`/`M`-suffixed figure (one decimal place under 100 of the
    unit, none above, matching the footer mock's own "384k" shape) so a
    token count reads the same family wherever it appears (repo footer,
    task-row context figure). Not itself a ruling — the exact threshold/
    precision is this function's own implementer choice, same footing as
    `_format_running_time`."""
    for unit, size in (("M", 1_000_000), ("k", 1_000)):
        if n >= size:
            value = n / size
            return f"{value:.0f}{unit}" if value >= 100 else f"{value:.1f}{unit}"
    return str(n)

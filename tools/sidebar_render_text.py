"""Row -> plain display text, no curses -- the pure render pipeline a
headless caller (or a test) can exercise without a TTY. `render_lines()` is
the entry point: flatten() a Fleet, then compose each Row's own text
(feature/task layouts share their width-aware column math with the curses
painters via `_feature_row_layout`/`_task_row_layout`; an agent row goes
through the citation ladder's `identity_block`). `footer_lines`/
`done_footer_line`/`phase_mark`/`phase_dot_suffix` are pure formatters with
no populated data source yet (kept defined and tested, not dead).
"""
from __future__ import annotations

from sidebar_citation import _agent_expansion_fits, identity_block  # noqa: E402
from sidebar_glyphs import (  # noqa: E402
    NO_ACTIVITY_TEXT,
    PHASE_MARK,
    STATUS_EMOJI,
    SUBAGENT_GLYPH,
    _SUBAGENT_LIVE_GLYPH,
)
from sidebar_model import Fleet, TERMINAL_TASK_STATUSES  # noqa: E402
from sidebar_rows import INDENT_UNIT, Row, flatten  # noqa: E402
from sidebar_text import _cell_width, _truncate  # noqa: E402


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


def _agent_row_lines(row: Row, width: int, expand: bool) -> list[str]:
    """The agent row's 1-2 output lines (see `identity_block`), each
    prefixed with the row's own depth indent — `width` MUST be the row's
    real available column budget: the degradation ladder trims the model,
    then folds/drops the attribution to fit it, so a caller that instead
    hands this a generous sentinel and hard-truncates the composed string
    afterward can silently lose the role text on a deeply-indented row
    (regression, 2026-07-26 — the "writing ⋮ 🌿 ⋮" empty-role frame)."""
    indent = INDENT_UNIT * row.depth
    content_width = max(width - len(indent), 0)
    return [indent + line for line in
            identity_block(row.activity, row.role, row.model, content_width, expand,
                            effort=row.effort)]


def _row_text(row: Row) -> str:
    indent = INDENT_UNIT * row.depth
    if row.kind == "subagent":
        # A task/subagent that has reached a terminal state carries its own
        # STATUS_EMOJI glyph, so a completed row visibly reads as completed
        # (sidebar-titling item 4, Decision-058); otherwise its own
        # scheduled/doing glyph (rule 6, 2026-07-26).
        glyph = (STATUS_EMOJI[row.status] if row.status in TERMINAL_TASK_STATUSES
                 else _SUBAGENT_LIVE_GLYPH.get(row.status, SUBAGENT_GLYPH))
        return f"{indent}{glyph} {row.label}"
    if row.kind == "agent":
        return _agent_row_lines(row, width=200, expand=False)[0]  # defensive fallback only
    if row.kind == "repo" or row.kind == "accordion":
        # an accordion row is one step's own line — `label` is already the
        # fully composed glyph+small-caps text (`_step_row`), nothing more
        # to add; the curses draw path (`_draw_step_row`) additionally
        # layers the ACTIVE step's KITT sweep, which the plain-text path
        # never does (curses-only animation).
        return f"{indent}{row.label}"
    if row.kind == "task":
        return f"{indent}{compose_task_row_text(STATUS_EMOJI.get(row.status, '○'), row.label, row.progress_glyph, 200)}"
    # feature carries no progress cell of its own — see `_task_progress_glyph`.
    return f"{indent}{STATUS_EMOJI.get(row.status, '○')} {row.label}"


def _feature_row_layout(
    glyph: str, name: str, pct: int | None, width: int, badge: str | None,
) -> tuple[str, str, int, str, str]:
    """(glyph, shown_name, pad_width, badge_text, pct_text) for a feature row
    at `width` columns — the single source of truth for BOTH the plain-text
    dump path (`compose_feature_row_text`) and the curses per-column
    painter (`_draw_feature_row`), so their layouts can never drift apart
    (the same sharing pattern the file already used for
    `_feature_row_segments` before this step).

    `pct` is `None` for every live caller (operator ruling, 2026-07-26: a
    feature carries no percentage of its own — progress belongs to the
    task alone, drawn there as its fill circle) — `pct_text` is then "",
    the same as an absent badge. The parameter itself stays (rather than
    being deleted) purely so `FeatureRowLayoutTests` can keep asserting on
    the tail-composition math directly; nothing in the live render path
    ever passes an int here any more.

    Every measurement here is `_cell_width`, not `len()` — `glyph` is
    often a status emoji (e.g. the failed ❌, East-Asian-Wide, two cells
    for one character) and undercounting it by one cell is exactly what
    let a feature row overflow the pane edge (sidebar-teamwork defect 1)."""
    pct_text = f"{pct}%" if pct is not None else ""
    badge_text = f"{badge} " if badge else ""
    tail_len = _cell_width(badge_text) + _cell_width(pct_text)
    budget_for_name = max(width - _cell_width(glyph) - 1 - tail_len, 0)
    shown_name = name if _cell_width(name) <= budget_for_name else _truncate(name, budget_for_name)
    used = _cell_width(glyph) + 1 + _cell_width(shown_name) + tail_len
    pad_width = max(width - used, 0)
    return glyph, shown_name, pad_width, badge_text, pct_text


def compose_feature_row_text(
    glyph: str, name: str, pct: int | None, width: int, badge: str | None = None,
) -> str:
    glyph, shown_name, pad_width, badge_text, pct_text = _feature_row_layout(
        glyph, name, pct, width, badge,
    )
    return f"{glyph} {shown_name}{' ' * pad_width}{badge_text}{pct_text}"


def _task_row_layout(
    glyph: str, name: str, progress: str | None, width: int,
) -> tuple[str, str, int, str]:
    """(glyph, shown_name, pad_width, tail) for a task row at `width`
    columns — the progress cell (if any) is a SHORT, FIXED tail that
    always survives truncation intact; the NAME is what ellipsises when
    the row is too narrow (operator ruling, 2026-07-26: "a truncated name
    still reads, a truncated number misleads" — the same holds for the
    progress circle).

    Measured in `_cell_width`, not `len()` — same reasoning as
    `_feature_row_layout`, whose glyph vocabulary (STATUS_EMOJI) this row
    shares."""
    tail = f" {progress}" if progress else ""
    budget_for_name = max(width - _cell_width(glyph) - 1 - _cell_width(tail), 0)
    shown_name = name if _cell_width(name) <= budget_for_name else _truncate(name, budget_for_name)
    used = _cell_width(glyph) + 1 + _cell_width(shown_name) + _cell_width(tail)
    pad_width = max(width - used, 0)
    return glyph, shown_name, pad_width, tail


def compose_task_row_text(glyph: str, name: str, progress: str | None, width: int) -> str:
    glyph, shown_name, pad_width, tail = _task_row_layout(glyph, name, progress, width)
    return f"{glyph} {shown_name}{' ' * pad_width}{tail}"


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

    No animation, curses-only (bus-message-specifying B5, same "curses-only"
    split as the pre-existing spinner/blink animation): a repeated render of
    the same Fleet is byte-identical. Most rows render one line; an "agent"
    row renders 1 or 2 (quote, then its subordinate attribution line) per
    `identity_block` — `_agent_expansion_fits` decides once, for the whole
    frame, whether there's real room for the second line, so the extra
    lines are a property of the actual available height, never a per-row
    guess (operator ruling, 2026-07-26). The extra attribution line carries
    no selection marker of its own — it is not a separate Row."""
    rows = flatten(fleet)
    if not rows:
        return [_truncate(NO_ACTIVITY_TEXT, width)]

    expand = _agent_expansion_fits(rows, height)
    if height is None:
        window, start = rows, 0
    else:
        offset = clamp_scroll_offset(offset, selected, len(rows), height)
        window, start = rows[offset:offset + height], offset

    lines = []
    for i, row in enumerate(window, start=start):
        marker = ">" if i == selected else " "
        if row.kind == "feature":
            indent = INDENT_UNIT * row.depth
            avail = max(width - len(marker) - len(indent), 0)
            glyph = STATUS_EMOJI.get(row.status, "○")
            # A feature carries no percentage of its own (operator ruling,
            # 2026-07-26) — pct=None, so compose_feature_row_text's tail is
            # empty; the pane's own dimmer background band (curses-only,
            # `_draw_feature_row`) is what sets a feature row apart from a
            # task row, not a number.
            body = compose_feature_row_text(glyph, row.label, None, avail)
            lines.append(_truncate(f"{marker}{indent}{body}", width))
        elif row.kind == "task":
            indent = INDENT_UNIT * row.depth
            avail = max(width - len(marker) - len(indent), 0)
            glyph = STATUS_EMOJI.get(row.status, "○")
            body = compose_task_row_text(glyph, row.label, row.progress_glyph, avail)
            lines.append(_truncate(f"{marker}{indent}{body}", width))
        elif row.kind == "agent":
            body_lines = _agent_row_lines(row, max(width - len(marker), 0), expand)
            lines.append(_truncate(marker + body_lines[0], width))
            lines.extend(_truncate(" " * len(marker) + extra, width) for extra in body_lines[1:])
        else:
            lines.append(_truncate(marker + _row_text(row), width))
    return lines

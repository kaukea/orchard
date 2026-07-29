"""The per-frame dispatcher: erases the screen, then hands each Row to its
own kind-specific painter (repo/feature/task/accordion/agent/subagent),
tracking the current repo's hue as it goes so task-related rows can
resolve their own THIRD/FOURTH. Dead-space fill (sidebar-teamwork defect 1)
paints any remaining viewport rows in the repo's own dim fill hue rather
than leaving a bare void once content runs out. Once a repo's own rows are
all drawn — never merely once the loop stops for lack of room — its
FOOTER (`sidebar_paint_footer._draw_repo_footer`, spec §3's "the block's
LAST section") draws immediately after them, ahead of the next repo's
header or the dead-space fill.
"""
from __future__ import annotations

import curses

from sidebar_citation import _agent_expansion_fits  # noqa: E402
from sidebar_colour import _repo_hue  # noqa: E402
from sidebar_curses_colour import _ColourCache, _safe_addstr  # noqa: E402
from sidebar_glyphs import NO_ACTIVITY_TEXT  # noqa: E402
from sidebar_model import Repo  # noqa: E402
from sidebar_paint_feature import _draw_feature_row  # noqa: E402
from sidebar_paint_footer import _draw_repo_footer  # noqa: E402
from sidebar_paint_header import _draw_header  # noqa: E402
from sidebar_paint_identity import _draw_identity_block, _draw_subagent_row  # noqa: E402
from sidebar_paint_shared import _fill_row_bg  # noqa: E402
from sidebar_paint_step import _draw_step_row  # noqa: E402
from sidebar_paint_task import _draw_task_row  # noqa: E402
from sidebar_render_text import _row_text  # noqa: E402
from sidebar_rows import Row  # noqa: E402
from sidebar_text import _truncate  # noqa: E402


def _draw(
    stdscr, rows: list[Row], selected: int, offset: int,
    colour_pairs: dict[str, int], agent_colours: list[int] | None,
    colours: _ColourCache, tick: int, has_moved: bool = False,
    repos: list[Repo] | None = None,
) -> None:
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    if not rows:
        _safe_addstr(stdscr, 0, 0, _truncate(NO_ACTIVITY_TEXT, max_x), curses.A_DIM)
        stdscr.refresh()
        return

    # `repos` is None (unset) for every pre-existing caller/test that never
    # learned this parameter exists — an empty lookup, so the footer simply
    # never finds a match and draws nothing, same as before this step.
    repo_by_name = {r.name: r for r in (repos or [])}
    expand = _agent_expansion_fits(rows, max_y)
    y = 0
    # The current repo's hue triple — updated on every "repo" row, reused
    # by every "task"/"accordion"/"agent"/"subagent" row until the next one
    # (each resolves its own THIRD/FOURTH from this via `task_chain_roles`;
    # feature rows carry everything colour-related they need directly on
    # the Row already, see `task_colour`/`feature_colour`/`_open_block_bg`).
    hue = _repo_hue("")
    # The `Repo` object backing the CURRENT repo's block, so its footer can
    # be drawn once every row belonging to it has been — looked up by name
    # against `repo_by_name` (`Row` itself carries no age/worked/tokens/
    # dollars; only `sidebar_model.Repo` does). None until the first "repo"
    # row is seen, and again once its own footer has already been drawn
    # (`for`/`else` below covers the natural end-of-list case exactly once).
    current_repo: Repo | None = None
    for i, row in enumerate(rows[offset:offset + max_y], start=offset):
        if y >= max_y:
            break
        if row.kind == "repo":
            if current_repo is not None:
                y = _draw_repo_footer(stdscr, y, max_x, current_repo, colours, hue)
            current_repo = repo_by_name.get(row.label)
            hue = _repo_hue(row.label)
            _draw_header(stdscr, y, max_x, row.label, row.paused, i == selected and has_moved, colours)
            y += 1
            continue
        if row.kind == "feature":
            _draw_feature_row(stdscr, y, max_x, row, i == selected, colours)
            y += 1
            continue
        if row.kind == "task":
            y = _draw_task_row(stdscr, y, max_x, row, i == selected, colours, hue, tick)
            continue
        if row.kind == "accordion":
            y = _draw_step_row(stdscr, y, max_x, row, i == selected, colours, tick, hue)
            continue
        if row.kind == "agent":
            y = _draw_identity_block(stdscr, y, max_x, row, i == selected, expand, colours, hue)
            continue
        if row.kind == "subagent":
            y = _draw_subagent_row(stdscr, y, max_x, row, i == selected, colours, hue)
            continue

        text = _truncate(_row_text(row), max_x)
        attr = colour_pairs.get(row.status, 0)
        if i == selected:
            attr |= curses.A_REVERSE
        _safe_addstr(stdscr, y, 0, text, attr)
        y += 1
    else:
        # Reached only when the loop above ran to the end of its own
        # slice WITHOUT `break`-ing for lack of room — i.e. every row
        # belonging to the last repo drawn was actually drawn, not merely
        # as many as fit. The `break` path (out of vertical room mid-repo)
        # skips this on purpose: that repo's own block is not fully shown,
        # so its footer has nothing settled to summarise on screen yet.
        if current_repo is not None:
            y = _draw_repo_footer(stdscr, y, max_x, current_repo, colours, hue)

    # DEAD-SPACE FILL (sidebar-teamwork defect 1): the loop above only ever
    # stops short of `max_y` once `rows` itself has run out — the slice
    # `rows[offset:offset + max_y]` already claims every row the viewport
    # can hold, so reaching here with `y < max_y` means there is genuinely
    # nothing further to show, never a row scrolled past. `stdscr.erase()`
    # already blanked those remaining rows to nothing; paint them in the
    # current repo's own dim FILL hue instead (the same tone a feature row's
    # band and a task row's own bar background already use) so the pane's
    # surface claims the full height it was granted rather than stopping in
    # a bare, unstyled void the moment its content does.
    for fill_y in range(y, max_y):
        _fill_row_bg(stdscr, fill_y, max_x, hue["fill"], colours)

    stdscr.refresh()

"""Fleet -> Row assembly ("model building and folding" in this round's
discovery pass): the Row dataclass and flatten()/_feature_rows()/_task_rows()
depth-first walk that turns a Fleet into the flat list every render layer
(plain-text or curses) consumes. This is the one place the presentation
tree is BUILT; sidebar_render_text.py and the curses paint modules only
ever read a Row, never construct one.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sidebar_colour import _repo_hue  # noqa: E402
from sidebar_colour_lineage import feature_colour_base, task_colour_base  # noqa: E402
from sidebar_glyphs import (  # noqa: E402
    FEATURE_MARKER,
    TARGET_SEPARATOR,
    _ACCORDION_STEP_GLYPH,
    _PROGRESS_CIRCLES,
)
from sidebar_text import small_caps  # noqa: E402
from sidebar_model import (  # noqa: E402
    TERMINAL_TASK_STATUSES,
    Agent,
    Feature,
    Fleet,
    Step,
    Subagent,
    Task,
)


# --------------------------------------------------------------------------
# Presentation model (pure, no curses)
# --------------------------------------------------------------------------

# Indent unit for the six-level tree (repo/feature/task/accordion/agent/
# subagent), one unit per `Row.depth` — 2 columns per level (operator
# ruling, 2026-07-26, "very compact form": on a narrow pane, indentation
# competes directly with content, so it is the minimum that keeps a level
# legible, not the earlier 4-space draft).
INDENT_UNIT = "  "


@dataclass
class Row:
    depth: int
    kind: str  # "repo" | "feature" | "task" | "accordion" | "agent" | "subagent"
    target: str  # exact tmux window name to navigate to on Enter
    label: str
    status: str | None
    paused: bool = field(default=False)  # only meaningful for kind == "repo"
    repo_name: str = field(default="")  # owning repo's name; only meaningful for kind == "feature"
    progress_pct: int | None = field(default=None)  # kind == "feature" only; no source in this grammar
    progress_glyph: str | None = field(default=None)  # kind == "task" only — see `_task_progress_glyph`
    activity: str = field(default="")  # kind == "agent" only — the "doing" text
    role: str | None = field(default=None)  # kind == "agent" only
    model: str | None = field(default=None)  # kind == "agent" only
    # kind == "accordion" only — the ACTIVE step's own KITT sweep gate: true
    # only when it also has a genuinely "working" agent, not merely the
    # furthest-along position (an idle/stale/stopped agent's step is still
    # positionally "active" but has nothing live to signal — see
    # `_step_row`/`_draw_step_row`).
    live: bool = field(default=False)
    # kind in {"task", "accordion", "agent", "subagent"} only — this row's
    # owning OPEN task's own already-allocated colour (Ct, grade 2,
    # `task_colour_base`, computed once per feature by `_assign_task_
    # colours` so every row under the same task agrees on it). None for a
    # terminal task's own row (it uses a fixed done/failed colour instead,
    # see `_draw_task_row`) and for repo/feature rows (not applicable).
    task_colour: tuple[int, int, int] | None = field(default=None)
    # kind in {"task", "accordion", "agent", "subagent"} only — this row's
    # owning FEATURE's own grade-1 colour (`feature_colour_base`, computed
    # once per feature by `_feature_rows`), threaded the same way `task_
    # colour` already is. Only consumed when `SIDEBAR_COLOUR_SCOPE=feature`
    # re-roots the THIRD/FOURTH chain at the feature rather than the repo
    # (see `task_chain_roles`) — None otherwise (repo scope) and for
    # repo/feature rows (not applicable).
    feature_colour: tuple[int, int, int] | None = field(default=None)
    # kind == "task" only — the task row's own right-aligned METRICS text,
    # running time first (operator ruling, 2026-07-29 — see `_task_metrics_
    # text`). None when nothing is known yet, which is every task today:
    # `Task` carries no timestamp of its own for this to read.
    metrics: str | None = field(default=None)


def _agent_row(
    agent: Agent, target: str, depth: int, task_colour: tuple[int, int, int] | None,
    feature_colour: tuple[int, int, int] | None,
) -> Row:
    return Row(depth=depth, kind="agent", target=target, label=agent.role or agent.session_id,
               task_colour=task_colour, feature_colour=feature_colour,
               status=agent.status, activity=agent.activity, role=agent.role, model=agent.model)


def _subagent_row(
    sub: Subagent, target: str, depth: int, task_colour: tuple[int, int, int] | None,
    feature_colour: tuple[int, int, int] | None,
) -> Row:
    return Row(depth=depth, kind="subagent", target=target, label=sub.label, status=sub.state,
               task_colour=task_colour, feature_colour=feature_colour)


def _agent_and_subagent_rows(
    agent: Agent, target: str, depth: int, task_colour: tuple[int, int, int] | None,
    feature_colour: tuple[int, int, int] | None,
) -> list[Row]:
    """An agent's identity-line row, followed by its own subagent rows at
    the SAME depth (rule 6, 2026-07-26: a subagent hangs under the STEP its
    parent agent is on, not one level deeper than its parent) — both carry
    the owning task's own colour (`task_colour`, Ct) and the owning
    feature's own colour (`feature_colour`), so the curses draw path can
    paint them on the same open-block background as their step, and
    resolve the THIRD/FOURTH chain in either colour scope, without any
    further lookup."""
    return [_agent_row(agent, target, depth, task_colour, feature_colour), *(
        _subagent_row(sub, target, depth, task_colour, feature_colour) for sub in agent.subagents
    )]


def _step_row(
    step: Step, target: str, depth: int, task_colour: tuple[int, int, int] | None,
    feature_colour: tuple[int, int, int] | None,
) -> Row:
    """One line of the task's five-step accordion — a COLLAPSE KEEPS ITS
    OWN LINE (operator correction, 2026-07-26: "collapse keeps the line,
    it doesn't go to the previous one"), so every one of the five states
    (done/active/todo) gets its own row, always small caps, keeping its
    place among the five rather than folding into a shared summary line.
    The active step's agents (and their subagents) are the caller's job to
    nest beneath this row, one level deeper (see `_task_rows`) — this row
    itself only ever carries the step's own name and mark, plus the owning
    task's colour (`task_colour`) and feature's colour (`feature_colour`),
    which `_draw_step_row` resolves through `task_chain_roles` into its own
    FOURTH background (operator ruling, 2026-07-28 — supersedes the
    grade-3 `content_colour_base(task_colour)` reading this docstring
    previously described)."""
    glyph = _ACCORDION_STEP_GLYPH[step.state]
    label = f"{glyph} {small_caps(step.name)}" if glyph else small_caps(step.name)
    live = step.state == "active" and any(a.status == "working" for a in step.agents)
    return Row(depth=depth, kind="accordion", target=target, label=label, status=step.state,
               live=live, task_colour=task_colour, feature_colour=feature_colour)


def _task_metrics_text(task: Task) -> str | None:
    """The task row's own right-aligned METRICS text — running time first,
    tokens/context/model+effort a later step's own seam to fill (operator
    ruling, 2026-07-29: a single-task feature's task row shows its
    METRICS, especially its running time — see `_task_display_label` for
    the labelling half of the same ruling). Always None today: `Task`
    (sidebar_model.py) carries no timestamp of any kind — no `_seen_ts`,
    no `started`/`updated` — for this function to read a running time
    from. The ruling's own graceful-degradation instruction ("render from
    what exists today — event timestamps / `_seen_ts` age") names a
    source that exists only inside `sidebar_model.py`'s per-session `rec`
    dict, never threaded onto `Task` itself; that threading is a model-
    layer change outside this file's scope. Nothing is invented here to
    paper over the gap — the caller renders this row's metrics slot
    exactly as blank as it always has, until a later step gives `Task` a
    real field to read."""
    return None


def _task_display_label(task: Task, feature_name: str, single_task: bool) -> str:
    """The task row's own displayed text — literally "Task" when this is
    the feature's ONLY task and its name is a plain duplicate of the
    feature's own already-shown name (operator ruling, 2026-07-29,
    superseding the 2026-07-28 "show it plainly" call —
    `test_name_drop_rule_is_retired` in the pre-existing test suite — for
    this exact case). A solo task with nowhere better to derive its own
    name from falls back to reusing `feature_name` verbatim
    (`_identity_task_keys` in sidebar_model.py); showing that borrowed
    string a second time, right under the feature row that already shows
    it, repeats information rather than adding any. A second task, or a
    name that genuinely differs from the feature's, is NOT this case —
    `task.name` keeps showing plainly, unchanged, same as before this
    step."""
    if single_task and task.name == feature_name:
        return "Task"
    return task.name


def _task_progress_glyph(task: Task) -> str | None:
    """The task row's right-aligned progress cell — completed steps out of
    five, computed client-side from `task.steps` (never a wire/marker
    field: step state is a display concern, per the role->step map ruling
    already governing it). None for a task with no steps at all (nothing
    to show progress through — e.g. every agent on it is role-unmapped)."""
    if not task.steps:
        return None
    done = sum(1 for step in task.steps if step.state == "done")
    return _PROGRESS_CIRCLES[min(done, len(_PROGRESS_CIRCLES) - 1)]


def _task_rows(
    task: Task, target: str, depth: int,
    task_colour: tuple[int, int, int] | None = None,
    feature_colour: tuple[int, int, int] | None = None,
    feature_name: str = "",
    single_task: bool = False,
) -> list[Row]:
    """A task's own row (name left-aligned — `_task_display_label`, "Task"
    literal for the feature's solo duplicate-named task, operator ruling
    2026-07-29 — its progress circle and METRICS right-aligned,
    `_task_progress_glyph`/`_task_metrics_text`); `task_colour` is
    this task's own already-allocated Ct, grade 2, computed once per
    feature by `_assign_task_colours` — None for a terminal task, which
    uses a fixed done/failed colour instead, curses-only); `feature_colour`
    is the owning feature's own grade-1 colour, threaded the same way for
    the `SIDEBAR_COLOUR_SCOPE=feature` chain re-rooting (`task_chain_
    roles`). `feature_name`/`single_task` are `_feature_rows`'s own already-
    known values, threaded down purely for `_task_display_label`'s
    duplicate check. Plus — while it is still open — its five-line step
    accordion (`_step_row`, one row per `PHASES` entry, each keeping its
    own place whether done/active/todo), the active step's agents (and
    their subagents) nested one level deeper than that step's own row, and
    any role-unmapped agent (fails open, rendered directly under the task,
    no step to nest it in). A terminal task (`TERMINAL_TASK_STATUSES`)
    folds: its own row is all that shows."""
    name = _task_display_label(task, feature_name, single_task)
    rows = [Row(depth=depth, kind="task", target=target, label=name, status=task.status,
                 progress_glyph=_task_progress_glyph(task), task_colour=task_colour,
                 feature_colour=feature_colour, metrics=_task_metrics_text(task))]
    if task.status in TERMINAL_TASK_STATUSES:
        return rows
    for step in task.steps:
        rows.append(_step_row(step, target, depth + 1, task_colour, feature_colour))
        if step.state == "active":
            for agent in step.agents:
                rows.extend(_agent_and_subagent_rows(
                    agent, target, depth + 2, task_colour, feature_colour,
                ))
    for agent in task.unstepped_agents:
        rows.extend(_agent_and_subagent_rows(agent, target, depth + 1, task_colour, feature_colour))
    return rows


def _feature_collapsed(feature: Feature) -> bool:
    """A feature folds to its own single row once EVERY task is done — a
    still-open or failed task holds it expanded (operator ruling, 2026-07-
    26: a failed task is never quietly absorbed into a "complete" feature).
    An empty task list is never collapsed — there is nothing to have
    finished."""
    return bool(feature.tasks) and all(t.status == "done" for t in feature.tasks)


def _assign_task_colours(
    hue: dict[str, tuple[int, int, int]], feature_id: str, tasks: list[Task],
) -> dict[str, tuple[int, int, int]]:
    """One Ct (grade 2, `task_colour_base`) per OPEN task in `tasks`,
    keyed by `task_id` — computed together, in order, so each new task's
    rejection test sees every sibling already assigned so far (a terminal
    task never enters or occupies this: it uses its own fixed done/failed
    colour instead, and freeing up its slot for reuse needs no bookkeeping
    beyond simply not being in this dict, operator ruling 2026-07-26)."""
    assigned: dict[str, tuple[int, int, int]] = {}
    for task in tasks:
        if task.status in TERMINAL_TASK_STATUSES:
            continue
        assigned[task.task_id] = task_colour_base(
            hue, feature_id, task.task_id, list(assigned.values()),
        )
    return assigned


def _feature_display_label(feature: Feature) -> str:
    """The feature row's own displayed text (operator, 2026-07-28: "so
    🧩/<human feature name>" — U+1F9E9 JIGSAW PUZZLE PIECE, then a literal
    "/", then the feature's own name). `feature.name` already resolves
    through `_identity_task_keys`'s precedence (explicit `identity.
    feature_name`, then the middle segment of an `f/<feature>/<task>`
    identifier) down to `_finalize_feature`'s own existing honest fallback
    — the bare `feature_id` — when NEITHER is available. That bare-
    fallback case is told apart here by `feature.name == feature.
    feature_id` (true only when nothing was ever resolved) and rendered
    WITHOUT the marker: prefixing a raw internal identifier with "the
    marker for a human name" would itself be an invented claim that a real
    name exists. Chosen and reported, not decided silently."""
    if feature.name == feature.feature_id:
        return feature.name
    return f"{FEATURE_MARKER}/{feature.name}"


def _feature_rows(feature: Feature, repo_name: str, depth: int) -> list[Row]:
    """A feature's own row, followed by each of its open tasks (each a
    genuinely DIFFERENT segment of the same `f/<feature>/<task>` identifier
    where that shape is available — `_identity_task_keys` in sidebar_model.
    py resolves the feature row's own name and each task's own name from
    different segments of it, so the two rows carry different text by
    construction; there is no longer a name to drop or blank (the retired
    `_sole_same_named_task`/name-drop rule this replaced existed only to
    paper over the two rows showing the identical borrowed string)."""
    target = f"{repo_name}{TARGET_SEPARATOR}{feature.name}"
    rows = [Row(depth=depth, kind="feature", target=target, label=_feature_display_label(feature),
                 status=feature.status, repo_name=repo_name)]
    if _feature_collapsed(feature):
        return rows
    hue = _repo_hue(repo_name)
    task_colours = _assign_task_colours(hue, feature.feature_id, feature.tasks)
    # This feature's own grade-1 colour — computed once here (mirrors `task_
    # colours` above) and threaded onto every row below via `Row.feature_
    # colour`. `task_chain_roles` no longer re-roots THIRD/FOURTH on it
    # (that mechanism was retired along with `_chain_step` — Dracula
    # adoption, 2026-07-28: THIRD/FOURTH are fixed designed tones now, not
    # a computed chain), but the field is harmless to keep threading.
    feature_colour = feature_colour_base(hue, feature.feature_id)
    single_task = len(feature.tasks) == 1
    for task in feature.tasks:
        rows.extend(_task_rows(task, target, depth + 1,
                                task_colour=task_colours.get(task.task_id),
                                feature_colour=feature_colour,
                                feature_name=feature.name, single_task=single_task))
    return rows


def flatten(fleet: Fleet) -> list[Row]:
    """Fleet -> flat list of Row, depth-first: repo, its features, each
    feature's open tasks, each open task's steps (or unmapped agents), each
    active step's agents and their own subagents.

    A repo with no live session (`not repo.has_session`) is skipped entirely
    — header AND group — an empty project has nothing to show (sidebar-
    titling item 3).

    Within a repo's features, `done` features sort FIRST (stable sort,
    done-first), ahead of everything still live — sidebar-titling item 7.
    Tasks/steps/agents/subagents keep their model order (see
    `_assemble_repo`/`_live_subagents`)."""
    rows: list[Row] = []
    for repo in fleet.repos:
        if not repo.has_session:
            continue
        rows.append(Row(depth=0, kind="repo", target=repo.name, label=repo.name,
                          status=repo.status, paused=repo.paused))
        features = sorted(repo.features, key=lambda f: f.status != "done")
        for feature in features:
            rows.extend(_feature_rows(feature, repo.name, depth=1))
    return rows

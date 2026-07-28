- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# Features first-class: land Decision-105 everywhere, not just the sidebar

## Proposal

Operator, 2026-07-28: *"We're going to make features a first level concept in all of
the work we do."* Confirmed at intake as landing Decision-105 across every surface —
board, sidecars, branches, worktrees, supervisors, the close, and the GitHub
projection — rather than the display alone.

Decision-105 (2026-07-26) already ruled the model: the tree is
`area -> component -> feature -> task -> step -> agent -> subagent`, a feature spans
many tasks, and — the operator's words — *"every artifact still assuming [feature ==
task] is wrong."* That ruling was applied to the sidebar renderer and nowhere else.
This task is the rest of it.

## Blockers

None on the reading side. The shape of the feature object is the operator's to set —
`docs/TODO.md` is a file format, and file formats are his sole responsibility
(Decision-115's own framing). The bloom round is where that shape is converged.

## Findings

**Where feature == task is still assumed.** Read off the live tree at `ceca7ae`:

- `docs/TODO.md` — a flat list of TASKS. `feature` appears only as one value in the
  badge's type field (`feature · bug · refactor · housekeeping · completion`), which
  makes it a peer of `bug`, not a container of anything. Nesting is expressed by
  two-space indentation and `~edge` tags; neither creates a feature node.
- `docs/TODO.md.d/<id>.md` — one sidecar per task. A feature has no sidecar, so it
  has nowhere to carry its own scope, its own testing agreement, or its own state.
- Branches and worktrees — `f/<id>` and `.claude/worktrees/<id>` are created per
  task. The `f/` prefix already says "feature" while naming a task.
- The supervisor — one per feature in its charter, one per task in practice, because
  the gardener hands off a single board line.
- The close — the groundskeeper squashes one branch and flips one board badge, so a
  feature spanning several tasks has no moment at which it is itself complete.
- `board_gh.py` — the GitHub projection maps a board line to an issue. A feature
  spanning many issues has no representation beyond the `~edge` tags.
- `CHANGELOG.md` — one entry per closed task, so the reader sees the parts and never
  the feature.

**Already correct and usable as the reference implementation:** the sidebar's orchard
marker (Decision-099) is keyed `(project, feature)` and holds the tasks under that
feature with their states. It is the one place a feature is already a durable object.

### Full site inventory, read off `ceca7ae`

**The board grammar (`board_lint.py`, `AGENTS.files.md` §TODO).** One regex matches
every line at every depth (`board_lint.py:70`); level is inferred purely from indent
(`:77`, `depth = len(indent) // 2`); the same six-field badge is required of a parent
line and a leaf line alike (`:96`). A parent is defined only as "has children", and is
required to be contentless — it must carry no area (`:107-112`) — so a feature is
modelled as a roll-up, never as a thing with its own identity. Every line demands its
own sidecar (`:113`), with no relation between a parent's sidecar and its children's.
The readiness stage is applied at every depth (`:102`), though Decision-105 places the
five steps inside a task only.

**The GitHub projection (`board_gh.py`).** There is a `Task` class (`:88`) and no
Feature class anywhere in the file. A parent's children are flattened into markdown
text in the issue body under a "Sub-tasks" heading (`:159-172`); a feature line and its
task lines are pushed as sibling issues with no hierarchy between them (`:228-237`).
`sync_relationships` (`:357-378`) syncs only `blockedBy` — no parent/child link is ever
sent to GitHub, although the same GraphQL path already in that function is what a real
sub-issue link would use. An issue born on GitHub is minted at column zero, always typed
`feature`, never attached to a parent (`:542-552`).

**The identity chain (`courier.py`, `orchard_topic.py`, `sidebar.py`).** This is where
the conflation is load-bearing rather than cosmetic. `sidebar.py` is already correct:
it has a `Feature` class holding a *list* of `Task` (`:1053-1062`), and it assembles on
the pair `(feature_id, task_id)` (`:1596-1618`). But `courier.py:371` sets
`feature_id = <worktree directory name>`, and `identity_of()` (`:368-382`) returns no
`task_id` at all — so `orchard_topic._identity()`'s task keys are always dropped, and
the sidebar's correct two-level key is permanently populated with `task_id ==
feature_id`. The correct data structure exists and is starved of data. Separately,
`project_slug()` (`:966-987`) embeds the branch, so two tasks of one feature on
different branches would land in two different projects.

**The naming helper (`feature_name.py`).** Called "feature" throughout (`:2`), but its
own docstring says task (`:51`), and it resolves any board line at any depth by sidecar
basename (`:59-72`). Its public API takes a single id — there is no `(feature, task)`
pair to give it.

**The rule files.** `AGENTS.files.md:123` heads the section "per-feature design-spec
contract" and its very next line (`:125`) says the sidecar is "the durable contract for
ONE task" — the two words for one object, two lines apart. §Changelog (`:299-310`)
anchors one detail block to one `archive/<feature-id>` tag, so feature, branch,
workflow and changelog entry are one chain. `skills/workflow/SKILL.md:87` states it
most plainly of all: *"The chosen task's `{#id}` becomes the `<feature-id>`."* That
same skill forbids branching from a feature branch (`:58`), which forecloses a task
branch living under a feature branch.

**The agents.** `agents/supervisor.md` contradicts itself: `:20-22` already carries
Decision-105 correctly — *"A feature holds MANY tasks, commonly worked at the same
time. You are not a queue"* — while `:64-65` has that same supervisor create exactly
ONE worktree and ONE branch, leaving the concurrent tasks nowhere to run. `:161` stops
the whole feature pipeline on a single task's failure. `agents/gardener.md:14` hands
ONE feature to a landscaper, while `:153-155` offers parallelism as "other ready tasks,
each in its own landscaper" — which silently promotes every task to a feature.
`agents/groundskeeper.md:3` uses both words for the same object inside one sentence.

### The load-bearing question

Everything above resolves once one thing is ruled: **does a task get its own branch and
worktree beneath its feature, or do a feature's tasks share one feature branch?** The
worktree cardinality decides the supervisor's shape, whether the close needs a per-task
variant plus a feature-level close, whether one changelog entry covers a feature or a
task, and where a real `task_id` comes from for the identity chain. It is the first
question, and the rest are consequences of it.

### Mechanical versus ruled

Renames and label fixes with no behaviour change: `feature_name.py`'s helper name and
its caller in `courier.py:381`; the heading/body contradiction at `AGENTS.files.md:123`;
the `created_during` field, which actually records a branch id; the "task" strings in
`board_gh.py:257,512` and `board_lint.py:62,123`; `groundskeeper.md:3`; and the dated
schema-1 compatibility shim at `sidebar.py:1244-1252`, which can be deleted once writers
emit a real `task` key.

Everything else needs the operator's ruling: worktree and branch cardinality; whether a
feature line gets a different badge grammar from a task line and whether level is indent
or an explicit marker; whether a feature gets its own sidecar; whether a feature becomes
a real GitHub parent issue with sub-issue links; changelog granularity; landscaper per
feature or per task; and whether sibling tasks share one orchard project directory.

## Questions

Converged by the bloom round with the operator; recorded here as they are settled.

## Testing

To be agreed at scope. The board is machine-checkable — `board_lint.py` reads the
badge grammar — so a format change has a real verification surface.

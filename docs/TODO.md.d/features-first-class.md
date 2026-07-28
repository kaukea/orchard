- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# Features first-class: land Decision-105 everywhere, not just the sidebar

## Proposal

Operator, 2026-07-28: *"We're going to make features a first level concept in all of
the work we do."* Converged by the bloom round of 2026-07-28 (all rulings below are
the operator's, dictated during that round). A feature is a long-living, first-class
concept on every surface — and never a git construct.

**1. Git — main-branch development stands.** Every task gets a short-lived branch off
main, named `f/<feature>/<task>` (operator's example: `f/oauth-auth/pbkcd`), and lands
on main individually by squash merge, exactly as today. There is NO integration or
feature branch, ever — the operator does not believe in long-running feature branches.
A feature is a set of short-lived task branches. It is useful to record which base a
feature started at; the feature then gains new tasks later, in several disconnected
rounds — the feature is long-living, its branches never are. Review trigger set by the
operator: revisit this ruling when agent teams are fully implemented in Claude.

**2. Board — strictly two levels, two badge grammars.** Feature lines get a distinct
badge: feature id, its gh# parent issue, the list of components it touches, and
derived task progress. A feature delivers value: it TOUCHES components, it does not
own them (one feature can touch many components; bugs belong to components, and a
component can belong to one or more features). Task lines keep today's six-field
badge; the five readiness steps stay inside tasks (Decision-105). One fixed,
badge-free `One-offs` bucket line — the one-off bucket IS the empty feature — holds
every task that belongs to no feature; this keeps the format topologically correct
without inventing features where there are none. The lint knows exactly three shapes:
feature line, task line, the single One-offs bucket. Accepted render:

```
- 🌿 {#oauth-auth} ❘gh#40❘ ⟶ login, tokens ◾◾⬜ 2/3
  - {#refresh-tokens} ❘seeded❘feature❘m❘auth❘gh#71❘
  - {#logout-everywhere} ❘sprouted❘feature❘s❘auth❘gh#72❘
- 📦 One-offs
  - {#fix-flicker} ❘tended❘bug❘xs❘sidebar❘gh#61❘
```

**3. Sidecars — the feature is a container file.** A feature gets ONE sidecar
`docs/TODO.md.d/<feature>.md` holding feature-level scope plus its tasks as `## Task`
sections. Writing is segregated: each task's agent writes only its own section; when
task writing needs coordination, the agent messages the gardener (there is no
orchestrator role). Standalone tasks are called ONE-OFFS and keep their own sidecar
file as today.

**4. GitHub — the feature is a parent issue.** This maps to GitHub's sub-issues
perfectly (operator's words). The feature issue carries the full design — matching
the practice of designing a large feature while only building the minimum viable
product first. Task issues attach as real sub-issues at mint, across disconnected
rounds, to the same still-open parent. The parent closes only when the operator rules
the feature delivered (native GitHub behaviour: nothing auto-closes it). One-offs are
flat issues with no parent. Issues born on GitHub are UNFILED: triage assigns each to
a feature or to one-offs before a board line exists (the triage UI exists but is
currently buggy — operator observation).

**5. Changelog & close — flat WIP, structure at release.** One squash merge = one
task = one flat changelog entry per visible change; nothing feature-shaped can exist
between releases (there is nothing to squash at feature level). At release time the
flat entries are structured into a release block grouped by feature (one-offs listed
plain), then flatness begins again. Archive tags mirror branch names:
`archive/<feature>/<task>`, keeping entry–tag–branch one chain.

**6. Agents — a team of landscapers per feature.** The gardener knows the high-level
plan: which tasks are waiting for each feature, which depend on one another, and
tries to parallelise non-conflicting ones. The supervisor makes it real: decides how
many landscapers, who does what, launches the team, and introduces the landscapers to
one another before they start. The team shares context or uses messaging — whichever
is token-efficient. Task↔landscaper binding is fluid: it is dangerous to statically
assign a task to one landscaper when part of it can be built inside another task, so
distribution is negotiated over messages. Potential conflicts are dealt with upstream
before anything lands. The supervisor intervenes only when work diverges from the
original intent (the autonomy ladder/metronome, Decision-075) — and the operator wants
these rules kept very, very light. The supervisor runs the close sequentially as
today. One feature-level runtime (shared team context) is preferred: more efficient,
safer, saves tokens.

**7. Identity — no namespace change.** The fix that avoids a singular namespace when
worktrees are at play STANDS: each task finishes on its own and each task session
lives in an independent world. The sidebar's feature→task grouping is fed by the
feature carried in posted message metadata — the orchard model already has features
with tasks inside them. The courier is transport only: it cares about session ids and
topics, never about features.

## Decision entries

Proposed for promotion by the gardener (rulings are the operator's, cleaned from
dictation; the render in §2 was explicitly accepted):

- Branch naming: short-lived task branches off main named `f/<feature>/<task>`; no
  feature/integration branches ever; review when Claude agent teams land.
- Board grammar: two levels, distinct feature badge (id, gh#, touched components,
  derived progress), literal badge-free One-offs bucket as the empty feature.
- Feature sidecar: container file with segregated per-task `## Task` sections;
  coordination via message to the gardener; one-offs keep their own files.
- GitHub projection: feature = parent issue + sub-issues; unfiled issues triaged
  before minting; one-offs flat; parent closed only by operator ruling.
- Changelog: flat per-squash entries; feature structure applied only at release
  cut, grouped by feature; archive tags `archive/<feature>/<task>`.
- Build runtime: supervisor-launched team of landscapers with fluid task binding,
  shared context/messaging, upstream conflict handling, metronome-only
  intervention, sequential close; rules kept very light.

## Blockers

None. The file-format shapes (board grammar, container sidecar, branch and tag
naming) were set by the operator in the bloom round.

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

**The identity chain (`courier.py`, `orchard_topic.py`, `sidebar.py`).** As read at
intake: `sidebar.py` is already correct — a `Feature` class holding a *list* of `Task`
(`:1053-1062`), assembled on the pair `(feature_id, task_id)` (`:1596-1618`) — while
`courier.py:371` appeared to set `feature_id = <worktree directory name>` with no
`task_id`. CAVEAT (bloom round): the operator states the courier only cares about
session ids and topics, and that worktree detection was supposed to have been removed
long ago — this intake reading may describe removed or regressed code and MUST be
re-verified against HEAD before any build acts on it. Separately, the per-branch
project namespace is now RULED correct (Proposal §7), not a defect.

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
same skill forbids branching from a feature branch (`:58`) — consistent with the
bloom ruling: task branches come off main, there is no feature branch to branch from.

**The agents.** `agents/supervisor.md` contradicts itself: `:20-22` already carries
Decision-105 correctly — *"A feature holds MANY tasks, commonly worked at the same
time. You are not a queue"* — while `:64-65` has that same supervisor create exactly
ONE worktree and ONE branch, leaving the concurrent tasks nowhere to run. `:161` stops
the whole feature pipeline on a single task's failure. `agents/gardener.md:14` hands
ONE feature to a landscaper, while `:153-155` offers parallelism as "other ready tasks,
each in its own landscaper" — which silently promotes every task to a feature.
`agents/groundskeeper.md:3` uses both words for the same object inside one sentence.

### Mechanical versus ruled

Renames and label fixes with no behaviour change: `feature_name.py`'s helper name and
its caller in `courier.py:381`; the heading/body contradiction at `AGENTS.files.md:123`;
the `created_during` field, which actually records a branch id; the "task" strings in
`board_gh.py:257,512` and `board_lint.py:62,123`; `groundskeeper.md:3`; and the dated
schema-1 compatibility shim at `sidebar.py:1244-1252`, which can be deleted once writers
emit a real `task` key. Everything that previously needed a ruling received one in the
bloom round (Proposal §§1-7) or is explicitly deferred below.

### Bloom round result (2026-07-28)

Adaptive measurement over 7 dimensions, 38 items total. Convergence: overall SE
0.419, band **lower** — per the graduated outcome this returns to the gardener for
replanning, no launch. Per dimension (SE / items / top hypothesis):

- branch_cardinality: 0.923 / 8 / EXHAUSTED, misfit flagged — see below
- feature_identity: 0.333 / 3 / container sidecar
- board_grammar: 0.317 / 6 / distinct feature badge
- github_projection: 0.249 / 6 / parent issue + sub-issues
- changelog_close: 0.327 / 6 / flat task entries only
- agent_cardinality: 0.300 / 6 / team of landscapers per feature
- orchard_project: 0.485 / 3 / per-branch worlds unchanged

**Misfit note (branch_cardinality).** Mid-round the operator reversed the apparent
early convergence: the early items' previews drew task branches "under" a feature
branch, which he was reading as the NAMESPACE (`f/<feature>/<task>`), not as git
integration branches. The engine's recorded top hypothesis for this dimension is a
statistical artifact of those early items; the operator's final ruling was explicit,
restated, and confirmed ("exact", with the Claude-teams review trigger) — Proposal §1
is the spec. The exhaustion and misfit are what drove the band to lower.

Launch-sizing recommendation from the engine: size **l**, model claude-fable-5,
effort high. Caveat: v1 item parameters (discrimination/difficulty) are LLM-assumed,
not corpus-fitted — the convergence numbers are indicative, not calibrated.

## Voluntary deferrals

Explicitly left open (Decision-027), each with its decision criterion:

- **Single-task feature runtime.** Uniform supervisor-always shape ONLY IF it costs
  the same tokens AND reduces implementation complexity; otherwise keep today's
  path — the existing system already parallelises and tokens must not be wasted.
  Decide at build with measured token cost.
- **One-off branch naming** under the new scheme (today `f/<id>`; the ruled scheme
  names `f/<feature>/<task>` for feature tasks). Not ruled for one-offs; settle at
  plan.
- **Where the feature's starting base is recorded** (container sidecar frontmatter
  is the obvious home). Not pinned; settle at plan.
- **courier.py current state.** Verify the intake reading against HEAD before any
  identity-chain work; the operator expects worktree detection to be gone already.
- **Branch-model review trigger.** Revisit Proposal §1 when agent teams are fully
  implemented in Claude (operator condition attached to the confirmation).

## Questions

All settled in the bloom round of 2026-07-28; rulings recorded in the Proposal:
branch cardinality (§1), board grammar and One-offs bucket (§2), feature sidecar
shape (§3), GitHub projection and unfiled triage (§4), changelog and archive tags
(§5), build-time team model and coordination (§6), orchard identity (§7).

## Testing

To be agreed at scope. The board is machine-checkable — `board_lint.py` reads the
badge grammar, and must learn the three ruled shapes (feature line, task line, the
single One-offs bucket) — so the format change has a real verification surface.

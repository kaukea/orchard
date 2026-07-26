- created: 2026-07-26
- created_by: Sebastien Lambla
- created_during: gardener session (post-cutover live check a)

## Findings

- OPERATOR OBSERVATION (2026-07-26, verbatim): "only a black 'orchids'
  centered text on a white background, no other line". Pane capture
  confirms: the project name centered, zero session rows.
- This IS bus-finishing's deferred live acceptance check (a) — "the sidebar
  still shows session activity end-to-end after the cut" — FAILING on first
  observation. The release cut is held on this check passing.
- Environment verified NOT at fault before boarding (gardener diagnostics):
  - The pane runs the RIGHT file: `python3 .ai/repositories/serialseb/
    orchids/tools/sidebar.py`, cwd = main checkout, no worktree in the
    path; mirror at 231b59d, `tools/sidebar.py` byte-identical with main.
  - The renderer is the NEW one: its child `inotifywait -m -r … /run/user/
    1000/orchard/projects` watches the orchard tree.
  - The DATA side is live: `projects/kaukea.orchids/` holds a
    `<sessionid>.marker` and fresh events (gardener `status: triaging`
    posted 13:42 via `orchard_topic.py`, courier announce), yet no row
    renders.
- Styling also wrong in the same view: black-on-white, no project hue —
  possibly the same defect (nothing past the header paints), noted, not a
  separate report.
- `--once` produced a curses traceback under a non-tty (cbreak ERR) —
  whether the consolidated renderer still has a one-shot mode is unclear.
  Pulled INTO scope by operator ruling 2 (below); no longer a loose end.
- BLOOM ROUND (Decision-050, 2026-07-26): three operator answers, relayed
  verbatim through the gardener, closed the WHAT. Engine report, taken as
  given: overall SE 0.518, band "lower", launch-sizing recommendation m
  (claude-opus-4-8, xhigh), zero misfit flags, no deferral candidates.
  Caveats: v1 item parameters are LLM-assumed, not corpus-fitted
  (uncalibrated_items: true); the acceptance dimension converged (SE
  0.30) while the testability dimension reads non-converged (SE 0.74) as
  an instrument artifact — its final confirmation item would have
  re-asked a ruling the operator had already stated twice and was not
  posed, leaving residual posterior mass on the never-probed "landscaper's
  call" hypothesis, which ruling 2 overrode. Substance is settled; the
  band, taken as given, routes the launch decision back to the gardener.

## Proposal

Make the consolidated `tools/sidebar.py` render session rows from the live
orchard tree, and give the display a durable tree to render.

Diagnosis (2026-07-26, confirmed by reproduction — see Findings): FOUR
independent code defects, not one.

1. `watch()` returns silently when its `inotifywait` child dies; the watch
   thread ends and the UI freezes on its last frame forever. This is what
   the operator was looking at — the pane froze when the archiver compacted
   the projects tree.
2. `_assemble_repo` admits a feature row only for
   `identity.agent == "landscaper"`; the gardener is consumed as the repo
   header and every other role is dropped. The frozen frame held a gardener
   and an architect, so: header, no rows.
3. The repo hue IS applied, then destroyed — `_rgb_to_xterm256` resolves the
   orchids purple onto the grayscale ramp (index 236), and the default
   selection adds `A_REVERSE`, inverting it. That is the reported
   "black text on a white background".
4. The model rebuilds from events every scan, so the 120-minute event
   archival erases rows that must persist until restart.

The fix, architecturally (operator design, this session): the MARKER stops
being a zero-byte per-session touch-file and becomes the durable TREE NODE,
keyed `(project, feature)`, carrying area, node state and the feature's
completed tasks. The transport writes it from the identity already in the
envelope; the sidebar reads the tree from it. Events supply live state; the
marker supplies structure and memory. Retention, correct placement of late
data whose upstream messages have been archived, and revival-by-moving-the-
file-back all fall out of that one mechanism.

In scope: the four defects; the marker format change and its transport
writer; `--once` restored as a real one-shot curses frame (ruling 2); a
regression test that fails when a project with a live marker and fresh
events yields zero rows, asserted through a NON-landscaper identity
(ruling 3); a migration entry for the marker format.

Deferred, returned to the gardener: the pruning process itself (operator:
undecided, a UI concern); the `:session:` routing prefix leaking into
marker/event filenames and double-prefixing `to` addresses, which gives one
session two markers — a transport addressing defect, not a renderer one.

### ROUND 2 (2026-07-26) — the agreed plan after the failed eyeball

The round-1 diagnosis above was correct as far as it went and its four
defects are built. What it got WRONG is the model: it treated feature and
task as one thing, because that used to be true. The operator corrected the
whole hierarchy this session, and the display is rebuilt to it.

WHY THE EYEBALL FAILED — not a live-half defect. `sidebar-mount.sh` resolves
its own directory through a symlink into `.ai/repositories/serialseb/
orchids/`, a checkout pinned to `main`, and has no flag or environment
variable pointing elsewhere. The sidebar mounted into an agent's window
therefore runs MAIN's renderer whatever branch the worktree holds. Captured
side by side at identical pane size (32x51) against the identical tree: the
main-build pane drew three lines and no activity; the branch-build pane drew
the same rows PLUS live activity subscripts and the five stage dots, with a
status posted two minutes earlier appearing without a restart, and the
header carrying `ESC[48;2;44;24;62m`, the exact orchids purple. Rows and hue
both already pass on the branch build. A full round was spent on a defect
that was not there, because the operator was shown pre-change code.

IN SCOPE, agreed this session:
1. The renderer gets the real hierarchy: project -> feature -> task -> step
   -> agent -> subagent. Six levels where it has three.
2. A SESSION STOPS BEING A ROW. It resolves to an agent on a step of a task.
   Two sessions on one feature draw ONE feature, not two — the duplicate the
   operator saw on screen.
3. The three collapse rules, and nothing else ever hidden: a finished step
   folds to a plain line as the next opens; a task folds once all its steps
   are complete; a feature folds once all its tasks are. A new task REOPENS
   its feature and revives the completed siblings from the marker cache.
4. Identity gains `task` alongside `feature`, written by the transport. Only
   the agent knows which task it is on and nothing can infer it.
5. The step is derived client-side from the AGENT ROLE via a static map in
   each agent charter's frontmatter, so it survives the pending `groomer`
   rename. The map FAILS OPEN — an unmapped role still renders, without a
   step — and is a FALLBACK, so an explicit phase on the wire later is an
   addition rather than a rewrite.
6. The gardener's events carry no `identity` block at all, so its session is
   dropped and every delegation it scheduled is orphaned: no subagent row
   can render, and the gardener is never matched as the header supplier.
   Fixed.
7. The mount runs current code, so the operator's own window can show a
   branch build.

DEFERRED, returned to the gardener: an explicit phase on the wire (the
operator's own "second step"); the AREA and COMPONENT levels above the
feature, which is why the marker's `area` field must stop pretending to be a
per-task attribute; the pruner, unchanged.

## Testing

Live, operator eyeball (the standing check-a gate), confirmed as written
by ruling 1: with the gardener session running, the bar shows the orchids
header WITH its hue and one session row carrying current status; the row
updates on a fresh `orchard_topic.py post status` without restart.
Missing hue keeps check (a) failing even with rows working. Passing this
closes check (a) and re-arms the release-cut trigger.

Build-time, automated (ruling 3): a regression test, runnable through the
restored `--once` path, failing whenever a project that holds a live
`<sessionid>.marker` and fresh events yields zero session rows.

## Decision entries

Operator rulings, 2026-07-26, answered in the Decision-050 bloom round
and relayed verbatim through the gardener:

1. The check (a) pass bar is rows AND hue — the Testing gate stands as
   written; missing hue keeps check (a) failing even with rows working.
2. `--once` (one-shot render) is restored as part of this fix so the
   renderer is testable; acceptance remains the operator's live eyeball.
3. An automated regression test ships with the fix: it fails when a
   project with a live marker and fresh events yields zero rows.

Decisions taken in the build round (2026-07-26), for mechanical folding:

## [2026-07-26 CEST] Decision-NNN: The fleet display is five levels, and only the task persists
#sidebar #hierarchy #orchard #marker #retention

The display hierarchy is `project -> feature -> task -> agents -> subagents`.
An AGENT is an own-session delegation sent to complete a task; there may be
several per task and they are usually sequential — a sower, a valve running
alongside, a cleanup — until the work returns to the orchestrator. A
SUBAGENT is what an agent spins up. A TASK is created by the orchestrator
and is normally a board item, though not always, since work is sometimes
asked for outside the workflow.

Agents and subagents are EPHEMERAL. They appear while working and stop
displaying when they finish, and that includes an agent's name, model and
activity — those are a subscript of the task it is working, never a thing
that outlives it. The task is the one that does not disappear. On screen: a
task being worked shows its agent's subscript and that agent's subagent rows
beneath it; once every agent on the task has stopped, the task remains as a
single row carrying its terminal state, with nothing beneath it.

The earlier reading of this feature treated agent and task as one row,
because in practice a single agent works a single task and the two were used
interchangeably. That conflation is what made an earlier draft of this build
cache agent identity and delegation labels for persistence — the two things
that must NOT persist.

## [2026-07-26 CEST] Decision-NNN: The orchard marker is the durable task node, keyed by project and feature
#sidebar #orchard #marker #retention #transport

The marker stops being a zero-byte per-session heartbeat and becomes the
durable record of the TASK: one file per `(project, feature)`, carrying the
area and the tasks under that feature with their states, so a completed task
survives without activity. It holds nothing agent-shaped — no role, name,
model or activity — because those are live-only and are read from the event
stream alone. Events supply what is happening now; the marker supplies what
remains when nothing is happening.

Pruning archives the node rather than deleting it, so moving the file back
rehydrates the feature's tasks when new work starts in it. AREA is stored
inside the marker, not in its filename — keying the filename on the feature
alone keeps revival a single direct lookup instead of a glob across archived
areas, which would fork one feature into two nodes whenever a new task
arrived in an unseen area.

## [2026-07-26 CEST] Decision-NNN: Retention is until restart; the pruner is deliberately undesigned
#sidebar #retention #marker

Operator ruling: a completed feature or task stays for the lifetime of the
session, until restart. How long beyond that, and when pruning runs, is
explicitly UNDECIDED and treated as a later user-interface concern — no
pruning policy or process is designed or built now. What ships is only the
shape a future pruner needs: archiving a node rather than deleting it, and
restoring it by moving the file back. This refines Decision-094 (staleness
is a colour, not a removal), which assumed rows survive because their events
do; they do not, since the 120-minute archival of Decision-091 removes the
events a rebuilt-every-scan model depends on.

## [2026-07-26 CEST] Decision-NNN: The sidebar renders a row for any identity, not only landscapers
#sidebar #rows #identity

A session earns a row the first time an identity is seen for it, whatever
its role; the gardener continues to supply the repo header. The previous
landscaper-only filter silently dropped every other role — an architect
session with a live marker and fresh events rendered nothing — which is the
defect that failed live acceptance check (a). Identity decides that a row
EXISTS and labels it; the marker decides how long it LIVES. Mailboxes that
never carry an identity, such as `operator`, never become rows.

## [2026-07-26 CEST] Decision-NNN: Exact hue comes from a direct-colour terminfo, not palette redefinition
#sidebar #colour #hue #terminal

The renderer selects a direct-colour terminfo (`tmux-direct` / `xterm-direct`,
`RGB`, `colors#0x1000000`) when truecolor is advertised, so ncurses accepts
the mock's exact RGB values as colour numbers and no approximation runs at
all. `can_change_color()` — false under `tmux-256color`, which is what forced
the approximation — stops being relevant, because direct colour needs no
palette redefinition. The 256-colour path survives only as a fallback for
terminals that genuinely cannot do better, and is corrected there too: the
24-step grayscale ramp may only win for near-neutral colours, never for a
chromatic one, having previously resolved the orchids purple to gray. A
header is also no longer inverted merely by being the default selection.

## [2026-07-26 CEST] Decision-NNN: A round-trip test needs a static-data companion
#testing #rule #fixtures

Operator rule, given verbatim: "never test code where the caller and the
callee are the same code without another test with static daata vaidated at
feature riting time."

A test in which our own writer produces the input our own reader consumes
proves only that the two agree with each other. When both are wrong in the
same way it still passes, so the suite reports health while the behaviour is
broken. Any such round-trip test must therefore be ACCOMPANIED by a test
over static data — fixture content hand-validated at the time the feature is
written, ideally captured from the running system — so the contract is
pinned to something neither side of the code can move.

This branch is the worked example of why. Its writer and reader agreed on a
marker shape that cached agent identity; every round-trip test passed, and
the shape was still wrong, being rejected outright once the operator saw the
model it implied. Earlier in the same feature a suite of 332 tests passed
against a sidebar that rendered an empty pane, because every fixture in it
described the one agent role the code happened to handle. Green tests
written this way measure agreement, not correctness.

A corollary governs maintenance: when a static fixture disagrees with the
code, the fixture is not the thing to fix. It is the older, independently
validated party, and the disagreement is the signal the rule exists to
produce.

## [2026-07-26 CEST] Decision-NNN: A watcher's death must not silently freeze the sidebar
#sidebar #liveness #robustness

`watch()` consumed its `inotifywait` child's output with a `for` loop, so the
child exiting ended the loop, returned from `watch()`, terminated the watch
thread and left the user interface redrawing a stale frame indefinitely —
with no exception, no log line and no fall-through to the polling branch
already present in the same function. Observed live: the archiver compacting
the projects tree killed the watcher, and the pane showed a frozen frame for
twenty minutes while a second sidebar started afterwards rendered correctly
from identical data. A supervising loop is mandatory: the watcher is
restarted, or the polling fallback takes over, and the display never stops
following the tree while the process lives.

Decisions taken in the ROUND 2 planning conversation (2026-07-26), for
mechanical folding:

## [2026-07-26 CEST] Decision-NNN: A feature spans many tasks; the display is seven levels
#sidebar #hierarchy #feature #task #taxonomy

The full tree is `area -> component -> feature -> task -> step -> agent ->
subagent`. Area and component come from the ARCHITECTURE.md taxonomy; the
renderer enters at FEATURE and builds downward, because the work is code.

It USED to be true that only tasks existed, that a task was always the role
of an orchestrator, and that feature, task and orchestrator session were one
to one. THAT IS NO LONGER TRUE, and every artifact still assuming it is
wrong. A feature spans multiple tasks as a tree. Operator's worked example:
"message bus version two" is the FEATURE; idempotent sending, outbox
buffering and messaging prioritization are three TASKS under it.

Within a task the five STEPS run — ideation, scoping, designing, building,
releasing. The steps belong to the TASK, not to the feature. Several tasks
of one feature are commonly worked at the same time, and more than one agent
may work a single step, which is rare but real: a step holds a LIST of
agents and a feature a LIST of open tasks, neither being a single-slot
field.

This supersedes the five-level reading recorded earlier in this same
feature, which omitted area and component above and collapsed step into the
task below.

## [2026-07-26 CEST] Decision-NNN: Nothing is ever hidden except by the two collapses
#sidebar #retention #collapse #revival

Nothing is hidden merely for being inactive: a feature is NOT hidden because
one of its tasks is idle. There are exactly two collapses. A TASK collapses
once everything in it is complete, folding its steps, identity lines and
subagent rows inside a single row carrying its terminal state. A FEATURE
collapses once ALL of its tasks have completed, leaving one row. A finished
STEP folds to a plain line as the next opens, keeping its place in the five.

The two levels have DIFFERENT LIFETIMES, and that asymmetry is the entire
reason for caching and revival. A TASK is terminal: it is completed or it is
not, and it never reopens — a change, an addition or a bug fix becomes a NEW
task, never a revisit. A FEATURE is not terminal and is not idempotent:
adding a task expands what the feature does, so a collapsed feature REOPENS
and its completed tasks are revived alongside the new one rather than lost.
A feature's completed mark is therefore never a permanent state, only its
current one — which is what the archive-a-node-and-move-it-back shape exists
to serve.

## [2026-07-26 CEST] Decision-NNN: The active step is derived from the agent's role, in the UI
#sidebar #step #role #ui

OPERATOR RULING, given for the THIRD time before it was written down. Twice
before — once when the model was first mapped, once on repeat — it was
stated and never recorded, and that omission is precisely why the same
ground was re-covered. The failure was the recording, not the ruling.

WHICH step is active is computed CLIENT-SIDE by the renderer from
information already collected off the bus. It is a user-interface concern,
not a bus concern: no event names a step, and nothing is added to the
transport to supply one.

The derivation is the AGENT ROLE, because each role currently sits in
exactly one step — gardener in ideation, landscaper in building,
groundskeeper in releasing, and so on. The map lives in each agent charter's
frontmatter, so a role's step travels with the role's own definition and
survives a rename, `groomer` being mid-rename as this is written. It FAILS
OPEN: an unknown or unmapped role still renders, without a step, because the
entire defect class this feature exists to fix is rows silently vanishing.
The map is a FALLBACK, so an explicit phase on the wire — deliberately
deferred as a second step — would win over it and arrive as an addition
rather than a rewrite.

## [2026-07-26 CEST] Decision-NNN: Messaging carries which task an agent is on
#transport #identity #task #sidebar

The role gives the step but not the TASK. With a feature spanning many
tasks, an identity block carrying only the feature cannot place an agent,
and nothing downstream can infer that placement. The identity block
therefore gains `task` alongside `feature`, written by the transport.

This is structure rather than presentation — only the agent knows which task
it is working — and it is not a step, so it stands with the ruling above
rather than against it. The division is: the bus says WHO and ON WHAT, and
the interface works out WHERE IN THE PIPELINE that puts them.

## [2026-07-26 CEST] Decision-NNN: A subagent speaks through its spawner, or it should be an agent
#transport #delegation #subagent #sidebar

A subagent has no session of its own. It is registered under its parent's
full session ID as the parent plans it, and it carries no model, no status
text and no identity. Anything it has to report travels through the agent
that spawned it — which is exactly why the delegation schedule / begin / end
messages exist, and why the display needs nothing beyond the three facts
they carry: that the subagent was PLANNED, that it is DOING, that it is
DONE.

The operator's corollary is the design test: if a unit of work genuinely
needs to post its own updates, that is the signal it should have been an
AGENT with its own session rather than a subagent. The reporting shape
decides the kind, not the other way around.

Subagent rows are live-only and are folded away when their task collapses,
like everything else inside it.

## [2026-07-27 CEST] Decision-NNN: Depth is carried by background colour, and colour encodes lineage
#sidebar #colour #layout #contrast #accessibility

Nesting in the fleet display is expressed by BACKGROUND COLOUR rather than by
indentation, which frees the horizontal space indentation was consuming — at
32 columns an agent line has 24 usable cells and its quote plus role is
exactly 24, so indentation and content were competing for the same cells.

The bands: the project header is centred and carries a gradient from a first
colour to a second; the feature row is painted the whole available line in the
second; the task row sits on that with a left vertical bar whose FOREGROUND is
the task's own colour; each of the five steps is a full line from cell one,
centred, in small caps, on a third colour. An OPEN step and everything inside
it — its agents, their quotes and attributions, their subagent bubbles — share
a DIMMER variant of that third colour, so the expanded stage reads as one
block whose bounding box is easy to find. Step labels are centred rather than
left-aligned: the full-width band already gives the eye an edge at both ends,
so a centred small-caps label reads as a section header over left-aligned
content, and no indent cell is spent.

COLOUR IS DERIVED IN THREE GRADES — feature base, then task base, then content
base — so colour encodes LINEAGE: which feature a task belongs to, and which
task a block of content belongs to, are both legible without reading a word.
A task's colour is drawn from within its feature's range, randomly rather than
ordinally: no ramp, no lightness ladder, no evenly spaced rotation, because a
task's colour carries identity alone and must not imply sequence, age or
priority. Separation between siblings comes from choosing well — a candidate
too close to a live sibling is redrawn — not from a scheme. The colour must
nonetheless be STABLE for the life of the task, so it is derived
deterministically from the task's identity rather than sampled at render time;
a task that changed colour as it repainted, or two panes disagreeing about a
task's colour, would both read as defects. Tasks never reopen, so colours may
be reused freely and no recycling or exhaustion machinery is built.

CONTRAST IS CALCULATED, not eyeballed, against the known guidelines and at
runtime from the resolved colours rather than from hardcoded pairs — the
feature hue varies per project and the palette is explicitly open beyond the
orchid colours. Where a derived pair fails, the FOREGROUND moves; the
background does not, because it is carrying structure. Where a terminal cannot
render the derived colour, readability outranks fidelity: a wrong-but-readable
colour beats an accurate unreadable one.

Feature base colours are assigned as features are created, kept in the
repository and synchronised with GitHub. A renderer reads that value when
present and derives one from the project hue when it is absent or
unparseable — a permanent fallback rather than a stopgap, since a feature
without an assigned colour must still render sensibly.

## [2026-07-27 CEST] Decision-NNN: Never combine the dim attribute with a custom background
#sidebar #curses #terminal #rendering

Found by reproduction and bisection while building the colour bands:
combining ncurses' `A_DIM` with a custom truecolor pair, immediately followed
by another custom-pair draw on the next row, CORRUPTS that next row's
background. Dimming is therefore never expressed as an attribute over a
non-default background; the foreground is blended toward its own background
in RGB instead, which produces the same visual result without the state
corruption.

A second rendering trap was found alongside it: writing to a window's literal
last column with `addstr` triggers an auto-wrap cursor advance that can
desync the colour state for the row drawn next. That one cell is written with
`insch` instead, which cannot safely carry wide or multi-byte characters and
so is used only for a space.

Both are the same class of defect — a drawing call whose damage lands on the
NEXT row rather than its own — which is why they were only ever visible as an
unexplained band of wrong colour somewhere else on screen, and why they were
found by bisection rather than by reading the code.

Related tooling note, recorded because it cost real time: `tmux capture-pane
-e` does NOT faithfully reconstruct a busy multi-pair row in this environment,
even under the project's two-stable-captures protocol. It also emits a colour
only when it CHANGES, so a row inheriting the previous row's background shows
no escape at all and reads as unstyled. Ground truth for what was actually
drawn is the raw `pipe-pane` byte stream.

## [2026-07-26 CEST] Decision-NNN: A feedback surface must run current code
#tooling #feedback #sidebar #mount

`tools/sidebar-mount.sh` resolves its own directory through a symlink into
`.ai/repositories/serialseb/orchids/`, a checkout pinned to `main`, and
accepts no flag or environment variable pointing elsewhere. The sidebar
mounted into an agent's window therefore runs MAIN's renderer whatever
branch the worktree holds, so a feature that changes the sidebar can never
be seen working in the window of the very session building it.

This cost a full round. The operator's live acceptance check was run against
pre-change code and reported the pre-change behaviour, while the branch
build — which already passed both halves of the agreed bar — was never on
screen. The rule that follows is general: when the purpose of a surface is
to collect the operator's verdict, it must run the code under judgement,
mounted at present time and torn down with the verdict. Showing out-of-date
code to gather feedback produces a verdict about the wrong artifact.

## Result

Result: built and automatically tested; AWAITING THE OPERATOR'S LIVE EYEBALL,
which is the agreed acceptance gate and cannot be self-approved.

ROUND 2 SUMMARY. The round-1 eyeball failed against code that was never on
screen — the mounted pane runs the fleet-vendored renderer pinned to `main`,
so the branch build was never what the operator judged. Diagnosing that
uncovered the deeper problem: the display's model was wrong, not just its
wiring. A feature spans many tasks, a task passes through five steps, and
agents sit on steps — where the renderer had three levels and minted one row
per session.

WHAT SHIPPED, 9 commits this session on `f/sidebar-empty-rows`:
- `fcb9fe5` role-to-step map in each agent charter's frontmatter
- `924a5a8` the mount runs the caller's own checkout, not the vendored copy
- `53629e1` the task travels in every message's identity; marker schema 2
- `d7a471d` a session's role survives a resume
- `49724aa` the six-level tree, the three collapses, revival, fail-open
- `fc9d1c8` the round's rulings staged as decisions
- `1e3dd99` static-data fixtures pinning the transport contract
- `f3e4425` depth by background colour, three-grade lineage, computed contrast
- `7408b6f` a task says its own name again

TESTED: `python3 -m pytest tests/ -q` -> 436 passed, 6 subtests passed (416
at the start of round 2). Plus live verification against the real bus, not
fixtures — see the section above: the branch transport wrote the new identity
shape and upgraded the live marker to schema 2 in place; `courier.py init`
turned this session's zero-byte heartbeat into a persisted role and
`identity_of()` then resolved it with the environment variable unset; and the
rebuilt renderer was read back off the operator's own 32-column pane, with the
open step's dimmed block confirmed spanning its agent and subagent lines by
decoding the raw escape sequences.

NOT SELF-APPROVED. Ruling 1's bar is rows AND hue on a live pane, judged by
the operator. That judgement is his alone and has not been given.

### LIVE EYEBALL FAILURE, 2026-07-26 (operator verdict, verbatim)

- Static data renders: "project name, feature name etc showing static data
  for this project".
- Live data does NOT: "No agent or activity anywhere" — no session row
  appeared, and none appeared even as a fresh status post landed on the
  runtime tree during the look.
- New observation to fix alongside it: "Missing difference between feature
  and task" — the rendered rows do not distinguish the two levels.
- Operator ruling on ordering: "Cosmetic changes once it works" — function
  first. Ruling 1's bar (rows AND hue) still gates the eventual close.

So the marker half of the build works and the EVENT half does not: structure
paints, liveness does not. Diagnosis in progress; nothing below is closed.

### Live verification performed against the real bus (round 2)

Not fixtures — the branch code exercised against `/run/user/1000/orchard`:

- THE TRANSPORT WROTE THE NEW SHAPE LIVE. A real status event posted through
  this worktree's `orchard_topic.py` carries the full identity block —
  `agent`, `feature`, `feature_name`, `name` as the feature_name alias,
  `task`, `task_name`, `parent` — and the same post UPGRADED the live
  `sidebar-empty-rows.marker` IN PLACE to `"schema": 2` with its `tasks[]`
  entry keyed on `task`. The pre-upgrade schema-1 marker was captured as a
  fixture first and is now the only surviving record of the retired shape.
- THE RESUME FIX WORKS ON THE LIVE BUS. `python3 tools/courier.py init` run
  against this session turned its zero-byte heartbeat marker into
  `{"role": "landscaper"}`, and with `CLAUDE_CODE_AGENT` UNSET,
  `courier.identity_of()` then resolves `agent_type: landscaper` from that
  file rather than from the environment. That is the whole mechanism proven
  end to end, not asserted.
- BOTH RENDERERS COMPARED SIDE BY SIDE at identical pane size (32x51) against
  the identical tree, which is how the failed eyeball was diagnosed: the
  vendored main build drew three lines and no activity; the branch build drew
  the rows with live activity subscripts, the stage dots, and the header's
  exact `ESC[48;2;44;24;62m` purple, updating on a status posted two minutes
  earlier without a restart.

### OPERATOR ACTION — repairing the running gardener

The gardener session is anonymous on the bus because it was RESUMED and a
resume drops the role. It cannot be repaired automatically: no record was
ever written for it. From the gardener's own pane, once this branch is
merged and synced:

    python3 tools/courier.py init --agent gardener

This persists its role under its session id, and every later event from that
session — and any future resume of it — then carries an identity. Verified by
the equivalent run against this landscaper session, above. Until it is run,
the renderer's fail-open path and the parent-chain derivation are what keep
the gardener's header and its subagents on screen.

### Prior build state, retained for reference (NOT a result)

- branch: `f/sidebar-empty-rows`
- base: `53aae9d` (local `main`)
- tested: `python3 -m pytest tests/ -q` → **375 passed, 3 subtests passed**
  (332 at branch point; 43 added). Plus direct verification against the LIVE
  orchard tree, not only fixtures: both on-screen states reproduced by
  removing every event file and reading what the real renderer drew, and a
  real one-shot frame captured from a throwaway tmux pane via `pipe-pane`,
  confirming the header's exact `48:2::44:24:62` purple.
- NOT self-approved: the standing check (a) gate is the operator's live
  eyeball on a running sidebar. Automated coverage is met; the visual gate
  is his.

### Confidence — what is verified, and what is not

Stated per change, because it differs sharply and a single number would
mislead.

VERIFIED AGAINST REALITY, fails loudly rather than quietly:
- row eligibility (an architect session reappeared live), `--once` (raw pty
  bytes captured from a real pane, exit 0), filename validation (checked
  against every name actually present in the live tree, including
  `operator.marker`, through which operator questions are delivered — it is
  accepted, so the new raising validator does not break that path), and task
  persistence (reproduced by deleting every event file).

WORKS HERE, LESS CERTAIN ELSEWHERE:
- HUE depends on this machine's terminfo shipping a `*-direct` entry. Where
  none exists it falls back to the chroma-gated 256-colour cube, which is
  unit-tested but eyeballed only once. Degrades to an approximate colour,
  never a crash.
- MARKER SEMANTICS: the static-fixture rule already exposed one hole here
  (`working` was unreachable for a marker-only task). Assume siblings exist.
  In particular the MULTI-TASK LIST SHAPE HAS NEVER EXISTED IN PRODUCTION —
  today one feature maps to exactly one task, so that shape is exercised
  only by fixtures written in this session.
- WATCHER RESTART is proven for the tested failure, a killed child.
  Untested: inotify watch-limit exhaustion, the root being replaced by a new
  inode, and a permanently-failing binary, where it retries on a one-second
  backoff indefinitely.

WEAKEST, AND DELIBERATELY ON THE RECORD:
- THE ENFORCEMENT HOOK FAILS OPEN. Documented behaviour: a hook exiting
  non-zero-but-not-2 is a non-blocking error and execution continues. So if
  the script goes missing, loses its execute bit, or `jq` is absent after a
  sync, enforcement silently disappears and nothing reports it. Fail-closed
  on identity, fail-open on its own breakage.
- COMMAND MATCHING has a stated ceiling: a call written to a file and then
  executed, an encoded payload decoded at runtime, or nesting past three
  unwrapping levels still passes. Matching command text is not parsing a
  shell, and the hook's header says so rather than implying completeness.
- NOTHING HAS RUN POST-SYNC. The hook and the rewritten charters take effect
  only after this merges and `kauk sync` converges the vendored copies. The
  configuration that will actually run has never run.

### PRIORITY 0 FOLLOW-UP — the outbox, for token savings (operator, in session)

Operator: "write up the outbox because i need the token savings as a
priority 0". Written up here in full so the next round starts from evidence
rather than re-deriving it. NOT built on this branch.

THE COST, MEASURED THIS SESSION. Every courier round-trip pays a fixed
overhead independent of payload:
  parent side (Opus):  SendMessage call ~80-150, result blob ~80,
                       task notification ~100-150  => ~330 per round-trip
  courier side (Haiku): turn preamble ~250, plus ~130 per command
Measured from this session's own courier: cumulative 31,195 at announce
(one-off charter load), then deltas of +927 for 5 commands, +1,800 for 9,
+1,250 for 6, +675 for 3, +412 for 1.
So five separate asks cost ~1,650 parent tokens; one ask carrying five costs
~330. The dominant term is PARENT-SIDE, on the expensive model, and it is
the envelopes and notifications rather than the instructions.
Caching does not remove this: the courier's context is cached, so each
resume re-reads rather than rebuilds it — but that read happens once PER
TURN over a context that keeps growing. Turns are the unit of cost.

THE DESIGN.
1. OUTBOX, correctly located. `orchard_deliver` currently writes
   `.{name}.partial` INSIDE the destination directory and renames within it,
   so the staging area is the recipient's own mailbox. The temp file and an
   outbox are the same concept in the wrong place (operator). Give each
   sender a real outbox; delivery becomes one atomic move across the
   boundary. Same-filesystem requirement already holds, both being under
   `$XDG_RUNTIME_DIR/orchard`.
2. ANY AGENT MAY WRITE ITS OWN OUTBOX. That act is private, published to
   nobody, affects no other agent — so nothing needs enforcing and no
   courier turn is spent. Parent cost per message falls from ~330 to ~50: a
   plain script call, no SendMessage, no notification.
3. PUBLICATION IS THE COURIER'S. Only the move has an outside effect, so
   only the move is restricted. The courier sweeps and publishes N queued
   messages in ONE turn. Cost stops scaling with how often agents speak and
   starts scaling with how often the courier sweeps — an operator-controlled
   number. This also gives the courier the first responsibility on this path
   that the script cannot perform for its caller (see the finding below that
   it currently injects, removes and verifies NOTHING when posting).
4. AUTH HANDSHAKE (operator design). The publishing step expects an auth
   value known to the sender script — sender agent plus a uuid, or a
   subagent-script handshake. A bypass then still SUCCEEDS at writing but is
   never forwarded, and the sender is told so. This is deliberately not
   prohibition: it makes a bypass ineffective and self-reporting rather than
   blocked. Derive it per sender rather than as one shared secret, so a
   leaked value implicates one agent and rotates without a fleet reset.
5. "SENT" STATUS IN THE BUS, SURFACED IN THE UI (operator: "UI matters
   too"). A message carries a delivery state, and the sidebar shows it. This
   is what makes a skipped courier visible rather than silent — the gap
   `hooks/courier-init.sh` already names when it says it can detect a
   skipped courier but not withhold anything.
6. SUBSCRIPTION FILTERING. Recipients declare what they want relayed, so
   couriers stop paying to hand up traffic nobody asked for. Inbound side of
   the same economy. INFLOW IS EXPLICITLY NOT TOUCHED IN THE FIRST ROUND
   (operator: "not touch the inflow just yet") — the outbox and its flush
   are the whole of it; filtering follows separately.
7. PRIORITY PER SUBJECT — urgent / normal / low (operator design). Each
   subject in the closed corpus carries one of the three, and the priority
   decides WHEN THE OUTBOX FLUSHES rather than whether a message is sent.
   That is what converts the outbox from a queue into the token lever: an
   urgent message triggers a sweep, a normal one rides the next scheduled
   sweep, and a low one waits for a sweep it does not itself justify. The
   flush policy, not the message rate, becomes the thing that determines
   cost — and the operator sets it.
   Worked implication: status telemetry, the highest-frequency traffic in
   the fleet and the reason this economy matters, is LOW — nothing waits on
   it, and a stale status word costs nothing. A question to the operator, or
   a lifecycle signal a parent is blocked on, is URGENT and must not sit in
   a queue waiting for a sweep. Assigning the three across the 22-subject
   corpus is a design step of its own and should be done with the operator
   rather than inferred, since it is the actual policy.

POSTURE, ruling this round: "I'm working on the working assumption that you
cannot completely forbid... just make it either too much work for the agent
or if it does the work, it passes, then no one will know none the wiser and
fair do." Raise the cost; do not chase absolutes. An agent that does the
work to bypass has done no harm and the outcome is accepted. All artifacts
must describe the mechanism that way — `agents/courier.md` was corrected on
this branch for claiming harness enforcement it does not deliver.

CONSEQUENCE FOR WHAT THIS BRANCH BUILT: guarding the MOVE is a far smaller
target than guarding the whole posting surface by matching command text. The
`PreToolUse` hook would shrink rather than grow, the charters could let
agents write directly again, and the regex ceiling documented in
`hooks/courier-only-transport.sh` would stop being load-bearing.

### Follow-ups returned to the gardener — NOT written to the board here

-6. THE SESSION-NAMING HOOK HAS NOT TAKEN EFFECT on the operator's running
   session. He states the deal: "repo shold be the name of the session and
   going there on the board shoul bring me to the ex-orchestrator window,
   that was the original deal". The resolver was corrected on this branch to
   honour it — a bare repo target resolves to the SESSION of that name and
   selects its orchestrator window, being the window whose name carries no
   repo-and-feature separator. But `tmux list-sessions` shows exactly one
   session, named `main`, holding all three windows. So repo-level navigation
   will resolve NOTHING on his machine until sessions are actually named
   after their repository. Deliberately NOT worked around: no special-casing
   of `main`, no guessing a session by anything other than its name. The code
   is right and the environment has to catch up, which belongs with the
   naming follow-up above.
   TO BE CLEAR ABOUT WHOSE FAULT THE NAME IS — he did not choose it: "i did
   not nmeit i asked it to benamed and maybe the hook fixed in the last few
   hours is still not ok". `main` is tmux's DEFAULT name for a session
   created without one, which is consistent with the rename never landing
   rather than with a deliberate choice. He suspects the recently-fixed hook
   is still wrong. A read-only diagnosis was run to establish what is
   supposed to perform the rename, whether it is runnable, and whether it
   could ever have applied to the already-running session; findings below the
   DIAGNOSIS RESULT — THERE IS NO HOOK, AND THERE NEVER WAS. The agreed
   contract (docs/TODO.md.d/session-naming.md, operator scope ruling
   2026-07-21) is explicitly "no hook build-out, no wrapper — `claude --name`
   at launch carries the session name; enforcement is forward-only at launch
   sites". `agents/gardener.md:9` still launches the top-level session as
   `claude --agent gardener` with NO `--name`, so it falls back to tmux's
   default of `main`. Every other launch site received the contract; the
   top-level one was missed when it was implemented. Confirmed: no
   `rename-session`, `new-session -s` or equivalent exists anywhere in
   hooks/, .claude/hooks/ or settings.json.
   TWO CONSEQUENCES. No hook could have fixed this, so the recent hook work
   was never going to help. And nothing can rename a session already running:
   the mechanism is launch-time only, so it takes effect at the next gardener
   launch and not before.
   THE FIX IS ONE LINE — `claude --agent gardener --name "orchids"` — the
   bare repository name, per session-naming.md's "one orchestrator per
   repository, so its session name IS the repository".
   SECOND DEFECT IN THE SAME FILE: `agents/gardener.md:184-185` still creates
   landscaper windows with the `▸` separator, though the navigator moved to
   `/` on 2026-07-24 (commits 202efea, aa4700d). This one is DEFUSED rather
   than outstanding — the resolver on this branch now accepts either — but
   the creator and the contract still disagree.
   OWNER: an existing task already covers this, `docs/TODO.md.d/
   tmux-naming.md`, created 2026-07-26, which names the separator mismatch as
   inherited work. Returned there rather than fixed here: it is the gardener's
   own charter, the naming scheme is being reworked, and the operator has
   ruled remaining work minor.

-5. NAVIGATION, EVERYTHING BEYOND THE MINIMAL SEPARATOR FIX. Resolution by
   pane working directory rather than by window name, a visible message when
   navigation fails instead of a silent no-op, real-tmux integration tests,
   and cross-session switch verification. All were specified and then CUT by
   the operator's minor-work-only ruling. The reason they matter is recorded
   above at ledger item 32: matching a window by the FORMAT of its name is
   what let this rot unnoticed, and mocked tests asserting invented names is
   what kept it hidden. The repo-level row is part of this: the gardener's
   window is named "claude", so a repo target cannot match by name at all,
   and that was deliberately left unfixed rather than special-cased.

-4. WINDOW AND SESSION NAMING IS WRONG — a STANDING complaint, restated:
   "i have compained that none of the windows or sessions are named
   corectly". The operator then gave the intended scheme: "session name
   should be repo (there a hook it seems to work ok), the titltes for tasks
   have gone mad (look at the length of this one), it was supposed to show
   featue -> task (the other plugin i have reads the focused pane name and it
   gets overwritten back and forth i think)".
   So: SESSION = repo, which already works via a hook. WINDOW TITLE =
   `feature -> task`, which does NOT: the live window is named `orchids ▸
   Sidebar empty rows: header renders, zero session rows off the live orchard
   tree — check (a) failing` — the feature's entire board title, not a
   feature-and-task pair. He also suspects a TUG-OF-WAR: another plugin reads
   the focused pane's name and something overwrites it back and forth.
   WHY IT MATTERS TO THE DISPLAY, and the connection is worth keeping: the
   feature's NAME on the board is that whole sentence, so the feature row and
   the task row both inherit it and read alike. Much of the feature/task
   confusion this round fought with colour is really bad data — once the
   names are a short feature and a short task, the rows differ for free.
   THE TEXT BAR ALWAYS SHOWS THE AGENT NAME (operator ruling, separate from
   the window-title scheme above and not to be merged with it): "the text bar
   should always be theagent name i never know who im talking to, i hae all
   the other areas to tell me the rest." The bar answers exactly one
   question — WHO AM I TALKING TO — and every other surface already carries
   the feature, the task and the state. Today it carries the feature's whole
   board title and answers nothing.
   NOT BUILT HERE: window titling is set at spawn by the gardener, the names
   come from the board, and both are the gardener's, never a landscaper's.
   Also under the minor-work-only ruling.

   ACCOUNTABILITY NOTE, recorded because it is the pattern this feature keeps
   hitting rather than a grievance: the operator observes "we're very far off
   one of your agent's |cockpit view, done| from two days ago". A previous
   agent declared the cockpit view DONE while the reality was nowhere near
   it. The same shape recurred twice more inside this feature — a suite of
   332 tests green against a sidebar rendering an empty pane, and a `done`
   staged against a live eyeball that had been run on code which was never
   the build. Every instance shares one cause: something was declared
   finished on evidence that never touched the running thing. It is the
   reason the testing gate on this feature is the operator's live look and
   cannot be self-awarded.

-3. THE STATISTICS ARE GONE. Operator, in passing: "especially as we lost all
   statistics in this one". Recorded as a real loss to investigate rather than
   as an aside — what was being shown, when it stopped, and whether this
   feature's rebuild or an earlier change is responsible. ARCHITECTURE.md
   describes age, worked, tokens and dollars fields that "currently always
   render at their empty default", which may be the same gap seen from the
   code side. NOT investigated here, on the minor-work-only ruling.

-2. THE DEVELOPMENT MODEL, stated by the operator 2026-07-27 and previously
   unrecorded anywhere: "one session = 1 repo, 1 repo = 1 window, 1 feature =
   1 window, grouped by repo. Hence the navigaton from the sidebar to switch
   quickly where attention is required across many sessions and windows."
   So: a tmux SESSION per repository, a WINDOW per feature, windows grouped
   by repo. THE SIDEBAR IS A NAVIGATION SURFACE, not merely a status display —
   its purpose is jumping to wherever attention is needed across many sessions
   and windows, which is why row selection resolves to a tmux destination.
   This constrains the display: a row must be able to identify WHERE its work
   is happening, not only WHAT is happening, and the six-level rebuild added
   four row kinds (task, step, agent, subagent) that did not exist when the
   navigation was written. Whether each of them resolves to a usable
   destination is being checked before close rather than assumed.

-1. ONE RENDERER PROCESS PER WINDOW, ALL INDEPENDENT AND ALL REDUNDANT
   (operator observation, 2026-07-27: "each sesion in tmux will have to
   relaunch the same orchard in each session it has, and each session pane
   will always be idependent, is thatcorrect?"). Correct, with the refinement
   that it is per WINDOW rather than per session, since `sidebar-mount.sh`
   mounts into a window. Every mounted window therefore runs its own renderer
   with its own `inotifywait` watcher, building an identical model of the same
   runtime tree — two live at the time of writing. `link-window` is the
   exception: a linked window carries its pane into several sessions without
   relaunching, being the same window; panes cannot be shared across different
   windows.
   The waste is bounded but real, and grows with the number of open windows.
   The alternative shape — one renderer with thin viewers — is a different
   design and was deliberately NOT built here. NOTE the constraint any such
   change must keep: independent panes must agree on what colour a task is,
   which is why the task colour is derived deterministically from the task's
   identity rather than sampled at render time. Sampling would make the
   lineage encoding meaningless across windows.

0. FEATURE BASE COLOURS ARE ASSIGNED AT CREATION, STORED IN THE REPO AND
   SYNCHRONISED WITH GITHUB (operator, 2026-07-27): "Feature base colours can
   be decided in advance as features get created, kept in repo and
   synchronized with github". This is grade 1 of the three-grade colour model
   becoming DATA rather than derivation. SPLIT deliberately: this branch
   builds only the READ side — the renderer reads a feature's stored base
   colour when present and falls back to deriving one from the project hue
   when absent or unparseable, which is every feature today since nothing
   writes it yet. Assigning at creation, persisting to the repository and
   synchronising with GitHub touches the board and `board_gh.py`, which are
   the gardener's and never a landscaper's to edit, so they are RETURNED
   rather than built. The fallback is permanent, not a stopgap: a feature
   with no assigned colour must always render sensibly.

1. `:session:` routing prefix leaks into filenames. The live tree holds
   `:session:<uuid>.marker` and `:session:<uuid>.<ts>.json`, and inside
   those envelopes `to` reads `:session::session:<uuid>` — the prefix
   applied twice. One session therefore owns two markers and is counted
   twice by anything enumerating the tree. This is a transport addressing
   defect, out of scope here, and it was deliberately not fixed.
2. Features carry no `area`. The marker has an `area` field that is always
   null because nothing in the repository supplies one: zero of 139
   sidecars carry an `area:` key, and the Functionality|Areas table in
   ARCHITECTURE.md is a decisions taxonomy enforced by `board_lint.py`, not
   a per-task attribute. Populating it needs an operator ruling per feature,
   so it was left dormant rather than invented.
3. The marker pruner is undesigned, by operator ruling — retention is until
   restart, and when to prune is a later user-interface concern. Only the
   archive-and-move-back shape ships.
4. Residual dead keys in an in-place-upgraded marker: a marker first written
   by the earlier shape retains top-level `name`/`area` keys after the merge
   strips `sessions` and the rejected task entries. They are unread and
   harmless, and the file self-clears with the tmpfs, so this was left
   alone rather than chased.
5. `_fold_sessions`'s latest-snapshot-wins fold is sensitive to `iterdir()`
   order when two events of one session tie on mtime. Pre-existing. Seen
   INDEPENDENTLY BY TWO agents during this feature — once while building the
   model and once while writing the static fixtures, the second of which had
   to work around it in test scaffolding to get a deterministic result.
   Raised from "not worth chasing" to a real follow-up on that basis: two
   independent sightings in one feature is a defect asserting itself, not a
   curiosity.
7. THE ENFORCEMENT HOOK FAILS OPEN and nothing detects it. If
   `hooks/courier-only-transport.sh` goes missing, loses its execute bit, or
   `jq` is unavailable, the documented behaviour is that a non-blocking hook
   error lets the call proceed — so the single-caller rule silently ceases
   to exist with no signal. Worth a companion check that verifies the hook
   is live, in the spirit of `courier-init.sh`'s "detection, not a capability
   gate" note. NOT built here; it is a different problem from the one the
   operator scoped.
8. The general Bash/Python permission posture. The operator observed that
   both "should be an ask in general anyway or an outright deny". Evidence
   gathered while scoping it: permission RULE LISTS are session-wide, so a
   deny cannot be relaxed for the courier — `permissions.md` is explicit
   that hook decisions do not bypass permission rules and that a tool denied
   at any level cannot be allowed at another. Per-agent frontmatter DOES
   support `tools`, `disallowedTools`, `permissionMode` and `hooks`, so
   posture can be set per role; only the allow/ask/deny lists cannot. The
   documented recipe for this shape is the inverse of a deny list: allow
   broadly and let a pre-tool hook block specifics, which is what this
   branch built. A wider posture decision remains open and is the operator's.
6. THE SIDEBAR NEVER RE-MOUNTS ITSELF. Operator expectation, raised in
   session: "a CTRL+C seem yo have closed the sidebar. Im expecting that any
   activity would reopen it righy?" It does not. `tools/sidebar-mount.sh` is
   invoked at LAUNCH ONLY — `agents/gardener.md:26` mounts it into the
   gardener's window at boot, `agents/gardener.md:178` mounts it into each
   landscaper's window at spawn, and `ARCHITECTURE.md:177` describes it as
   "mounted at launch … strictly best-effort". No hook in `settings.json`
   calls it. So a pane closed for any reason — a stray interrupt, a crash,
   the renderer exiting — stays closed until the next gardener boot; a
   landscaper spawn only mounts into its OWN new window and never repairs an
   existing one. The script is already idempotent and no-ops when a pane is
   present, so it is built for repeated calling and simply has nothing
   calling it. Fix shape: invoke it from a hook (UserPromptSubmit for
   self-healing on any activity, or SessionStart for a narrower repair).
   RETURNED rather than built by operator ruling, because hooks live in the
   shared `settings.json` and an edit there reaches every consuming repo on
   its next sync — a decision of its own, not a rider on this feature.

## Changelog entry

Staged verbatim for the gardener to place at ingest (Decision-034).
Rolling — folded from each sower's `ingest_increment` as it returned.

### 🐛 Bug fixes

- 🐛 The fleet sidebar no longer freezes silently when its filesystem
  watcher dies. The watch loop is now self-supervising: it reaps the dying
  child, restarts it with a short backoff against crash loops, and falls
  back to polling while the projects tree is absent — so a compaction pass
  rewriting that tree can no longer leave a pane showing a stale, empty
  frame indefinitely.

- 🐛 Every working session now earns a sidebar row, not only those
  identifying as landscapers. An architect or any other role working
  alongside the gardener previously rendered nothing at all, leaving a
  project header above an empty pane; the gardener still supplies the
  header, while mailboxes that never carry an identity stay absent.

- 🐛 A session's row no longer disappears on a timer. The model takes its
  structure from the durable per-feature markers and layers live events on
  top, so a row survives the archiver removing its two-hour-old events and
  persists until the runtime tree itself clears.

- 🐛 The per-repository header colour renders as its real hue again. The
  256-colour approximation was letting the grayscale ramp win for any dark,
  desaturated colour, turning the intended purple into gray, and the header
  was additionally forced into reverse video merely because the selection
  defaulted to the first row on startup. A colour with genuine hue now
  always resolves into the colour cube, a terminal advertising truecolor is
  driven through a direct-colour terminfo so exact values pass through
  untouched, and the reverse-video highlight appears only once the operator
  has actually navigated.

- 🐛 A completed item now reads as completed. Terminal rows carry their own
  tick or cross rather than the generic presence dot, and render in green or
  red instead of an accidental third colour — the status and identity
  colours were being combined into an arbitrary one, because a colour pair
  is a bitfield and the two cannot be merged.

### ✨ New features

- ✨ The orchard transport writes a durable per-feature marker alongside the
  existing per-session heartbeat, recording the task a feature maps to: its
  name, its area and its state, merged in place and never truncated, so a
  task that has completed survives without any activity to keep it alive.
  The marker holds nothing agent-shaped. Agents are delegations sent to
  complete a task and there may be several, usually in sequence; they and
  the subagents they spin up appear while working and stop displaying when
  they finish, along with their name, model and activity. The task is the
  one thing that does not disappear, so a task whose agents have all
  stopped remains as a single row carrying its final state.

- 🔒 Message filenames are validated at a single writer. Two write paths
  previously built their own destinations, and both produced names the
  transport's design forbids — one lost its file extension, and a routing
  prefix applied twice leaked a colon into a marker name, leaving one
  session owning two markers and counted twice. Names outside the permitted
  shapes are now rejected rather than repaired.

- 🔒 The courier is the only caller of the message transport, enforced by
  the harness rather than agreed by convention. A pre-tool hook refuses the
  posting commands for any agent that is not the courier, using an identity
  the harness supplies rather than one the agent can set. The rule fails
  closed, so a role added later is denied by construction. Its limits are
  stated in the file: it stops accidental and casual bypass, not a
  determined one.

- 🐛 A task whose telemetry has been archived now still reads as working
  rather than turning gray while the work is genuinely running. Staleness is
  unchanged and still checked first, so a task nothing has written to within
  the liveness window continues to read as not-heard-from.

### ROUND 2 — the display gets its real shape

- ✨ Each pipeline-role charter now carries a `step:` key in its frontmatter,
  mapping the role to its stage — ideation, scoping, designing, building or
  releasing — so the sidebar can work out which step a task is on from the
  role of whoever is working it, with nothing about steps travelling on the
  message bus. The sidecar courier role and the three cloud agents carry no
  step at all: an absent step renders as no step rather than a default,
  because silently inventing a placement is the defect class this work
  exists to remove.

- ✨ Every message travelling between agents now records which task is being
  worked, not just which feature. A feature used to mean a single task worked
  by a single session, so naming the feature was enough; a feature now spans
  several tasks and more than one is commonly in progress at once, so the
  feature alone no longer says what anyone is doing. Which stage of the
  pipeline that task has reached is deliberately not sent, being a question
  about how work is displayed rather than about what happened.

- 🐛 A session that is resumed no longer forgets what it is. Resuming carries
  over the session's identifier but not the role it was started with, so every
  resumed agent became anonymous and the helpers it delegated to were
  attributed to nobody and never appeared. The role is now remembered against
  the session's identifier the first time it is known, and a session may also
  declare its own, which it can always do because it has just read its own
  charter. A declared role never displaces one the system supplied, and a
  remembered one is never overwritten — least of all by an absence, which is
  exactly what a resume looks like.

- ✅ The message transport's contract is now pinned by tests reading bytes
  captured from the running system, alongside the tests that exercise the code
  against itself. A test whose input is produced by the same code that reads it
  can only show the two agree, and this project has twice shipped a green suite
  over behaviour that was visibly broken. The retired message shape was captured
  before it was replaced and survives as the only record of it.

- 🐛 The sidebar pane mounted into an agent's window now runs the renderer
  belonging to the checkout that asked for it, falling back unchanged to the
  shared copy for any repository that carries no renderer of its own. It
  previously always ran the shared copy, which tracks the main branch, so a
  branch changing the sidebar could not be seen working in the window of the
  session building it — a full round of review was spent judging code that
  was never on screen.

- 💄 Depth in the sidebar is now shown by background colour rather than by
  indentation, which had been competing with the content for the same cells:
  at the width the pane actually runs, an agent's line has twenty-four usable
  columns and its status and role together are exactly twenty-four. The
  project header is a gradient, a feature is a band painted the whole line, a
  task hangs a coloured bar off it, and each of the five steps takes a full
  centred line of its own. An open step and everything inside it share a
  dimmer shade, so the work being done reads as one block with findable edges.
  Colour also carries lineage: a task's colour comes from within its feature's
  range and its content's from the task's, so which feature a task belongs to
  is legible without reading a word. Task colours are unordered by design —
  they say identity, never sequence or priority — and derive from the task
  itself, so they look arbitrary while staying identical across a redraw, a
  restart, or two panes showing the same tree. Every foreground and background
  pairing is checked against the published contrast ratios, and the foreground
  is what moves until it passes; the background never gives way, being the
  part that carries meaning. A feature may pin its own base colour, and one
  that does not simply derives from its project's.

- 🐛 Three things the display was losing are lost no longer: all five steps
  keep their own line instead of being abbreviated away under narrow width, a
  status keeps the role that produced it by shortening the status text first,
  and a task says its own name rather than being blanked for resembling its
  feature's — an empty-looking row being the very appearance this work exists
  to remove.

- 🐛 A genuine terminal rendering defect was found and fixed on the way:
  combining dim text with a custom background could corrupt the background of
  the row drawn immediately afterwards, so dimming is now done by blending the
  colour itself rather than by asking the terminal to dim it.

## Readme delta

Staged for the gardener to apply via the `readme-sync` skill at ingest
(Decision-034). README.md currently ends its transport section with "The
fleet sidebar (`tools/sidebar.py`) is the one renderer, reading the topic
tree directly." That is now incomplete in a way a reader would notice, since
telemetry archives after 120 minutes and the sidebar visibly keeps drawing
work whose telemetry is gone. Replace that sentence with:

> The fleet sidebar (`tools/sidebar.py`) is the one renderer, and it draws a
> tree: a project holds features, a feature holds the tasks it spans, a task
> passes through five steps, and the agents working a step appear inside it
> with the subagents they spawn. It reads the topic tree for what is
> happening now and a per-feature marker for what remains when nothing is —
> telemetry archives after 120 minutes, but a task stays on screen until the
> runtime tree itself clears. Agents and subagents are live only and
> disappear when they finish; the task is the one that does not. Nothing else
> is ever hidden: a task folds away once all of it is complete, a feature
> once all its tasks are, and a new task reopens a finished feature with its
> completed siblings alongside it.
>
> Which step a task is on is worked out from the role of whoever is working
> it, using the `step:` field in that agent's own charter, so nothing about
> pipeline stages travels on the message bus. Depth is shown by background
> colour rather than indentation, and colour is inherited from project to
> feature to task, so which feature a task belongs to can be seen without
> reading a word.
>
> The pane runs the renderer belonging to the checkout that mounted it,
> falling back to the shared copy for a repository that has none of its own —
> so a branch changing the sidebar can be seen working in the window of the
> session building it. Run it with `--once` to paint a single frame and exit,
> or `--dump` for a plain-text view of the model.

Rationale for surfacing `--once`/`--dump`: `--once` is a new user-facing
flag, and the pair is the only way to inspect the sidebar without a live
pane, which is what anyone debugging it reaches for first.

## Architecture determination

UPDATED on-branch (ARCHITECTURE.md, the message-courier section). Two
triggers fired, both from `AGENTS.shared.md`:
- "how modules or components connect (data flow, wiring)" — the transport
  now writes a durable task marker that the renderer reads, a new connection
  between the two that did not exist; the file previously described the
  transport as "flat message files plus a per-session marker", which no
  longer covers what is on disk.
- "a cross-cutting pattern" — the five-level display hierarchy
  (project → feature → task → agents → subagents) governs what any renderer
  may treat as durable, and was nowhere in the document.
Both are now recorded there.

## Migration determination

NOT required, and the reason is evidenced rather than assumed. The marker
format change is strictly ADDITIVE: nothing in the repository reads the
existing `<sid>.marker`'s content — `sidebar.py::_fold_sessions` skips it,
`orchard_compact.py` globs `*.json` only, and no hook or the question broker
references it. The old marker keeps its transport role untouched, feature
markers appear as sessions post, and the runtime tree is `$XDG_RUNTIME_DIR`
tmpfs that clears at logout. A `migrations/` entry would therefore contain
no state-guarded step. Per AGENTS.files.md §Migrations every action must be
guarded by observable state and actually convert something; there is nothing
to convert.

## Operator requests

Ledger of everything the operator asked for in-session, as received.

1. "its code" — the defect is code, not environment. IMPLEMENTED (all four
   root causes are code; no environment change is required).
2. Retention: a completed task stays for the lifetime of the session, until
   restart; pruning undecided, a UI concern, not to be designed now.
   IMPLEMENTED as scope (marker persistence) + DEFERRED as stated (no
   pruner built).
3. The marker becomes a per-feature cached tree node so late data lands in
   the right place and completed sibling tasks survive; pruning archives
   rather than deletes, and moving the file back revives the node.
   IMPLEMENTED (build step 1/2).
4. "will you not need the feature as part of the filename?" — yes; filename
   keyed on feature, area moved inside the contents. IMPLEMENTED.
5. "Can we fix why ncurses does the chroma thing anyway?" — investigated:
   the approximation was ours, not ncurses'. Fixed at the root via a
   direct-colour terminfo. IMPLEMENTED (build step 4).
6. Corrected the display hierarchy to five levels and ruled that only the
   task persists, agents and subagents being ephemeral. IMPLEMENTED (steps
   8a, 8b, 9) — this reversed an earlier part of the build.
7. "im not doing any of this you an just reload it" — reload the sidebar
   rather than hand the operator steps. DONE, but badly: the reload sent an
   interrupt to a mis-resolved tmux target, which closed both sidebar panes
   and submitted a stray shell command as a prompt into the gardener's
   session. Panes were restored on the branch build and the incident was
   reported at once. Recorded because the operator should not have to
   discover it.
 8. "Im expecting that any activity would reopen it righy?" — it does not;
   the mount is launch-only. RETURNED as follow-up 6 by operator ruling, NOT
   built here.
9. "the tree shuld have a timstamp as per previous decisiosn" and "filename
   valdation should be part o tis job" — IMPLEMENTED: one writer, one
   validator, and both malformed shapes fixed at source.
10. "There are areas of functionality on github and on issues, prblem to be
   fixed hilistically" — corrects an earlier finding of mine that no area
   existed anywhere; areas live on GitHub and on issues. NOT built: returned
   as follow-up 2, to be solved across those sources rather than by
   inventing a per-sidecar field.
11. "we'll leave the pruner behind for a wile" — DEFERRED, unchanged.
12. "the posting of messages straight through the script must be forbidden
   rather than propose-like done… find a way an agent CANNOT call the script
   without having called the subagent" — IMPLEMENTED as far as the harness
   permits, with the ceiling stated plainly in the hook and in Confidence
   above. It is not absolute and is not described as such.
13. "RULE OF TESTING: never test code where the caller and the callee are the
   same code without another test with static daata vaidated at feature
   riting time" — IMPLEMENTED and recorded as a decision. It immediately
   found a real defect that 404 round-trip tests had passed over.
14. "you absolutely can change thepermission per agent" — correct, and my
   claim otherwise was wrong. Verified against the documentation: per-agent
   `tools`, `disallowedTools`, `permissionMode` and `hooks` are all
   supported; only the allow/ask/deny rule lists are session-wide.

Round 2 (2026-07-26), after the failed live eyeball:

15. Revert the staged Result to in-progress and diagnose why LIVE activity
   does not render. IMPLEMENTED. Result reverted; cause found and it was not
   a live-half defect — the pane was running main's renderer, not the
   branch's.
16. "Cosmetic changes once it works" — function first, with the rows-AND-hue
   bar of ruling 1 still gating the close. HONOURED as ordering; no cosmetic
   work was done in this round.
17. "Missing difference between feature and task" — IMPLEMENTED as scope:
   the renderer gains the task level it never had.
18. The corrected hierarchy, given at length: a feature spans many tasks as
   a tree; five steps run within a task; agents with identity sit on steps
   and a step may hold more than one; subagents share their parent's session
   id and surface only as scheduled / doing / done; nothing is ever hidden
   except a completed task and a wholly-completed feature; a feature reopens
   when a new task arrives. IMPLEMENTED as the whole of the round-2 scope.
19. "the real way to do it is to make sure messaging does provide which
   feature slash task is worked on ... and then the static mapping can happen
   on the [client] side" — IMPLEMENTED: identity gains `task`, the step stays
   UI-derived from the role. He also called an explicit phase on the wire "a
   second step"; DEFERRED on his own framing.
20. "any subagent that wants to post updates should do it through its
   spawner. Otherwise it should probably be an agent" — RECORDED as a
   decision, including the corollary that the reporting shape is what decides
   whether a unit of work is a subagent or an agent.
30. LIVE-PANE FEEDBACK, 2026-07-27, on the rebuilt renderer: "two notes: the
   brighter side block is correct *if* it is the background of the preceing
   ine asit denotes delegation. and Buuilding should have the same bckroun as
   the other section titles, and the entries witin a section should be lighter
   not go back to the normal background, and thespinner on the task doesn't
   spin, i'll get the color coding (inside the step shuld be lighter or the
   color implicitness of inheritnce breaks) for antoher time, and I think the
   checkmarx or red markx next to the step shoujld be right aligned or the
   first character on the line, but that's justaesthetics".
   IMPORTANT REVERSAL: contents inside an open step must be LIGHTER than their
   section title, not darker. This SUPERSEDES his earlier "background colour is
   dimmer in a stage when its open" — the open region is still one contiguous
   findable block, but it is distinguished by being lighter. His stated
   principle governs any future change here: a child must read as DERIVED from
   its parent, and reverting to the base background asserts the opposite,
   breaking the implicitness of colour inheritance.
   Also: every step title shares ONE background whether active or not — being
   active is said by the mark, the sweep and what appears beneath, never by
   recolouring the title; the brighter side block takes the PRECEDING line's
   background because that is what marks the line as a delegation from it; the
   task spinner is FROZEN, which is a real defect and not styling; and the
   step's tick or cross should be right-aligned or first on the line, which he
   marked as aesthetics. The wider colour-coding conversation he DEFERRED
   explicitly to another time.

32. NAVIGATION IS COMPLETELY BROKEN — and it is the ORIGINAL requirement.
   Operator: "well yes the FIRST thing i asked is a list i can navigate with
   the keyboard to land on the right window whatever the session or window".
   Measured against the live tmux server, BOTH targets resolve to nothing:
     'orchids'                       -> None
     'orchids/Sidebar empty rows: …' -> None
   Two independent faults. The producer builds `repo` + "/" + `feature` while
   windows are actually named `repo` + " ▸ " + `feature` (space, U+25B8,
   space). And the gardener's window is named "claude", not after its repo,
   so a repo-level target can never match by name at all.
   NOT CAUSED BY THIS ROUND'S REBUILD: `tools/sidebar_nav.py` was untouched
   throughout, and the four new row kinds correctly inherit the feature's
   target, which is right because the tmux topology is repo-window and
   feature-window. The rebuild merely gave me a reason to look.
   WHY IT ROTTED SILENTLY, which is the more important finding: the
   navigation tests mock the tmux layer entirely and assert against invented
   window names — some of which use "▸" while the producer uses "/". They
   passed continuously while the feature had never once worked. This is the
   static-fixture rule (Decision, this feature) asserting itself a third
   time: a test that never touches the real thing measures agreement, not
   correctness.
   FIX IN FLIGHT, and deliberately not a separator patch: resolution moves to
   matching a window by its pane's WORKING DIRECTORY — real state that
   survives renames and formatting conventions — with tolerant name matching
   kept only as a fallback, and a visible message on failure so a silent
   no-op can never hide it again.

31. VOCABULARY CORRECTION, and it invalidates a reading applied throughout
   this feature: "dimmer fr me meant lighter / more ubdued /less of the
   colour or a color that mathes on the color wheel the container". Every
   use of "dimmer" in this feature's specification meant SUBDUED — lighter,
   less saturated, or a harmonising neighbour on the colour wheel — and never
   darker. The darker reading was mine; English carries both senses.
   This reaches further than the open step: the FEATURE ROW was specified as
   a "full length dimmer background colour" and must be subdued rather than
   darkened too. The general rule, which settles future cases without asking:
   a contained thing is a SUBDUED version of its container so that it reads
   as belonging to it — darkening breaks the inheritance because it reads as
   a different band rather than a quieter one, while lightening,
   desaturating, or shifting to an adjacent hue all preserve it.

27. THE ACCORDION CORRECTION, and it was my error not his: "in an accordion,
   collapse keeps the line, it doesn't go to the previous one". I had told
   the sower to put all five steps on ONE line and abbreviate them until they
   fitted 32 columns. His earlier ruling already said otherwise — "a finished
   step folds to a plain line as the next opens, keeping its place among the
   five" — and I mis-read "keeping its place" as keeping a slot in a shared
   line rather than keeping its own line. Corrected mid-flight. Five step
   lines, always, one per step; a collapsed step keeps its line and shows no
   contents; the active one expands. This also dissolves the truncation
   defect rather than solving it: with a line each there is nothing to
   abbreviate away.

28. DEPTH IS BACKGROUND COLOUR, NOT INDENT (operator, final layout model):
   "Instead of focusing on indent, lets focus on background color: orchids:
   gradient from A to B. MessageBus would be baground B alll the way (paint
   wole avail line). Task: ue vertical br left with BG B abd FG Ct where Ct is
   a backgroud colour for that task. We are back to blocks so we ca center
   aligh again, from cell 1 sowe takeeachof the 5 steps and make them a full
   ligne centred, bacground C. Inside each the logic above is the correct one,
   i woulld put the moving gradient on the current stage."
   He offered left-aligned steps at the cost of an extra indent cell and asked
   for an opinion; the answer given was CENTRED, on the grounds that the
   full-width band already supplies the edge, and that at 32 columns the saved
   cell is real — the agent line has 24 usable columns and the quote plus role
   is exactly 24. Indentation therefore stops being the structure, and the
   `│` continuation characters retire with it.
   MINE, NOT HIS, and overrulable on sight: the agent and subagent lines inside
   a step stay on background C so the section reads as one block, and Ct varies
   per task so two open tasks are told apart by bar colour alone.
   Operator process note, taken as a standing instruction: "this is going to go
   back and forth so either we drop this discussion or we very accurately
   agree" — the drip-feed of one refinement per turn was my failure. The
   correction is to state a complete specification once and build it, not to
   ask again.

29. COLOUR IS DERIVED IN THREE GRADES, AND CONTRAST IS COMPUTED (operator):
   "calculate contrast levels guidelines are knwn orchid colours but others
   are permitted. Each task get its own colour as long as it is in the colour
   range chosen for the featrure. so feature color base -> task color base ->
   content color base, that's three grades". Plus: "background oclour is
   dimmer in a stage when its open, visually it'seasy to find the bounding
   box".
   Colour therefore encodes LINEAGE rather than decoration — a task's colour
   is allocated from its feature's range, and the content beneath it from the
   task's, so which feature a task belongs to and which task a block of
   content belongs to are both readable without a word. The orchid palette is
   the starting point but is explicitly not a closed set.
   Contrast is CALCULATED against the known guidelines at runtime from the
   resolved colours — not hardcoded pairs — because the feature hue varies per
   project. Where a derived pair fails, the foreground moves; the derived
   background does not, since it is carrying structure. Sibling tasks need a
   minimum perceptual separation as well as containment in the range, so how
   allocation behaves when a feature has more tasks than the range can
   separate is an open implementation question put to the sower.

26. NOT YET DONE at the time of writing, found by my own look at the live
   pane after the renderer landed at 49724aa — recorded here so none of it
   can be quietly lost. The six-level structure works (one feature row, one
   task row, one accordion line, both sessions merged as agents, subagents
   attached), but: the accordion TRUNCATES to two of five steps, which is
   omission and breaks the feature's own spine; the agent quote has lost its
   attribution, rendering `“committing”` with no role at all; the vestigial
   `0%` still sits on the feature row after progress moved to the task's
   circle; feature and task STILL print the same text, which is the
   operator's original complaint unresolved; and the gradient header, the
   full-width dimmer band and the KITT sweep are unbuilt. Dispatched as step
   3b. The band is treated as LOAD-BEARING rather than decorative, since it
   is what makes a feature visibly not a task — the visual item and the
   original complaint are one fix.

25. LAYOUT, given in full while waiting on the renderer, with the operator
   explicitly lifting his own "cosmetics later" ordering for it so the work
   lands in the same pass rather than costing a second round: "Orchids is the
   gradient centered, feature left aligned below, full length dimmer
   backgound colour, next line accordion for the feve steps, centered small
   caps, the actuve ones thata are expanded get the kit animation, the oher
   ones are collapsd. Within an active steps (ideation, scoping etc) goes the
   agent, status, model we agreed (italics for the quote?) and they get
   (finally) an indent, whote, net line the agent, next lines with the bubbles
   as correctly fisplayed the pending ones. Steps small caps always" — plus
   "very compact form" as an overriding constraint, and "accordion is under
   the task of course" settling the one placement I had flagged as my own
   reading. Italics on the quote: he asked, I answered yes. IMPLEMENTED as
   scope in the renderer step.
   The identity line becomes a book-style epigraph — italic quote, then the
   role and model as an attribution beneath — degrading version, then model,
   then the attribution rejoining the quote line, then the role, with the
   quote itself never dropping. Compactness wins at every choice point, but
   nothing is ever OMITTED to save a line: not a pending subagent bubble, not
   a step, not a task. Collapse and abbreviate, never omit.

24. "you cannot call yourself for a resume as you already know you come from
   resume and you know who you are" — CORRECT, and a better primary
   mechanism than the process-tree walk I had specified. A resumed session
   knows its own role because it has just loaded its own charter; the role is
   unavailable to the HARNESS, not to the session. IMPLEMENTED as an explicit
   self-declaration argument to `courier.py init`, with precedence:
   harness-supplied wins, self-declaration fills a gap only, then the
   persisted record, then the launching command line as a last resort. A
   self-declared role never overwrites a harness-supplied one, which keeps
   the existing intent that identity comes from something the agent cannot
   set. Materially better than the original: it repairs the CURRENTLY RUNNING
   gardener, which persistence-at-first-launch alone could not.

23. "is that because its force launched at startup rather than calling it
   through /gardener?" — RIGHT INSTINCT, adjacent cause. Established by
   direct observation: the gardener process is `claude --resume
   1e6b83cc-...`, parent `-bash`, with NO `--agent` flag on the command line
   and none of CLAUDE_CODE_AGENT, CLAUDE_AGENT, ORCHID_PARENT_SESSION,
   ORCHID_PARENT_PROJECT, CLAUDE_CODE_SESSION_ID or AI_AGENT in its
   environment. A spawned landscaper by contrast runs `claude --agent
   landscaper --name ...` and does get CLAUDE_CODE_AGENT. So the role is lost
   not by being force-launched but by being RESUMED: a resume drops the flag
   the role came from, and nothing on the process can name it afterwards.
   This is fleet-wide — any resumed agent goes anonymous on the bus, not only
   the gardener. IMPLEMENTED as step 1b, via the SessionStart hook that
   already runs `courier.py init`, so no shared settings.json edit is needed.
   Honest limit: it cannot repair the currently-running gardener session,
   which never had a record written; it takes effect from a session's next
   launch. The renderer failing open covers the display meanwhile.

22. "steps flash from time to time (or i saw two) but no content within
   them. First two lines hav the same text not sure which one is which" —
   observed live on the pre-rebuild renderer. Both confirmed by capture and
   both are in scope for the renderer step: the two identical lines are ONE
   feature minted twice, once per session (a dead predecessor and the live
   one), and the step block flashes because it is drawn under only whichever
   row is currently working, so it appears and disappears as staleness flips
   between them — while every dot is empty because no step carries the
   agents working it. Relayed to the sower in flight as acceptance criteria.
   IMPLEMENTED pending that step's return and the live re-check.

21. Two role-to-step assignments are MINE, not his, and are flagged for his
   review: `bloomer -> scoping` and `sower -> building`. He named only
   gardener/ideation, landscaper/building, groundskeeper/releasing and
   designing as the renamed groomer. OPEN — cheap to correct, being one
   frontmatter line each.

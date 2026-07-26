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

## Readme delta

(pending — determined at close)

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

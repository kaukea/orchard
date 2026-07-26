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

## Result

Result: done (pending the operator's live eyeball, which is the agreed
acceptance gate and cannot be self-approved)

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
   the same economy.

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

## Readme delta

Staged for the gardener to apply via the `readme-sync` skill at ingest
(Decision-034). README.md currently ends its transport section with "The
fleet sidebar (`tools/sidebar.py`) is the one renderer, reading the topic
tree directly." That is now incomplete in a way a reader would notice, since
telemetry archives after 120 minutes and the sidebar visibly keeps drawing
work whose telemetry is gone. Replace that sentence with:

> The fleet sidebar (`tools/sidebar.py`) is the one renderer. It reads the
> topic tree for what is happening now, and a per-feature task marker for
> what remains when nothing is: telemetry archives after 120 minutes, but a
> task stays on screen until the runtime tree itself clears. Agents and the
> subagents they spin up appear while they work and disappear when they
> finish — the task is the one that does not. Run it with `--once` to paint
> a single frame and exit, or `--dump` for a plain-text view of the model.

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

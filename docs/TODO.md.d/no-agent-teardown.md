- created: 2026-07-29
- created_by: gardener
- created_during: main
- readiness: blocked-on-answers

# There is no landscaper teardown at all: an agent never touches a UI element

## Proposal

**Operator ruling, 2026-07-29, verbatim: "there should not be a landscaper teardown at
all".**

An agent never closes its own window, never resolves another agent's window, and is
never handed a handle for one. `tools/landscaper-teardown.sh` is not a script to fix or
repoint — it goes, with everything that exists only to feed it.

The design is Decision-114, already ruled: an agent states only LOGICAL placement from a
closed vocabulary of four — `none · sibling · child · background` — and a plugin subagent
inside the launcher's context realises it, owns the UI element, and closes that element
once `lifecycle:stopped` has happened. Creation and destruction sit in one component,
driven by the two lifecycle events rather than by anyone remembering to call a teardown.

Scope as it stands — the operator's to set, not derived:

- Delete `tools/landscaper-teardown.sh` and its references in the charters.
- Delete `.return-window`.
- Drop `@gardener_id` — it exists only as a focus-return handle for the teardown.
- The placement component closes the UI element on `stopped`, mirroring creation on
  `starting`.
- Charters request placement BY WORD and stop describing window mechanics.

## Current state (observed live, 2026-07-29)

`tools/landscaper-teardown.sh:46` hard-fails with `die "no gardener window found
(@gardener_id unset)"` unless a tmux window carries a non-empty `@gardener_id`. Nothing
stamps it. Window `main:1` carries none; a landscaper in `main:2` could not complete its
teardown, leaving its window, worktree and branch behind — the groundskeeper correctly
refusing to force-remove a worktree a live landscaper still holds.

Every close stalls this way today.

## Findings (this round — read-only, current charters)

GROOMER'S READING, not ruled, but drawn directly from the three charters read this round
(`agents/landscaper.md`, `agents/supervisor.md`, `agents/groundskeeper.md`):

- **`landscaper.md:179`** still has the landscaper call
  `.claude/tools/landscaper-teardown.sh <id>` on itself as its own last act — an agent
  closing its own window, exactly what "there should not be a landscaper teardown at all"
  rules out. This line goes.
- **A different, newer mechanism already exists in the other two charters** and is NOT the
  same design as this task's plugin-subagent: `supervisor.md` (the close section) has the
  groundskeeper "TRIGGER the tmux-topology window-release primitive (it lives in the
  tmux/window plane and EXECUTES the release; you trigger it, it executes it)", and
  `groundskeeper.md` step 9 does the same — "TRIGGER the tmux-topology window-release
  primitive" — gated on the landscaper's `lifecycle:stopped`, but observed by **polling**
  ("poll the courier state files or the window's absence; up to ~3 minutes").
  This is closer than `landscaper-teardown.sh` (no self-close, no window mechanics named in
  the charter prose) but it is still a **call-and-trigger**, not a **listen-for-the-event**
  — Decision-129's "never called back and told to clean up" and this session's "the
  supervisor should supervise and listen" / "not poll marker mtimes" both land squarely on
  this polling wait. It has to change from "groundskeeper triggers, then polls for
  `stopped`" to "the placement component listens for `lifecycle:stopped` itself and closes
  on it" — the groundskeeper stops owning that wait at all.
- **`.return-window` is already treated as retired in `supervisor.md`**: *"`.return-window`
  retires — the parent (you, then the gardener) knows its own pane."* That text already
  assumes this task's own scope item (delete `.return-window`). No sibling task claims it;
  closing this Question below.
- **`@gardener_id`** is referenced only inside `landscaper-teardown.sh` itself (as the
  focus-return handle) — no charter prose depends on it once that script is deleted. Same
  conclusion: this task's to drop, not a sibling's.
- **`gardener.md`** carries no live teardown call to remove — its one mention of "teardown"
  (`agents/gardener.md:168`) is prose reasoning about creator-owns-destroys, not a
  mechanism; nothing to delete there.

## Questions

1. **Which component is "the plugin subagent inside the launcher's context" concretely —
   does it get built in this task, or does the removal land first and the listener follow
   as a dependency?** GROOMER'S READING: the courier already demonstrates the pattern
   Decision-129 wants ("the courier closes its own Monitor because the courier armed it") —
   a component that creates a resource arms a listener on the SAME event stream and acts on
   it itself, in-process, no one calling it back. No existing component in this tree does
   that for a tmux window today; `supervisor.md`/`groundskeeper.md`'s "trigger the
   window-release primitive" is the closest analogue but is a call, not a listen, and its
   wait is a poll, not an event wake (see Findings). Recommendation: this task both deletes
   `landscaper-teardown.sh`/`.return-window`/`@gardener_id` AND builds the listener,
   because leaving the delete for this task and the listener for later reopens exactly the
   stall this sidecar documents under "Current state" — there would be nothing to close the
   window at all in the interval. Needs the operator's call before scope is fixed.
2. **What happens in the plain-ssh case** — no second surface exists, so `sibling`/`child`
   degrade. GROOMER'S READING only, not settled by anything read this round: silent
   degrade is invisible to the operator watching one pane (the feature's own stated
   purpose), so the launcher probably ought to learn it got less than it asked for and say
   so — but this is a design call (Decision-114 is silent on it) and stays a genuine open
   Question, not inferred into scope.
3. **Does the groundskeeper's close sequence still gate worktree removal on the landscaper
   being "gone", and if so, on what signal now that polling is out?** Not asked by the
   original sidecar; raised because Findings above show the current gate is
   poll-then-wait. GROOMER'S READING: likely the same `lifecycle:stopped` event the new
   listener component consumes, just also read by the groundskeeper for the worktree-removal
   gate — but whether the groundskeeper itself becomes an event-listener too, or continues
   to synchronously wait on something, is this task's design surface and not preemptively
   answered here.

## Testing

To agree at scope. Expected shape: a landscaper reaching `lifecycle:stopped` has its
window closed by the placement component, with no agent having called a teardown —
observed on the operator's screen, and `grep -r landscaper-teardown` / `grep -r
return-window` / `grep -r gardener_id` returning nothing outside history. End to end per
the parent feature's Testing (Decision from `observability.md`): the operator watches a
close run to completion driven by the `stopped` event alone.

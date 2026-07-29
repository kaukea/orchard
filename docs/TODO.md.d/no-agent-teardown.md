- created: 2026-07-29
- created_by: gardener
- created_during: main

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

## Questions

- **Does the placement component get built in this task, or is the removal its own step?**
  If the removal lands alone, the close needs something to depend on in the interval.
- **Which component is "the plugin subagent" concretely**, and does one exist to extend?
- **What happens in the plain-ssh case**, where no second surface can be offered and
  `sibling`/`child` degrade — is a degraded placement silent, or does the launcher learn
  it got less than it asked for?

## Testing

To agree at scope. Expected shape: a landscaper reaching `lifecycle:stopped` has its
window closed by the placement component, with no agent having called a teardown —
observed on the operator's screen, and `grep -r landscaper-teardown` returning nothing
outside history.

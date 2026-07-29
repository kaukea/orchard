- created: 2026-07-29
- created_by: gardener
- created_during: main

# There is no landscaper teardown at all: an agent never touches a UI element

## Proposal

**Operator ruling, 2026-07-29, verbatim: "there should not be a landscaper teardown at
all".**

This kills the self-teardown model outright. `tools/landscaper-teardown.sh` is not a
script to fix, repoint or keep working — it is a script to delete, along with everything
that exists only to feed it. An agent never closes its own window, never resolves another
agent's window, and is never handed a handle for one.

This is Decision-114 being landed, not a new design. That decision already ruled that an
agent states only LOGICAL placement from a closed vocabulary of four — `none · sibling ·
child · background` — and that a plugin subagent inside the launcher's context realises
it, owns the UI element, and **closes that element itself once `lifecycle:stopped` has
happened.** Creation and destruction sit in one component, driven by the two lifecycle
events rather than by anyone remembering to call a teardown. Symmetric by construction.

Scope:

- **Delete `tools/landscaper-teardown.sh`** and every reference to it in the charters.
- **Delete `.return-window`**, which exists only to serve it.
- **Drop `@gardener_id` as a requirement.** It was invented as a focus-return handle for
  the teardown script; with no teardown there is nothing to return focus from, and the
  fleet does not need the tag at all. (Do NOT restore the stamp — see Findings; an
  earlier draft of this task proposed exactly that and was wrong.)
- **The placement component closes the UI element on `stopped`**, as the mirror of
  creating it on `starting`.
- Charters stop describing window mechanics and request placement BY WORD.

**Out of scope:** building the plugin/placement component itself if that is larger than
this removal — but the removal must not leave the close depending on a script that no
longer exists. The two halves may be sequenced, not skipped.

## Findings

### The current failure this replaces

`tools/landscaper-teardown.sh:46` hard-fails with `die "no gardener window found
(@gardener_id unset)"` unless some tmux window carries a non-empty `@gardener_id`.
Nothing on `main` stamps it. Observed live 2026-07-29: window `main:1` (the gardener's
own) carries no `@gardener_id`, and `main:2` held a landscaper that could not complete
its own teardown — leaving its window, worktree and branch behind, with the groundskeeper
correctly refusing to force-remove a worktree a live landscaper still holds.

Every close stalls this way. The ruling above is why the fix is removal rather than
repair: the stall is a symptom of an agent being made responsible for a UI element in the
first place.

### The stamp was landed and then reverted — evidence retained for the audit, not for restoration

`git log -S'@gardener_id "$CLAUDE_CODE_SESSION_ID"' -- agents/gardener.md` on main:

    dd9586a  🎯 close-family-fakes: transport, close dispatch, four-fakes verdicts
    2260f35  🐛 Gardener stamps @gardener_id at boot, as specified
    2fbc3cc  sidebar-empty-rows: squash merge + ingest + decision fold
    47bc619  ✨ Tmux topology: window per landscaper, spec committed

Added at `47bc619`, corrected at `2260f35`, **removed at `dd9586a`** — a squash whose
branch base (`9452ee1`) predated twenty-one commits of `main`. A squash writes its whole
tree and conflicts with nothing, so the revert was silent.

This matters now only as evidence of the detection gap below. The stamp itself is not
coming back.

### `dd9586a` — the detection gap, which is the durable finding

`dd9586a` overwrote everything on `main` between `9452ee1` and its own parent — 21
commits — across 16 files, including `tools/courier.py` (853 lines), `tools/sidebar.py`
(2336 lines), `agents/gardener.md` (193 lines), `agents/courier.md` and `ARCHITECTURE.md`.

Some damage was later repaired by unrelated work: `9de9975` rebuilt the sidebar renderer
fresh, so `tools/sidebar.py` is not a live casualty. The courier
(`transport-test-reconciling`) is the one nobody repaired, and `dd9586a` is still the
last commit to touch `tools/courier.py`.

**A stale-base squash produces no conflict, no failing test, and no warning.** Two
separate landed fixes were destroyed and neither was noticed for two days. See
`groundskeeper-verify-hardening` for the close-side guard.

### A predecessor reported the breakage and was talked out of it

The `close-family-fakes` stream logged `@gardener_id` as unstamped on 2026-07-27 and
called it `[NEW, HIGH — blocks my close]`. Its successor then recorded, under "errors
made this session", that it had *wrongly* reported the stamp missing because it was
"fixed on main at `2260f35`" — self-correcting against a SHA that `dd9586a` had already
reverted. The retraction was wrong; the original report was right.

Decision-113 exactly: a finding carries the SHA and paths it was written against. Both
agents reasoned about `agents/gardener.md` at different SHAs, and the one who checked
later got the worse answer.

## Testing

To agree at scope. Expected shape: a landscaper reaching `lifecycle:stopped` has its
window closed by the placement component, with no agent having called a teardown and no
`@gardener_id` anywhere in the tree — observed on the operator's screen, and by
`grep -r landscaper-teardown` returning nothing outside history.

- created: 2026-07-29
- created_by: gardener
- created_during: main

# Bus addressing: "parent" stops being an address once supervisors and parallel workers exist

## Proposal

Operator ruling, 2026-07-29, on reading the cross-worktree wake defect: **there is more
to fix than the parent project, because the supervisor makes "parent" useless.** The
transport addresses messages by a single inherited `parent`, and that model no longer
describes the fleet it runs on.

Two things broke it at once:

- **A supervisor now sits between the gardener and the landscaper** (Decision-075). The
  landscaper's `parent` is its supervisor, the supervisor's `parent` is the gardener —
  so "signal the parent" means something different at each hop, and neither hop can
  address the gardener directly without knowing the topology it was told not to learn.
- **Parallel workers** (Decision-121: a feature is built by a TEAM of landscapers with
  fluid task binding). Several agents share one logical destination, and one agent may
  need to reach a sibling rather than an ancestor. A single-slot `parent` cannot express
  either.

This task settles what an agent addresses instead. It is the design question underneath
the live defect — the immediate `ORCHID_PARENT_PROJECT` breakage is separate and fixed
first (see Blockers).

## Blockers

- The LIVE defect is fixed ahead of this task, not inside it: `orchard_send`
  (`tools/courier.py:1130`) computes `target_project = ORCHID_PARENT_PROJECT or
  project_slug()`, and `ORCHID_PARENT_PROJECT` is unset, so a child in a feature worktree
  writes its close signal into its OWN per-branch orchard directory while its parent
  watches another. Diagnosed on `f/transport-test-reconciling`, recorded in that sidecar.
  That is a defect with a known small fix; THIS task is the model that replaces the
  concept once the bleeding stops.

## Questions

- **What is the address?** Candidates, not ruled: a session id (what it is today, via
  `:session:<id>`), a task id, a feature id, a role, or a topic subscription where the
  sender names a subject rather than a recipient. Decision-121's "the team shares context
  or uses messaging, whichever is token-efficient" suggests feature-scoped addressing, but
  the operator has not ruled it.
- **Does an agent ever need to address a SIBLING**, or does all traffic go through the
  supervisor that introduced them? Decision-121 says the supervisor "introduces the
  landscapers to one another before they start", which implies direct sibling traffic.
- **What replaces the per-worktree project directory** as the delivery boundary? It was
  introduced to fix a real mailbox collision (a second worktree's `teardown` deleting the
  first's waiting mail) and it created the cross-worktree wake defect. Both problems are
  real; the boundary needs to be somewhere else.
- **Is `ORCHID_PARENT_SESSION` injection at spawn still the mechanism**, or does the
  courier resolve its destination at send time from durable state?

## Findings

- `ORCHID_PARENT_SESSION` is injected at spawn and IS set; `ORCHID_PARENT_PROJECT` is not
  injected at all. Measured live 2026-07-29 in a landscaper session.
- Live sibling orchard directories observed in one run: `@main`,
  `@f-board-grammar`, `@f-skill-renames-and-splits`,
  `@f-transport-test-reconciling` — four separate delivery worlds with no route between
  them.
- Cost evidence, this session: three supervisors watched three live, working landscapers
  all night and each reported "no lifecycle signal received" on every wake, because the
  signals were being written where nobody was watching. The supervisors then fell back to
  polling pane contents and marker mtimes — which is the expensive path the structural
  lifecycle events were designed to replace (Decision-090).

## Testing

To agree at scope. Expected shape: a message sent from an agent in a feature worktree
arrives at its intended recipient in `main` and at a named sibling in a third worktree,
proven by the recipient acting on it rather than by inspecting the filesystem — the seam
no current test crosses.

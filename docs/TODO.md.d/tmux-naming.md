- created: 2026-07-26
- created_by: Sebastien Lambla
- created_during: orchestrator session (post-bus-landing scope round)

## Findings

- OPERATOR RULING (2026-07-26): the naming rework is tmux
  integration/extraction work that LIVES ON ITS OWN — a standalone task
  completing the EXISTING tmux work already done; it is not a chapter of the
  [[tmux-topology]] spec (the spec interfaces with it).
- Standing ruling it exists to satisfy: prior branch/feature/window naming
  schemes are REJECTED — a better scheme is designed WITH the operator, from
  his requirements, never from the incumbent artifact.
- Inherits [[sidebar-titling]]'s unfinished tail and its hard finding:
  window names `<repo>/<name>`, session named 1:1 to the repository, STABLE
  pane titles — knowing that `allow-rename off` governs the window name
  only and an OSC 2 write still clobbers `pane_title` with both rename
  options off (live-tested 2026-07-25; the salvage was reverted). The
  correct pane-title mechanism (persist/re-assert, or a title hook) is
  designed here.
- Branch `f/sidebar-titling` (9752aed) stays parked as this task's
  inheritance — its worktree stands untouched.
- From [[tmux-topology]]'s close (2026-07-26, follow-up returned): this task
  ALSO owns the window-name separator alignment — the creator writes `▸`
  while the sidebar navigator resolves `/`, a live navigation mismatch
  found in that discovery — alongside the pane-title persistence mechanism.
  The committed spec (docs/tmux-topology.md) declares the naming contract
  only; the mechanism lands here.

## Proposal

Scope designed with the operator at this task's own round: the naming
scheme (sessions, windows, panes, and their tmux mechanics), then the
integration/extraction that completes the existing tmux work with it.

## Testing

Agreed with the operator at scope time; the sidebar-titling live gate
(stable titles on his screen in one look) carries over as the known
acceptance shape.

- created: 2026-07-19
- created_by: fable-5
- created_during: f/status-channel

## Blockers

- None at the parent level; ordering lives on the children.

## Questions

- (parent rolls up — open questions live in the children)

## Findings

- Re-scoped 2026-07-20 by operator dictation: **Orchard is the fleet workbench** — the
  cross-repository view, selection and dispatch UX (Decision-024). The former content of
  this sidecar (live cross-repo messaging) moved to [[cross-repo-bus]].
- Operator's core problem: repos are picked by mood or perceived importance, with no
  global overview of all repositories needing attention, and no visible cross-repo
  dependencies (worked example: manifest-by-convention moving from orchids to kauk).
- Governing principle: **Orchard only presents what each repository's gardener has
  already prepared** — it never derives, scans, or re-triages. Each gardener maintains
  a simple parseable summary file ([[orchard-summary]]); Orchard reads and renders those.
- Overlap to manage: [[github-board-sync]] is already a functional cross-repo board view
  (GitHub issues + the Orchidarium user Project, cloud-triaged). Orchard is the LOCAL,
  terminal-first, selection-and-dispatch counterpart reading local files; they share the
  underlying board data and must not fork it.

## Proposal (the operator's UX walkthrough, 2026-07-20)

1. Launch `orchard` from anywhere. It presents the fleet: what projects exist, counts of
   pressing / broken / blocked issues, prepared next tasks, cross-repo dependencies —
   all from the gardeners' summary files ([[orchard-summary]], [[orchard-view]]).
2. The operator selects repositories to work on → one tmux session per selected repo;
   window 1 is that repo's gardener, auto-launched, told the selection, and it
   double-checks the choice against the live board. Choosing something new instead drops
   into the normal gardener intake flow ([[orchard-launch]]).
3. Task list agreed per repo → one window per landscaper; every coder the landscaper
   dispatches appears as a stacked pane; on completion the window closes and focus
   returns to the gardener ([[tmux-topology]]).
4. A small, always-visible, navigable left sidebar shows every repo and job with live
   state — waiting-for-input / working / complete, design-vs-development phase, close
   state as a bonus ([[fleet-sidebar]]); short descriptive names are its prerequisite
   ([[session-naming]]).
5. Underneath: the gardener→landscaper handover is formalised so landscapers receive
   build-ready sidecars with questions pre-asked ([[handover-contract]]), enabling cloud
   agents to take the analyzable share of landscaper work ([[cloud-architect]]) — the
   operator wants that pair delivered together, with strong gating.

## Testing

Parent-level: the walkthrough above executed end-to-end across at least two repositories
(orchids + one more), from `orchard` launch to a closed task returning focus — agreed per
child at blooming.

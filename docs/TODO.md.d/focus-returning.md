- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

- Sequencing only: starts after bloomer v1, in the operator's one-at-a-time
  sidebar-fix series.

## Questions

- Confirm the two-part rule as intake heard it: (1) on a feature's finish the
  orchestrator window ALWAYS becomes the tmux selected/current window; (2) the
  operator's visible focus (what he is looking at) changes ONLY when he is
  sitting in that feature's session at that moment.

## Findings

- Observed (operator, 2026-07-24): the return-to-orchestrator behaviour at
  feature close does not implement the selected-window vs visible-focus split;
  the current teardown path (`.claude/tools/architect-teardown.sh`) is to be
  characterised against the rule at bloom.

## Proposal

(to shape at bloom) The teardown/return path always selects the orchestrator
window; it switches the client's visible focus only when the client is
currently on the closing feature's window.

## Testing

Live verification: close a feature while (a) sitting in its window and (b)
sitting elsewhere; selected window and visible focus behave per the rule in
both cases, confirmed by the operator.

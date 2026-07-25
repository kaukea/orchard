- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (courier board triage)

## Blockers

- ⊘[[bus-finishing]] — round 2 starts only after the bus lands: the operator
  believes these are FAKE PROBLEMS, symptoms of the old fan-out/close design,
  and the round examines them against the finished bus instead of building
  onto the old one.

## Questions

- Per item: still real once the bus is finished? The expected answer for
  most is "dissolved — close with evidence".

## Findings

- OPERATOR RULING (2026-07-25): "I believe all of these are fake problems" —
  [[close-dispatching]] (already handled by documentation: the gardener's
  redispatch duty), [[window-closing-owning]], [[zombie-revival]],
  [[sidebar-witnessing]]. One second-round feature addresses them together.
- sidebar-witnessing in particular is expected to dissolve with the fan-out
  cut (the observed inboxes cease to exist; topics have no ghost-row
  mechanics).

## Proposal

After [[bus-finishing]] merges: re-examine each of the four against the new
transport; close what dissolved with evidence, rescope the residue (if any)
into precise small tasks. No building on the old design.

## Testing

Per surviving item at rescope time; the dissolution verdicts themselves are
evidence-based (code paths gone, reproduction impossible).

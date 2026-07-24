- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

- Sequencing only: starts after bloomer v1, in the operator's one-at-a-time
  sidebar-fix series.

## Questions

- Which agents and surfaces are the worst offenders — where did the operator
  see free-prose questions instead of the built popups?
- Where should the do-not-interrupt rule be enforced (rule files, agent
  definitions, or a hook) so it binds every agent rather than relying on
  prose?

## Findings

- Observed (operator, 2026-07-24): the single/multiple-choice question
  machinery built for operator interaction is not being used by agents, and
  the do-not-interrupt rule that governs its use is not honoured.
- The bloomer v1 build ([[psychometric-discovery]]) makes the popup path
  load-bearing — the instrument asks through these popups.

## Proposal

(to shape at bloom) Agents ask the operator through the built choice-question
machinery under the do-not-interrupt rule; free-prose questioning stops.

## Testing

Live verification: after the fix, an agent question round arrives via the
popups and respects do-not-interrupt; the operator confirms.

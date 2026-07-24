- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

- Sequencing only: the operator ordered the sidebar bug fixes to start after
  the bloomer v1 build lands, one at a time, each verified live on the
  orchestrator's own sidebar after coding.

## Questions

- Exact title composition: confirm the rendering is `<faint repo>/<prominent
  name>` — a light/thin repo name and a `/` BEFORE the name, so the name is
  what the eye sees most and the repo least — and whether it applies to
  session rows, the project header row, or both once sessions are named after
  projects ([[orchestrator-identity]]).
- Should a project with no open session render at all (orchids and SignMc
  currently show as empty groups)?

## Findings

- Observed (operator, 2026-07-24): gradient backgrounds are missing from the
  project name rows (orchids, SignMc). Both projects render as empty groups
  although no session is open for either.

## Proposal

(to shape at bloom) Project rows regain their gradient backgrounds; titles
render the repo name faint/thin followed by a `/` so the name dominates and
the repo recedes.

## Testing

Live verification: after the fix the orchestrator's mounted sidebar is
refreshed and the operator confirms the rendering to his liking — his stated
gate for every fix in this series.

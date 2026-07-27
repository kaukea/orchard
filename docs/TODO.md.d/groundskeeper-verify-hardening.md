- created: 2026-07-27
- created_by: fable-5
- created_during: f/close-family-fakes

# Groundskeeper verify hardening: post-merge suite run against a pre-merge baseline

## Blockers

- none

## Questions

- Should a red post-merge suite HALT the close before push, or land + auto-intake the failures as a bug (what the gardener did by hand today)?

## Findings

- 2026-07-27, close-family-fakes close: the groundskeeper twice reported the close clean on stale evidence — first citing the sidecar's recorded branch test count (345 passed) as the Testing gate without running anything post-merge, then dismissing 36 real failures as "not related" when the pre-merge baseline (69/0 in the same files) proved them a merge regression. Both were caught only by the gardener's observe-the-repo verification.

## Proposal

- The groundskeeper agent def gains a mandatory verify step: after the squash (and any conflict resolution), run the project's full test suite on the merged result and compare against the same suite at the pre-merge main SHA; report both numbers in the typed result. A recorded sidecar test count never satisfies this step.
- Workflow-component change (agent def), gardener-authored on main per Decision-065.

## Testing

- Def review + next real close exercises the step and reports both baseline and post-merge numbers.

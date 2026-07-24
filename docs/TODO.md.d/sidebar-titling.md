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
- Pane capture (2026-07-24 evening, orchestrator, `tmux capture-pane -e` on
  the live sidebar): confirms and extends the report —
  - `orchids` header renders bold+reverse-video (`[1;7m`), `SignMc` renders
    bold only (`[1m`): no gradient anywhere, and the two project headers are
    not even styled consistently with each other.
  - No repo/`/name` composition exists on any row; session rows show only
    the board title, truncated mid-word with no ellipsis ("last-night-
    discussio", "Bloomer charter: clo"), so concurrent sessions on one
    feature are indistinguishable (ghost-row aspect recorded in
    [[sidebar-witnessing]]).
  - The reverse-video project header is the loudest element on screen — the
    opposite of the requested tame/faint repo rendering.

## Proposal

(to shape at bloom) Project rows regain their gradient backgrounds; titles
render the repo name faint/thin followed by a `/` so the name dominates and
the repo recedes.

## Testing

Live verification: after the fix the orchestrator's mounted sidebar is
refreshed and the operator confirms the rendering to his liking — his stated
gate for every fix in this series.

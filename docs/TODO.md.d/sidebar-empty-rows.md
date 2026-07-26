- created: 2026-07-26
- created_by: Sebastien Lambla
- created_during: gardener session (post-cutover live check a)

## Findings

- OPERATOR OBSERVATION (2026-07-26, verbatim): "only a black 'orchids'
  centered text on a white background, no other line". Pane capture
  confirms: the project name centered, zero session rows.
- This IS bus-finishing's deferred live acceptance check (a) — "the sidebar
  still shows session activity end-to-end after the cut" — FAILING on first
  observation. The release cut is held on this check passing.
- Environment verified NOT at fault before boarding (gardener diagnostics):
  - The pane runs the RIGHT file: `python3 .ai/repositories/serialseb/
    orchids/tools/sidebar.py`, cwd = main checkout, no worktree in the
    path; mirror at 231b59d, `tools/sidebar.py` byte-identical with main.
  - The renderer is the NEW one: its child `inotifywait -m -r … /run/user/
    1000/orchard/projects` watches the orchard tree.
  - The DATA side is live: `projects/kaukea.orchids/` holds a
    `<sessionid>.marker` and fresh events (gardener `status: triaging`
    posted 13:42 via `orchard_topic.py`, courier announce), yet no row
    renders.
- Styling also wrong in the same view: black-on-white, no project hue —
  possibly the same defect (nothing past the header paints), noted, not a
  separate report.
- `--once` produced a curses traceback under a non-tty (cbreak ERR) —
  whether the consolidated renderer still has a one-shot mode is unclear.
  Pulled INTO scope by operator ruling 2 (below); no longer a loose end.
- BLOOM ROUND (Decision-050, 2026-07-26): three operator answers, relayed
  verbatim through the gardener, closed the WHAT. Engine report, taken as
  given: overall SE 0.518, band "lower", launch-sizing recommendation m
  (claude-opus-4-8, xhigh), zero misfit flags, no deferral candidates.
  Caveats: v1 item parameters are LLM-assumed, not corpus-fitted
  (uncalibrated_items: true); the acceptance dimension converged (SE
  0.30) while the testability dimension reads non-converged (SE 0.74) as
  an instrument artifact — its final confirmation item would have
  re-asked a ruling the operator had already stated twice and was not
  posed, leaving residual posterior mass on the never-probed "landscaper's
  call" hypothesis, which ruling 2 overrode. Substance is settled; the
  band, taken as given, routes the launch decision back to the gardener.

## Proposal

Make the consolidated `tools/sidebar.py` render session rows from the live
orchard tree: the model must surface a project's sessions (marker = alive,
events = status/phase colouring) exactly as the bus-finishing contract
states — done green, failed red, not-heard-from gray, working normal.
Diagnose why the built model yields zero rows for a project with a live
marker and fresh events; fix; keep the header hue contract
(solid per-repo hue) alive past the header.

Scope, settled by operator rulings (2026-07-26 bloom round, below):
restore the `--once` one-shot render mode inside this fix so the renderer
is testable, and ship an automated regression test that fails when a
project with a live marker and fresh events yields zero rows — the exact
defect class of this bug.

Voluntary deferrals: none — the round's only loose end (`--once`
restoration) was pulled into scope by ruling 2.

## Testing

Live, operator eyeball (the standing check-a gate), confirmed as written
by ruling 1: with the gardener session running, the bar shows the orchids
header WITH its hue and one session row carrying current status; the row
updates on a fresh `orchard_topic.py post status` without restart.
Missing hue keeps check (a) failing even with rows working. Passing this
closes check (a) and re-arms the release-cut trigger.

Build-time, automated (ruling 3): a regression test, runnable through the
restored `--once` path, failing whenever a project that holds a live
`<sessionid>.marker` and fresh events yields zero session rows.

## Decision entries

Operator rulings, 2026-07-26, answered in the Decision-050 bloom round
and relayed verbatim through the gardener:

1. The check (a) pass bar is rows AND hue — the Testing gate stands as
   written; missing hue keeps check (a) failing even with rows working.
2. `--once` (one-shot render) is restored as part of this fix so the
   renderer is testable; acceptance remains the operator's live eyeball.
3. An automated regression test ships with the fix: it fails when a
   project with a live marker and fresh events yields zero rows.

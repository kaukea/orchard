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
  whether the consolidated renderer still has a one-shot mode is unclear;
  worth restoring for testability (build's call).

## Proposal

Make the consolidated `tools/sidebar.py` render session rows from the live
orchard tree: the model must surface a project's sessions (marker = alive,
events = status/phase colouring) exactly as the bus-finishing contract
states — done green, failed red, not-heard-from gray, working normal.
Diagnose why the built model yields zero rows for a project with a live
marker and fresh events; fix; keep the header hue contract
(solid per-repo hue) alive past the header.

## Testing

Live, operator eyeball (the standing check-a gate): with the gardener
session running, the bar shows the orchids header WITH its hue and one
session row carrying current status; the row updates on a fresh
`orchard_topic.py post status` without restart. Passing this closes
check (a) and re-arms the release-cut trigger.

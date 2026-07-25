- created: 2026-07-18
- created_by: fable-5
- created_during: interactive

## Blockers
- None.

## Questions
- Project field mapping: which board badge fields become Project custom fields
  (status/urgency/readiness/component/repo), and which saved views (master
  by-priority, by-repo, roadmap)?
- Cross-repo dependency representation: native sub-issues / dependency links
  vs a Project field mirroring `blocked_by` — verify what GitHub offers at
  build time.
- Claude GitHub App auth: API key vs subscription OAuth token, and secret
  distribution across the three owners (serialseb, SafeKeepIt, kaukea) —
  org secrets don't span owners.
- Injection/actor gating: on public repos anyone can file issues; the
  workflow must run the gardener only for the operator's own
  issues/comments (actor allowlist), never on third-party text.
- Workflow-file delivery: RESOLVED — a manifest `template` entry
  (`template templates/board-sync.yml .github/workflows/board-sync.yml`);
  it must be template, not link: a symlink would target the gitignored
  .ai/ clone and Actions only executes real files. Remaining: pushes
  touching workflow files need the workflows permission, and template
  files are project-owned, so template changes don't propagate on sync —
  acceptable for a stable trigger shim that delegates logic to the agent.
- Race with a live local session on main: cloud gardener pushes intake
  commits; local sessions already pull at start — define retry/ff-only
  behaviour on push rejection.
- Project naming and location (user-level project on serialseb).

## Findings
- Result: FUNCTIONAL (f/github-board-sync, 2026-07-18). Shipped: board_gh.py
  (issue projection + Project rows + pull ingestion), the user Project
  "Orchidarium" (private, 28 rows), central board-sync workflow + shim
  (kauk laid), gardener pull-at-boot/push-after-write wiring. Live-tested
  both repos end-to-end (orchids ingest ed3e4bb, kauk shim 8ca6645).
  Increments remain per the 2026-07-19 test plan below: body/comment and
  Project-drag ingestion, Claude-app triage, and the privacy fallout fix
  (private package repo vs kauk's runner access, Decision-013).
- Operator problem (2026-07-18): ~15 concurrent projects, some interdependent;
  no cross-project review of pending work and priorities. Console UI can't
  carry it; GitHub Projects v2 chosen as the view.
- A USER-level Project aggregates issues from repos across owners
  (serialseb, SafeKeepIt, kaukea) — org-level would not span them.
- The board badge already reserves a `gh#` column; issues follow each repo's
  visibility, so the board sanitization rule applies verbatim to issue bodies.

## Proposal
Operator rulings (2026-07-18):
- Files canonical; GitHub is the view. FULL ingestion at sync: GitHub-born
  issues become sidecars, field edits become board updates, comments land in
  the sidecar; then files rule until push-back.
- Issues for ACTIVE tasks only (todo/doing/blocked/paused; closed on
  done/cancelled). Issue body = sanitized summary + open questions; the
  sidecar stays the full record.
- Sync is the GARDENER'S job only — pull at session start, push at close
  (same pattern as kauk sync); child sessions never touch GitHub.
- Ingestion is EVENT-DRIVEN over GitHub, not polled (operator, 2026-07-18):
  a GitHub Actions workflow in each repo receives issue/Project events and
  runs the Claude GitHub integration AS THAT REPO'S GARDENER — the
  checkout carries the vendored orchids package, so the role, skills, and
  board rules are in place; it ingests the change into sidecar/board and
  commits to main. Local sessions stay for real work; the cloud gardener
  only triages board events. Works with the Pi off; no idle cron runs.
- Pilot: orchids + kauk; the fleet follows via the package.

## Testing
Pilot verified live 2026-07-18: projection (20+8 issues, gh# badges), Project
rows (Orchidarium, 28), ingestion (stub + closed-from-GitHub), event path on
both repos (orchids direct ed3e4bb, kauk shim 8ca6645), idempotent re-runs.

## Test plan — 2026-07-19 (capabilities → outcomes)
Run in real conditions, not synthetic loops. Pass = the stated outcome,
nothing else changed.

1. **Phone-born task.** File an issue from the phone on orchids, no label.
   → Within ~1 min a `📋 Board ingest` commit lands on main: stub sidecar
   (`created_by: gh-ingest`) + board line with its gh#.
2. **Couch close.** Close a real board issue from the phone.
   → Ingest commit flips that task's board status to `done`; nothing else moves.
3. **Board-side close.** Mark a task done locally, run push.
   → Its issue closes with the "task reached" comment; Orchidarium row Status
   flips to done at next sync.
4. **Session intake.** Intake a new task on the board, push.
   → Issue + Orchidarium row appear with Status/Urgency/Readiness/Component
   matching the badge; gh# committed on the badge.
5. **Field drift.** Change a task's urgency on the board, push.
   → Only that row's Urgency changes in Orchidarium.
6. **Gardener boot.** Start a fresh gardener session after (1).
   → Pull runs before the board read; the untriaged stub is surfaced in the
   render; bloom assigns type/component and push updates the issue body.
7. **Central update propagation.** Edit the central workflow on orchids main
   (e.g. a log line); file a kauk issue.
   → kauk's run shows the new logic with no kauk-side change (shim untouched).
8. **Write race.** Hold an unpushed board commit locally; fire (1) meanwhile;
   then push local.
   → Both land (workflow rebase-retry; local pull-at-start); no lost lines.
9. **Actor gate.** An issue authored by a non-operator account.
   → The workflow job is skipped; nothing is committed.
10. **Privacy fallout (Decision-013) — expect kauk's event path BROKEN.**
    With kaukea/orchids private, kauk's runner can no longer (a) call the
    cross-owner reusable workflow nor (b) checkout the package with its
    repo-scoped token. Confirm the failure, then pick the fix: an org/user
    PAT secret for both operations, or vendoring workflow+tool into
    consumers via the package (manifest copy/ro pairs with this).
11. **Known gaps (expected to fail — feed the next increment).** a) Editing
    an issue's body/comments on GitHub is not ingested into the sidecar.
    b) Dragging a card between Status columns in Orchidarium does not reach
    the board. c) No Claude-app triage of stubs. Confirm each is still a gap,
    then scope the increment.

Outcome record: tick each scenario in this section with commit SHAs / run ids.

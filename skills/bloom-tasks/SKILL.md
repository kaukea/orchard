---
name: bloom-tasks
description: Run a board-blooming pass — dispatch the prep-only bloomer over the stalest opted-in tasks so their sidecars advance through the readiness pipeline without the operator driving each one. NOT a cron; a manual/on-demand trigger fired by the operator ("bloom the board") or by the gardener when it notices the change signal (docs/decisions.md or a sidecar moved since the last swept SHA). Commit-only, N=2 per pass.
roles: [process/workflow]
share: github
compatibility: Requires git
metadata:
  tags: [blooming-pass, staleness-walk, bloomer-dispatch, readiness-pipeline, change-signal, board-stale-script]
---

# Intent (bloom)

Blooming keeps parked tasks *ready* — it advances their sidecars through the readiness
pipeline (`queued → working → blocked-on-answers → plan-ready`) so that when the operator
picks one up, the discovery is already done. It is a **subagent dispatched on a trigger**, not
a scheduled cron (Decision — blooming is change-triggered / on-demand). Automatic scheduling
(a cloud routine wrapping the *same* bloomer) stays a possible later enhancement; the bloomer
is trigger-agnostic, so adding a schedule later changes only how it is kicked off.

# Triggers (any fires a pass)

1. **Operator asks** — "bloom the board", "do a blooming pass", etc.
2. **Gardener notices the change signal** — `docs/decisions.md` or a sidecar moved since
   the last swept SHA. The gardener evaluates this live at a natural board-holding moment;
   there is no clock. No change → no pass → no board churn.
3. **Handoff — every operator go (Decision-050).** The gardener dispatches the bloomer
   on the picked task BEFORE any landscaper is spawned — the mandatory bloom round that
   closes the WHAT (functional completeness, Decision-027) at the moment of launch. This
   trigger targets exactly the picked task(s), is not N-capped, and a `plan-ready` badge
   does not skip it.

# The pass (what the gardener / operator runs)

1. **Find candidates.** Run the staleness walk:
   - default: `python3 .claude/tools/board_stale.py --n 2` — the 2 stalest bloomable tasks.
   - change-signal check: `python3 .claude/tools/board_stale.py --since "$(cat .claude/state/last-bloom.sha)"`
     lists bloomable tasks whose sidecar or a hard dep moved since the last pass; bloom the
     stalest 2 of those.
   Bloomable = a parked task (`status` todo|functional); `done`/`cancelled` are terminal.
   **Cost cap: N=2 per pass** — never fan the bloomer over the whole board at once.
2. **Dispatch the bloomer** on each chosen `<id>` — `Agent` tool `subagent_type: bloomer`,
   one task per bloomer. PREFER the Agent tool from a live session: a `claude --bg` bloomer
   is headless and PARKS FOREVER on its first permission prompt (live-fired 2026-07-22 —
   two bloomers blocked 19 minutes unattended); use `claude --bg --agent bloomer --name
   "orchids ▸ ${id//-/ }"` only when the needed permissions are pre-allowed. The
   `--name` carries the feature's human name (id with `-` → spaces), never the role. The
   bloomer is **prep-only**: it
   advances the stage, fleshes the sidecar, projects the readiness badge, runs `board_lint.py`,
   and commits (`🌸 bloom: <id> → <stage>`). It never builds, branches, or opens a PR — a
   build-ready task is left at `plan-ready` for the operator.
3. **Record the swept SHA.** After the pass, write HEAD so the next change-signal check has a
   baseline: `git rev-parse HEAD > .claude/state/last-bloom.sha` and commit it.
4. **Re-triage.** The gardener ingests the bloomers' one-line results (and any Questions
   they raised for the operator) and folds them into the board-walk.

# Boundaries

- **Single writer** — the bloomer only touches *parked* tasks, never the one the operator is
  actively building (no blooming a task with an open worktree / `f/<id>` branch).
- **Commit-only, no push** — the operator/gardener pushes; blooming never reaches a remote
  on its own. The human merge/review gate is preserved (nothing autonomous reaches `main`).
- **Supervised first** — review the bloomer's commits before enabling any recurring schedule
  (there is none yet); the first autonomous-to-`main` path stays gated off.

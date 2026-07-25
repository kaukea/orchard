- created: 2026-07-21
- created_by: fable-5
- created_during: f/app-identifying

## Blockers

- None.

## Questions

- OPEN SEAM (operator to rule): what is the cloud callback physically — (a) the
  existing board-sync (fired on issue-close) absorbing the gardener's close
  duties, or (b) a distinct cold-started gardener-cloud post-merge hop
  (board sync + decisions promotion + headless "have a look")?
- Mechanism choice: GitHub MERGE QUEUE (native FIFO + auto-rebase; composes
  with the approval gate: approve → enqueue → ordered merge) vs
  optimistic-retry on atomic ref update. NOT a global `concurrency:` group —
  cancel-in-progress:false drops mid-queue pendings.

## Findings

- Deterministic ordering is a THIRD concern ("Mr. Rabbit with the clock") — a
  peer of the groundskeeper and the gardener, owned by neither
  (Decision-040). Merge order == changelog order: the same authority.
- Unified local/remote loop (operator, converged 2026-07-21): one loop shape;
  the entire local/remote difference lives in exactly TWO seams —
  SEAM 1 launch (launcher subagent: local → worktree+spawn, remote → no-op) and
  SEAM 2 merge (Mr. Rabbit merges the same either way, and ALSO writes
  changelog+readme AT MERGE TIME against current main, fixing the two-commit
  seam; local/interactive may ask the gardener, cloud/headless decides
  alone — free, because append-against-current-main-in-queue-order is
  deterministic).
- LOOP CLOSE (both modes): after merge, Rabbit CALLS the gardener — "work
  done, have a look" — the gardener is demoted from doing-the-merge to
  notified-after; residual = board sync + duties, not ordering.
- Minor-change close model (operator): groundskeeper PREWRITES all close
  artifacts (squash subject/body, notes on branch tip, tag, docs gate); the
  serialized merge reconciles with live main and MOVES the notes onto the
  resulting squash commit.
- Singleton question resolved: no persistent single gardener needed —
  serialize only the MERGE and let each instance reconcile with current main;
  concurrent instances then perform as well as one. Cloud concurrency is
  already per-issue, so contention exists only at merge-to-main.
- Why changelog moved off the landscaper (Decision-034 context): a single
  landscaper knows one branch and cannot order across parallel work —
  global-ordering knowledge, same authority as merge ordering.
- Untested hypothesis (landscaper): once the merge is serialized and the merger
  reads current main, single-branch blindness vanishes — a queue-serialized,
  main-reading groundskeeper might write the changelog itself, and a distinct
  cloud gardener role may not be needed at close at all.

## Proposal

Give the fleet a deterministic merge-ordering authority ("Mr. Rabbit"):
serialize merges to `main` (merge queue or optimistic-retry), apply
changelog/readme at the serialized merge against current main, move prewritten
notes onto the squash, then call the gardener to close the loop. Same path
local and cloud; only the may-it-ask seam differs.

## Testing

To agree when bloomed — expected: two concurrent feature closes land in a
deterministic order with changelog entries in merge order and notes on the
squash commits.

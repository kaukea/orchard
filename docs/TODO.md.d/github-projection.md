- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# GitHub projection: feature = parent issue, real sub-issues, unfiled triage — Decision-119 built

## Proposal

Task of feature **Feature creation**. Implement Decision-119 in
`tools/board_gh.py`: a feature projects as a parent issue carrying the full
design; task issues attach as native sub-issues at mint, across disconnected
rounds, to the same still-open parent; the parent closes only on the operator's
delivered ruling; one-offs are flat issues; issues born on GitHub are UNFILED
and triage assigns them to a feature or one-offs before a board line exists.

Verified 2026-07-28 against the live `kaukea/orchids` schema (`gh api
graphql`, read-only introspection, no writes): `Mutation.addSubIssue`,
`removeSubIssue`, and `reprioritizeSubIssue` all exist, and `Issue` carries
`subIssues`/`subIssuesSummary` fields — the same shape `sync_relationships`
already drives for `addBlockedBy`/`removeBlockedBy`. No plan gate blocks this
repo. `AddSubIssueInput` takes `issueId` (parent) + `subIssueId` (or
`subIssueUrl`) + optional `replaceParent`.

Scope, all within `board_gh.py`, function by function:

1. **`Feature` class, beside `Task` (`:88`).** Mirrors `Task`'s shape (title,
   path, gh, status) minus per-task fields (readiness/urgency don't apply to a
   parent). Parsed from a distinct board-line grammar the sibling task
   `board-grammar` defines (this task blocks on that interface, not on its
   implementation — either can land first once the feature-line shape is
   agreed).
2. **`sync_feature(board, feature)` (new function, called from `push`
   alongside today's per-task loop).** Creates the parent issue on first push
   (`gh issue create`), updates its body/labels on subsequent pushes
   (`gh issue edit`), never closes it — closing is reserved for the operator's
   delivered ruling recorded on the sidecar, read the same way `push` already
   reads task status today.
3. **`sync_subissues(board, by_id)` (new function, parallel to
   `sync_relationships` `:357-378`).** For each task with a `gh` number whose
   parent feature also has a `gh` number: `addSubIssueIds = subIssues(first:50)`
   read (mirrors `blocked_by_ids`), diff against desired, call
   `addSubIssue`/`removeSubIssue` for the delta — identical control flow to
   the existing `blockedBy` sync, same node-id lookup helper
   (`issue_node_id`).
4. **`issue_body` (`:159-172`).** Delete the "Sub-tasks" markdown block
   entirely once `sync_subissues` runs — native sub-issues render in GitHub's
   UI on their own; keeping the markdown list would duplicate and drift from
   the native relationship. `Related` block (unaffected) stays as-is.
5. **Pull, UNFILED minting (`:542-552`).** Replace the unconditional
   `- \`feature · todo · · queued · · gh#N\`` board-line append with an
   UNFILED path: write the sidecar stub (unchanged), but do NOT append any
   board line — instead register the issue in a new `## Unfiled` staging list
   (location/format: TBD by the triage-UI question below) for the operator's
   triage step to consume. No top-level `feature` line is minted directly
   from `pull` any more.

Depends on `board-grammar` for the feature-line shape `Feature` parses and for
what a filed task's board line looks like once it belongs to a feature. The
two tasks may land in either order once that shared interface is agreed
first — recommend agreeing the interface as a short doc note in whichever
task lands first, so the second isn't blocked on a merge.

## Questions

1. The operator observed the existing triage UI is buggy. Two options:
   - **(a) Fix it here.** Bundle the triage-UI fix into this task's scope,
     since UNFILED minting (item 5 above) is the exact code path the buggy UI
     drives — touching it once avoids a second round through the same
     function.
   - **(b) Report only, defer to a follow-up task.** Keep this task to the
     three items Decision-119 actually specifies (Feature object, sub-issue
     attachment, UNFILED minting); file a separate bug task for the triage UI
     once its symptom is reproduced, since "buggy" isn't yet characterized as
     a concrete defect and conflating the fix risks scope creep on a task
     that's otherwise cleanly bounded.

   Recommendation: **(b)** — the bug hasn't been characterized (no repro,
   no filed defect), and Decision-119 doesn't mention the triage UI at all.
   Bundling an uncharacterized bug fix into a scoped feature task is exactly
   the kind of scope expansion the shared AGENTS rules flag for a separate
   surfaced choice. Operator to confirm or pick (a).

## Findings

Inventory references in the feature sidecar (`features-first-class.md`
§Findings, "The GitHub projection").

GraphQL surface confirmed live against `kaukea/orchids` (2026-07-28,
read-only): `addSubIssue`, `removeSubIssue`, `reprioritizeSubIssue` mutations
present; `Issue.subIssues`/`subIssuesSummary` fields present; no plan
restriction observed. `sync_relationships` (`:357-378`) is a directly
reusable template for `sync_subissues`.

## Testing

1. `python3 tools/board_gh.py push` against a throwaway feature + one throwaway
   task on the real `kaukea/orchids` repo: confirm the parent issue is minted
   exactly once (re-running push does not create a duplicate), the task
   attaches as a native sub-issue (`gh issue view <task#> --json
   subIssueSummary` or the GitHub UI shows it under the parent's sub-issues),
   and the issue body no longer carries a markdown "Sub-tasks" list.
2. Close the task issue on GitHub, then `python3 tools/board_gh.py pull`:
   confirm the parent issue stays open (only the operator's delivered ruling
   closes it).
3. Open a brand-new issue directly on GitHub (no board label), then
   `python3 tools/board_gh.py pull`: confirm a sidecar stub is written but NO
   top-level board line is appended — the issue lands in the Unfiled staging
   list instead of minting a stray `feature` line.
4. Clean up: close/delete the throwaway parent + task issues and remove their
   sidecars before merging.

---
name: history-rewrite
description: MUST be read in full and followed step-by-step before rewriting any
roles: [process/workflow]
  repository's main into the canonical structure (per-feature f/ branches that never
  existed, anchor commits, archive/ tombstone tags, squash template, commit-count
  notes, optional operator QES on squashes). Two prior migrations failed because the
  agent inferred or bypassed the procedure — execute verbatim, verify every gate,
  STOP on anything uncovered.
metadata:
  tags: [ migration, history, rewrite, main, forensics, anchor, squash, archive, notes, qes ]
  share: github
---

# History rewrite (main-branch migration)

Rewrites a repo whose `main` grew without the workflow into the canonical shape.
FORENSIC discipline: the original refs are read-only inputs; every step has a
mechanical verification; the operator gates the partition, the signing, and the swap.

## The anti-nightmare clause

This skill exists because two migrations failed when the agent inferred instead of
reading, or bypassed steps entirely. Therefore: execute the steps IN ORDER, tick each
checkbox, and if ANY verification fails or ANY situation is not covered here — STOP
and ask the operator. Improvising a workaround is the failure mode, not a recovery.

## Checklist

- [ ] Applicability gate: project `AGENTS.md` has no `repository:` value other than
      `orchids` (missing/empty = `orchids`; anything else, e.g. `gitflow` → STOP,
      this skill does not apply)
- [ ] Preconditions met (clean tree, kauk install done, backup ref created)
- [ ] Sensitive-content sweep of full history done; findings surfaced BEFORE rewriting
- [ ] Feature partition proposed and OPERATOR-APPROVED before any ref is written
- [ ] Every feature: branch → ANCHOR COMMIT → cherry-picks → archive tag → templated
      squash → note → SHA-map references rewritten → three-way verify
- [ ] Final tree identity: rewritten tip tree == original main tip tree
- [ ] QES pass (only if this project requires it) done; every squash verifies G;
      notes re-attached to the re-signed SHAs
- [ ] Swap executed ONLY on the operator's explicit go; backup ref retained

## 0 · Preconditions

**Applicability:** the project's `AGENTS.md` declares the repository shape. A
`repository:` value other than `orchids` (e.g. `repository: gitflow`) means the repo
keeps its own branching model — STOP, this skill does not apply. A missing or empty
value counts as `orchids`.

Clean tree; `kauk install` already run (the repo is package-managed); work happens in a dedicated worktree on
branch `tmp/main-rewrite`; tag `backup/pre-rewrite` on current `main` FIRST.
Original `main` is never checked out, committed to, amended, or deleted.

**Dispatch note:** §0–§1 are read-only (the backup tag is the only ref created, and it
touches nothing). The gardener may run them as a parallel background subagent;
every write from §2 on waits behind operator gate #1.

## 1 · Sweep, then partition (operator gate #1)

Sweep the full history for sensitive content (conversation quotes, personal data,
secrets — `AGENTS.shared.md` sensitive-content rule); anything found is listed for
the operator: it must be scrubbed in this rewrite, not carried over.

Read `main` oldest→newest and propose the partition: a table of
`commit-range → f/<feature-id> → squash title`. Rules: every commit lands in exactly
one feature; order preserved; no commit reworded, squashed, or dropped inside a
feature. Present the table and WAIT for approval. Do not touch a ref before it.

## 2 · Rebuild, feature by feature (oldest first, dates preserved)

Process groups oldest-first by their first original commit. Maintain an old→new SHA
map for every commit you create.

1. Branch `f/<id>` from `rw/main` exactly where it stands — moving oldest→youngest
   means `rw/main` IS the feature's start point, so the Base is already found.
2. **ANCHOR COMMIT — MANDATORY first commit on every branch:** empty `🎉` commit
   stating the feature's intent, `Base: <sha>` trailer recording the branch point
   (git cannot recover it naturally). Its date = the feature's first original commit
   date; it is the start marker for lead-time.
3. Cherry-pick the group's commits verbatim, oldest→youngest, preserving author,
   author-date, and committer-date.
4. Tag `archive/<id>` on the branch head.
5. Squash-merge onto `rw/main` with the workflow-complete template — `🎯`/`Head:` =
   the NEW branch-head SHA, `📦` per the rev-list rule, `⌛` lead-time = anchor →
   last commit, computed from the ORIGINAL dates; the squash's author/committer
   dates = the group's last original commit date, so main's chronology and ordering
   are preserved.
6. `git notes add -m "commit-count: N"` on the squash.
7. Rewrite any old-SHA references in commit messages via the map (three agents have
   skipped this — it is a step, not an afterthought).
8. VERIFY, all three or STOP: the `archive/<id>` tag exists and `🎯`/`Head:` resolve
   to it (one agent once produced only the main commit — this catches that) ·
   `rw/main^{tree}` == the group's last original commit tree · dates monotonic.
   Interleaved groups make the per-feature tree check impossible: STOP and
   re-partition with the operator, never skip the check.
9. Delete the `f/<id>` ref — the archive tag is the tombstone.

## 3 · Final integrity

`rw/main^{tree}` == `main^{tree}` (byte-identical content), every `archive/*` tag
resolves, every squash carries its note, the SHA map covers every created commit.
All of it, or STOP.

## 4 · QES signing (per-project; operator gate #2)

Only if THIS project requires signed squashes (its `AGENTS.md`, or the operator,
says so — not every project does). If not required, skip to §5 and swap `rw/main`.

The signing pass re-signs every squash on `rw/main` with the operator's card via
signmc (`resign.sh`), producing `main-signed`. The card and PIN mean the operator is
present. Re-signing CHANGES every squash SHA: re-attach each `commit-count` note to
its re-signed commit and re-run the SHA-map pass over message references
(CHANGELOG `_base:` lines included) AFTERWARDS, then verify
`git log --show-signature` shows G on every squash and no note was orphaned.

## 5 · Swap (operator gate #3)

Only on an explicit "swap it": point `main` at the rewritten tip (`main-signed`, or
`rw/main` when §4 was skipped); the backup ref stays; push only per the operator's
instruction. The agent NEVER initiates the swap.

## 6 · Record

Close gate as usual: decisions entry for the migration, CHANGELOG, board task
updated. The old→new SHA map is attached to the task's sidecar Findings.

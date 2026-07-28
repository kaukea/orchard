---
name: workflow-complete
description: Read and follow the moment a workflow closes — the user approved it with MAKE IT SO, or it is being abandoned. Defines the entire close procedure: documentation update, clean tree, marker tag, squash-merge, integrity verify, mandatory push to origin (commits + tag + notes), worktree removal, the mandatory handover write, and cancellation. The workflow skill defines everything up to the approval gate; this skill defines everything after it.
roles: [process/workflow]
tracked: true
metadata:
  tags: [ workflow, complete, finish, end, merge, squash, tag, cleanup, cancel, handover ]
  share: github
---

# Intent (Workflow completion)

The close procedure for a workflow. Load and follow this skill the moment a
workflow finishes — the user has approved it with `MAKE IT SO` — or is being
abandoned. The `workflow` skill defines everything up to and including the
testing and approval gates; this skill defines everything after them.

A workflow can only close once every item on the Workflow Completion checklist
(in the `workflow` skill) is satisfied. The Testing and User-approval gates that
precede this skill are non-negotiable and the model may not self-approve either —
do not load this skill to skip them.

Run these steps in order.

## Documentation Update

Update the project's agent-facing state on the feature branch, in a commit that the squash will carry to `main`. Do
NOT create a separate commit on `main` after the merge — the squash already lands these files, and an extra commit
pollutes history.

- [ ] Memory and documentation files must be reviewed to reflect the current state of the project, discarding
      out-of-date information.
- [ ] Agreed work, follow-up work, and future work must be updated on the board (`docs/TODO.md` + sidecars, `AGENTS.files.md` §TODO).
- [ ] The `## Changelog entry` is STAGED verbatim in the sidecar result — do NOT
      edit `CHANGELOG.md`; the gardener places it at ingest, operator-gated
      (Decision-034; format `AGENTS.files.md` → §Changelog).
- [ ] The `## Readme delta` (user-facing changes) is staged in the sidecar result,
      or an evidenced no-change determination recorded — do NOT edit `README.md`;
      the gardener applies it via `readme-sync` at ingest (Decision-034).

## Clean tree

Agents leave files behind tracking their work.

If files are included by .gitignore as preserve `!<path>` or ignore `<path>`, they are to be commited, otherwise alert
the user and propose adding the directory or the file to `.gitignore`, with a recommendation.
Examples:

- OpenCode plan files (`.opencode/plans/`, `plan.md`, or similar)
- Agent task files, scratchpads, or temporary reasoning files created by the tool
- Any file the tool created to track its own progress, not for the project
- Propose to the user to add any such file to the `.gitignore` file
- Do not delete files without user confirmation

Task files always get committed:

- `docs/TODO.md` + `docs/TODO.md.d/` sidecars — project work tracking yet to do.
- `CHANGELOG.md` — single release/record artifact (human release notes + machine provenance).
- `AGENTS.shared.md` and all symlinks coming from the `.ai` directory — they are shared rules.
- Memory files under `.claude/projects/` that are still relevant. Delete obsolete ones before committing.

(Workstream logs are not a tree concern — they live inside `.git/the-works/`, uncommittable; see Workstream log close below.)

## Marker tag

You must add a tag named `archive/<feature-id>` to the feature branch you're merging.

## Merge squash

Before merging, record the commit count of the feature branch:

```
N=$(git rev-list main..f/<feature-id> --count)
```

You must merge squash the feature branch onto the `main` branch, following this template.

```
<gitmoji> <subject>

🎯 <branch-head> 📦 <commits> ⌛ <lead-time>

<body>

Branch: <branch>
Head: <branch-head>
Agent: <model>
```

- `<branch-head>` — Short SHA of the feature branch HEAD (the same commit that `archive/<feature-id>` tags).
- `<commits>` — Number of commits squashed.
- `<lead-time>` — Human-readable lead time (e.g., "2d 8h", "1m 2d") between the first commit of the feature branch and
  the merge commit. NOT measured from the commit you branched off of on `main`.
- `<branch>` — The feature branch you are merging.
- For anything else follow the rules in the git-workflow skill.

A close that carries no content to `main` — a no-content task or an abandoned experiment — uses this same template
with an **empty** commit. See *Abandoned and no-content closes* below.

After creating the squash commit, write the commit count as a git note on the new HEAD:

```
git notes add -m "commit-count: $N"
```

The note is pushed together with `main` and the `archive/<feature-id>` tag in the mandatory
*Push to origin* step below — never as a one-off here.

## Verify squash integrity

After the squash commit, verify that no content was lost and the metadata is correct:

```bash
# Tree content must match the intended close:
#   full-carry  → squash tree == branch tree (the work landed on main)
#   empty close → squash tree == parent tree (no-content task or abandoned experiment:
#                 nothing carried to main; the branch content stays under the archive tag)
SQUASH_TREE=$(git rev-parse HEAD^{tree})
BRANCH_TREE=$(git rev-parse archive/<feature-id>^{tree})
PARENT_TREE=$(git rev-parse HEAD~1^{tree})
if [ "$SQUASH_TREE" = "$BRANCH_TREE" ] || [ "$SQUASH_TREE" = "$PARENT_TREE" ]; then
  :  # full-carry (matches branch) or empty close (matches parent) — both valid
else
  echo "ERROR: tree mismatch (squash is neither the full branch tree nor an empty close)"
fi

# Commit count must match rev-list
NOTED_COUNT=$(git notes show HEAD 2>/dev/null | grep commit-count | cut -d' ' -f2)
ACTUAL_COUNT=$(git rev-list $(git merge-base main~ archive/<feature-id>)..archive/<feature-id> --count)
[ "$NOTED_COUNT" = "$ACTUAL_COUNT" ] || echo "ERROR: commit count mismatch (noted=$NOTED_COUNT actual=$ACTUAL_COUNT)"
```

If either check fails, do NOT delete the branch. Investigate and fix the squash commit first.

## Push to origin

**Mandatory, every close** — full-carry and empty/abandoned alike. Once the squash, tag, and integrity
check have passed, push three things to `origin` in one shot: the squashed `main` (the commits), the
`archive/<feature-id>` tombstone tag, and the commit-count git note CI reads for versioning.

```sh
git push origin main "refs/tags/archive/<feature-id>" "refs/notes/*"
```

This is not optional and not conditional — every workflow close ends by publishing the merged history,
the tombstone, and the note, so origin always mirrors the local close.

If the push fails (box offline, auth, rejected non-fast-forward), the **local close still stands** — the
squash, the `archive/` tag, and the branch history under it are intact and authoritative. Do NOT roll back,
re-squash, or skip the remaining close steps. Report the failure to the operator verbatim and let them
decide when to retry; never silently swallow it.

## Workstream log close

Record the outcome as the closing act, before removing the worktree — split by
sensitivity (this is a **mandatory** close step; full protocol in the `handover` skill):

- **Durable, sanitized task state** → the task's sidecar (`docs/TODO.md.d/<id>.md` →
  `## Findings` + a `Result:` line, per `AGENTS.files.md` §Sidecar): outcome, merged
  SHA (or cancelled), what was tested and the real result. Committed — so no
  conversation quotes, personal data, or secrets.
- **The stream's log** — append the final `## State` (outcome `done` | `reverted` |
  `wip`, merged SHA or tombstone tag) to YOUR session log in
  `$(git rev-parse --git-common-dir)/the-works/<feature-id>/`, make sure `## Decisions
  (pending promotion)` carries every ruling not yet in `docs/decisions.md`, then
  `touch` the stream's `_closed` marker. The ingester (parent — or this session
  itself when top-level) promotes decisions/TODO and deletes the directory.

## Close worktree and delete the branch

Once the squash, tag, and integrity check have all passed, remove the worktree and delete the branch ref. The
`archive/<feature-id>` tag is the tombstone — it keeps every commit on the branch reachable, so the ref is redundant
and `git branch` only ever shows live work.

```sh
git worktree remove .claude/worktrees/<feature-id>
git branch -D f/<feature-id>
```

Order matters: the worktree must be removed *before* deleting the branch — a worktree still holding the branch
checked out blocks the ref deletion. After this step the source repo is fully clean. (If the integrity check above
failed, do NOT delete the branch — fix the squash first.)

## Return to the parent (remind the operator)

The close is done, the stream is marked closed. Switching sessions is operator-driven and the
parent only ingests when it is foregrounded, so the final act is a reminder — not an
action you can take:

> Closed. Run `/resume "<project>"` (or `orch`) to return — the parent will
> ingest this handover automatically.

This applies to both the success and cancellation paths.

## Abandoned and no-content closes (the empty-squash variant)

There is no separate cancellation procedure. A workflow that carries no code to `main` — an abandoned experiment
(changes deliberately not carried) or a no-content task (audit/surfacing that produced no changes) — closes through
the SAME steps as any other: documentation, clean tree, marker tag, squash, integrity verify, handover, worktree
removal, branch deletion. The only difference is that the squash commit is **empty** — stage nothing and use
`--allow-empty` in place of `git merge --squash`:

```sh
git checkout main
git commit --allow-empty -F <message-file>   # same message template as Merge squash above
```

- **Abandoned experiment** → `💩` gitmoji; body records what was tried, what blocked it, that the content is not
  carried over, and anything reusable elsewhere.
- **No-content task** → the gitmoji that fits the work; body describes what was done.

The branch's real commits stay reachable under `archive/<feature-id>` exactly as in a full-carry close, so the
abandoned/empty work is discoverable via the tag — not via a lingering `f/*` ref. The integrity check's empty-close
arm (squash tree == parent tree) covers this; the branch is then tagged and deleted like any other close.

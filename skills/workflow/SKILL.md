---
name: workflow
description: MUST be read before starting any task, plan, or coding work. Defines branch rules, worktree setup, and the testing + approval gates. When work is finished (the agent prompts the user for MAKE IT SO) or abandoned, the close is executed via the workflow-complete skill. No work begins without following this.
roles: [process/workflow]
tracked: true
metadata:
  tags: [ git, workflow, start, begin, task, plan, branch, finish, complete, gate, approval ]
  share: github
---

# Intent (Workflow)

Any task, plan, workstream, or other set of tasks a coding agent executes sequentially for the user is called a workflow
and must follow those instructions.

## Checklist

The whole workflow must be followed, you must complete all these steps.

Workflow Start:

- [ ] Closed workstreams ingested if announced (`_closed` under `.git/the-works/*/`): promote → archive — see the `handover` skill
- [ ] Own session log created in `.git/the-works/<feature-id>/` (`handover` skill), rolled as work progresses
- [ ] Working tree resolved with user
- [ ] Skills synchronized
- [ ] Git commit format understood
- [ ] Worktree created at `.claude/worktrees/<feature-id>` with anchor commit

Workflow Completion — executed via the `workflow-complete` skill, loaded on `MAKE IT SO` or abandonment:

- [ ] Completed testing
- [ ] User approval received (`MAKE IT SO`)
- [ ] Updated required documentation
- [ ] Tree cleaned
- [ ] Created marker tag
- [ ] Merged squash
- [ ] Verified integrity
- [ ] Pushed to origin (commits + `archive/` tag + notes)
- [ ] Worktree removed and branch ref deleted (archive tag is the tombstone)
- [ ] Workstream log closed for the gardener (final `## State`, `_closed` marker)

## Rules

- Any work MUST follow these rules unless user override
- work MUST NOT start writing code until all conditions in workflow start have been executed

# Workflow start

A workflow is called differently in different agents: plans, tasks, workstreams, or others. They are all synonyms.

As soon as the user indicates the start of a new workflow, the workflow has started and you must follow the rules of the
workflow start immediately.

- work never starts on a dirty tree. Ask the user for confirmation to stash dirty files, do a WIP git commit, or treat
  the current state as a completed workflow and end it before starting the new one.
- all work MUST happen in a dedicated `git worktree`, on a feature branch named `f/<feature-id>`. Branch state lives
  in the worktree's HEAD, so concurrent agents working in the source repo cannot move it under you.
- a feature branch MUST ONLY branch from the `main` branch, never from another feature branch.
- Merge commits during a workflow are forbidden, unless overruled by the user.
- A workflow always closes the same way: tag `archive/<feature-id>` on the branch HEAD, squash-merge to `main`,
  then DELETE the branch ref. The `archive/` tag is the permanent tombstone — it keeps every commit on the branch
  reachable, so the ref is redundant and `git branch` only ever shows live work. Abandoning an experiment or closing
  a no-content task is the SAME close with an empty squash commit (see the `workflow-complete` skill), never a
  separate "keep the branch" path.
- Branch deletion happens ONLY as the final step of a close, after the `archive/` tag exists. An `f/*` branch with
  NO `archive/` tag is open work — actively in progress OR suspended ("we'll see later", priorities switched, no
  `MAKE IT SO` yet) — and is NEVER deleted; it persists untouched until its own eventual close. Absence of the tag
  is the signal: untagged = open/suspended → preserve; tagged = closed → already deleted at that close. No process
  (board reconciliation included) deletes an untagged branch.
- Feature branches are required. The user MAY explicitly override for a given workflow to allow direct commits on
  `main` (or another non-`f/` branch). Absent that override, the feature-branch rule is absolute — but for a task
  the agent judges micro, it PROPOSES that override up front (see Micro-task path below) instead of waiting for
  the operator to remember it.
- No work goes uncommitted. If work was done — even work that leaves no file changes to record (investigation,
  configuration applied elsewhere, a manual action, a decision reached, a dependency verified) — it is STILL
  captured by a commit that describes it, using an empty commit (`git commit --allow-empty`). The absence of a
  diff is never a reason to leave work unrecorded in history; the commit message IS the record.

## Workflow Preparation

As soon as a user indicates wanting to start a workflow:

- **No feature named (e.g. bare `/workflow`):** the agent reads the board
  (`docs/TODO.md` slim index; sidecars in `docs/TODO.md.d/`) and proposes the next
  task to pick up — highest priority, unblocked, respecting documented order/deps —
  then CONFIRMS with the operator before proceeding. The operator may choose a
  different task. The chosen task's `{#id}` becomes the `<feature-id>`.
- Discuss the feature with the operator: scope, intent, constraints, recovery plan. The agent MUST NOT
  generate a feature-id, create a worktree, or write code before this discussion has happened.
- From the discussion, generate a concise, kebab-case `<feature-id>` (e.g., `add-login-feature`,
  `fix-payment-bug`). The agent proposes it; the operator may correct.
- Create a worktree off the head of local `main`. `git fetch` is best-effort — any error is ignored. If
  `origin/main` is ahead of local `main`, local `main` is fast-forwarded to `origin/main` first, so the
  worktree always branches from the new head of local `main`.

  ```sh
  git -C <source-repo> fetch --all || true
  git -C <source-repo> fetch . origin/main:main 2>/dev/null || true
  git -C <source-repo> worktree add .claude/worktrees/<feature-id> -b f/<feature-id> main
  ```

  The second `fetch` fast-forwards local `main` from `origin/main` when ahead; it is a no-op when local
  `main` is current or `origin/main` was not fetched. Errors from either fetch are ignored. All
  subsequent work in this workflow happens inside `.claude/worktrees/<feature-id>`. The worktree pins HEAD to
  your branch: other agents working in the source repo cannot accidentally move it.

- Synchronize the skills using `kauk sync --status` (report any drift to the operator; `kauk sync`
  on their go — see the `kauk` skill). Any error from the sync is ignored; the workflow proceeds regardless.

- Create an anchor commit describing the intent of the workflow, with a `🎉` gitmoji and a `Base:`
  trailer containing the SHA of the commit the branch was created from. This commit is the anchor for
  the branch and the starting point for all future work in this workflow.

## Micro-task path

The full machinery (worktree, anchor, archive tag, squash, handover) exists for work
with scope; a one-commit triviality earns none of it. When a task looks micro — the
agent judges it a single commit's worth, with no design choice to make and no
meaningful testing question (a typo, a prose fix, a one-line config value) — the
agent OFFERS, before creating anything: *"this is micro — direct commit on `main`
instead of a full workflow?"* The operator's acceptance IS the direct-commit
override; the agent never self-selects this path.

On acceptance:

- No worktree, no branch, no anchor, no tag, no squash, no handover. One
  properly-formatted commit straight on `main` (`git-commit` skill; the commit
  carries `Branch: main` — sanctioned for micro-task commits only).
- The close gate collapses to what actually happened: almost always nothing beyond
  the diff; a decision, if one was somehow made, is still appended.
- Push behaviour is unchanged.

**Promotion** — the moment a micro-task grows (a second concern appears, a test is
warranted, a choice surfaces), the agent STOPS and promotes it to a real workflow:
worktree off the current `main`, full machinery from there. A micro-commit already
landed stays on `main` as the trivial fix it was; the grown scope starts fresh.

# Finishing a workflow

When the work is finished — whether **you judge it complete** or the **user calls it
complete** — the workflow does not close silently. Two gates come first, in this
order; neither may be self-approved.

If you believe the work is done, do NOT proceed on your own: run the Testing gate,
then present the approval summary below and explicitly ask the user to reply
`MAKE IT SO`. The close begins only when the user has approved with that exact
phrase.

**On `MAKE IT SO` (approved) or a decision to abandon, load and follow the
`workflow-complete` skill** — it carries the entire close procedure (documentation,
clean tree, marker tag, squash-merge, integrity verify, worktree removal, the
mandatory handover write, and cancellation).

## Testing

Testing is the agreed method, between user and model, of ensuring a feature is complete and behaves as the workflow
described. The model and user must agree on a methodology appropriate to the change, and the model must have run it
and reported the results before the workflow can end.

Examples — pick what fits the change:

- Unit tests for new or modified logic
- Integration tests for cross-component behaviour or external boundaries
- Manual testing — a run-through to verify the workflow's functionality, which need not be committed (a transcript,
  screenshot, or described outcome is enough)

The model is encouraged to propose the most appropriate test for the feature, rather than wait to be asked. Once the
user agrees on the methodology, the model may carry it out autonomously instead of re-asking at each step.

## ⛔ User approval gate

STOP. The workflow MUST NOT proceed past this point without explicit user approval.

Provide a single concise summary, then wait for the user to reply with `MAKE IT SO`. Do NOT begin documentation
updates, tag creation, merge, or branch cleanup until the user has typed that exact phrase. "Looks good", "thanks",
or a thumbs-up is NOT approval.

The summary MUST:

- Fit on roughly one screen — bullet points, not prose. Don't re-narrate the diff.
- Cover every change against the agreed workflow:
  - Features implemented as agreed
  - Features modified, descoped, or skipped — with the reason
  - Shortcuts taken: mocks, hardcoded values, suppressed errors, disabled checks, skipped validation, TODOs left in
    code
  - Decisions made without consulting the user
  - Anything in the diff that does not match the workflow's stated intent
- Disclose problems encountered: failed approaches, dead ends, partial fixes
- State honestly what was NOT tested or what testing was skipped
- Propose the squash title for the merge step, so the user can approve it now

The model MUST NOT:

- Claim a feature is complete when it is partially implemented
- Hide shortcuts behind euphemisms ("simplified", "streamlined", "for now", "minimal version")
- Omit changes that fell outside the agreed workflow
- Wait for the user to ask about a known issue — surface it proactively

# TODO intake

When the operator adds a task ("add this todo …"), the agent does NOT append it
verbatim. It rewires it into the existing structure:

1. **Place it** on the board — a badge+title line in `docs/TODO.md` under its
   functionality heading, prose in the sidecar `docs/TODO.md.d/<id>.md` — in the
   canonical format (`AGENTS.files.md` §TODO + §Sidecar).
2. **Fold, don't duplicate** — if an existing task already covers it, add it there
   (a `feature` subtask checkbox, or a note) instead of creating a near-duplicate.
3. **Link** related tasks via edges on the board line (`⊘<id>` blocked-by, `~<id>` related).
4. **Confirm** the placement (group + whether folded or new) with the operator.

The operator states intent; the agent owns where it lands and how it connects.

Metadata are cheap, overridable hints, not contracts (Decision-047):

- **`created_during`** — always set to the current feature-id; it is the free, automatic
  "attached to the work I'm doing now" link, no judgement needed.
- **`size: s|m|b`** — stamp only when the task is *born during current work* (a free
  byproduct of already-loaded context); coarse buckets, never hours. Omit for cold/idea
  captures — the gardener sizes those on demand at triage.
- **`blocked_by`** — only for a true ordering gate; use a soft `parent`/related ref for
  mere association. A durable "do A then B" becomes a `blocked_by` link; a mere chosen
  order stays session-only (gardener's `MOOD.md`).

Never block intake on getting these right — approximate-and-free beats precise-and-slow.

# Decisions confidence (staleness)

Decisions read old→new (per `AGENTS.files.md` §Decisions) are not equally trustworthy: a
decision's confidence decays with age and with how much has changed since.

- Before relying on a decision to justify doing — or skipping — work, the agent
  weighs its age. The older it is, the lower the bar to surface it.
- For an old or pre-dating-significant-change decision, the agent treats it as
  PROVISIONAL and re-confirms with the operator ("Decision-NNN (<date>) says X — is
  that still current?") rather than assuming it holds.
- Recent decisions are taken as current without ceremony. This complements the
  supersession + idiosyncrasy rules in `AGENTS.files.md` §Decisions; it does not replace them.

The age judgement relies on the timestamped decision heading format
(`## [YYYY-MM-DD HH:MM TZ] Decision-NNN: <Title>`), defined in `AGENTS.files.md` §Decisions.

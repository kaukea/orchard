---
name: git-workflow
description: Use when opening or closing a branch-based workflow — the Branch trailer, main's immutability, and where the MAKE IT SO / squash-merge gates live. Loaded by roles that open or close workflows (landscaper, beekeeper, groundskeeper, and the cloud equivalents architect-cloud, housekeeper-cloud, orchestrator-cloud); roles that only commit along the way load the `writing-commits` skill instead.
categories: [process/orchard]
dependencies-skills: [writing-commits]
share: github
compatibility: Requires git
metadata:
  tags: [branch-trailer, main-immutable, squash-merge-gate, make-it-so, workflow-branch]
---

# git workflow mechanics (MUST)

Companion to the `writing-commits` skill (commit format and hygiene, generic to every repo) — read
both when you open or close a branch-based workflow.

## Branch trailer (MUST)

- `Branch:` is required on every commit and is the current feature branch — never
  `main`, with one exception: an operator-accepted micro-task commit (`organising-work` skill
  → Micro-task path) carries `Branch: main`.
- Add it beneath the `writing-commits` skill's format template, after `Agent:`.

## `main` is immutable (MUST)

- `main` is immutable: no amend, no rebase, no rewrite. Tags and notes are SHA-anchored
  and would be lost.
- **Feature branches are mutable** for trivial fixups only (typo, prose, a missing
  semicolon). Larger changes get a new commit.
- **Verify the current branch before staging.** If the workflow requires a feature
  branch and you're not on `f/…`, stop.

## Gating and close

- **MAKE IT SO** is the build-start gate that turns an agreed plan into edits — see the
  `organising-work` skill.
- **Squash-merge mechanics** — the close commit format, trailers, and tagging — see the
  `workflow-complete` skill.

---
name: git
description: Use when committing files to git. Generic hygiene — format, gitmoji, scope discipline — that applies to every commit, in every repo or process.
categories: [development]
share: github
compatibility: Requires git
metadata:
  tags: [git, commit, gitmoji, scope-discipline, batch-pushes]
---

# git commits (MUST)

## Checklist

- [ ] Tests run if any exist
- [ ] Format applied (see below)
- [ ] Subject ≤ 52 characters
- [ ] Body wrapped at 72 characters
- [ ] `Agent:` trailer present (add `Branch:` too where the `git-workflow` skill applies)
- [ ] Scope rules followed

Commit one logical change at a time. The user may override any rule.

## Scope discipline (MUST)

- **Touch only what you modified.** External changes during a workflow (user edits, tool output, parallel processes) are not yours by default — do not stage, commit, revert, or delete them.
- **Related external changes:** inspect, pre-stage what looks related, ask once grouped, positive default: *"Include these N because <reason>?"*
- **Unrelated external changes:** ask once, combined: *"These N files look unrelated to this workflow — confirm? If so, once the merge commit has landed, should I commit them on main, open a new feature branch, or will you handle it yourself?"*
- **User edits to `.md` files** are committed separately from code changes.
- **Stage specific paths:** `git add <file>`, never `git add -A` / `git add .`.
- **Verify the current branch before staging.** `git branch --show-current` or read `git status`.
- **Surface merge conflicts; do not auto-resolve.** Show the conflicting hunks, propose a resolution, wait for confirmation.
- **Test results are not fabricated.** The `✅ x/y` (or 🚫) line reflects a run you actually performed in this session. If you didn't run tests, omit the line.
- **No destructive operations without explicit user consent:** `reset --hard`, `--force` / `--force-with-lease`, `--no-verify`, `branch -D <unmerged>`, `checkout -- <dirty>`, `push`, `rebase`, `cherry-pick`.
- **Batch pushes (MUST).** origin is wired to workflows: never push per-change during a discussing/refining round — commit locally and push ONCE when the round settles, or when the push is itself the intended signal a watcher waits on. Issue/PR comments are the same trigger class — one consolidated comment per round (Decision-033).

## Style

- `<subject>` describes the change in imperative form, e.g. "Encapsulate class X". Avoid generic opener verbs like "add".
- `<subject>` starts with a capital letter and never ends with punctuation.
- Both `<subject>` and the body explain the **WHY**, not the HOW. Keep technical detail short and only when necessary. No `HOW:` or other prefixes — the body is explanation only.
- The body is prose for a stranger: full sentences, no session shorthand — the `writing-prose` skill applies to it, and to PR descriptions and issue comments alike.

## Format

```
<gitmoji> <subject>

<test-emoji> x/y

<body>

Agent: <model>
```

- `<subject>` line ≤ 52 characters.
- `<model>` in `Agent:` is the LLM model name and version.
- `<gitmoji>` is the closest match in https://gitmoji.dev, in Unicode.
- `<test-emoji>` is ✅ (passed) or 🚫 (failed), followed by `<x>` succeeding and `<y>` total. If no tests were run, omit the line entirely.
- Body lines wrap at 72 characters.
- A process that runs branch-based workflows adds a `Branch:` trailer on top of this
  format — see the `git-workflow` skill for that rule; it is not part of generic hygiene.

## Repo ownership = push rights (parked 2026-08-12, until broadcast)

Whether a repo counts as the operator's own is a question about *rights*, not
about the account named in the origin URL: he maintains repos under foreign
orgs, and a clone under a familiar-looking owner proves nothing.

- Authoritative check (authenticated `gh`):
  `gh repo view OWNER/REPO --json viewerPermission --jq .viewerPermission`
- `ADMIN` / `MAINTAIN` / `WRITE` → can push → his.
- `READ` / `TRIAGE` → someone else's, however hard it is worked in.
- No remote at all → local work → his.
- Non-github.com remotes: gh cannot answer — fall back to an explicit owner
  list, never to name-guessing.
- Never on a hot path: it is a network call. Cache the verdicts and refresh
  off-thread; `seb.tmux/sebdeck/rights.py` is the reference implementation
  (day-long cache, background refresh, ranking reads only the cache).

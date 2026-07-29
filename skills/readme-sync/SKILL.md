---
name: readme-sync
description: MUST be read at workflow completion when the work added or changed user-facing behaviour, CLI flags, build steps, or required developer tooling. Checks README.md is aligned with the current feature set, usage examples, and developer instructions before the squash.
roles: [process/workflow]
metadata:
  share: github
  tags: [readme, documentation, doc-sync, pre-squash, user-facing, developer-tooling]
---

# Intent (README sync)

`README.md` has two audiences, in this order of priority: **users** deciding whether to
use the tool and finding their first usage example, then **developers** setting the
project up to contribute. The README is allowed to diverge from the implementation
between workflows — this skill is the catch-up point, bringing it back in sync before
the squash.

## Checklist

- [ ] Trigger categories that fired during the workflow identified
- [ ] Update-playbook action applied for each fired trigger
- [ ] README structure still follows: title → hook → how-it-works → config → developer
- [ ] No false claims, no references to retired tools, no broken examples
- [ ] README updates committed on the feature branch (squash carries them to `main`)
- [ ] README touch noted in the squash body

## When to run

Trigger at workflow end — after the user-approval gate, before the squash — if the workflow changed any of:

- **The pitch** — what the tool is, why it exists, what it solves.
- **User-visible features** — new capabilities, removed capabilities, changed defaults.
- **Usage examples** — CLI commands, sample inputs/outputs, sample configs.
- **Required tooling** — new build dependency, new test runner, new external service.
- **Build / install / run steps** — anything a fresh contributor would follow.

If the workflow was purely internal (refactor, test-only changes, bug fix with no behavioural change), this skill is a no-op. Record that judgement in the workflow summary and move on.

## Voice

The README is marketing copy at the top and recipe instructions at the bottom — not technical reference. Lead with the hook, not the architecture. The reader should feel pitched to, not lectured at.

- **Hook** — open with the pain or the wish the tool answers. *"Tired of managing skills across multiple repositories?"* beats *"This tool is a CLI that synchronises skill files"*.
- **Tagline** — one line that names the tool and the promise. *"`.ai` is the fastest, smallest executable to deal with all this mess."*
- **Show, don't describe** — every claim earns its place by being followed quickly by a concrete example. If you can't demonstrate the point in three lines of shell, the section is probably too abstract.

Emojis are welcome where they earn their place — a marker that helps the eye land, not decoration. Don't sprinkle them.

## Structure of README.md

Order matters. Users read top-down and stop when they have what they came for.

1. **Title + tagline** — the tool name and the promise, in one line. (Logo lands here once it exists.)
2. **The hook + value pitch** — the marketing intro: what problem this solves, why a reader should care.
3. **How it works** — concrete, copy-pasteable invocations. Happy path first. Initialize → edit → sync, that shape.
4. **Configuration / advanced usage** — flags, options, less common flows.
5. **Developer section** — at the end. Required tools, install, build, test, contribution notes.

The developer section sits at the bottom because users outnumber contributors. By the time a casual reader has scrolled past the usage examples, they have already gotten what brought them in.

## Update playbook

For each trigger that applied to the completed workflow:

- **Pitch changed** → rewrite the intro so it still describes the current tool.
- **New feature** → add a "How it works" example; if the list is getting long, prune the least illustrative one.
- **Removed feature** → delete its example; if it was prominent, note the removal briefly.
- **CLI / config surface changed** → update every example that references the changed surface.
- **New tool or build step** → extend the developer section's prerequisites and steps.
- **Build pipeline reshape** → rewrite the developer section's build / test / run instructions.

## Diverging is fine, lying isn't

The README may legitimately omit experimental features, internal-only flags, or work in progress.

It must NOT:

- Claim something works that doesn't.
- Reference a tool no longer in the pipeline.
- Show an example that fails verbatim.

If keeping a section honest would require disclosing too much, remove the section instead.

## Workflow integration

The `workflow` skill's Documentation Update step lists this skill. When a workflow's user-approval-gate summary mentions any trigger category above:

1. Run this skill's checklist as the final pre-squash step.
2. Commit README updates on the feature branch so the squash carries them to `main`.
3. Note the README touch in the squash body.

## Worked example

What "good" looks like, in the voice this skill is asking for:

````markdown
# .ai

> Skills, agents, and shared rules — across every repository, in sync.

**Tired of managing skills across multiple repositories?** `.ai` is the
fastest, smallest executable to deal with all this mess. One binary,
one folder per repo, one command to keep them aligned.

## How it works

Initialize a repo:

```sh
dotai init
```

Edit a skill — they're just plain markdown:

```sh
$EDITOR .ai/skills/workflow/SKILL.md
```

Sync your changes everywhere:

```sh
dotai sync
```

That's the whole flow.

## Configuration

…

## For contributors

Build from source: …
Run the tests: …
````

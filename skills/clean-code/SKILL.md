---
name: clean-code
description: Use for any code change in any language. Boundaries that keep agents from writing hundred-line spaghetti — short methods, self-descriptive code with no comments, composition over imperative chaining, DRY, SOLID, composable functional style.
categories: [development]
metadata:
  tags: [ short-methods, no-comments, composition, dry, solid-principles, self-descriptive-code, functional-style ]
  share: github
---

# Clean code

Boundaries to keep agents from doing what they do best: spaghetti, one hundred lines
at a time. Per-language skills (`coding-*`) add stack specifics on top.

## Checklist

- [ ] Methods are short — one responsibility each
- [ ] No comments — the code is self-descriptive (names carry the intent)
- [ ] Components compose behind a shared interface instead of imperatively calling the next one
- [ ] No duplication (DRY) — extracted, not copy-pasted
- [ ] SOLID respected — especially single responsibility and dependency direction
- [ ] Functional style where it fits — composable, not dogmatically pure

## Rules

- **Short methods.** A method that needs scrolling is several methods.
- **No comments; self-descriptive code.** If a comment feels needed, rename or
  restructure until it isn't. (Constraint-comments the code cannot express are the
  rare exception.)
- **Prefer composition sharing the same interface** over one component imperatively
  calling the next — pipelines of interchangeable parts, not call-chains welded
  together.
- **DRY.** The second copy is the moment to extract.
- **SOLID** — see `AGENTS.shared.md`'s `## Software principles`; binds every edit,
  not just new design.
- **Functional style — composable, not pure.** Favour small transformations that
  chain; don't contort the code for purity's sake.

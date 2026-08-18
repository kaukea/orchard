---
name: enforcing-rules
description: MUST be read at session start, before any other action including replying to the user. Enforces loading of AGENTS.shared.md (generic shared rules) and AGENTS.md (project-specific rules) into context before the agent does anything else in a session.
categories: [general]
tracked: true
share: github
metadata:
  tags: [agents-md, agents-shared-md, session-start, load-first, bootstrap]
---

# Intent (Read AGENTS files)

At session start, two files at the repository root carry the rules the agent must obey:

- `AGENTS.shared.md` — generic instructions applying to this repository and others using the same skills. Assumed present at the repository root.
- `AGENTS.md` — instructions specific to this repository. Created if missing.

## Checklist

- [ ] `AGENTS.shared.md` loaded
- [ ] `AGENTS.md` loaded (created first if missing)
- [ ] No other action taken (including replying to the user) before both files have been loaded

## Rule

Before any other action in a session — including replying to the user's first message, listing files, reading other documentation, running any tool — both files must be loaded.

If `AGENTS.md` is missing, the agent creates it at the repository root with this stub:

```markdown
# <project-name>

This file describes project-specific instructions for AI agents working on this repository.

For instructions that apply across multiple projects, see `AGENTS.shared.md`.
```

`<project-name>` is the basename of the repository's root directory (`basename $(git rev-parse --show-toplevel)`). The agent then loads the newly-created file and proceeds.

This rule is non-negotiable. The user may override per-session by stating so explicitly.

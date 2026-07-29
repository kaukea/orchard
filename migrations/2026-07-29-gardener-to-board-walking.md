# 2026-07-29 — `skills/gardener` renamed to `skills/board-walking`

The `gardener` skill is renamed to `board-walking`: a skill's name must describe
the reusable behaviour it provides, never duplicate an agent/role name, and
`skills/gardener` duplicated the `gardener` agent's own name. Content is
unchanged — only the directory, `name:` field, and `description` moved. Any
repo-local reference to the skill by its old id needs the same rename.
Consuming repos drop any stale `gardener` laydown so only `board-walking`
(laid fresh by `kauk sync`) remains.

## Detect → convert

```sh
# Remove a laid-down gardener skill ONLY when it is a symlink whose target is
# gone (dangling after the rename). A real directory (copy/local mode) is left
# untouched for the judgement step below — it may hold local edits.
d=".claude/skills/gardener"
if [ -L "$d" ] && [ ! -e "$d" ]; then rm "$d"; fi
true
```

## Then: reconcile a copy/local install (judgement)

If `.claude/skills/gardener` still exists as a real directory (copy or `local`
mode in `.ai.toml`), it is a pre-rename local variant. Move any local edits
into `.claude/skills/board-walking` (laid by `kauk sync`), then remove the old
directory. Update any repo-local reference to the `gardener` skill id —
a path, a `Skill` tool invocation, a cross-reference from another SKILL.md, a
mention in this repo's own README skill listing — to `board-walking`.
Do NOT touch a reference to the `gardener` AGENT/role (e.g. `agents/gardener.md`,
"the gardener agent"): the role keeps its name; only the skill moved.

## Verify

No `.claude/skills/gardener` remains (neither a dangling symlink nor, after
reconciliation, a real directory); the board-walk/triage/hand-off doctrine is
present as `.claude/skills/board-walking`.

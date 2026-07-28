# 2026-07-29 — `git-commit` skill split into `git` + `git-workflow`

The `git-commit` skill is removed, replaced by two skills: `git` (generic
commit hygiene — format, gitmoji, scope discipline, applies to every commit)
and `git-workflow` (branch/workflow mechanics — the `Branch:` trailer, main's
immutability, and pointers to the MAKE IT SO / squash-merge gates). Consuming
repos drop any stale `git-commit` laydown so only `git` and `git-workflow`
(both laid fresh by `kauk sync`) remain. Link-mode installs are already
pruned by `kauk sync` (its target is gone after the split); this migration
cleans a stale symlink for older kauk versions and flags the copy/local case
for judgement — a real directory may carry local edits and is never
clobbered.

## Detect → convert

```sh
# Remove a laid-down git-commit ONLY when it is a symlink whose target is gone
# (dangling after the package split). A real directory (copy/local mode) is left
# untouched for the judgement step below — it may hold local edits.
d=".claude/skills/git-commit"
if [ -L "$d" ] && [ ! -e "$d" ]; then rm "$d"; fi
true
```

## Then: reconcile a copy/local install (judgement)

If `.claude/skills/git-commit` still exists as a real directory (copy or
`local` mode in `.ai.toml`), it is a pre-split local variant. Move any local
edits into `.claude/skills/git` or `.claude/skills/git-workflow` (both laid
by `kauk sync`) depending on which half of the content they belong to, then
remove the old directory. Update any repo-local reference to the
`git-commit` skill name to `git` or `git-workflow`, depending on whether the
reference relied on generic commit hygiene or on branch/workflow mechanics.

## Verify

No `.claude/skills/git-commit` remains (neither a dangling symlink nor,
after reconciliation, a real directory); commit hygiene is present as
`.claude/skills/git` and branch/workflow mechanics as
`.claude/skills/git-workflow`.

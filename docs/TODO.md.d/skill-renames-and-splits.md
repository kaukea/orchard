- created: 2026-07-17
- created_by: opus-4.8

## Blockers
- ~~None, but must land before or with `role-dag-frontmatter` — the rename changes the
  keystone file that defines the frontmatter contract.~~ Resolved: the rename was
  executed inside f/role-dag-frontmatter (2026-07-20, Decision-021).

## Questions
- `git-commit` split shape: two skills (`git` in `general` + `git-workflow` in
  `process/workflow`), or one skill whose sections are role-tagged? Two skills is the
  only shape the DAG can actually deliver on — a repo declining `process/workflow` must
  not receive the `Branch:` trailer rule — but it costs a second file and a second
  `description` in every session that takes both.
- Any other skill carrying the same double life? `readme-sync` reads workflow-only
  ("MUST be read at workflow completion") but its content is generic README guidance.

## Findings
- `doing-skills` → `authoring-skills`, in `general` (Decision-003). The rename is not
  cosmetic: it is the file that defines the frontmatter contract every other skill
  follows, so it is the keystone for the whole programme.
- `git-commit` genuinely carries two audiences: generic hygiene (gitmoji, subject ≤52,
  body wrap at 72, scope discipline, no-force-without-consent) and process-specific
  rules (`Branch:` trailer required and never `main`, main-is-immutable, feature
  branches mutable, MAKE IT SO gating). The second set is meaningless in a repo running
  a different process.
- The `Branch: main` conflict is live evidence: `git-commit` says `Branch:` is "never
  `main`", while the gardener's procedural-on-main carve-out requires exactly
  `Branch: main` for board commits — and does so in every repo, not just orchids. The
  split is where that contradiction gets resolved; it is currently unresolved in the
  package and worked around by convention.
- Renames must not silently break consumers: kauk `prune_links` garbage-collects
  dangling symlinks into `.ai/repositories/`, so a renamed skill disappears from
  consuming repos on next sync. Check whether anything references `doing-skills` by
  name (the `Skill` tool, other SKILL.md cross-references, `.ai.toml` entries).

## Proposal
1. ~~Rename `skills/doing-skills/` → `skills/authoring-skills/`; update `manifest.conf`
   and every cross-reference.~~ Done in f/role-dag-frontmatter (2026-07-20,
   Decision-021); lands with its squash-merge.
2. Split `git-commit` per the agreed shape; resolve the `Branch: main` contradiction
   explicitly in whichever half owns it.
3. Sweep for other cross-references broken by the renames.

## Testing
`kauk sync` on a scratch consuming repo: renamed skills appear under the new name, old
symlinks are pruned, no dangling links remain, no skill references a name that no longer
exists (grep the corpus for old ids). The `Branch:` rule reads unambiguously in both
halves — verified by a reader who has not seen this conversation.

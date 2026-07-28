- created: 2026-07-17
- created_by: opus-4.8

## Blockers
- ~~None, but must land before or with `role-dag-frontmatter` — the rename changes the
  keystone file that defines the frontmatter contract.~~ Resolved: the rename was
  executed inside f/role-dag-frontmatter (2026-07-20, Decision-021).
- Sequencing note (2026-07-29 bloom round): this task and `skill-terseness-pass` are
  being bloomed together as part of an operator-driven token-load reduction pass across
  the repo. `skill-terseness-pass` already declares `⊘skill-renames-and-splits` on the
  board (it runs after this one) — this split should land first so the terseness pass
  edits the post-split `git`/`git-workflow` files rather than the pre-split
  `git-commit`, avoiding rework.

## Questions

Both resolved — operator ruling, 2026-07-29 bloom round:

- ~~`git-commit` split shape~~ **Resolved: two complementary skills.** `git`
  (generic hygiene — gitmoji, subject ≤52, body wrap, scope discipline,
  no-force-without-consent) and `git-workflow` (`Branch:` trailer, main-immutable,
  MAKE IT SO gating, the squash-merge mechanics). Operator's own framing: the two
  are complementary, not overlapping. **Role-scoping refinement (operator):** only
  the roles that actually OPEN (start a branch/workflow) or CLOSE (squash-merge)
  need to understand the squash-merge machinery — `git-workflow` is pulled in by
  `landscaper`, `supervisor`, `groundskeeper` (and the cloud equivalents), not by
  every agent that merely commits along the way (`sower`, `groomer`, `courier` load
  `git` only). This is itself a token saving beyond the original split: most agents
  in the fleet never need `git-workflow` at all.
- ~~Other double-life skills~~ **Resolved: out of scope here.** Stays scoped to
  `git-commit`; a full-corpus double-life audit is `skill-terseness-pass`'s job,
  not this task's.

## Sizing

Operator ruling, 2026-07-29: sonnet-tier, "lowest acceptable model for each job" —
mechanical rename/split/grep work. Launch at `claude-sonnet-5`, effort `medium`
(downsized from the landscaper's default `claude-opus-5`/`xhigh`).

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
3. Update each agent's frontmatter/body skill references so only `landscaper`,
   `supervisor`, `groundskeeper` (and cloud equivalents `architect-cloud`,
   `housekeeper-cloud`, `orchestrator-cloud`) reference `git-workflow`; every other
   agent (`sower`, `groomer`, `courier`, `bloomer`, `gardener`) keeps `git` only.
4. Sweep for other cross-references broken by the renames.

## Testing
`kauk sync` on a scratch consuming repo: renamed skills appear under the new name, old
symlinks are pruned, no dangling links remain, no skill references a name that no longer
exists (grep the corpus for old ids). The `Branch:` rule reads unambiguously in both
halves — verified by a reader who has not seen this conversation.

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

**METHOD REPLACED 2026-07-29 by operator ruling (Decision-122): orchids publishes to
kauk and never vendors.** The original method below required `kauk sync` onto a scratch
consuming repo. That method is OBSOLETE, not merely unrunnable — it tested a vendoring
relationship that no longer exists, and `manifest.conf`'s absence (which made it
impossible to run) is the correct state rather than a defect to work around. A skill's
correctness in this repository is verified against this repository's own tree.

Agreed method:
1. **No dangling references.** Grep the whole tree for the old id `git-commit`: every hit
   is either the migration entry (which must mention it) or a deliberate historical
   reference. Zero live references to a skill file that no longer exists.
2. **Both halves resolve.** `skills/git/SKILL.md` and `skills/git-workflow/SKILL.md` each
   parse as valid frontmatter with `name` matching their directory.
3. **The `Branch:` contradiction is gone.** The rule appears in exactly one of the two
   halves, and reads unambiguously there — verified by a reader who has not seen this
   conversation. This was the substantive defect the split existed to resolve.
4. **Role-scoping holds** (the operator's refinement): only opening/closing roles
   reference `git-workflow`; `sower`, `groomer`, `courier`, `bloomer`, `gardener`
   reference `git` only.

~~`kauk sync` on a scratch consuming repo: renamed skills appear under the new name, old
symlinks are pruned, no dangling links remain, no skill references a name that no longer
exists (grep the corpus for old ids).~~ Struck per Decision-122.

- created: 2026-07-17
- created_by: opus-4.8

## Blockers
- Touches all 18 remaining files (26 → 18 after the 2026-07-29 forensic-domain
  deletion). `role-dag-frontmatter` is done. `skill-renames-and-splits` is being
  bloomed in parallel right now — still open, still same-files conflict risk.
  Sequence this one after it lands.

## Questions

Both resolved — operator ruling, 2026-07-29 bloom round:

- ~~Per-skill `description` budget?~~ **Resolved: judgement, not a hard byte
  cap.** A lint that *flags outliers for review* (>2× median) gets lintability
  without forcing a bad cut on a skill like `handover` whose length carries real
  trigger surface.
- ~~Frontmatter-only or body restructuring too?~~ **Resolved: WIDENED — body
  restructuring is in scope.** Operator overrode the frontmatter-only
  recommendation: this pass also cuts redundant/contradictory prose inside
  skill bodies (style, restatement of `AGENTS.shared.md`, section ordering),
  not just `description`/trigger text. Raises the difficulty from the original
  recommendation — sized accordingly below.
- **New requirement (operator): `metadata.tags` gets a real job.** Answers the
  dead-weight Finding below. Tags must be specific and short enough that a
  skill of interest can be located BY ITS TAGS ALONE — a working discovery
  index, not a placeholder. Part of this pass's frontmatter normalisation.

## Findings
- Re-measured 2026-07-29 against the current tree: 9 forensic-domain skills
  (`chain-of-custody`, `digital-signature`, `forensic-acquisition`, `icloud`,
  `machine-access`, `read-apfs`, `reverse-engineering-files`, `software-catalog`,
  `write-to-s3`) were deleted, dropping the corpus from 26 to **18 skills**.
  `description` now totals **5,758 b** (was 10,190 b across 26) — the deletion
  already did roughly half the byte-reduction work this task set out to do.
  Per-skill spread: 67 b (`history-rewrite`) to 676 b (`handover`), still ~10×
  with no rule behind it. The stale 26-skill/10,190 b figure this Finding replaces
  is recorded here for continuity, not carried forward as current.
- Conflicting advice is known to exist, not hypothesised: `git-commit` requires the
  `Branch:` trailer to be "never `main`", while the gardener's procedural-on-main
  carve-out requires `Branch: main`. Found 2026-07-17 while committing board work in
  this very repo. `skill-renames-and-splits` resolves this one; the pass should hunt
  for its siblings.
- The frontmatter contract itself is drifting: 26 `name`/`description`, 17 `metadata`,
  4 `share`, 4 `compatibility`, 3 `tracked`. `doing-skills` ships an unfilled
  placeholder (`tags: [ <grep-able trigger words> ]`) into the package.
- `metadata.tags` are consumed by nothing. Either give them a job or drop them — but
  decide, rather than leaving 17 skills carrying dead weight.

## Proposal
Per skill, in one pass: tighten `description` to its actual trigger, normalise
frontmatter to the (by then updated) `authoring-skills` contract, remove advice that
contradicts another skill or restates `AGENTS.shared.md`, and cut what the role DAG has
made redundant. Record each conflict found and its resolution — the conflicts are the
valuable output, not the byte count. **Widened (operator ruling):** also restructure
skill bodies where they carry redundant style/prose or restate `AGENTS.shared.md`
verbatim. **Tags (operator ruling):** rewrite every `metadata.tags` list so the skill
is locatable by its tags alone — specific enough to disambiguate from siblings, short
enough to stay cheap; drop tags that don't earn a place in that index.

## Sizing

Operator ruling, 2026-07-29: sonnet-tier, "lowest acceptable model for each job," same
principle as `skill-renames-and-splits`. Launch at `claude-sonnet-5`, effort `high`
(bumped from the initially-recommended `medium` — body restructuring across 18 files
plus a real tags pass is more judgement-heavy than a frontmatter-only sweep).

## Testing
Before/after `description` byte count per role node, reported honestly (a pass that
cuts nothing is a real result). Every conflict found is either resolved or raised as a
task. Spot-check: pick 3 skills and confirm an agent reading only the new text reaches
the same behaviour as the old — a skill that got terser but stopped firing is a
regression, not a win. New: pick 5 skills at random, and confirm each is findable from
its `metadata.tags` alone (no title, no description) by someone who knows what they're
looking for but not its name.

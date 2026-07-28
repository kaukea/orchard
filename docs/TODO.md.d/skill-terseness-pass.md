- created: 2026-07-17
- created_by: opus-4.8

## Blockers
- Touches all 18 remaining files (26 → 18 after the 2026-07-29 forensic-domain
  deletion). `role-dag-frontmatter` is done. `skill-renames-and-splits` is being
  bloomed in parallel right now — still open, still same-files conflict risk.
  Sequence this one after it lands.

## Questions
- Is there a per-skill `description` budget, or is terseness judged case by case? The
  spread is now 67 b (`history-rewrite`) to 676 b (`handover`) with no rule behind it.
  A budget is lintable; judgement is better prose.
  **Recommendation**: judgement, not a hard byte cap — `handover`'s length carries the
  protocol's trigger surface (session-start, close, cross-agent handoff) and a cap
  would force it to under-trigger; a lint that *flags outliers for review* (say, >2×
  median) gets the lintability without forcing a bad cut.
- Does "more effective" include restructuring a skill's body, or only its frontmatter
  and its trigger clarity? The bodies vary hugely in length and discipline.
  **Recommendation**: frontmatter/trigger clarity only for this pass. Body
  restructuring is a second, larger concern (style, redundancy with
  `AGENTS.shared.md`, section ordering per `authoring-skills`) and mixing it into a
  terseness pass risks scope creep across 18 files in one sitting. Split it into a
  follow-up task if the pass surfaces body-level problems worth fixing.

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
valuable output, not the byte count.

## Testing
Before/after `description` byte count per role node, reported honestly (a pass that
cuts nothing is a real result). Every conflict found is either resolved or raised as a
task. Spot-check: pick 3 skills and confirm an agent reading only the new text reaches
the same behaviour as the old — a skill that got terser but stopped firing is a
regression, not a win.

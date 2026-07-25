- created: 2026-07-17
- created_by: opus-4.8

## Blockers
- Touches all 26 files. Must not run concurrently with `role-dag-frontmatter` or
  `skill-renames-and-splits` — same files, guaranteed conflicts. Sequence it last.

## Questions
- Is there a per-skill `description` budget, or is terseness judged case by case? The
  spread is 80 b (`history-rewrite`) to 559 b (`forensic-acquisition`) with no rule
  behind it. A budget is lintable; judgement is better prose.
- Does "more effective" include restructuring a skill's body, or only its frontmatter
  and its trigger clarity? The bodies vary hugely in length and discipline.

## Findings
- The corpus has never had a quality pass. `description` totals 10,190 b across 26
  skills and every byte loads in every session; `forensic-acquisition` (559 b) is 7×
  `history-rewrite` (80 b) without being 7× the skill.
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

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
- **Skill-vs-agent-def duplication, found 2026-07-29 (operator-prompted dedupe
  check).** Two concrete pairs, beyond the git-commit/gardener-carve-out conflict
  above:
  - `skills/gardener` (2588 words) vs `agents/gardener.md` (4173 words) — the skill's
    own opening admits it: "repos with the role-agent layer: the gardener agent def
    governs session mechanics... this skill supplies board doctrine below." orchids
    HAS the agent layer, so most of the skill's content is restating what
    `agents/gardener.md` already carries. Not necessarily pure waste — other
    kauk-sync consumer repos without the agent layer may still need the full skill
    — confirm audience split before cutting.
  - `skills/workflow` (2152 words) + `skills/workflow-complete` (1590 words) vs
    `agents/landscaper.md` (3273 words) — landscaper is the sole real consumer of
    either skill and its own system prompt already restates branch rules, the
    testing/approval gates, and the close procedure inline. Same shape of question:
    does the agent-def defer to the skill (cut the inline restatement) or does the
    skill become a thin pointer (cut the skill body)?
  - General pattern worth checking while in the corpus: any skill whose sole
    trigger is "read by agent X" is a duplication candidate against agent X's own
    system prompt, not just against `AGENTS.shared.md`.
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
verbatim, OR restate content already carried in a consuming agent's own system prompt
(see the `skills/gardener` and `skills/workflow`+`skills/workflow-complete` pairs in
Findings) — resolve per-pair which side (skill or agent-def) stays authoritative and
which becomes a thin pointer, checking kauk-sync cross-repo audience before cutting a
skill some consumer repos may still need in full. **Tags (operator ruling):** rewrite every `metadata.tags` list so the skill
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

## Interrupted then RESUMED 2026-07-29 (parking reversed by the operator)

Operator order: *"kill that agent, delay till courier is done."* Its supervisor was
stopped; the landscaper was left alive, parked at its plan gate in tmux window
`orchids ▸ skill-terseness-pass`, worktree `.claude/worktrees/skill-terseness-pass`
on `f/skill-terseness-pass` at `a421c6c`. **Zero commits, clean tree — no edits were
made.** The branch and worktree are intact for resumption.

Where it stopped: at the plan gate, asking the operator the duplication-scope call for
`skills/gardener` vs `agents/gardener.md` and `skills/workflow` +
`skills/workflow-complete` vs `agents/landscaper.md` — which side of each pair stays
authoritative. Its dying supervisor also reported having checked sibling repositories on
disk (which the worktree-scoped explorers could not reach) and finding something
materially relevant to the cross-repo audience question; **that finding was not captured
before the stop and is lost unless the landscaper is resumed.**

Parking REVERSED minutes later — operator: *"let it run then, when finished ingest."* A
fresh supervisor was launched over the same live landscaper and worktree; the
`⊘bus-addressing` dependency is NOT applied. The landscaper still owes the operator an
answer at its plan gate before it builds.

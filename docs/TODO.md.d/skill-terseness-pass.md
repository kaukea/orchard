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

**Duplication-pair resolution — FROZEN (operator ruling, 2026-07-29 plan gate):** the
skill stays full/authoritative in both pairs; the consuming agent-def is what gets
thinned to defer to it, never the reverse — regardless of whether orchids is currently
the sole consumer (no cross-repo manifest exists to check against; this ruling is the
scope boundary, not a further audit). Additionally: `workflow`/`workflow-complete` are
NEVER folded into any single role's agent-def, permanently — the role that opens/closes
a workflow is expected to keep changing over time, so the split must survive who
currently happens to be the sole consumer. And: a skill's name must describe the
reusable behaviour it provides, never duplicate an agent/role name — `skills/gardener`
violates this (named identically to the `gardener` agent) and is renamed to
`skills/board-walking` (operator's own pick) as part of this pass; this is a rename of a
managed artifact, so it ships with a `migrations/` entry (see `migrations/2026-07-29-git-commit-split.md`
for the freshest same-shape precedent).

**Frozen build step list (landscaper plan phase, Decision-025):**
1. `skills/authoring-skills/SKILL.md` — add the tags-as-discovery-index guidance and the
   new skill-naming rule (no dep).
2–5. Per-skill frontmatter/terseness pass over the 15 "plain" skills (everything except
   `authoring-skills`, `gardener`, `workflow`, `workflow-complete`), batched ~4 per
   parallel sower (dep: 1).
6. Rename `skills/gardener` → `skills/board-walking`, sweep cross-references, ship the
   migration entry, thin `agents/gardener.md` to defer to the renamed skill (dep: 1).
7. Thin `agents/landscaper.md`'s restatement of `workflow`/`workflow-complete` content to
   defer to those skills — the skills themselves are left untouched in ownership (dep: 1).
8. Testing per the agreed method below, plus: zero dangling `gardener`-skill-id
   references, migration entry present (dep: 2–7).

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

### Result (2026-07-29, post-build)

- **Byte/tag audit** (mechanical, whole corpus, before → after): total `description`
  bytes 6,518B → 6,249B across 19 skills (18+`board-walking` replacing `gardener`, +1
  for the `git`/`git-workflow` split already landed pre-build). Median 322B → 289B.
  Only outlier >2x median is still `handover` (676B) — the operator's own named
  exception, untouched by design. `shortcut-file` went 0 → 7 tags; `diagnostics` went
  17 → 7 tags.
- **Conflict resolution**: every conflict found was resolved, none deferred. The
  `Branch:` trailer contradiction was already clean (prior feature). The 2
  skill-vs-agent-def duplication pairs (`gardener`↔`agents/gardener.md`,
  `workflow`+`workflow-complete`↔`agents/landscaper.md`) are resolved per the frozen
  ruling — skills stay full, agent-defs thinned. The kauk-audience question was
  resolved by direct operator ruling in-session, not left open.
- **3-skill behaviour-equivalence spot check** (fresh Haiku reader, no session
  history): `agent-behaviour`, `clean-code`, `handover` — all 3 still fire on their
  original trigger conditions; both `AGENTS.shared.md` references they now carry
  (Testing gate, Handover & delegation §durable-facts and §sensitive-content) verified
  to exist with equivalent substance. One nuance, not a defect: `clean-code`'s pointer
  to `AGENTS.shared.md`'s Software principles is thin (a bare list, doesn't expand
  SOLID) but the skill's own body still carries the actual applicable rules, so no gap
  in practice.
- **5-skill tag-findability blind test** (fresh Haiku reader, tags only, no
  name/description): `shortcut-file`, `git-workflow`, `coding-lmstudio`,
  `workflow-complete`, `clean-code` — 5/5 correctly matched to a realistic usage
  scenario from tags alone. One minor friction noted (both `git-workflow` and
  `workflow-complete` tags mention "squash-merge"), resolved on second look by each
  skill's more specific tags.
- **Zero dangling `gardener`-skill-id references**: confirmed by full-repo grep. Every
  remaining hit is either this feature's own migration entry, a historical migration
  record of an unrelated past rename, or this sidecar's own description of the change
  — no live pointer to the old path remains. `migrations/2026-07-29-gardener-to-board-walking.md`
  is present.
- **Full-corpus frontmatter validation** (mechanical, added at the testing gate, not
  originally in the agreed method but a natural extension of it): all 19 `SKILL.md`
  files now parse as valid YAML with `name` matching their directory and `roles` /
  `description` present. This caught **two pre-existing invalid-YAML bugs**, both
  unrelated to this pass's own edits (verified against the base commit `a421c6c`
  before this build touched either file): `history-rewrite` (an inserted `roles:` line
  had split its description scalar, silently truncating it — found and fixed by the
  batch-C sower as a byproduct) and `workflow-complete` (an unquoted colon inside the
  description broke YAML parsing — found and fixed directly at this testing gate).
  Worth a follow-up: a CI/pre-commit lint that validates `SKILL.md` frontmatter would
  have caught both earlier.

**Process note (shared-worktree sower dispatch)**: 6 parallel sowers were dispatched
into this same worktree without per-sower `isolation: "worktree"`. 3 intermediate
commits ended up with commit messages that don't fully match their diffs (one sower's
plain `git commit` briefly swept up another's staged-but-uncommitted files) — verified
byte-for-byte that no content was lost or overwritten (every batch touched disjoint
files) and no two sowers edited the same file. Since this branch is squash-merged at
close, the messy intermediate history doesn't reach `main`. Recorded as a dispatch
lesson for future parallel-sower builds sharing one worktree.

### Result

Result: **done**. Branch `f/skill-terseness-pass` @ `be1bf14`. Build: 1 sower for the
authoring-skills contract update, 6 parallel sowers for the per-skill batches + the two
coupled duplication-pair steps (2 built inline by the landscaper at the testing gate:
the workflow-complete YAML fix, and the full-corpus mechanical validation) — 7 sowers
total, 0 steps built inline from the original 8-step plan. Tested per the agreed method
plus the mechanical frontmatter validation described above; all results reported
honestly, including the two bugs it surfaced. No follow-up tasks spawned by this
feature beyond the one-line lint suggestion above, which is for the gardener to place
on the board if it agrees.

## Decision entries

## [2026-07-29 02:18 CEST] Decision-NNN: Skill vs consuming agent-def duplication resolves toward the skill
#skills #agent-defs #duplication #terseness

Where a skill and an agent-def it feeds restate the same content, the skill stays
full/authoritative and the agent-def is what gets thinned to defer to it — never the
reverse. Applies even where orchids is currently the sole real consumer of the skill:
no cross-repo manifest exists to verify other consumers' agent-layer status, so
"orchids-only today" is not grounds to fold a skill's content into one role's agent-def.

## [2026-07-29 02:18 CEST] Decision-NNN: workflow/workflow-complete never merge into a role
#skills #workflow #agent-defs

`skills/workflow` and `skills/workflow-complete` stay separate, reusable skills,
permanently — never folded wholesale into any single role's agent-def (e.g.
`agents/landscaper.md`), because which role opens vs. closes a workflow is expected to
keep changing over time. A role's agent-def may defer to these skills and stop
restating their content inline, but the skills' own content is never merged elsewhere.

## [2026-07-29 02:18 CEST] Decision-NNN: Skills are named for the behaviour, never for an agent
#skills #naming #authoring-skills

A skill's name must describe the reusable behaviour it provides, never duplicate an
agent/role name — a skill is meant to be usable by any agent, and naming it after one
role suggests the opposite. Folded into the `authoring-skills` contract as a naming
rule. `skills/gardener` was the one violation in the corpus and is renamed to
`skills/board-walking`.

## Changelog entry

Cut redundant and contradictory prose across all 19 skills: tightened `description`
fields to their actual trigger, gave `metadata.tags` a real job as a discovery index
(a skill must now be findable by its tags alone), and removed passages that restated
`AGENTS.shared.md` or a consuming agent's own system prompt in favour of a reference.
Renamed `skills/gardener` → `skills/board-walking` (a skill must never be named after
an agent/role) and thinned `agents/gardener.md` and `agents/landscaper.md` to defer to
their skills instead of restating them — `workflow`/`workflow-complete` stay
permanently separate, reusable skills, never folded into any one role. Fixed two
pre-existing invalid-YAML frontmatter bugs found along the way (`history-rewrite`,
`workflow-complete`).

## Readme delta

`README.md`'s skill listing already updated in-branch as a direct, necessary
correction of the `gardener` → `board-walking` rename (a stale cross-reference would
have been a live defect, not a staged suggestion) — no further README delta beyond
that one-line rename is needed for this feature.

## Architecture

No `ARCHITECTURE.md` trigger fired: this feature changed skill/agent-def *content*
(frontmatter, trigger text, cross-references, one rename) but touched no application's
or module's responsibility or boundary, added/removed/repurposed no component, changed
no data flow or wiring between modules, and introduced no new architectural style or
cross-cutting pattern. Evidenced by the diff itself — every changed file is a `.md`
skill/agent-def or a migration entry, none of which `ARCHITECTURE.md`'s Composition
hierarchy (Solution/Application/Module/Component/Element) describes.

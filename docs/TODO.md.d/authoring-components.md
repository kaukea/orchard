- created: 2026-07-29
- created_by: gardener

## Proposal

Operator, 2026-07-29 (token-load reduction pass): a recurring discipline, not a
one-off pass — a skill that keeps any COMPONENT (a `skills/*/SKILL.md` or an
`agents/*.md`) terse and non-redundant, applied both when a component is
authored fresh and when an existing one is revisited. Named to sit alongside
`authoring-skills` rather than replace it.

Trigger: measured just now that `agents/courier.md` (~4000 words) and
`agents/gardener.md` (~4200 words) are loaded fresh by every session of every
agent that spawns them — courier especially, since every agent in the fleet
loads one. `skill-terseness-pass` (gh#56) already tracks the same discipline
for skills' `description` frontmatter (re-measured 2026-07-29 at 5,758 bytes
across 18 skills) but nothing today covers `agents/*.md` bodies or
`AGENTS.shared.md`, and nothing makes the discipline recur once applied.

## Questions

- **Overlap with `authoring-skills`.** Does `authoring-components` absorb and
  rename `authoring-skills` (widening its contract to cover agent-defs too), or
  does it sit alongside it as a distinct concern (terseness/non-redundancy)
  while `authoring-skills` keeps owning structure (frontmatter shape, section
  order, one-concern rule)? The name was picked to read as a sibling, but the
  boundary needs a ruling before the skill is written.
- **Overlap with `skill-terseness-pass`.** Does `authoring-components` supersede
  that task's one-time sweep (becoming the mechanism that both runs the initial
  pass AND stays live afterward), or does the one-off task still run once and
  this skill only prevents regrowth going forward?
- **Trigger mechanism.** Is this skill self-invoked by convention (an author
  reads it before touching a component, same as `authoring-skills` today), or
  does it need a hook/lint (`board_lint.py`-style check) so a bloated
  `description` or body is caught mechanically rather than by discipline alone?
- **Scope of "terse."** Frontmatter `description` only, or does it also cover
  trimming redundant prose in a component's body (e.g. content that restates
  `AGENTS.shared.md`, already flagged as a live problem in
  `skill-terseness-pass`'s Findings)?

## Findings

Fleet-wide per-session multipliers measured 2026-07-29 (word counts):
`agents/courier.md` 4023, `agents/gardener.md` 4173, `agents/landscaper.md`
3273, `agents/supervisor.md` 3257, `agents/groundskeeper.md` 1296,
`agents/groomer.md` 906, `AGENTS.shared.md` + `AGENTS.md` 1608 combined. Every
agent-type's frontmatter `description` (the blurb the Agent tool and the
available-agent-types listing show) is also paid by every session regardless
of which agent is actually dispatched — same shape of cost as the skills
catalog listing that `skill-terseness-pass` already targets.

## Proposal (build shape, draft — confirm at plan)

A new skill under `skills/`, read before authoring or materially revising any
`agents/*.md` or `skills/*/SKILL.md` file (and `AGENTS.shared.md`/`AGENTS.md`).
Likely carries: a terseness checklist, a redundancy check against
`AGENTS.shared.md` and sibling components, and (pending the trigger-mechanism
question above) a lint the same way `board_lint.py` checks the board.

## Testing

To be agreed at plan — likely mirrors `skill-terseness-pass`'s method:
before/after byte or word count per touched file, reported honestly, plus a
spot-check that a component read fresh after trimming still produces the same
agent behaviour.

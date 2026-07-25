- created: 2026-07-25
- created_by: Sebastien Lambla

## Blockers

- ~~Final word+emoji picks for the orchestrator and the architect (operator is
  reviewing alternatives), and the planter/sower pick for the builder.~~
  RESOLVED — all picks ruled 2026-07-25 (see Findings).

## Questions

- ~~Orchestrator: gardener or orchardist — and which glyph carries best at a
  glance?~~ RULED (operator, 2026-07-25): GARDENER 🌳.
- ~~Architect: which landscaper-family word and glyph?~~ RULED (operator,
  2026-07-25): LANDSCAPER 🌿.
- ~~Builder: planter or sower?~~ RULED (operator, 2026-07-25): SOWER —
  provisional in his words ("if we find a better name, we will rename it").
  Glyph 🌱 (ruled with the set, 2026-07-25).

## Findings

- Operator ruling (2026-07-24/25, mock round 5): every role wears an
  orchard name — all of them, not a mix. Settled so far: bloomer 🌸
  (native, stays) · housekeeper → groundskeeper · bus → courier (old-mail
  family, post-horn flavour) · builder → the planting family. Approved in
  principle: "close enough … I like all of them."
- THE FULL SET, RULED (operator, 2026-07-25 morning — closes the naming
  vocabulary): orchestrator → GARDENER 🌳 · architect → LANDSCAPER 🌿 ·
  builder → SOWER 🌱 · housekeeper → GROUNDSKEEPER 🧹 · bus → COURIER 📮 ·
  bloomer stays BLOOMER 🌸. Courier glyph constraint (operator): a small
  envelope is unreadable — a larger envelope or a mailbox; 📮 chosen, 📬
  the fallback if the red box reads wrong on screen. Recorded as
  Decision-085.
- Visibility rule: the roles the operator watches longest get the most
  visible emojis.
- Cloud variants are NOT a user-facing identity: user surfaces show WHERE a
  thing executes via two location badges (local machine / cloud),
  orthogonal to the role emoji. The cloud badge exists from day one.
- Footprint (expect the retire-groom-vocabulary shape, wider): agent
  definition files and their frontmatter, orchestrator/architect/builder/
  housekeeper/bus references across skills (workflow, bloom-tasks, kauk,
  handover…), hooks, docs, ARCHITECTURE role table, README, sidebar
  renderer role map, board_gh projections. A migration file ships in the
  same branch (managed-artifact renames, §Migrations).

## Proposal

(to shape once the three picks land) One branch renames every role to its
orchard name with its emoji, adds the two location badges to user surfaces,
and carries the migration; no behaviour change rides along.

## Testing

To agree when scoped — expected: a session of each renamed role boots clean
under its new name; the sidebar shows role emojis and location badges; no
old role word remains outside history.

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

AGREED METHOD (operator, 2026-07-25) and REAL RESULT:
- pytest suite: **369 passed, 8 subtests passed** (green).
- courier.py + transitional bus.py shim round-trip: init/root/broadcast/receive OK;
  shim `bus.py root` == `courier.py root` (execs through).
- orchard_topic imports courier cleanly; `_courier()` resolves to tools/courier.py.
- sidebar render smoke: renamed role + Decision-085 glyph render, NBSP-glued, wide-char
  aware; NO location badge (dropped from scope).
- grep gate: no old role word / transport "bus" in code or canonical surfaces (excepting
  proper-noun task ids, the `bus-message-specifying` ruling record, the transitional bus.py
  shim fallback, and history).
- migration dry-run (isolated, run ×2): dangling old-name laydowns removed, shim preserved,
  `the-works/bus`→`courier` moved + compat symlink, idempotent.
- OPERATOR-GATED (post merge + kauk sync): live-boot one renamed role under its new name and
  confirm the 📮 courier glyph reads at sidebar size (📬 fallback if the red box reads wrong).

## Result

Result: **done** — branch `f/orchard-renaming` @ HEAD `2cceb35` (Base `7b32e0e`, 🎉 anchor).
Location badges dropped, `-cloud` variants and legacy `groomer` untouched, history left as history.
Delegation: discovery **6 explorers**; build **9 builders** (agent-defs · transport+shim · sidebar ·
scripts · hooks/manifest · skills · canonical-docs · sidecar-sweep · internal Bus→Courier) + **1 tests
builder**. Inline (integration keystones, justified): the migration, the cross-file integration fixes
(4 unowned files + the tmux teardown-handle reconciliation + 3 courier hooks), and the sidebar
wide-char render fix. Zero builder-ownable steps built inline.

ARCHITECTURE determination: **EDITED on-branch** (trigger fired — components renamed + a
cross-cutting subsystem renamed). ARCHITECTURE.md updated: the role table (six roles),
the "## The message bus"→"message courier" section, the repo-layout filenames, and the
teardown-handle contract (`@arch_id`→`@landscaper_id`). MIGRATION: shipped in-branch
(`migrations/2026-07-25-orchard-role-rename.md`) — managed-artifact renames + state-dir move.

## Changelog entry
(stage verbatim; the orchestrator places it at ingest — Decision-034)

### Fleet roles renamed to orchard names; message bus renamed courier
Every agent role now wears an orchard name and glyph: orchestrator→gardener 🌳, architect→landscaper 🌿,
builder→sower 🌱, housekeeper→groundskeeper 🧹, bus→courier 📮 (bloomer 🌸 unchanged). The message-bus
transport was renamed wholesale to **courier** (`tools/courier.py`; a transitional `tools/bus.py` shim
execs it for one release so live sessions are not cut off). The sidebar identity line now renders each
role's glyph, with wide-char-aware column accounting. A dated migration converges consuming repos
(drops dangling old-name laydowns, moves `the-works/bus`→`courier` with a compat symlink). No behaviour
change; `orchid:`/`orchard:` namespaces untouched.

## Readme delta
(User-facing summary for the orchestrator to apply via readme-sync at ingest — Decision-034. NOTE: the
README's role/transport references were also swept ON-BRANCH for rename consistency, like ARCHITECTURE;
reconcile if staging-only was expected.)
Fleet roles are now gardener / landscaper / sower / groundskeeper / courier (bloomer unchanged), each
shown with its glyph (🌳🌿🌱🧹📮🌸) in the sidebar identity line; the message bus is now "courier". Agents
launch by their new names (`--agent gardener`/`landscaper`, `subagent_type courier`, etc.).

## Decision entries
(staged verbatim, sanitized, decisions.md format; UNNUMBERED — housekeeper assigns the next free number)

## [2026-07-25] Decision-NNN: bus→courier is a full subsystem rename, shipped behind a transitional shim
#naming #bus #courier #transport #renaming #migration
Ruling (operator, 2026-07-25): the `bus`→`courier` rename in Decision-085 is a FULL subsystem rename, not
role-only — `tools/bus.py`→`tools/courier.py`, the `the-works/bus` state dir→`courier`, the envelope
schema title, and `test_bus*`→`test_courier*`. To avoid severing live messaging (the transport had just
changed under bus-transport-v2 and its cutover is delicate), it ships behind a one-release cutover:
`tools/bus.py` remains a thin shim that `exec`s `courier.py`, the courier hooks accept BOTH tool names,
and the migration moves the state dir with a `bus`→`courier` compat symlink. The `orchid:` wire-grammar
prefix and the `orchard:` topic transport keep their names (they are not the bus). Consequence: the tmux
teardown handle follows architect→landscaper — `@arch_id`/`arch:<id>` become `@landscaper_id`/`land:<id>`
in the live launcher+teardown+docs, superseding Decision-048's handle name (history keeps `@arch_id`).

## [2026-07-25] Decision-NNN: location (local/cloud) is not part of the role rename and is deferred
#naming #cloud #location #sidebar #scope
Ruling (operator, 2026-07-25): cloud vs local is NOT an agent-type distinction and will not be — it is a
planning/execution-time property that applies to anything, orthogonal to the role. The location badges
were therefore DROPPED from the orchard-renaming feature; `tools/sidebar.py`'s `LOCATION_BADGES` constant
stays unwired. Only the role glyph was wired into the identity render. The `-cloud` def variants were left
untouched this pass (the cloud model is being reworked).

## Operator requests (ledger)
- 2026-07-25, mid-build: "…manifest time killing the manifest next as soon as you get release out of the
  door." READING: after this rename ships, retiring `manifest.conf` is the NEXT task — OUT of this
  feature's scope. Status: NOT acted on; RETURNED to orchestrator as a follow-up (below). Reading unconfirmed.

## Follow-ups — RETURN to orchestrator (not written to the board by me)
1. `docs/TODO.md` board-index role-word sweep was DENIED to me (architect is write-guarded from the board).
   The orchestrator should sweep role words in these rows: external-blockers, github-board-sync,
   orchard-summary, orchard-launch, tmux-topology, sidebar-witnessing, launcher-subagent, bloomer-repointing,
   agent-metadata, readme-changelog-ownership, message-bus, bus-close-cleanup, bus-singleton, bus-recycling,
   focus-returning (+ description-only on the done/cancelled rows cloud-architect, architect-delegation).
2. bus-* board tasks must replan onto **courier** names after this lands (files bus.py/courier.py, hooks,
   tests, schema are renamed): gh#210 fanout-cutover, gh#211 bus-close-cleanup, gh#212 bus-singleton,
   gh#45 cross-repo-bus, gh#209 bus-relay, gh#213 bus-recycling, gh#193 sidebar-witnessing,
   gh#195 pretty-sidebar, gh#30 zombie-revival.
3. NEW follow-up: retire `manifest.conf` (operator's mid-build note) — confirm reading + schedule.
4. 5 ORPHAN sidecars (no board row, status undeterminable) were NOT swept: cloudpath-naming, hops-measuring,
   intake-deduping, origin-stamping, revise-commenting — orchestrator to confirm active/dead and sweep if active.
5. The separate planned `orchid:`→`orchard:` prefix migration (bus-transport-v2 note) is NOT this feature —
   do not conflate.

## Proposal (final, shipped)
One branch renamed the six roles to their orchard names + glyphs (Decision-085), performed the full
bus→courier subsystem rename behind a transitional shim + compat-symlink cutover, wired the role glyph into
the sidebar render (wide-char aware), renamed `skills/orchestrator`→`skills/gardener`, swept prose across all
active surfaces, and shipped the managed-artifact migration. Location badges deferred; `-cloud`/`groomer`
untouched; no behaviour change.

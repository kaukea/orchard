- created: 2026-07-17
- created_by: opus-4.8

## Blockers
- None. Independently useful: a cross-repo `⊘` can be hand-written today, before any
  inbox exists. Do not sequence this behind `cross-repo-inbox`.

## Questions
- **Edge syntax for an external id.** Needs to be unambiguous against local ids and
  cheap for `board_lint.py` to split. Candidate: `⊘serialseb/kauk#role-aware-delivery`
  (`<owner>/<repo>#<task-id>`).
- **How does the gardener resolve one?** It needs the other repo's board. Read a
  local checkout if present (both repos are on-box today), or fetch? What is the
  behaviour when the other repo is absent — report unresolved, or fail?
- **What does the lint do with an unresolvable external id?** It cannot check another
  repo's board without reading it. Warn, skip, or resolve when the checkout exists?
  A silent skip makes the edge decorative — the current failure mode, restated.
- **How does the blocker's *status* reach the render?** "Blocked on kauk#X" is only
  useful if the board can say whether X is still open. That means reading the other
  board's badge, not just resolving that the id exists.

## Findings
- Board edges are single-board by construction. `board_lint.py`'s no-orphan-subtasks
  rule resolves every `⊘`/`~` id against entries on the same board, so an external id is
  currently a lint error, not an expressible edge.
- The gap is live and already costing us: orchids `role-delivery` is gated on kauk
  `role-aware-delivery` (filed 2026-07-17). That dependency exists only as prose in two
  Findings sections, on two boards, which nothing checks. Either side can drift and
  nothing will complain.
- The gardener's boot sequence already reads the board and the handover; adding
  external-blocker resolution extends a read it already performs. But the role is
  deliberately lean and reconstitutes from a bounded set — an unbounded fan-out to
  other repos' boards would break that property. Bound it.
- Operator ruling (2026-07-17): the gardener MUST include external blockers when it
  loads its tasks. A task blocked on another project's work is not "queued" — rendering
  it as such is a lie the board currently tells.

## Proposal
1. Extend the edge syntax with a qualified external form.
2. Teach `board_lint.py` to recognise it and to resolve it when the other checkout is
   present — never to silently accept an unresolvable one.
3. Teach the gardener's boot/board-render to resolve external blockers and surface
   them in the render, including the blocker's current status.
4. Update `AGENTS.files.md` §TODO (edges) and the `gardener` skill together — the
   format and the reader are one change.

## Testing
Two on-box repos with a real cross-repo edge (orchids `role-delivery` ⊘ kauk
`role-aware-delivery` — it already exists, so this is a live test, not a fixture).
Assert: lint resolves it and stays clean; the board render shows it as blocked with the
external task's real status; closing the kauk side unblocks the orchids side on the next
render. Negative: a bogus external id fails the lint rather than being skipped.
Absent-checkout case reports unresolved rather than claiming clean.

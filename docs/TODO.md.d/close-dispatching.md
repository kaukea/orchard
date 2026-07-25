- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (orchard-renaming close gap)

## Blockers

- None.

## Questions

- Who owns the gate-word dispatch when the architect dies at that exact moment —
  should the orchestrator treat every `finished` bus signal as "verify a
  housekeeper exists, dispatch if not", making recovery automatic instead of
  operator-noticed?

## Findings

- Live failure, 2026-07-25 morning (feature orchard-renaming): the architect
  staged its result on-branch (e8b398b), signaled `finished` on the bus, received
  THAT IS ALL, self-tore-down — and the housekeeper dispatch that Decision-054
  says happens AT the gate word, in parallel with self-teardown, never ran.
  No close: no tag, no squash, stream not marked `_closed`, no final `## State`
  in its log, no telemetry note. The operator noticed by absence ("nothing else
  doing renaming"); recovery was a manual orchestrator dispatch of the
  housekeeper with a written brief.
- Same event, second defect: the orchestrator skill still describes the OLD close
  ("a returning sub-job marks its stream _closed; the ingest hook nudges you") —
  it predates Decision-054/055 and gave the orchestrator no duty to notice a
  finished-but-uncloses feature. The operator flagged it as "the old workflow".
- Related earlier leftovers, same family: the bus-transport-v2 close stopped
  before worktree/branch removal (found at 2026-07-25 boot, cleaned at ingest).

## Proposal

Make the close dispatch survive the architect's death: the `finished` signal
(which reaches the orchestrator's courier regardless) becomes the trigger the
orchestrator acts on — verify a close is running for that feature; if none,
dispatch the housekeeper with the standard brief. Update the orchestrator skill
text to the Decision-054/055 choreography while in there.

## Testing

To agree when scoped — expected: kill an architect between countersign and
dispatch in a scratch feature; the close still lands (tag + squash + `_closed`
stream) without operator intervention.

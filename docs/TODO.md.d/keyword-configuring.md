# Keyword configuring: the gate-phrase table becomes configuration

- created: 2026-07-22
- created_by: Sebastien Lambla

## Blockers

- None hard; sensible after [[operator-interacting]] lands (the envelope is
  where the table is consumed).

## Questions

- Where the table lives (repo config consumed by the boundary translation
  and the popup broker) and whether per-repo overrides are wanted.

## Findings

- Operator (2026-07-22): the keywords are quotes from famous movies and
  will be made configurable in the future; today's table is hard-coded in
  the gardener def (Decision-057 + addenda): coding start = the NO-NO
  phrase and the glacial-pace phrase (internal MAKE IT SO); coding end =
  THAT IS ALL; ENGAGE = cloud dispatch only.

## Proposal

Move the operator gate-phrase table out of def prose into configuration
read by every operator-input boundary (gardener relay, question/gate
popup), so phrases can be added or changed without editing agent
definitions. Internal protocol strings stay fixed.

## Testing

Change a phrase in configuration; the boundary honours it without any def
edit; internal strings and in-flight builds unaffected.

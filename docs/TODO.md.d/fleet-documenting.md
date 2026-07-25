# Fleet documenting: agent wiki pages; channels with JSON Schemas

- created: 2026-07-22
- created_by: Sebastien Lambla

## Blockers

- Wiki publishing must run with USER credentials — GitHub Apps and Actions
  tokens cannot push wiki repos (digest-identity Findings, verified live
  2026-07-22). A local build publishes fine with the operator's own auth;
  a cloud/callabloom path cannot until a machine-user exists.

## Questions

- Page granularity: one wiki page per agent (name, description, rules), or
  per role family? Presumed per-agent; confirm at bloom.
- Whether the wiki pages are generated from the agent defs (single source,
  regenerated at close/sync) or hand-authored — generated recommended, or
  they will drift.

## Findings

- Operator intake (2026-07-22, no priority): every agent's name,
  description and rules gets its own wiki page; every communication
  channel is documented — event names, and a JSON Schema attached to each,
  "like we agreed in a previous decision". No decision entry in
  docs/decisions.md records that agreement explicitly, but the precedent
  artifact exists: `tools/message.schema.json` ships with the courier — the
  convention to extend.
- Channel inventory to document (as of today): courier envelope (announce /
  depart / send / broadcast / signal / status), lifecycle signals
  (on-closing / on-closed / finished / abandoned / done / blocked, plus
  the supervisor's kill-broadcast, Decision-068), activity broadcasts
  (`orchid:activity:*`, `orchid:subagent:*`), and the question/gate
  envelope ([[operator-interacting]], including the popup ask).

## Proposal

Two halves, one documentation build:
1. A wiki page per agent — name, description, rules — generated from the
   agent defs so the wiki cannot drift from the source.
2. A communication-channels reference — every channel and event named, each
   carrying an attached JSON Schema (extending the
   `tools/message.schema.json` precedent), covering the inventory above and
   published alongside the agent pages.

## Testing

Every agent def has its wiki page and every documented event validates
against its attached schema (a real captured message per event type run
through the schema); regeneration from source produces no diff when nothing
changed.

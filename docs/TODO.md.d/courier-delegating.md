- created: 2026-07-26
- created_by: Sebastien Lambla
- created_during: gardener session (courier-identity observation)

## Findings

- OPERATOR RULING (2026-07-26 — Decision-096, verbatim intent): in-session
  subagents have no identity and load NO courier of their own. NOTHING
  writes messages without a courier — direct transport writes are an
  architecture-breaking move. A session-bearing agent may delegate a
  REFERENCE to its own message sidecar to a subagent; it never loads a
  courier for the subagent. Per-subagent couriers lead to agents inventing
  fake session ids and other very poor designs.
- Observed trigger: the sidebar-empty-rows bloom round loaded its own
  courier (~35k subagent tokens for announce, two posts, release) inside
  the gardener's session; the transport also carries events under a
  session id belonging to no known session.
- Implementation surfaces: agent charters that tell subagent-tier roles to
  load a courier (bloomer; any groundskeeper-class text) — workflow
  component, gardener-authored; the delegated-reference mechanism and any
  mechanical enforcement (courier.py refusing non-courier writers /
  registration from identity-less callers) — product code, landscaper
  work.

## Questions

- Boundary: does the courier-only write rule cover a session-bearing
  agent's OWN mechanical posts (the gardener charter currently instructs
  `orchard_topic.py post status` directly)? Asked by the gardener
  2026-07-26; answer shapes charters and enforcement.

## Proposal

Implement Decision-096: subagent-tier rounds use a delegated reference to
their parent's courier for every send; no courier load, no direct
transport writes, no synthetic session ids. Charters amended accordingly;
enforcement at the courier so the rule is architectural, not behavioural.

## Testing

Agreed at scope/plan time; known shape — a bloom-class round runs
end-to-end with zero courier loads of its own, its telemetry riding the
parent's sidecar under the parent's true session id; a direct-write
attempt from an identity-less caller is refused.

- created: 2026-07-20
- created_by: Sebastien Lambla

## Blockers

- None.

## Questions

- What counts as a diagnostic event: errors, gate violations, stalls/wedges, token
  pressure, hook misfires, dead sidecars? Severity levels?
- Transport per habitat: local agents have the courier (identity/status already ride it —
  [[bus-liveness]], [[agent-metadata]]); cloud agents have no courier and no pane — PR
  comments, run artifacts, a committed file, or the `/fire`-style endpoint in reverse?
  One logical channel over two transports, or two channels?
- Consumers: the [[fleet-sidebar]] (a job's error/wedge state), the gardener (triage),
  the operator directly? Retention and where diagnostics land durably (they are transient
  chatter, so `.git/the-works/`-shaped, not committed docs?).
- Relationship to the `diagnostics` skill (code troubleshooting scripts): distinct — this
  is agents diagnosing THEMSELVES to the fleet — but the naming must not collide.

## Findings

- Operator (2026-07-20): a CROSS-CUTTING concern of the Orchard programme — a diagnostic
  channel for agents, explicitly BOTH cloud and local. Motivating context from today: an
  landscaper's close handshake failed silently (flush race), the courier once never ran in any
  session and nothing said so, and a wedged/dead agent is indistinguishable from a quiet
  one ([[bus-liveness]]). Cloud agents ([[cloud-architect]]) make the blind spot worse —
  no pane to glance at.

## Proposal

- (to be bloomed once the Questions are answered; expected shape — one diagnostic event
  format, per-habitat transport, sidebar and gardener as first consumers)

## Testing

To agree at blooming; must cover one local and one cloud agent each surfacing a forced
diagnostic event end-to-end to the consumer surface.

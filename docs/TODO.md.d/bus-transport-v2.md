- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (carried from the bus-message-specifying close)

## Blockers

- This is the COMPLETION FOLLOW-UP of [[bus-message-specifying]] (functional):
  v1 delivered the vocabulary/display grammar; this carries the transport half.
- Deferred by operator ruling (2026-07-25): the METRONOME project will need a
  transport much bigger and stronger and is expected to REPLACE this wholesale
  — so v2 is designed-but-unbuilt preparation, not built now. `⊘metronome`.
  Scope now was light fixes only (delivered by [[bus-message-specifying]] v1
  and [[bus-close-cleanup]]).

## Questions

- Six from the security review, batched, all UNRULED except enforcement:
  enforcement model (RULED cooperative); global-state location (transient vs
  crash-survival tension); folder key type (public-key + signing?); first-agent
  anchor crash/revocation; operator_origin & gate-phrase signing; cloud-leg
  key custody. Full text: the security review (below).

## Findings

- THE DESIGN RECORD lives in [[bus-message-specifying]]'s sidecar Findings
  (rounds 1–18, on main after the c1734c0 close) — do not re-derive it. Full
  security review at `.git/the-works/_ingested/bus-message-specifying/
  security-review.md`. This task is the home for that transport design once
  v1's vocabulary landed; the design is summarized here, authoritative there.
- REQUIREMENT AXES (operator): reduce traffic · enforce conformance · encrypt ·
  support cloud agents — plus addressed peer messaging (project + session id)
  and allow-listed real-time topics.
- THE SEAL IS THE ENVIRONMENT BOUNDARY (round 17), NOT the local UID: fleet
  membership across environments is the permissioning seal; crypto keeps
  anything OUTSIDE the fleet from seeing traffic. The security review's
  local-same-UID criticals (C1–C4) are OUT of this threat model (single-user
  machine); the crypto that matters is the cross-environment leg
  (cloud/GitHub/API sealing). Enforcement model is COOPERATIVE (bus.py the
  convention; no daemon, no per-agent UIDs).
- SCHEMA SKETCH (operator, round 9, his design — illustrative, not frozen):
  typed one-liners, `Subject:<type>`, payload in body; the bus subagent stays;
  broadcast → topics (v1 `global` only). Addresses From `:session:<id>`; To
  `:session:<id>` (authorized) | `:topic:<name>` (fixed list, daemon-signed).
  Types: status (word + optional 0–100 + text) · outcome success|fail ·
  lifecycle (payload = display minimum: location + project) · delegation
  begin|end · operator relay (unicast) · bus subscribe|unsubscribe (folder +
  monitor lifecycle). Prefix orchid:→orchard: (rides the rename). Identity
  never rides the bus — derived locally from the worktree/CLI.
- CLOUD LEG (verified): per-flavour inbound adapters exist — GitHub events;
  channel plugins into Claude-web sessions; session-events API for Managed
  Agents; polling as the universal fallback. Envelopes crossing the boundary
  get sealed + signed.
- CARRIED CODE FOLLOW-UPS from the v1 close (small, independent of the big
  redesign): (a) `bus.py status_of(session_id)` refactor to retire
  `sidebar_model._read_status` parameterized duplication; (b) remove the
  legacy `orchid:activity` parse fallback after one transition release.

## Proposal

To shape when metronome's shape is known, or if the operator pulls a slice
forward. The transport is the layer ABOVE v1's vocabulary: v1 is what a
message SAYS; v2 is who it reaches, on what topic, sealed how, admitted by
whom. Nothing here is built until the operator rules a build.

TOMORROW (operator, 2026-07-25 end-of-day — pulled forward, this is next
session's first work): "refine and implement vocab v2 and make sure cross-repo
works." So this task IS built next, not left for metronome — refine the schema,
implement it, and prove cross-repo messaging end to end.
- CROSS-REPO TARGET: the working stack is panopticon, seb.throwy, and SignMc —
  get messaging working ACROSS these repos first. ("panopticon, seb.throwy on
  top of SignMc — that's the first.")
- TRACKER FILE (operator didn't know where it is): `~/.config/orchids/
  sidebar-registry.json` — the cross-repo list the sidebar reads. Today it
  holds only orchids + SignMc; add panopticon and seb.throwy to exercise
  cross-repo. (Override: `ORCHIDS_SIDEBAR_REPOS`.)
- Current bus is PER-REPO (spool under each repo's git dir) — cross-repo
  addressing has NO substrate yet; that substrate is the core of this work.

## Testing

To agree at dispatch. The assured-scenario gate carried from
[[bus-message-specifying]] round 18 applies: an agent must learn a peer's
completion through the bus alone, no git/filesystem polling — enabled by
[[bus-close-cleanup]].

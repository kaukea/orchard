- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: f/bus-transport-v2

## Blockers

- The cross-repo addressing substrate does not exist: the bus spool lives under
  each repo's own git dir, so a `:session:` address cannot reach a session in
  another repository. Building that substrate is part of this task, not a
  prerequisite — listed here so nobody assumes it is already there.

## Questions

- Scope split with [[cross-repo-bus]] (gh#45): that task already names live
  cross-repo messaging. Does this task absorb it, or does bus-relay carry only
  the request/response mechanics while cross-repo-bus carries the substrate?
  Recommendation: absorb — the operator's roadmap treats them as one arc
  ("finishing the bus off").
- "Manual auth" for `:session:` unicast is ruled but undefined: what does the
  authorisation step look like in practice?

## Findings

- Operator roadmap to "bus good enough" (direct, 2026-07-25): request/response
  between agents · verify nested mtime (FOLDED into bus-transport-v2, shipped) ·
  handle internal subagents (delegation family, shipped in the data layer).
  Once request/response lands, the bus is good enough.
- Request/response messages are DELETED by the script upon reading (operator,
  ruled 2026-07-25).
- Channels ruling (operator, 2026-07-25): (1) SendMessage between two RELATED
  agents (parent↔child); (2) broadcast status on topics; (3) SendMessage between
  UNRELATED agents is managed by seb.house — out of scope here.
- Cross-repo target set: panopticon, seb.throwy, SignMc ("panopticon, seb.throwy
  on top of SignMc — that's the first"). The sidebar's cross-repo list lives at
  `~/.config/orchids/sidebar-registry.json` (today: orchids + SignMc; override
  `ORCHIDS_SIDEBAR_REPOS`).
- The topic root is already user-wide (`$XDG_RUNTIME_DIR/orchard/topics/`), so
  topic traffic crosses repos by construction; it is the inbox/unicast leg that
  is repo-scoped.

## Proposal

Finish the bus: `:session:` unicast request/response with manual authorisation
and delete-on-read, reachable across repositories (the addressing substrate),
so an agent in one repo can request from and respond to an agent in another.
V1 fan-out retirement is NOT here — that is [[fanout-cutover]].

## Testing

Carried assured-scenario gate from [[bus-message-specifying]] round 18: an agent
learns a peer's completion through the bus alone — no git or filesystem polling.
Cross-repo variant: the peers sit in two different repositories.

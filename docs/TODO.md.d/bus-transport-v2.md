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

- PENDING OPERATOR APPROVAL — agent proposals withdrawn from the design
  record (2026-07-25); NOT buildable until ruled:
  (a) write mechanics: atomic tmp+rename per event write, so a reader never
      observes a half-written event (the rename also advances the topic
      directory's own mtime);
  (b) whether the round-9 envelope fields (From/To/Subject) appear INSIDE
      the event file, or are carried structurally (filename = from,
      directory = to, content type = subject) — the events-only ruling
      reads as structural, but the reconciliation is unruled;
  (c) a timestamp inside the event (earlier agent addition `ts`) —
      withdrawn; the file's own mtime may already serve.
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

## Findings — THE DICTATED DESIGN (operator, 2026-07-25 night, authoritative)

Dictated live across the 01:55 recovery session and this one; SUPERSEDES the
round-9 sketch where they differ (topic list, daemon signing). This is the
frame every iteration builds inside — implement ONLY the iteration below.

- TOPICS: any component may create one; no fixed list, nothing daemon-signed
  (daemon withdrawn → cooperative enforcement follows). Family/name for
  projects: `repository/<project>`. Root is USER-wide (not machine-wide, not
  in any repo's git dir): `$XDG_RUNTIME_DIR/orchard/topics/<family>/<name>/`.
- THE ONE SCRIPT: every bus interaction goes through ONE Python script. It
  enforces the write location, the message content, the Subject, the From by
  detecting the session id (`:session:<id>`), and the To from the agent's
  up-front instructions (`:topic:repository/<project>`). A type not
  permitted on a topic is rejected at accept time.
- COLONS ARE LOAD-BEARING: `:session:<id>`, `:topic:<name>`; subscribe
  grammar `orchard:bus:subscribe:<topic>` / `orchard:bus:unsubscribe:<topic>`
  (subscribe = create the agent's topic folder + monitor; unsubscribe =
  delete all of it, discard remaining content). Not this iteration — recorded
  so nothing is invented differently later.
- ACTIVITY: every lifecycle/status/agent change posts a MESSAGE to the
  project topic; the topic directory's mtime therefore advances on every
  write and IS the sidebar's activity signal (operator-exempt from the
  no-filesystem-sync rule; the exemption covers the folder time only).
- AGENT SIDE: a small table — when X happens, ask your bus to post Y. The
  bus sidecar discovers all metadata itself; the parent agent does nothing
  and never learns a path, a format, or an ordering rule.
- MESSAGE TYPES: FOUR planned; TWO named so far — `appeared` (an agent has
  started) and `completed` (it has reached stopped). The other two are
  UNNAMED: do not invent them; their absence is an iteration wall.
- EVENTS ONLY, FLAT (operator, 2026-07-25 05:1x): an agent may advertise
  ONLY the events in the operator's document — nothing else rides the bus;
  status/phase/subagent-progress chatter serves no purpose and is OUT
  (extension of the event set only as needed to fill gaps, operator-ruled).
  A topic directory is FLAT — event files only, no subtrees. The only
  identity an agent gives is its session id, which IS the filename of the
  last event it posted — one file per session, the latest event replacing
  the previous. Event CONTENT stops at: the event type, plus at most a
  generic parent session id ("we stop there" — operator). No worktree,
  feature, model, or any other identity field rides an event.
  CORRECTION (2026-07-25): an earlier revision of this bullet also stated
  atomic tmp+rename mechanics and mtime-by-rename as design — those were
  UNAPPROVED agent additions, withdrawn to Questions pending the
  operator's ruling.
- CONSUMER: `tools/sidebar_v3.py` (untracked on main, operator-pocketed)
  already reads the topic dirs' mtimes with a 60-minute active window. Do
  not modify it in this iteration.
- STOPGAP TO SUPERSEDE: `tools/orchard_topic.py` on main is a bare one-arg
  mtime touch (`post`, no type, no message) — it cannot carry the
  differences between events and is NOT the design; reshape or replace it.
- STANDING CONSTRAINTS (operator): no log files; never close shared files;
  no filesystem-as-synchronization beyond the folder-mtime exemption; build
  exactly the requested iteration, nothing speculative.
- PERMISSION REALITY: bus subagents' Bash calls ride the auto-mode
  classifier (nothing bus-related is allowlisted); a bus was already denied
  running the stopgap once. Surface permission walls to the operator —
  never self-allowlist (the classifier blocks it, correctly).

## Proposal

The transport is the layer ABOVE v1's vocabulary: v1 is what a message SAYS;
v2 is who it reaches, on what topic, sealed how, admitted by whom. The
operator is feeding this design ONE ITERATION AT A TIME — the architect
builds the iteration below and NOTHING past it; later slices (subscribe
verbs, `:session:` addressing, the two unnamed types, encryption, cloud leg)
arrive as their own iterations when the operator opens them.

ITERATION 1 (open, operator-ordered): the one script's POST path for the
project topic, so the sidebar shows agents' work while it happens.
- `post` takes the message type — `appeared` | `completed` — and REJECTS
  anything else (a type not permitted on the topic is rejected at accept
  time — operator, round 9).
- It writes the event to `$XDG_RUNTIME_DIR/orchard/topics/repository/
  <project>/<session-id>` — the filename is the poster's session id; the
  content is the event type plus at most the generic parent session id,
  nothing else.
- Project discovered from the repository the call runs in; session id from
  the environment; callers pass nothing but the type (all metadata is
  discovered — operator).
- The bus contract's table (agents/bus.md) keeps exactly the two named
  moments: announce → post `appeared`; depart → post `completed`.

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

For iteration 1 (to confirm with the operator at the plan gate):
- Fixture: valid types write an enforced message file (fields present,
  atomic write observed); invalid types rejected naming the admitted set;
  no session id / outside a repo → hard exit.
- LIVE ACCEPTANCE, on the operator's screen: the mounted sidebar lists the
  project with a fresh age while a real session posts — behaviour observed
  end-to-end, not fixtures alone. An artifact that renders but displays
  nothing is a FAIL (operator ruling, 2026-07-25).

Carried for later iterations: the assured-scenario gate from
[[bus-message-specifying]] round 18 — an agent learns a peer's completion
through the bus alone, no git/filesystem polling ([[bus-close-cleanup]]).

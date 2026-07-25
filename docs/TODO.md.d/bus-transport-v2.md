- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: gardener session (carried from the bus-message-specifying close)
- completed: 2026-07-25
- completed_during: landscaper session f/bus-transport-v2

## Result (landscaper close, 2026-07-25)

Result: DONE — this feature delivered the sidebar DATA TRANSPORT slice of
bus-transport-v2 (the "courier equivalence for the side display"). Branch
`f/bus-transport-v2`. TESTED: 26 unit tests (`tests/test_orchard_topic.py`) pass
+ LIVE on-screen acceptance by the operator — a burst of events walked a session
line through its full lifecycle on his `sidebar_v3`; confirmed moving, and legible
once the feature/task name was added.

WHAT WAS BUILT:
- `tools/orchard_topic.py` — the sanctioned topic POSTER. `post <family> ...`
  over FIVE families: `lifecycle <starting|started|stopping|stopped>`,
  `status <=2 words>`, `delegation <schedule|begin|end> <subagent>`,
  `outcome <success|fail>` (agent-level), `task <completed|failed>` (task-level,
  GARDENER-ONLY). Every event carries the two fixed operations the courier answers
  itself and the agent never sees — identity (immutable) + status (mutable), from
  bus.py's identity_of/status_of. Validation is absolute; a violation refuses +
  records telemetry + bounces a rejection to the sender over the courier. Atomic write
  (`.<sid>.<ts>` -> rename) into `$XDG_RUNTIME_DIR/orchard/topics/repository/<repo>/`,
  repo via --git-common-dir (worktrees fold to one project), advancing the nested
  per-project mtime.
- `tools/sidebar_v3.py` — brought into the repo (was operator-pocketed) and grown
  from a bare projects list into the FUNCTIONAL per-session view: one line per
  session = feature/task · agent·model · lifecycle state · 2-word status · outcome,
  subtasks nested with scheduled/active/inactive. Reads only topic files; wakes no agent.
- `tools/feature-scoped tests` — 26 cases over all families, the gardener-only
  rule, and every reject path + telemetry.

GOVERNANCE (operator ruling, direct in-pane 2026-07-25): the gardener that
launched this feature is TAINTED — its relays and its sidecar commits on main
(5af7997..abbebd9) are NOT authoritative. This slice was built ONLY on the
operator's direct words + real pre-existing code. The full live-dictated design is
in the workstream log.

### Follow-up tasks — return to a FRESH gardener (not written to the board by me)
1. THE RELAY / request-response courier ("finishing the courier off"): `:session:` unicast
   with manual auth + delete-on-read; the CROSS-REPO addressing substrate (does not
   exist — courier is per-repo under each git dir); then retire v1's fan-out. Operator
   roadmap: request/response · verify nested mtime · handle internal subagents, plus
   cross-repo (panopticon, seb.throwy, SignMc). Its own feature(s).
2. PRETTY SIDEBAR phase: reformat/animate/colorise sidebar_v3 on this data
   foundation — project->feature->task grouping for concurrent features; the 5-phase
   accordion (active phase open / others closed; soft-red/green + filled/empty circle;
   no spinner on the open feature; collapse to name+emoji on outcome; subtasks FYI,
   no colour). The 5 phases are a UI MAPPING of the raw states, NEVER courier data.
3. FAN-OUT CUT-OVER: DEFERRED until sidebar_v3 reaches parity — the tracked
   sidebar_model.py reads courier INBOXES for identity/status, so killing the fan-out
   first blinds it. Then replace v1's fan-out announce/broadcast with topics
   (+ unicast-to-parent), killing the token leak. depart fan-out is already safe to
   remove; test_bus.py broadcast + test_bus_traffic role tests need updating.

## Changelog entry

Added a sanctioned agent-activity transport for the fleet sidebar. Agents post
lifecycle, status, delegation and outcome events (and the gardener a
task-outcome) through one script, `orchard_topic.py`, into user-wide topic
directories — validated absolutely, each event carrying the agent's identity and
live status, never touching another agent's inbox. A new `sidebar_v3.py` reads
those topics to show, per project, what each session is doing and its
queued/active subtasks, waking no agent.

## Readme delta

Developer-tooling note (not app behaviour): `tools/orchard_topic.py post
<lifecycle|status|delegation|outcome|task> ...` is the only sanctioned writer of a
project topic; `tools/sidebar_v3.py [--once]` renders the active projects and their
sessions from those topics.

## Decision entries

Decision-NNN #courier #transport #sidebar — The project topic is DATA, not UI. Agent
events carry raw state (lifecycle/status/delegation/outcome) plus the two fixed
operations the courier answers itself and the agent never sees: IDENTITY (immutable —
session, agent, feature, name, parent) and STATUS (mutable — model, tokens, spend).
The 5-phase display is a UI-side MAPPING of the raw states, never a field on the
courier. (Operator, 2026-07-25.)

Decision-NNN #courier #transport — A task is complete only when the GARDENER says
so: `orchard:task:outcome:completed|failed` is gardener-only, enforced by the
sender's identity at the script; agent-level `outcome:success|fail` is separate.
(Operator, 2026-07-25.)

Decision-NNN #sidebar #topics — A project = the git repo (via --git-common-dir), so
every worktree of a repo posts to one topic directory; the first poster is the
gardener and becomes the project header; a project appears only when someone
posts to it. (Operator, 2026-07-25.)

## Architecture delta (trigger fired: component added + new data flow)

New component pair: `orchard_topic.py` (sanctioned topic poster / event producer)
and `sidebar_v3.py` (topic consumer). New data flow: agents -> user-wide
`$XDG_RUNTIME_DIR/orchard/topics/repository/<repo>/` -> the sidebar, decoupled from
the inbox courier (no fan-out, no agent woken). Coexists with the legacy inbox transport
until the fan-out cut-over (follow-up 3). Groundskeeper: reflect the topic-transport
component + data flow in ARCHITECTURE.md.

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
  typed one-liners, `Subject:<type>`, payload in body; the courier subagent stays;
  broadcast → topics (v1 `global` only). Addresses From `:session:<id>`; To
  `:session:<id>` (authorized) | `:topic:<name>` (fixed list, daemon-signed).
  Types: status (word + optional 0–100 + text) · outcome success|fail ·
  lifecycle (payload = display minimum: location + project) · delegation
  begin|end · operator relay (unicast) · courier subscribe|unsubscribe (folder +
  monitor lifecycle). Prefix orchid:→orchard: (rides the rename). Identity
  never rides the courier — derived locally from the worktree/CLI.
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
- THE ONE SCRIPT: every courier interaction goes through ONE Python script. It
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
- AGENT SIDE: a small table — when X happens, ask your courier to post Y. The
  courier sidecar discovers all metadata itself; the parent agent does nothing
  and never learns a path, a format, or an ordering rule.
- THE EVENT LIST IS THE DOCUMENTED ONE (operator: "an agent can only
  advertise the events in my document and only those; extension possible
  as needed to fill gaps"): the lifecycle vocabulary already shipped by
  the v1 rounds — `started · building · testing · done · finished ·
  blocked · abandoned` (`LIFECYCLE_STATES` in bus.py; wire grammar,
  agents/bus.md; rounds record in [[bus-message-specifying]]). The two
  moments he described map onto it: an agent appears = `started`; has
  completed / reached stopped = the terminal states. The earlier
  `appeared`/`completed` tokens in this record were agent-minted and are
  DEAD — the topic speaks the documented list.
  OPEN (his, unreconciled — do not resolve): he also said "four different
  messages" for the sidebar; the documented list has seven states. Which
  states the project topic admits and what the sidebar's filter reads is
  his reconciliation to make.
- HIERARCHY (operator, 2026-07-25): project = the git repo; feature =
  (branch, gardener session id); any other agent = (name, session id,
  parent when needed).
- CHANNELS (operator, 2026-07-25): (1) SendMessage between two RELATED
  agents (parent↔child); (2) broadcast status on topics, for tracking and
  telemetry; (3) SendMessage between UNRELATED agents is managed by
  seb.house — delivered to its board 2026-07-25, out of scope here.
- LIVENESS (operator, ruled so far): following an agent's liveness serves
  exactly two scenarios — (1) the end of a feature's time, (2) displaying
  nicely in the sidebar. Candidate additions offered to the operator are
  UNRULED and not part of this design until he rules.
- SUBSCRIPTION IS A FILTER (operator, 2026-07-25): orchard sees a new
  folder appear in a project and subscribes with a filter on the TYPE of
  message to read — messages of other types are discarded at SCRIPT level,
  not courier level.
- FULL BROADCASTS ARE FORBIDDEN (operator): no broadcast to all — only
  posting to topics. (Kills v1's fan-out-to-every-inbox model.)
- MTIME PER AGENT AND PER PROJECT (operator): mtime preserved per agent
  and per project — if the mtime of a child dir is updated, the script
  updates the mtime of the parent dir too. Rationale, his: only orchard
  cares about the various projects, so the model works.
- REQUEST/RESPONSE (operator): deleted by the script upon reading.
- TOPIC/BROADCAST MESSAGES (operator): pruned regularly by the script, as
  they have a timestamp. (Narrows pending question (c): a timestamp for
  pruning is RULED; whether it is the file's own mtime or a field is the
  remaining sliver.)
- SIMPLICITY IS THE SCOPE (operator): "we can do more advanced in the
  future with FIFO or otherwise, but we're trying to keep this simple" —
  no FIFO, no advanced delivery machinery in this design.
- EVENTS ONLY, FLAT (operator, 2026-07-25 05:1x): an agent may advertise
  ONLY the events in the operator's document — nothing else rides the courier;
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
- PERMISSION REALITY: courier subagents' Bash calls ride the auto-mode
  classifier (nothing courier-related is allowlisted); a courier was already denied
  running the stopgap once. Surface permission walls to the operator —
  never self-allowlist (the classifier blocks it, correctly).

## Proposal

The transport is the layer ABOVE v1's vocabulary: v1 is what a message SAYS;
v2 is who it reaches, on what topic, sealed how, admitted by whom. The
operator is feeding this design ONE ITERATION AT A TIME — the landscaper
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
- The courier contract's table (agents/bus.md) keeps exactly the two named
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
- Current courier is PER-REPO (spool under each repo's git dir) — cross-repo
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
through the courier alone, no git/filesystem polling ([[bus-close-cleanup]]).

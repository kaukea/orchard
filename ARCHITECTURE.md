# orchids — architecture

The **how** behind [README.md](README.md)'s why and what. Designed as
Decision-075/076 in the originating fleet's decision log; this page is the
package-resident summary.

## The operating model — one pipeline, walked by real agents

```
bloom → [Questions] → select → [pick-HOW] → build·test loop
      → [sudo/on-box] [manual-test] → [MAKE IT SO] → close
```

A **gate** (bracketed) is a decision or capability point. The pipeline advances
as far as policy allows, then **parks** in the task's sidecar, recording what
it needs. Operator present = parks cleared in seconds; operator away = the run
stops at the first gate it cannot pass. Same machine either way — presence only
changes latency. `manual-test` and `MAKE IT SO` never auto-pass: testing and
build approval are human-only, always.

## Roles and dispatch

| Role | Model | Dispatch | Scope & boundary |
|---|---|---|---|
| gardener | opus | top-level session (`claude --agent gardener`) | Knows the board, prioritises, holds MOOD, launches ONE supervisor (its own subagent) per feature on explicit operator go and hands it that feature; the supervisor owns the feature's pipeline. Never codes; never opens a sidecar in steady state. Authors only the workflow component, directly on `main`. Never kills, reaps, or removes another agent's process, pane, window, or files — lingering state is reported to the operator, who rules on it. |
| bloomer | fable-5 | own pane inside the gardener's window (`tools/bloomer-launch.sh` / `bloomer-teardown.sh`) | The Decision-027 intake-measurement instrument: turns a two-to-three-sentence functional spec into a converged WHAT. Question selection and stopping are owned by the statistical engine `tools/bloom_engine.py` (EIG + IRT/Fisher-information selection, SE-threshold stop; item parameters flagged uncalibrated); phrasing and parsing by the LLM. Asks only on measured low confidence, records voluntary deferrals, and reports a graduated confidence band over the courier — the gardener executes any launch. Single-writer on its task's sidecar. Scheduled backlog-prep passes stay with the demoted predecessor definition until the repoint follow-up. |
| supervisor | sonnet | the gardener's own subagent, one per feature (Decision-068) | Owns ONE feature's pipeline from the gardener's launch to the result: EXTRACT next-agent context → SELECT & DISPATCH (spawns the landscaper as ITS OWN child, so the landscaper's lifecycle homes here) → WATCH the orchard lifecycle → fire the groundskeeper CLOSE → REPORT the result to the gardener and RELEASE what it created. Choreographs; never authors, never judges (Valve rules yes/no), never kills (Decision-081) — supervision COLLECTS. Death/timeout verification is its own; other agents "ask the supervisor." Carries NO Decision-085 role glyph — an internal gardener subagent, not a seventh garden role. |
| landscaper | opus | worktree session (`.claude/worktrees/<id>`, branch `f/<id>`), spawned by the supervisor as its own child | One feature; its sidecar is the whole scope — now a PURE SCOPE. Read-only discovery (parallel explorers) → plan agreed with the operator → **no file edit before MAKE IT SO** → builds/tests → on the operator's `THAT IS ALL`, countersigns and emits its terminal `lifecycle:stopped`+`outcome`. Dispatches no closer — the supervisor fires the close off that terminal signal. Never reads the board or prior conversation. |
| sower | sonnet | headless subagent from the landscaper | Exactly one step-spec; returns typed diff + self-test. |
| groundskeeper | sonnet | headless, in the MAIN repo, fired by the SUPERVISOR on the landscaper's terminal `lifecycle:stopped`+`outcome` (or the supervisor's verified silent-death verdict) | The deterministic close: verify docs, tag, squash-merge, push, remove worktree + branch. Verifies documentation, never authors it. |
| courier | haiku | one per agent, no session id of its own (shares its parent's) | Not on the pipeline — the sidecar that connects an agent to the message transport. Watches its parent's session mailbox, relays arriving messages up, sends on request. Owns the mechanism so no other role learns it. Closes only via a self-message wake, never an external kill (Decisions 041/046/081). Does nothing else. |

Isolation is per-dispatch (native worktrees), not a per-repo mode. One writer
per task, always.

Pipeline ownership is the **supervisor's**: the feature-close no longer
originates in the landscaper (self-dispatch) nor in the gardener
(dispatch-at-relay) — the supervisor fires it, on the landscaper's terminal
`lifecycle:stopped`+`outcome` or on its own verified silent-death verdict, then
reports the result to the gardener. Supervision COLLECTS, never kills
(Decision-081); death and timeout verification live with the supervisor, and
other roles ask it rather than checking themselves.

## The cloud path

The same pipeline ridden on GitHub events instead of a local session
(Decision-027): the feature is an issue, the gates are operator comments, the
close is a squash-merged PR.

`.github/workflows/cloud-path.yml` stays dumb — detect, gate, invoke. Every hop
cold-starts a headless role (`claude -p --agent <role>`) on a runner; state
lives only in the issue thread and the sidecar on `f/<id>`, so no hop ever
waits. Comments are actor-gated to the operator. Gate vocabulary: `ENGAGE`/⚙
kicks off, `MAKE IT SO`/🖖 builds, `THAT IS ALL`/🚪 closes; any other operator
PR comment revises.

| Cloud role | Model | Hop | Scope & boundary |
|---|---|---|---|
| gardener-cloud | haiku | `ENGAGE` → prologue | Resolves issue → task id (board `gh#` badge), checks the sidecar is ripe, flips the board to `doing` (its only `main` write, `docs/TODO.md` alone), creates `f/<id>`. Never plans or builds. |
| landscaper-cloud | opus | PLAN · BUILD · REVISE | Authors the tech plan and plan comment; on `MAKE IT SO` builds, tests, authors close docs, opens the PR (`Fixes #n`); revises on review comments. Never merges, never writes the board, never self-emits a gate. |
| groundskeeper-cloud | haiku | `THAT IS ALL` → close | Verifies the close-docs gate, amends, tags `archive/<id>`, `gh pr merge --squash`, commit-count note. The only role merging feature work into `main`; engages once, post-approval. |

Runners have no kauk: each job overlays `agents/` and `skills/` into `.claude/`
(the committed symlinks point into the untracked `.ai/` clone). Auth has two layers: the Claude CLI runs on the
operator's subscription OAuth token (`CLAUDE_CODE_OAUTH_TOKEN` secret), while every
GitHub action (comment, commit, PR, push, merge) is signed by **`callabloom[bot]`** —
a kaukea GitHub App token minted per hop from org secrets (`CALLABLOOM_APP_ID` /
`CALLABLOOM_PRIVATE_KEY`), falling back to the built-in `github.token` when absent.
`issue_comment` fires only from the default branch — pre-merge, hops are
exercised via `workflow_dispatch` (inputs: hop, issue). Intake and blooming stay
manual issue comments on this surface — GitHub has no iterative-survey
primitive, so the bloomer instrument is local-pane only; operator-less
statistical kick-off on the cloud surface is deferred with it.

## The message courier

A cross-cutting channel between top-level sessions, orthogonal to the pipeline —
no role depends on it to do its own job, and it belongs to no single agent type.

```
session ──spawns──> courier sidecar (shares parent's session id)
                          │                        │
        own mailbox scan ┘        orchard runtime tree:
                                   $XDG_RUNTIME_DIR/orchard/{projects/<repo>.<project>,topics/<name>}/
   arriving message ─────────────────────SendMessage───────> its own parent
```

- **Address** = the session id (`CLAUDE_CODE_SESSION_ID`), never derived from
  location. Role and worktree are separate facts, not folded into the address.
  A courier sidecar carries no session id of its own — it always resolves to
  its parent's.
- **Transport** = flat message files plus a per-session marker under the
  USER-WIDE runtime tree `$XDG_RUNTIME_DIR/orchard/{projects/<repo>.<project>,
  topics/<name>}/`, named `<sessionid>.<ts>.json` (+ `<sessionid>.marker`).
  tmpfs, per-user, and crosses repos by construction — the ONLY transport. The
  repo-scoped `the-works/courier/<sid>/` inboxes it replaced were REMOVED
  outright (2026-07-27): `--git-common-dir` is shared by every worktree, and a
  subagent inherits its parent's session id, so concurrent worktrees resolved to
  one box and could delete each other's inbox. A project directory is keyed
  `<owner>.<repo>@<branch>` — one per worktree, so agents on different features
  do not wake one another's monitors; the sidebar folds them back to one row.
- **Addressing**: `From` is always `:session:<id>`. `To` is `:session:<id>` (a
  directed message — a cross-project delivery is gated by the
  `~/.config/orchids/sidebar-registry.json` allowlist) or `:topic:<name>`. A
  directed session message is delete-on-read; `request`/`reply` give a
  blocking round trip.
- **The fan-out is killed** — there is no broadcast to every inbox any more
  (it was the token leak). Instead: status/lifecycle/outcome/delegation
  telemetry are TOPIC posts (`orchard_topic.py post ...`) into the project
  layout, which is the sidebar's feed; a lifecycle `signal` to a parent is a
  DIRECTED `:session:<parent>` message (cross-repo via `ORCHID_PARENT_PROJECT`,
  the same allowlist gating as any other cross-project `:session:` send); an
  operator question is a directed request to the reserved `:session:operator`
  mailbox. The old `orchid:*` broadcast WIRE GRAMMAR v1 is retired.
- **Subjects** are a CLOSED corpus of 22 exact strings, validated by exact
  membership — no regex, no `startswith`, no derivation:
  `orchard:agent:{status, outcome:success|fail,
  lifecycle:starting|started|stopping|stopped, delegation:schedule|begin|end,
  message:request|response|content}`, `orchard:bus:{subscribe,unsubscribe}`,
  `orchard:operator:message:{todo,instructions,request,response,content}`,
  `orchard:task:outcome:{completed,failed}` (gardener-only, enforced in both
  `courier.py` and `orchard_topic.py`). Variable data (a delegation subagent
  id, a subscribed topic) lives in the BODY, never the subject.
- **Liveness**: the per-session `<sessionid>.marker` mtime is the heartbeat —
  every write touches the marker and bumps the parent project directory's
  mtime too. Consumers scan or poll; an agent monitors its own session
  mailbox. The courier is a per-agent singleton with NO session id of its
  own (it shares its parent's), and its close is a self-message wake →
  self-teardown, never an external kill (Decisions 041/046/081): the
  `SessionEnd` hook only drops a wake message into the mailbox the courier's
  own watch is already on — it never tears anything down on the courier's
  behalf.
- **Compaction**: messages older than 120 minutes are zipped into a
  persistent archive under `$XDG_CACHE_HOME/orchard/archives/`, gated cheaply
  by a `.compacted` sentinel file so the hot path costs one mtime check
  (`tools/orchard_compact.py`).
- **Exception: `courier.py ask`** blocks for a reply — the one deliberate
  departure from "no delivery guarantee," used to put a question to the
  operator. It sends a directed orchard request to `:session:operator`;
  `tools/orchard-question-broker.py` is a narrow, token-free broker (a plain
  process, never an agent, mounted per tmux server by
  `tools/orchard-question-broker-mount.sh`) that drains that mailbox, defers
  popping while the operator has input in flight, pops a native tmux popup
  accepting only the defined option keys, and answers back over the same
  request/reply mechanism (`in_reply_to`) — none of that policy is exposed to
  the asking agent. A `Notification` harness hook backstops harness-native
  prompts that bypass this path.
- **No supervision kills** (operator ruling, 2026-07-25): no agent ever kills,
  reaps, or removes another agent's process, pane, window, or files — killing
  corrupts state and hides bugs. Agents start and stop themselves (self-teardown
  is each agent's own last act); whatever a dead agent leaves behind is reported
  to the operator as observed state, never cleaned up unilaterally. A lifecycle
  `signal` is always attributed to the caller's own session — signing as another
  session does not exist.
- **No delivery guarantee** outside `request`/`reply`/`ask`. An ordinary
  directed send is ephemeral, unacknowledged, and delete-on-read; a sender
  expects no answer and chooses to retry, abandon, or error.
- `identity` (immutable) and `status` (mutable — context occupancy and token
  spend) are answered by the sidecar off the parent's transcript, so they cost
  the parent no context and keep answering while it is busy or wedged; the
  same snapshot rides every `orchard_topic.py` event, so a topic consumer
  needs nothing else.
- **Operator approvals relay** as a distinct operator-origin class: an approval
  typed outside an agent's own window (e.g. in the gardener pane) is forwarded
  verbatim with an `operator_origin` flag, which a gate-waiting agent accepts as the
  operator's own word — ordinary peer traffic never closes a gate (Decision-047).

## The fleet sidebar

A pinned left pane in every gardener and landscaper window, mounted at launch
(`tools/sidebar-mount.sh`, idempotent and strictly best-effort). One renderer per
mount, all showing the same global picture.

```
$XDG_RUNTIME_DIR/orchard/projects/<repo>.<project>/<sessionid>.<ts>.json
                        │ build_model(): fold per-session events (identity/status snapshot on each)
                        ▼
                    Fleet/Repo/Feature/Subagent ──flatten──> sidebar.py (curses)
                                                                │ Enter
                                                                └─> sidebar_nav ──> tmux switch
```

- **`tools/sidebar.py` renders; `tools/sidebar_model.py` builds the model it
  renders.** The renderer owns the pure-text Row/render pipeline, the curses
  draw layer, and the CLI; it imports `build_model()`/`watch()` and every data
  class (`Fleet`/`Repo`/`Feature`/`Subagent`) from `sidebar_model.py`, never
  the other way round. `sidebar_model.py` reads the `projects/<repo>.
  <project>/` event layout directly, folds each project directory's event
  files into one record per session (latest of each kind wins), and
  assembles the Fleet/Repo/Feature/Subagent model — identity and role/model
  come off the identity/status snapshot every `orchard_topic.py` event
  carries, not a separate observation step. It never imports curses and
  never formats a string for a screen. A module of this name existed once
  before, as the old courier-inbox reader, and was deleted in the
  bus-finishing rewrite; this is a new module with a different job,
  extracted back out of `sidebar.py` so the renderer is no longer also the
  model builder. `sidebar_v3.py` (the topic-only prototype) stays deleted.
  `tools/sidebar_sim.py` is a fleet-event simulator: it writes a
  deterministic multi-project event tree, in the same on-disk shape
  `orchard_topic.py` produces, into an isolated runtime directory, so the
  sidebar can be developed and judged against a populated fleet instead of
  sparse live data; it refuses outright to write into the live runtime tree.
  Updates are event-driven (inotify on the projects root), polling-fallback
  otherwise.
- **`tools/sidebar-live.sh` is the acceptance surface for a sidebar branch under
  development, and it is a supervisor rather than a renderer.** A sidebar cannot
  be judged from inside the branch that changes it, and it cannot be judged from
  a pane opened before the change either; both its behaviour and its appearance
  are only visible while it runs. The script occupies a pane, follows its
  checkout's HEAD, and on each new commit exports that exact commit to a clean
  tree and runs the renderer from there. Two properties are the reason for the
  indirection. It tracks COMMITS, never the working tree, because a running
  renderer goes blank when its own source file changes underneath it — the
  process survives, nothing is logged, the display simply empties — so a
  half-saved file would otherwise present as a rendering fault. And the pane
  title names the commit on display, which is what makes a verdict given on the
  pane a verdict on known code (Decision-112). The renderer is unmodified and
  knows nothing about the supervisor.
- **Retention is COLOUR, not removal.** Nothing ever ages off the bar: a
  working session renders normally; a terminal outcome (success/fail, or the
  gardener-only task outcome) becomes a PERSISTENT one-liner — green for
  success, red for fail — that a later staleness check can no longer demote;
  a session with no event inside the ~1 hour active window and no terminal
  outcome yet renders GRAY ("not heard from in a while") instead of being
  dropped. Rows persist until a process restart clears the tmpfs projects
  tree — predictable, since a row never jumps in or out of the bar for no
  reason.
- **Renders the approved display grammar** (fixed visual contract: the blessed
  mock archived with the courier-message-specifying stream). Repo headers are solid
  per-repo hue blocks; a feature is ONE line — its name drawn over the progress
  fill derived from the phase channel, right-aligned percentage. One circle
  family carries state: ✓ done (green, sorted to top, retained), ⠧ active,
  ○ waiting/todo — no watch or timer glyphs; a stale/failed row falls back to
  the same muted/red treatment (see Retention above). The live feature line
  carries the frame's single animated element, a bidirectional lifted-band
  sweep; beneath it the small-caps phase label, the NBSP-glued identity line
  (status word ⋮ role ⋮ model on the model colour ramp), the five-phase
  checklist with inline subagent dots (● running, ○ queued — count is the
  information; done subagents vanish), and dim guide-line footers (age vs
  worked, tokens/dollars — deterministic zero-token local sources).
  Role-emoji and location-badge maps are data-driven so pending picks drop in
  without code changes. The event grammar this model reads (`orchard_topic.py`'s
  `lifecycle`/`status`/`delegation`/`outcome`/`task` verbs) carries no phase
  tick, question badge, or age/worked/tokens/dollars signal yet — those row
  fields stay in the model (so the renderer needs no special-casing once a
  source lands) but currently always render at their empty default; the `?N`
  question badge is retired outright (questions no longer reach a feature
  row at all — see below).
  A scroll offset follows the selected row once the tree exceeds the pane's
  height. The project header is a static half-block colour-gradient bevel (the
  classic orchid family), flat light-gray instead for a paused project. Each
  live agent gets a stable colour from an 8-entry orchid-species palette,
  degrading gracefully on a limited terminal. Truncated text ends in an ellipsis,
  never a hard cut. Role names appear nowhere; structure carries the role.
- **Navigates** by matching the tmux window name — the bare repository name for a
  repository's gardener, `<repo> ▸ <human name>` for a feature (the
  session-naming display forms, Decision-032). The human name is read from the
  board's authored short title (`docs/TODO.md`) / sidecar H1 — never a runtime
  grammar transform — falling back to the mechanical hyphen-to-space form only
  pre-intake (`tools/feature_name.py`, one helper, every title call site).
  Switching the client happens on Enter. Windows carry the human-readable
  identity. Teardown and reaping key off a stable `@landscaper_id` tmux **window**
  user-option, set on the landscaper window at launch — immune to the live
  status-glyph indicator that clobbers pane titles. `land:<id>` survives only as
  a non-load-bearing human hint on the pane title. `@landscaper_id` is the small stable
  handle contract the sidebar mount also consumes.
- **Mounted automatically** at the gardener's own boot, in addition to the
  existing per-landscaper-spawn mount — no manual step either way
  (`tools/sidebar-mount.sh`, idempotent).
- **Operator questions** no longer surface as a row badge (above): they go
  through the tmux popup broker, `tools/orchard-question-broker.py`, mounted
  once per tmux server by `tools/orchard-question-broker-mount.sh`. The
  broker reads `:session:operator` mailboxes directly — it is a CONSUMER of
  the message transport, not a subject or a field on the sidebar's own event
  grammar.
- Components in `tools/`: `sidebar.py` (the ONLY renderer — draws the model,
  `sidebar_v3.py` stays deleted), `sidebar_model.py` (the model layer: event
  folding, registry reading, tree assembly, imported by `sidebar.py`),
  `sidebar_sim.py` (fleet-event simulator for development and testing),
  `sidebar_nav.py` (navigation), `sidebar-mount.sh` (mount), `sidebar-live.sh`
  (per-commit acceptance surface for a branch under development), `feature_name.py`
  (ledger name resolution), `orchard-question-broker.py` +
  `orchard-question-broker-mount.sh` (the ask popup broker, above). Hide/show
  visibility is retired (operator ruling, 2026-07-25): `build_model()` (in
  `sidebar_model.py`) folds every directory under the projects root
  unconditionally, filtered only by whether it has a live session (see
  Retention above).

## The sidecar contract

Durable state lives in files; no role depends on chat history.

- `docs/TODO.md` — the slim board index, one badge line per task.
- `docs/TODO.md.d/<id>.md` — the task's **sidecar**, the single spine every
  role reads-and-advances: `Blockers / Questions / Findings / Proposal /
  Testing`. Formats in `AGENTS.files.md`.
- `docs/decisions.md` — rulings, greppable by `#keyword`; each entry also
  mirrors to GitHub as its own `Decision`-typed issue (`tools/board_gh.py`,
  same push pass as tasks) — a superseded entry closes there natively as a
  duplicate of the decision that replaced it, so the file's strike/pointer
  convention becomes real, traversable issue state instead of prose a reader
  has to eyeball.
- workstream logs (per-session, rolling) / `MOOD.md` — uncommittable by
  construction, kept in `$(git rev-parse --git-common-dir)/the-works/`.

Converting a live conversation into this model is a one-time distillation:
scope → `Proposal`, test method → `Testing`, open items → `Questions` /
`Blockers`, learnings → `Findings`, rulings → `decisions.md`, in-flight code →
committed on `f/<id>`. Then the session ends and the agents boot cold.

## Distribution (kauk)

orchids is a passive package; [kauk](https://github.com/serialseb/kauk)
installs and syncs it. An operator says **"install kauk/orchids"**; the agent
resolves the repo on GitHub and follows `Agent-installation.md`. In short:

1. kauk is vendored at `.ai/repositories/serialseb/kauk`.
2. `kauk init` writes `.ai.toml` and lays kauk's own skill.
3. `kauk install serialseb/orchids <origin>` clones the package, migrates
   existing files (byte-identical → symlink; project-only → adopted; diverged
   → preserved in history), and lays entries per `manifest.conf`.
4. `kauk sync` runs at workflow start and end.

This repository is also the package's own SOURCE, and does not install
itself as one of its own consumers: `.ai.toml` here carries no
`[sources."serialseb/orchids"]` entry, and every `.claude/**` link resolves
directly to this repository's own files. It did once, from `5fee5a7` until
2026-07-27, which meant every agent, skill, hook and tool executed a
vendored clone of the repository rather than the repository itself — the
clone sat several commits behind, across a whole transport rewrite, so
editing this repo's own code changed nothing about what actually ran until
somebody happened to sync, and no worktree could run its own code either,
since the links were absolute. `migrations/2026-07-27-unvendor-self.md`
converges any other clone still carrying the old self-referential entry.

`manifest.conf` line types: `skill <name> <role>` (delivery tuned per-repo in
`.ai.toml` by role section: `exclude|copy|link|local`), `link` (absolute
symlink, everyone), `template` (install-time copy, then project-owned),
`prefix` (block kept at the head of a project file).

## Repo layout

```
agents/            five pipeline roles + supervisor subagent + courier sidecar (→ .claude/agents/)
skills/<name>/     SKILL.md packages (→ .claude/skills/, per role)
hooks/             courier-init.sh · courier-end.sh (→ .claude/hooks/)
tools/             board_lint.py · board_stale.py · courier.py · orchard_topic.py · orchard_compact.py · orchard-question-broker.py · landscaper-teardown.sh · sidebar.py · sidebar_nav.py · sidebar-mount.sh (→ .claude/tools/)
templates/         AGENTS.md (template) · CLAUDE.md (prefix block)
migrations/        dated structural-upgrade instructions (YYYY-MM-DD-<slug>.md); applied
                   per clone against the .git/the-works/migrated watermark
AGENTS.shared.md   fleet-wide non-negotiable rules (linked)
AGENTS.files.md    file-format contracts: board, sidecars (linked)
settings.json      shared Claude Code settings (linked)
manifest.conf      what this package exposes, one typed line per entry
Agent-installation.md  the agent-facing install procedure
docs/              orchids' own board (TODO.md + sidecars)
```

## Taxonomy

The controlled vocabulary the board draws from (`AGENTS.files.md` §TODO): the
functionality is the board heading's first word; each leaf task carries exactly
one of its areas. `board_lint.py` enforces membership from this table —
the single source; agents do not invent values.

| Functionality | Areas |
|---|---|
| **Publication** | publication |
| **Process** | process |
| **Role** | sync · process |
| **Skills** | skills |
| **Future** | sync |

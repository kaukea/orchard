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
| orchestrator | opus | top-level session (`claude --agent orchestrator`) | Knows the board, prioritises, holds MOOD, hands ONE feature to an architect on explicit operator go. Never codes; never opens a sidecar in steady state. Authors only the workflow component, directly on `main`. Enforces the exit-grace lifecycle contract: kills a session that overruns its own declared window past its terminal signal, broadcasting that signal on its behalf. |
| bloomer | fable-5 | own pane inside the orchestrator's window (`tools/bloomer-launch.sh` / `bloomer-teardown.sh`) | The Decision-027 intake-measurement instrument: turns a two-to-three-sentence functional spec into a converged WHAT. Question selection and stopping are owned by the statistical engine `tools/bloom_engine.py` (EIG + IRT/Fisher-information selection, SE-threshold stop; item parameters flagged uncalibrated); phrasing and parsing by the LLM. Asks only on measured low confidence, records voluntary deferrals, and reports a graduated confidence band over the bus — the orchestrator executes any launch. Single-writer on its task's sidecar. Scheduled backlog-prep passes stay with the demoted predecessor definition until the repoint follow-up. |
| architect | opus | worktree session (`.claude/worktrees/<id>`, branch `f/<id>`) | One feature; its sidecar is the whole scope. Read-only discovery (parallel explorers) → plan agreed with the operator → **no file edit before MAKE IT SO** → builds/tests → on the operator's `THAT IS ALL`, countersigns and signals `finished` on the bus. Never reads the board or prior conversation. |
| builder | sonnet | headless subagent from the architect | Exactly one step-spec; returns typed diff + self-test. |
| housekeeper | sonnet | headless, in the MAIN repo, dispatched on the architect's `finished` signal | The deterministic close: verify docs, tag, squash-merge, push, remove worktree + branch. Verifies documentation, never authors it. |
| bus | haiku | one per session, loaded at session start | Not on the pipeline — the sidecar that connects a session to the message bus. Announces its parent, watches its inbox, relays messages up, sends on request. Owns the mechanism so no other role learns it. Does nothing else. |

Isolation is per-dispatch (native worktrees), not a per-repo mode. One writer
per task, always.

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
| orchestrator-cloud | haiku | `ENGAGE` → prologue | Resolves issue → task id (board `gh#` badge), checks the sidecar is ripe, flips the board to `doing` (its only `main` write, `docs/TODO.md` alone), creates `f/<id>`. Never plans or builds. |
| architect-cloud | opus | PLAN · BUILD · REVISE | Authors the tech plan and plan comment; on `MAKE IT SO` builds, tests, authors close docs, opens the PR (`Fixes #n`); revises on review comments. Never merges, never writes the board, never self-emits a gate. |
| housekeeper-cloud | haiku | `THAT IS ALL` → close | Verifies the close-docs gate, amends, tags `archive/<id>`, `gh pr merge --squash`, commit-count note. The only role merging feature work into `main`; engages once, post-approval. |

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

## The message bus

A cross-cutting channel between top-level sessions, orthogonal to the pipeline —
no role depends on it to do its own job, and it belongs to no single agent type.

```
session ──spawns──> bus sidecar ──announce──> every peer's inbox
                          │
   inbox events ──────────┘──SendMessage──> its own parent
```

- **Address** = the session id (`CLAUDE_CODE_SESSION_ID`), never derived from
  location. Role and worktree are separate facts, not folded into the address.
- **Transport** = one JSON file per message under
  `$(git rev-parse --git-common-dir)/the-works/bus/<session-id>/`, so every
  worktree of a repo shares one bus and nothing is committed. The set of folders
  IS the registry; there is no broker for ordinary traffic.
- **Exception: `bus.py ask`** (sidebar-polish, a lean trial) blocks for a reply —
  the one deliberate departure from "no delivery guarantee," used to put a
  question to the operator. `tools/orchard-question-broker.py` is a narrow,
  token-free broker (a plain process, never an agent) that watches for question
  envelopes, defers popping while the operator has input in flight, pops a
  native tmux popup accepting only the defined option keys, and answers back
  over the bus (`send --in-reply-to`) — none of that policy is exposed to the
  asking agent. A `Notification` harness hook backstops harness-native prompts
  that bypass this path.
- **Exit-grace lifecycle contract**: an agent declares `exit_grace_seconds`
  (default 10) on its first announce — how long it needs, after signaling
  `finished`/`abandoned`, to release its bus and exit. The orchestrator kills a
  process that overruns its own declared window and broadcasts the terminal
  signal on its behalf (`signal --on-behalf-of`) so the sidebar still evicts its
  row. Distinct from the bus-singleton task (which reaps stray bus-sidecar
  folders specifically, not whole agent processes).
- **Membership** is established by hooks, not prompts: `SessionStart` creates the
  inbox, `SessionEnd` broadcasts a departure and removes it — so a send to a
  finished agent fails immediately instead of vanishing into an unwatched folder.
- **Only top-level sessions** are members. Subagents belong to their spawner and
  already have `SendMessage`.
- **No delivery guarantee.** Messages are ephemeral, unacknowledged, and die with
  the inbox. A sender expects no answer and chooses to retry, abandon, or error.
- `orchid:identity` (broadcast once, immutable) and `orchid:status` (pulled,
  mutable — context occupancy and token spend) are answered by the sidecar off the
  parent's transcript, so they cost the parent no context and keep answering while
  it is busy or wedged.
- Agents **broadcast on a specified vocabulary** — WIRE GRAMMAR v1, canonical in
  `agents/bus.md`, mechanically enforced by `bus.py` (any other `orchid:*` body is
  rejected at send). Five classes, each with a declared consumer:
  `orchid:status:<word>` (one/two agent-chosen doing-words, on change only),
  `orchid:update:<sentence>` (log/cockpit-targeted), `orchid:phase:<phase>[:<k>/<n>]`
  (the five-phase spine ideation→scoping→designing→building→releasing, from which
  the sidebar derives a live percentage), `orchid:subagent:queue|start|done:<label>`
  (counts are the message), and `orchid:interrupt:question:<subject>` (emitted only
  by `bus.py ask`). Exactly three DERIVED interrupts may summon the operator —
  QUESTION ⇐ ask, SUCCEEDED ⇐ done/finished, FAILED ⇐ abandoned/blocked+notify —
  and `--notify-user` is illegal everywhere else. Sidecars never author wire text
  of their own. `bus.py validate` audits recorded traffic against the grammar.
  No new mechanism: plain broadcasts on the same bus.
- **Operator approvals relay** as a distinct operator-origin class: an approval
  typed outside an agent's own window (e.g. in the orchestrator pane) is forwarded
  verbatim with an `operator_origin` flag, which a gate-waiting agent accepts as the
  operator's own word — ordinary peer traffic never closes a gate (Decision-047). A
  close reaches a bus as a **wake** (an inbound message resuming it), never a passive
  timeout; on that wake the bus tears down its own inotify watch before departing
  (Decisions 046, 041).

## The fleet sidebar

A pinned left pane in every orchestrator and architect window, mounted at launch
(`tools/sidebar-mount.sh`, idempotent and strictly best-effort). One renderer per
mount, all showing the same global picture.

```
bus (per repo) ──observed──> sidebar_model ──Fleet──> sidebar.py (curses)
                                                            │ Enter
                                                            └─> sidebar_nav ──> tmux switch
```

- **Reads the bus as a pure observer** across every repository the Orchard
  registry (`~/.config/orchids/sidebar-registry.json`, `tools/orchard_registry.py`)
  currently resolves as visible — never mutating a bus file. Installing orchids
  in a repo (`.ai.toml` presence) registers it there and it appears in every
  mounted sidebar immediately, no add command; hiding a repo is conversational
  (ask any agent, or `/orchard hide <name>`/`show`) and persists across remounts.
  `$ORCHIDS_SIDEBAR_REPOS` survives only as an explicit manual override. State is
  attributed by message sender and accumulated in memory, so it survives the
  bus's ephemerality; a sender's state is evicted once its terminal lifecycle
  signal is observed (paired with the exit-grace contract above so a killed
  agent's row still clears). Updates are event-driven (inotify), never polled.
- **Renders the approved display grammar** (fixed visual contract: the blessed
  mock archived with the bus-message-specifying stream). Repo headers are solid
  per-repo hue blocks; a feature is ONE line — its name drawn over the progress
  fill derived from the phase channel, right-aligned percentage, dim-amber `?N`
  badge when questions wait (never red). One circle family carries state: ✓ done
  (green, sorted to top, retained), ⠧ active, ○ waiting/todo — no watch or timer
  glyphs. The live feature line carries the frame's single animated element, a
  bidirectional lifted-band sweep; beneath it the small-caps phase label, the
  NBSP-glued identity line (status word ⋮ role ⋮ model on the model colour ramp),
  the five-phase checklist with inline subagent dots (● running, ○ queued —
  count is the information; done subagents vanish), and dim guide-line footers
  (age vs worked, tokens/dollars — deterministic zero-token local sources).
  Role-emoji and location-badge maps are data-driven so pending picks drop in
  without code changes.
  A scroll offset follows the selected row once the tree exceeds the pane's
  height. The project header is a static half-block colour-gradient bevel (the
  classic orchid family), flat light-gray instead for a paused project. Each
  live agent gets a stable colour from an 8-entry orchid-species palette,
  degrading gracefully on a limited terminal. Truncated text ends in an ellipsis,
  never a hard cut. Role names appear nowhere; structure carries the role.
- **Navigates** by matching the tmux window name — the bare repository name for a
  repository's orchestrator, `<repo> ▸ <human name>` for a feature (the
  session-naming display forms, Decision-032). The human name is read from the
  board's authored short title (`docs/TODO.md`) / sidecar H1 — never a runtime
  grammar transform — falling back to the mechanical hyphen-to-space form only
  pre-intake (`tools/feature_name.py`, one helper, every title call site).
  Switching the client happens on Enter. Windows carry the human-readable
  identity. Teardown and reaping key off a stable `@arch_id` tmux **window**
  user-option, set on the architect window at launch — immune to the live
  status-glyph indicator that clobbers pane titles. `arch:<id>` survives only as
  a non-load-bearing human hint on the pane title. `@arch_id` is the small stable
  handle contract the sidebar mount also consumes.
- **Mounted automatically** at the orchestrator's own boot, in addition to the
  existing per-architect-spawn mount — no manual step either way
  (`tools/sidebar-mount.sh`, idempotent).
- Components in `tools/`: `sidebar.py` (renderer), `sidebar_model.py` (bus
  reader), `sidebar_nav.py` (navigation), `sidebar-mount.sh` (mount),
  `orchard_registry.py` (repo registration/visibility), `feature_name.py` (ledger
  name resolution), `orchard-question-broker.py` (the bus-ask popup broker,
  above). `/orchard show|hide` is a skill (`skills/orchard/`).

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

`manifest.conf` line types: `skill <name> <role>` (delivery tuned per-repo in
`.ai.toml` by role section: `exclude|copy|link|local`), `link` (absolute
symlink, everyone), `template` (install-time copy, then project-owned),
`prefix` (block kept at the head of a project file).

## Repo layout

```
agents/            five pipeline roles + bus sidecar (→ .claude/agents/)
skills/<name>/     SKILL.md packages (→ .claude/skills/, per role)
hooks/             bus-init.sh · bus-end.sh (→ .claude/hooks/)
tools/             board_lint.py · board_stale.py · bus.py · architect-teardown.sh · sidebar.py · sidebar_model.py · sidebar_nav.py · sidebar-mount.sh (→ .claude/tools/)
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

# orchids — decisions

Append-only. Grep by `#keyword`; read the TAIL, never the whole file.

## [2026-07-16] Decision-001: History migration is an orchestrator charter, gated by the AGENTS.md `repository:` field
#history-rewrite #orchestrator #repository #orchids #gitflow #migration #subagent #parallel

**Context:** No role owned the `history-rewrite` skill — the orchestrator's
direct-on-main carve-out covered only the workflow component, and the architect's
scope is one feature sidecar, not every ref. Operator ruling (2026-07-16).

**Decision:**
- The orchestrator charters history migration — the one repo-wide surgery in its
  domain. No architect: the scope is the whole ref graph, not a feature.
- **Applicability gate:** the project `AGENTS.md` declares `repository:`. Only
  `orchids` (the canonical workflow shape; missing/empty counts as `orchids`) is
  eligible. Any other value (e.g. `repository: gitflow`) means the repo keeps its
  own branching model — agents never restructure its history.
- **Parallel prep, gated writes:** the skill's §0–§1 (sensitive sweep + partition
  proposal) are read-only and run as a background subagent while the orchestrator
  keeps working the board. All writes (§2+) wait behind operator gate #1; the
  partition, QES, and swap gates remain operator-only.

**Touched:** `agents/orchestrator.md` (new History-migration section),
`skills/history-rewrite/SKILL.md` (applicability gate + dispatch note),
`templates/AGENTS.md` (`repository:` convention).

## [2026-07-17 11:02 CEST] Decision-002: Delivery is driven by a task-oriented role DAG declared in the definitions
#roles #taxonomy #delivery #frontmatter #manifest #kauk #sync #context-economy #install

**Context:** Every session in every repo loads all 26 skill descriptions (~10.2 KB)
whether or not the work is relevant. `manifest.conf` already carries a `role` field
(`dev|infra|org|all`), but it is **inert**: kauk's `resolve_mode` (`bin/kauk:41-56`)
reads it only as a section name to look up in `.ai.toml`, never as a filter, and no
`.ai.toml` in the fleet defines a role section — so all 26 skills link everywhere.
Agents are worse: plain `link` lines, installed unconditionally with no identity.
Operator ruling (2026-07-17).

**Decision:**
- **Roles are task-oriented, never job titles** — `development`, not `developer`.
  Follows SFIA 9 (activity-noun categories) and NICE/NIST SP 800-181, which renamed
  its whole vocabulary in 2023 explicitly "to avoid being mistaken for job titles".
- **Authors declare the role, in the skill/agent definition's frontmatter** — not in a
  central table. The author of a skill knows what it is for; `manifest.conf`'s role
  field is retired as the home for this.
- **Roles form a DAG, not a flat list.** Nodes nest (`security` → `forensics`); a
  definition may declare several paths (`coding-tofu` is genuinely both
  `development/tofu` and `infrastructure/tofu`). A flat list forces false choices and
  presents one specific process as universal.
- **Selection installs the chosen node's subtree**, plus its ancestors' own skills.
  A node with children is selectable as the coarse pick.
- **Agents become first-class and may declare required skills** — a dependency the
  package can state, rather than an assumption (e.g. the workflow needs the groomer).
- **The HOW is kauk's, not orchids'.** orchids ships the vocabulary, the declarations
  and the dependency edges; the reader, the install-time picker, and the filter are
  kauk's. orchids is data-only, so this work lands as data even while kauk ignores it.
- **The vocabulary must not preclude unbuilt siblings** (e.g. a `process/kanban` beside
  `process/workflow`). Not built now; not designed out either.

## [2026-07-17 11:02 CEST] Decision-003: The orchids role vocabulary
#roles #taxonomy #vocabulary #sync #forensics #workflow #general #process #security

**Context:** The concrete node list implementing Decision-002, decided against the
existing 26 skills. Supersedes nothing — `dev|infra|org|all` was never a decision,
just an artifact (kauk's auto-adoption stamps every adopted skill `dev`,
`bin/kauk:272`). Operator ruling (2026-07-17).

**Decision:** the node list is

```
general            read-agents · agent-behaviour · authoring-skills ·
                   git (generic half)
process
  └ workflow       workflow · workflow-complete · handover · groom ·
                   orchestrator · history-rewrite · readme-sync ·
                   git (workflow-specific half)
  └ (kanban)       reserved sibling slot — unbuilt, must stay expressible
development        clean-code · diagnostics
  └ dotnet         coding-dotnet
  └ tofu *         coding-tofu
  └ lmstudio       coding-lmstudio
  └ file-formats   shortcut-file · reverse-engineering-files *
infrastructure     software-catalog
  └ tofu *         coding-tofu
security           digital-signature
  └ forensics      chain-of-custody · forensic-acquisition · read-apfs ·
                   machine-access · icloud · reverse-engineering-files *
```

`*` = multi-parent (the DAG rule, Decision-002).

Rulings embedded in the above, each a choice among live alternatives:
- **`general` is not `core`.** "Core" implies mandatory, which is what smuggled one
  specific process into every repo. What is actually universal is ~700 bytes.
- **The workflow is a child of `process`, not a universal.** `handover`, `readme-sync`,
  `workflow-complete` and the `Branch:`/main-immutable git rules are *our* process, and
  a repo running a different one must be able to decline them.
- **`security` is the node; `forensics` is its child.** Matches SFIA, which files
  `Digital forensics (DGFS)` under Security services. We do not promote a leaf to a
  root. `digital-signature` sits at `security` — signing is not forensics-only.
- **`infrastructure`, not `operations`.** The corpus is IaC/provisioning and contains
  zero run-it-in-production skills. The two names overlap badly; pick one. (Noted:
  `infrastructure` is industry vernacular — Spotify, GitLab — not SFIA/NICE vocabulary.)
- **`git` splits** — generic hygiene (gitmoji, subject/body limits, scope discipline)
  is `general`; the `Branch:` trailer, main-immutable, and the MAKE IT SO gates are
  `process/workflow`.
- **`doing-skills` is renamed `authoring-skills` and sits in `general`.**

**Open, deliberately not ruled here:** `write-to-s3`'s placement. Provisionally
`security/forensics`, but the operator flagged it as likely carrying private
information that must not be published — a publication question, not a taxonomy one.
See TODO `pre-publication-cleanup`.

**Gap noted, not fixed:** `ARCHITECTURE.md` has no Taxonomy table, though
`AGENTS.files.md` §TODO requires `functionality`/`component` to draw from it and
`board_lint.py` lints `value ∈ glossary`. The board's `publication` / `process` /
`sync` values are de facto only.

## [2026-07-17 14:36 CEST] Decision-004: Agent dependencies — agent→agent edges are declared, in a `requirements:` map
#agents #dependencies #frontmatter #role-delivery #install-flow #kauk

Two rulings, closing `agents-first-class`'s last open questions:

- **Agents declare dependencies on other agents**, not just on skills. The real graph
  has these edges (the orchestrator hands to architect/housekeeper/groomer; the
  architect dispatches builder), and an undeclared edge deploys a broken agent.
  Consequence for the two-page install flow: page 1 greys out agents required by a
  chosen agent, exactly as page 2 greys out required skills — the pull-in is legible,
  never silent.
- **The declaration is a `requirements:` frontmatter map with two sub-lists**, kinds
  explicit:

      requirements:
        agents: [builder]
        skills: [workflow, workflow-complete, handover]

  Chosen over a flat mixed list (would need a cross-folder uniqueness rule) and over
  typed ids (`agent:builder` — noisier). The map form takes a third sub-list later
  without disturbing these two — how `agent-external-deps` stays unprecluded while
  deferred.

Context, not ruling: the `roles:` key remains `role-dag-frontmatter`'s to settle; the
dependency contract no longer waits on it. The resolution/greying engine is kauk's
`agent-deployment`.

## [2026-07-17 14:49 CEST] Decision-005: Roles declare as slash-path placements; `general` is explicit
#roles #frontmatter #role-delivery #skills #agents #kauk #taxonomy

Three rulings, closing `role-dag-frontmatter`'s questions:

- **Key + syntax:** `roles:` is a list of slash-separated full paths —
  `roles: [development/tofu, infrastructure/tofu]`. Rejected: bare node ids
  (ancestry invisible at the declaration site), nested YAML and `role:` + `parent:`
  pairs (tree edges copied into every declarer).
- **Paths are placements.** A declared path is a deliberate placement, and a
  multi-parent node may be placed under a subset of its parents —
  `roles: [development/tofu]` alone is valid, making per-route delivery expressible.
  Lint verifies each declared path exists in the vocabulary; an incomplete set is
  intent, not an error class.
- **`general` is explicit** (`roles: [general]`). A missing `roles:` key is a lint
  error — "forgot to declare" is never readable as "deliberately general".

Context, not ruling: the vocabulary stays declared in exactly one place
(Decision-002/003). The sidecar's "one round with kauk before committing" was waived
by ruling directly; kauk's reader implements this contract as written.

## ~~[2026-07-17 15:08 CEST] Decision-006: Architect sessions live in panes; the close returns to a pane~~
> Superseded by Decision-036 (window per architect; subagents hidden by default, peekable into right-column panes).
#tmux #workflow #architect #handoff #orchestrator #panes

Three rulings on the dispatch machinery, after the first live dispatch landed on a
window when the operator had asked for pane-level behaviour:

- **Agent sessions spawn as PANES, not windows** — the architect splits from the
  orchestrator's own pane, so the build runs next to the conversation that dispatched
  it.
- **The close handshake is pane-scoped.** `.return-window` line 1 carries a pane id
  (`%N`); the Stop hook lands the operator on exactly that pane, then kills the
  architect's pane. Legacy window ids (`@N`) remain honoured. Window-scoped return
  was insufficient the moment a window held more than one pane.
- **The spawn carries the initial prompt.** A fresh `claude` session waits silently
  for its first message; a trigger the operator must remember to type is a trigger
  forgotten. The spawn line is `claude --agent architect 'Boot: …'`.

Context, not ruling: the workflow machinery (agent defs, hooks, this contract) is
authored only by the orchestrator, directly on `main` — Decision-065's existing
ownership rule, restated at the operator's request after the pane requirement failed
to survive as conversation memory. Requirements about the machinery belong in the
agent def and this file, nowhere else.

## [2026-07-17 16:02 CEST] Decision-007: Agents hold a standing write-right over linked package files
#kauk #symlinks #permissions #skills #settings #workflow

The harness refuses Edit/Write through a symlink ("Refusing to write through
symlink"), and no setting exists to change that (verified against current Claude
Code documentation, 2026-07-17). The kauk skill's "edit at the path you loaded it
from, never chase the target" is therefore unexecutable as written. Operator ruling:

- **Agents are authorised — and required — to write linked package files by
  resolving the symlink and writing the target** in
  `.ai/repositories/<owner>/<repo>/`. That is kauk's local-edit surface; `kauk sync`
  reconciles (commit → rebase → push back). In the package's OWN repo, mirror the
  change to the real source files (repo root) in the same turn, or run `kauk sync`
  so checkout and source converge — never leave the two divergent.
- **The refusal is a harness limitation, not a policy signal.** It is not a "no";
  agents do not stop or re-ask on it. The operator's permission here is standing.
- **The fleet `settings.json` ships allow rules** — `Edit(.ai/repositories/**)` and
  `Write(.ai/repositories/**)` — so the resolved-path write is neither denied nor
  prompted, and (via permission-rule merge into the sandbox writable paths) not
  sandbox-blocked either.

Follow-up owed upstream: amend the kauk skill text (pull-only, lives in
serialseb/kauk) — see TODO `kauk-skill-symlink-write`.

## [2026-07-18 18:34 CEST] Decision-008: Transients live in .git/the-works/; structural changes ship dated migrations
#the-works #handover #mood #migrations #watermark #git #hooks

Two rulings from the-works workstream:

- **The uncommittable channel is namespaced.** `HANDOVER.md`, `MOOD.md`, and the
  migration watermark live in `$(git rev-parse --git-common-dir)/the-works/` — same
  guarantees as the former flat `.git/` placement (physically uncommittable,
  worktree-shared), plus an identity that cannot collide with git's own files or
  other tooling. Writers `mkdir -p` the directory.
- **Every structural change to a managed artifact ships a migration.** One dated,
  state-guarded file in the package's `migrations/` (format:
  `AGENTS.files.md` §Migrations), in the same branch as the change. The package
  version IS the highest migration filename; a per-clone watermark
  (`.git/the-works/migrated`) plus a `settings.json` hook announce pending entries;
  the agent merges all pending migrations and applies the net effect once.
  Historical entries may be backdated to the change they describe — a repo that
  never had the package converges by running the whole series, no fresh-install
  special case.

Context, not ruling: skills describe only the current world; legacy-conversion
clauses belong in migrations, never in skill text.

## [2026-07-18 18:36 CEST] Decision-009: Cross-repo writes are gated, surface-bound, and never the suggested route
#kauk #permissions #settings #cross-repo #skills #agents #symlinks

Narrows Decision-007's third ruling (the blanket `Edit/Write(.ai/repositories/**)`
allow rules). Decision-007's other rulings stand: the resolve-the-symlink write
procedure remains the sanctioned mechanism, and the harness symlink refusal remains
a limitation, not a policy signal. Three rules, by strength:

- **Hard gate.** No standing write-right over `.ai/repositories/**` as a whole.
  Because `kauk sync` pushes package edits back upstream, a clone write is a
  cross-repository change propagating fleet-wide — the harness permission prompt is
  the authorization gate, per occasion, not standing.
- **Surface boundary.** The fleet `settings.json` allows frictionless writes only
  inside a package's content surfaces: `agents/`, `skills/`, `files/` (the
  direct-into-repo symlink folder — the rule attaches to the folder, whatever it
  holds). Machinery (`manifest.conf`, `settings.json`, `hooks/`, `tools/`, `bin/`)
  is never writable from a consuming repo; machinery changes happen only in the
  package's own repo, through its own workflow.
- **Reasoning norm.** An agent avoids even SUGGESTING edits to a repository it is
  not working from: capture the issue (TODO naming the source repo, or report to
  the operator) and let the fix ride the source repo's workflow (`agent-behaviour`
  skill). Decision-007's write-through path is used only on explicit operator
  direction.

## [2026-07-18 18:39 CEST] Decision-010: Micro-tasks may ride main, offered by the agent, gated by the operator
#workflow #micro-task #main #commits #branching

A one-commit triviality (typo, prose fix, one-line config value) does not earn the
full workflow machinery. The agent, judging a task micro — single commit, no design
choice, no meaningful testing question — OFFERS a direct commit on `main` up front;
the operator's acceptance IS the existing direct-commit override. The agent never
self-selects the path, and promotes to a full workflow the moment scope grows (a
landed micro-commit stays on `main`; the grown scope starts fresh). Such commits
carry `Branch: main` — the sole exception to the git-commit trailer rule.

## [2026-07-18 19:10 CEST] Decision-011: Per-session workstream logs replace the handover; promotion is the ingester's
#the-works #workstream-log #handover #session #reset #relay #single-writer #todo #decisions

Supersedes the monolithic `HANDOVER.md` mechanics (the channel location rulings in
Decision-008 stand; this changes what lives there). Rulings:

- **Every session keeps its OWN rolling log** in `.git/the-works/<stream>/`
  (`YYYYMMDD-HHMMSS-<role>.md`): State (rewritten in place), Findings, Dead ends,
  Decisions pending promotion, Pointers — written as work happens, never
  reconstructed at the end. One file per session; a session never edits another's;
  a stream reads oldest→newest. This makes a reset or agent change
  non-destructive: the successor reads the stream and continues.
- **Single-writer on main's docs.** The board (`TODO`) and `docs/decisions.md` are
  written only by the orchestrator / top-level session. Children stage rulings in
  their log's "Decisions (pending promotion)"; the ingester promotes them. A
  top-level session (no parent) self-promotes at its own close.
- **Ingest = promote → archive.** A `_closed` stream (marker file, announced by
  the shared hook) is read, promoted, then MOVED to `.git/the-works/_ingested/` —
  PROVISIONALLY retained, not deleted: commit messages and the changelog already
  carry the positive record, but dead ends and failures have no committed home;
  a few weeks of use decide whether that archive earns its keep (follow-up task
  `ingested-retention`).

## [2026-07-18 20:28 CEST] Decision-012: orchids publishes at the renamed aihelp repo; org lands on kaukea
#github #origin #remote #org #kaukea #aihelp #publish

The repo's GitHub home is the former `SafeKeepIt/aihelp`, renamed to
`orchids` — chosen over creating a fresh repo so the dotai-sync era
stays attached. Its history was grafted in via an `ours` merge
(unrelated histories, tree untouched): every aihelp file was a
superseded May–June draft, so nothing was content-merged. Public
visibility retained (kauk clones unauthenticated by default).

Org naming: `kauk.ai` is impossible (GitHub names can't contain dots,
one case-insensitive namespace) and `kaukai` — settled on kauk's board
— turned out to be held by a dormant 2022 user account, as is `kauk`
(release ticket filed). Ruling: the org name is **kaukea** (6 letters,
kauk-kin), picked from a 409-name availability sweep. The operator
creates the org in the web UI (no API exists); the repo then transfers
`SafeKeepIt` → `kaukea`, with GitHub redirects covering both the
rename and the transfer. Dormant-release requests for `kauk`/`kaukai`
may still upgrade the name later; a rename from `kaukea` redirects.

## [2026-07-18 22:55 CEST] Decision-013: Private until scrubbed — the publish gate is real
#github #visibility #publication #scrub #leak #kaukea #board

Amends the visibility clause of Decision-012 (its repo-home and org rulings
stand): kaukea/orchids and serialseb/kauk are PRIVATE, effective immediately.
Tonight's public window (~2.5h, full history, forensic skills included) is
treated as a leak per the operator. Re-publicizing anything requires, in
order: the pre-publication-cleanup public/private split, a history scrub of
whatever surface goes public, and an explicit operator go. The
pre-publication-cleanup push gate applies to visibility changes exactly as to
pushes; no future session flips a repo public as a side effect of another
task.

## [2026-07-19 20:15 CEST] Decision-014: An agent's address is its session id
#message-bus #identity #session-id #agents #bus

Agent identity is `CLAUDE_CODE_SESSION_ID`, read from the environment. The first
draft derived it from the working directory — a linked worktree became its feature
id, the main checkout became `orch`. That ignored the environment, which already
publishes the answer, and collided for any two sessions sharing a location: the
orchestrator and a groomer both resolved to `orch` and would have drained each
other's mail.

Role (`CLAUDE_CODE_AGENT`) and worktree stay SEPARATE fields rather than being
folded into the address. A session id is unique but not guessable; a role name is
guessable but not unique. Conflating them yields something that is neither, and a
session-derived suffix on a name destroys the very property that makes an address
an address.

The creator learns the created agent's address because the created agent announces
it, naming its parent — flow is one-way, creator to created, so every edge of the
tree is known without a lookup service. `--session-id` can also mint one at launch
if a creator needs to know before first contact.

A subagent inherits its parent's environment verbatim (session id, role, PID —
verified). That is load-bearing, not a defect: it is what lets a bus sidecar
resolve to its PARENT's mailbox without being told who its parent is.

## [2026-07-19 20:15 CEST] Decision-015: Only top-level sessions sit on the bus
#message-bus #agents #subagents #scope

Bus membership is top-level sessions only. Subagents are the responsibility of the
agent that spawned them and already have `SendMessage` for talking to their owner;
they get no inbox and no address.

This dissolves the identity problem for sessions that have no stable name of their
own — several concurrent builders under one architect share no distinguishing role,
so naming them needed either a session-derived suffix (unguessable, therefore not an
address) or a per-task name (bookkeeping for a case nobody needs). Neither is built.

## [2026-07-19 20:15 CEST] Decision-016: No delivery guarantee, by design
#message-bus #delivery #reliability #bus

The bus offers no acknowledgement, no retry, no timeout and no redelivery. Messages
are deleted on consumption; a session's inbox is destroyed at SessionEnd along with
anything still unread.

A sending agent must expect never to receive an answer and decide for itself whether
to retry, abandon, or error. This is deliberate and pre-existing: building acks would
mean claim-then-delete, in-flight state, and a scheduler for timeouts — a broker,
which is exactly what the filesystem is being used to avoid.

Consequence accepted: a sidecar that dies between draining and handing up loses those
messages silently. The mitigation is not redelivery, it is that a requester notices
its own silence.

## [2026-07-19 20:15 CEST] Decision-017: The hook is the mechanism, not secrecy
#message-bus #hooks #sessionstart #sessionend #gate

Bus membership is established by SessionStart and SessionEnd hooks rather than by
instructions in agent prompts. Code does not drift; models do, and AGENTS.md and
CLAUDE.md get bypassed regularly. A hook applies to every agent in every flow,
including ones that never read their briefing.

The first draft claimed the session id was "withheld and returned by the bus — a gate
rather than a nudge", so an agent skipping its bus could not address anything. That
claim is false and has been removed: the id is an environment variable any agent can
read. What the design actually provides is DETECTION, not prevention — an agent that
never announces is visibly absent to every peer, so a skipped bus is discoverable
rather than silently deaf.

Loading the sidecar remains a model action, because a hook cannot spawn a subagent.
That is the acknowledged soft spot, accepted until the broader injection-integrity
problem is addressed.

## [2026-07-19 20:15 CEST] Decision-018: Identity is broadcast, status is asked for
#message-bus #identity #status #tokens #orchid #request-response

Immutable facts are broadcast once at load (`orchid:identity`): session id, agent
type, worktree, feature id, parent session. Mutable state is pulled on demand
(`orchid:status`): state, context occupancy, token spend.

Both logical requests are answered BY THE SIDECAR, off the parent's transcript, which
it can read because it shares the parent's session id. The parent is never woken, so
the exchange costs it no context — and status keeps answering while the parent is
busy, wedged, or mid-compaction. A parent that has never reported yields `unknown`
rather than silence, so a stalled agent stays distinguishable from a deaf one.

Token counts serve two consumers with near-identical payloads: an agent watching
context occupancy (its own death condition — context exhaustion degrades quietly
rather than failing loudly) and an operator watching spend. The four token classes
are carried broken out, never summed, because they bill at different rates and a
single total cannot yield cost.

Model and effort are deliberately NOT in identity: they can change mid-session (a
model disengaging, tokens running out), so identity-at-birth and status-at-time
would disagree. Adding them needs a rule for which wins, so they are parked rather
than half-built. Without a model there is no denominator, so counts ship raw and the
reader interprets.

`--visible` marks a payload the SENDING agent intends the user to see. It is about
agent-to-user surfacing through an agent-to-agent channel, and is unrelated to
whether operators address agents by name (they do not).

## [2026-07-20 01:44 CEST] Decision-019: Per-role model and effort are pinned in agent-def frontmatter; the orchestrator scales the architect by complexity
#workflow #agents #model #effort #frontmatter #orchestrator #tiering

Every agent def carries a `model:` and `effort:` YAML default, replacing the stale
generic tier names (`opus`/`sonnet`/`haiku`) with concrete current IDs. Registered
(operator, 2026-07-20):

- orchestrator — `claude-fable-5`, effort `high`
- architect — `claude-opus-4-8`, effort `xhigh` (the pegged default)
- builder — `claude-sonnet-5`, effort `high`; jobs are short-lived by design
- groomer — `claude-sonnet-5`, effort `low`
- housekeeper — `claude-haiku-4-5`, effort `low`
- bus (and the other pure-mechanism subagents) — `claude-haiku-4-5`, effort `low`

The architect's model is NOT fixed: the orchestrator scales it from the sized
complexity at handoff — up to `claude-fable-5` for the hardest long-horizon builds
(Fable pricing exceeds Opus-tier, so it is a per-task escalation, never the default),
the `claude-opus-4-8` peg for ordinary features, or down to `claude-sonnet-5` for
genuinely simple mechanical work. Effort scales on the same read. The frontmatter
value is the floor the override starts from; the orchestrator states any deviation
and gets operator agreement before launching. This heuristic lives in the
orchestrator definition. Sibling of Decision-018 / [[agent-metadata]], which surfaces
model+effort on the BUS at runtime — this pins the role DEFAULTS in the definition, a
different layer.

## [2026-07-20 19:45 CEST] Decision-020: Roles validation belongs to kauk; vocabulary referenced, never restated
#roles #frontmatter #lint #validation #kauk #taxonomy #authoring-skills

The role-dag-frontmatter lint (its Proposal item 3) is dropped from scope.
kauk's reader validates `roles:` when it consumes them — an orchids-side lint
over hand-authored declarations is circular, and placing enforcement in the
authoring skill is wrong because that skill is not the vocabulary's source of
truth. The vocabulary stays in Decision-003 and the frontmatter contract
REFERENCES it; no second vocabulary artifact is created in orchids. Follow-up
boarded ([[kauk-validate-roles]]): a `kauk package validate` stub now, real
taxonomy validation in kauk later.

## [2026-07-20 19:45 CEST] Decision-021: The authoring-skills rename rides role-dag-frontmatter
#skills #rename #authoring-skills #doing-skills #sequencing #roles

`doing-skills` -> `authoring-skills` is executed inside the role-dag-frontmatter
workstream at operator direction ("rewrite to the new name at the same time")
instead of waiting for skill-renames-and-splits. That task's rename item is
thereby done; its remaining scope is the splits (git-commit et al.) and any
further renames. Context: lands with the f/role-dag-frontmatter squash-merge.

## [2026-07-20 19:45 CEST] Decision-022: write-to-s3 is placed at security/forensics
#roles #write-to-s3 #taxonomy #forensics #publication

`write-to-s3` declares `roles: [security/forensics]`, adopting Decision-003's
provisional placement as the declared value (the lint-era "needs a value"
question dissolves with Decision-020, but the placement ruling stands). The
publication question (pre-publication-cleanup) is unchanged.

## [2026-07-20 20:10 CEST] Decision-023: The close parallelises and verifies by presence
#close #housekeeper #orchestrator #workflow #performance #delegation

Two speed rulings on the close (operator, 2026-07-20, after a 15-minute close
on a docs-only feature):

1. On "close it" the orchestrator dispatches the housekeeper IN THE BACKGROUND
   and PREPARES the stream ingestion while it runs — but commits nothing to
   `main` until the housekeeper returns: two writers on `main` mid-merge is a
   race, and an uncommitted tree trips the housekeeper's clean-tree step.
2. The housekeeper verifies the close-gate by PRESENCE (named commits, files,
   sections in the branch tip), deep-reading only reported skips or failed
   checks; a failed check is the proven gap it fills and flags.

A third proposal — moving the `completed:`/`completed_during:` header fill to
the architect's close-gate — is REJECTED for now: the operator does not
currently trust the architect (it does not dispatch builders as contracted;
see the architect-delegation task). Re-evaluate when that is fixed.

## [2026-07-20 20:44 CEST] Decision-024: Orchard is the fleet workbench; the cross-repo bus keeps its own name
#orchard #naming #cross-repo #workbench #fleet

The codename **Orchard** now means the fleet workbench: the cross-repository
view, selection and dispatch UX the operator specified 2026-07-20 (global
overview of every repository's prepared work, counts of pressing/broken/
blocked issues, cross-repo dependencies, session-per-repo launch). Orchard
PRESENTS ONLY what each repository's orchestrator has already prepared — it
never derives or re-triages.

The live cross-repository messaging previously carried under the Orchard name
moves to its own task id, [[cross-repo-bus]], scope unchanged. References to
"orchard" in older docs (e.g. the message-bus sidecar) should be read as the
workbench programme from this date.

## [2026-07-20 21:35 CEST] Decision-025: The handover contract — the sidecar is the WHAT, the HOW is the architect's, delegation is mandatory above s
#handover #architect #orchestrator #delegation #sidecar #what-how #questions #cloud

Operator rulings (2026-07-20), the contract behind [[handover-contract]]:

1. **WHAT/HOW split.** The sidecar carries the complete WHAT — feature
   definition, scope, constraints, relationships, and the operator's scope
   answers. The orchestrator owns getting it complete. The HOW — discovery and
   technical design — is the ARCHITECT's job (that is the role), presented at
   the plan gate and frozen by MAKE IT SO; it is never required handoff
   content. (Amends the former §Sidecar wording "Proposal is the HOW the
   architect runs".)
2. **Two question rounds, not a ping-pong.** Scope (WHAT) questions are put to
   the operator while the task is parked in the readiness pipeline; the spawn
   itself carries only the LAUNCH round — model/effort scaling (Decision-019)
   and the parallel-launch offer. When several RELATED features are in play,
   ONE scope round defines the WHAT across all (or the chosen subset) before
   ANY architect launches, cloud or local. An open scope question at launch
   means the handoff broke; a mid-build scope question pauses the build and
   goes through the orchestrator, it is not asked ad hoc.
3. **Delegation is mandatory above s-size.** An architect build above s-size
   MUST dispatch builders; zero builders fails the close gate. An s-sized
   feature may be built inline, stated and justified in the close report. The
   former "directly or via parallel builders" permission was the bug
   (absorbed architect-delegation task). Restores the trust condition behind
   Decision-023's deferred header-fill move.

The cloud consequence: an autonomous/cloud architect has no mid-flight
operator contact, so rounds one and two are its hard precondition —
[[cloud-architect]] builds on this contract.

## [2026-07-20 21:50 CEST] Decision-026: The groom word family is banned; the role vocabulary is ripen/ripener
#vocabulary #naming #ripen #skills #agents #readiness

Operator rulings (2026-07-20): the word family "groom"/"grooming"/"groomer" is
FORBIDDEN in all output and all artifacts — it relates to bad people in other
contexts. The replacement vocabulary is **ripen/ripener**, matching the orchard
metaphor: tasks RIPEN through the readiness pipeline until pickable; the
prep-only agent is the RIPENER; the skill is `ripen`. The rename of the skill,
the agent, and the verb across the corpus executes under
[[retire-groom-vocabulary]] with its §Migrations entry; until it lands, the old
artifact names are quoted only when technically necessary.

## [2026-07-20 21:59 CEST] Decision-027: The pipeline is orchestrator → ripener → architect; cloud rides issues and PRs, starting now
#pipeline #ripener #architect #orchestrator #cloud #scope #questions #deviance #handover

Refines Decision-025 (operator, 2026-07-20):

- The ORCHESTRATOR holds the high-level WHAT: what a feature does, what it
  replaces, what it allows, why it exists at all. Intake questions are asked
  before a task reaches the board proper.
- The RIPENER is a specific agent BETWEEN orchestrator and architect. It
  CLOSES the functionality scope with targeted questions on functional
  completeness; loose ends are left as explicit VOLUNTARY deferrals, never
  silent gaps. It decides by a statistical-probability criterion (see
  [[psychometric-discovery]]) that the scope is well enough defined for the
  architect to do its job, then KICKS THE ARCHITECT OFF AUTOMATICALLY.
- The ARCHITECT formulates the TECH plan: if it has real questions it asks
  them; if not it presents the architectural plan. File- and class-level
  changes are NOT pre-decided — that is what git and refactoring are for.
  The last question is a SUMMARY of the work → MAKE IT SO → build (local) /
  pull request (cloud).
- Question economy is the design direction: as the system refines, better
  questions upstream, fewer or none downstream. Today's gates exist because
  of existing behaviour (the error rate), not as permanent shape — they
  shrink as upstream improves.
- CLOUD HAS NO BLOCKER and does not wait: a new feature is a GitHub issue;
  the orchestrator's and ripener's rounds run as comments on the issue (or a
  discussion — either); MAKE IT SO → pull request; THAT IS ALL → housekeeper
  (worktrees locally; PR amends + merge in cloud). Waiting delays discovering
  the deviance in the system — start now. Amends this afternoon's "parked"
  note on [[cloud-architect]].

## [2026-07-21 01:57 CEST] Decision-028: The close is bus-driven — lifecycle signals replace the finishing hooks
#bus #lifecycle #close #choreography #hooks #teardown #liveness #metadata #status #tmux

Shipped by [[hook-choreography]] (operator plan-gate rulings, 2026-07-20/21):

- Lifecycle signal on the bus: `bus.py signal --state <started|building|testing|done|finished|blocked|abandoned>`,
  body `{kind: lifecycle, state, feature_id}`; directed to `ORCHID_PARENT_SESSION`
  when known and live, else broadcast. The parent session id is wired into the
  environment at architect spawn.
- The close rides the signals: the architect signals `done` at its gate and
  `finished` at the ALL IT IS countersign; the orchestrator acts on `finished`.
  The operator's THAT IS ALL is the SOLE close gate (PR-merge semantics — a comment
  before it means amend/abandon). There is NO separate "close it" step.
- Teardown division: the orchestrator owns tmux (`tools/architect-teardown.sh` —
  focus-return, then kill the `arch:<id>` pane found by TITLE); the housekeeper owns
  the git close, unchanged. The transcript-grep Stop hook, its jq race and the
  `/tmp/architect-close.log` leak are retired.
- Liveness: when a close is expected and the architect looks absent, the orchestrator
  inspects the pane directly (gone / pane_dead); the bus `orchid:status` probe is
  secondary; no scheduler. The broad [[bus-liveness]] framework stays deferred.
- Metadata ([[agent-metadata]] folded in): model + effort ride `orchid:status`
  (mutable), NOT identity — resolving Decision-018's open which-wins question: status
  is the live truth for mutable fields, identity the birth record. Token classes stay
  broken out; effort reads null until an env source exists.

## [2026-07-21 02:14 CEST] Decision-029: Duplicates fold into the older entry; rulings supersede the newer way
#merge #duplicates #supersession #board #tasks #decisions #dedup

Operator ruling (2026-07-21): the two relations get different merge models.

- DUPLICATE (the same thing filed twice — tasks, issues, board entries): the git
  model. The OLDER entry is the home; the newer one is struck as the duplicate and
  its content folds back into the older. Ids, edges and links keep resolving. A
  machine-generated stub with no unique history is deleted outright; a human-authored
  duplicate is cancel-struck on the board ("duplicate of [[x]]") so its trail
  survives. Any gh# badge the newer filing carried re-binds to the home.
- SUPERSESSION (a changed RULING): the newer wins — docs/decisions.md keeps its
  convention of striking the older heading with a "Superseded by" marker.

First execution: GitHub issue #23 folded into [[fleet-sidebar]] (da7cd2d).

## [2026-07-21 02:47 CEST] Decision-030: The gate vocabulary — operator words, and nothing else, trigger
#gates #vocabulary #signals #engage #makeitso #thatisall #cloud #close

Operator ruling (2026-07-21): the ritual words are THE signals — them, and their emoji
equivalents when in prose; nothing else triggers, and agents never self-emit a gate.
Actor-gated to the operator; unlimited amend rounds precede every gate.

- `ENGAGE` / ⚙ — kick-off: fires the prologue → plan hop (cloud: an issue comment;
  local: the operator's go to the orchestrator).
- `MAKE IT SO` / 🖖 — build gate: the architect may edit files from here, not before.
- `THAT IS ALL` — close approval (PR-merge semantics; a comment instead means
  amend/abandon — Decision-028).
- `ALL IT IS` — the architect's countersign; carried to the orchestrator as the bus
  `finished` signal (machinery, not an operator word).

Canonical prose documentation rides the unlanded f/cloud-architect branch (README,
ARCHITECTURE, the [[cloud-architect]] sidecar); this entry anchors the ruling in the
ledger meanwhile, per the operator's "documented outside of code".

## [2026-07-21 02:47 CEST] Decision-031: Automode by default; #madmax unrestricts a task's launches
#permissions #automode #classifier #madmax #launch #spawn #settings #housekeeper

Operator rulings (2026-07-21), after a close was repeatedly stalled by permission-
classifier denials (housekeeper dispatch, pushes, even a read-only grep):

- Sessions in these repos default to AUTO permission mode: `permissions.defaultMode`
  = "auto" in the shared settings.json — spawned agents (architects, housekeepers,
  headless sub-jobs) included. Friction is the exception, not the baseline.
- `#madmax` is a BOARD TAG (trailing the task line, like an edge): a tagged task runs
  unrestricted — every `claude` launch for that feature appends
  `--dangerously-skip-permissions`. Operator-set ONLY — and because anything published
  where an agent can read it will eventually be used (operator, same night), the
  prohibition is STRUCTURAL, not prose: before honouring the tag, the launcher
  verifies it reached the board in an operator-authored commit (git provenance), not
  merely that it is present. Definition: AGENTS.files.md §TODO; spawn wiring:
  agents/orchestrator.md.
- The housekeeper's effort rises low → high and its charter gains a concurrent-streams
  briefing (main moves mid-close; stale branch context ≠ reverts) after a live misread.

## [2026-07-21 03:28 CEST] Decision-032: One orchestrator per repository; its session name is the repository
#orchestrator #sessions #naming #singleton #resume #zombie

Operator ruling (2026-07-21), amending the session-naming contract mid-plan: session
names name SESSIONS, and the orchestrator is not a workstream — it orchestrates them.
Exactly ONE orchestrator session exists per repository; its claude session name is the
repository name alone (`orchids`), never the `<repo> / <human name>` slash-form,
which belongs to workstream sessions (architects, ripeners). Summoning is resuming:
`claude --resume` by the bare repo name reaches THE orchestrator — a second one is
never started (the [[zombie-revival]] path revives the same single session). Typing a
repository's name therefore always lands on its orchestrator.

## [2026-07-21 03:30 CEST] Decision-033: Batch the pushes — a push is a workload trigger, not a save
#push #github #workflows #tokens #batching #cloud #comments

Operator MUST (2026-07-21): while discussing or refining anything, do NOT push on
every change. origin is wired to workflows (cloud hops, watchers) — every push
triggers workloads and spends tokens downstream. Commit locally as work lands; push
ONCE when the refinement round settles, or when the push itself is the intended
signal (a watcher waiting on state). Issue/PR comments are the same trigger class:
consolidate a round into one comment rather than dribbling triggers.

## [2026-07-21 05:38 CEST] Decision-034: Changelog and README — content staged at the source, file written at the hub
#changelog #readme #close #ownership #architect #orchestrator #injection-integrity #staging

Operator ruling (2026-07-21), settling [[readme-changelog-ownership]] (gh#31): the
objection to hub authorship is information loss — the finesse of WHY a change was
made the way it was lives in the architect's context and dies in a retelling, the
same loss injection-integrity names. The settlement extends the pattern that
already works for decisions: STAGE at the source, PROMOTE intact at the hub.

- The ARCHITECT authors the CONTENT while context is hot — the changelog entry in
  its own words and the user-facing README delta — as staged blocks in its sidecar
  result. It no longer edits CHANGELOG.md or README.md.
- The ORCHESTRATOR authors the FILE at ingest — places the staged entry under the
  canonical format, merges parallel features without collision (post-squash, on
  main), applies readme-sync judgement, holds the operator gate on the entry.
  Placement and format only: the entry lands in the architect's words or not at
  all.
- The HOUSEKEEPER stays verify-only (Decision-023's clause stands; its presence
  checks move to the staged blocks). ARCHITECTURE.md stays architect-authored
  on-branch for now — structural content is feature-scoped; revisit if its
  collision rate says otherwise.

## [2026-07-21 06:18 CEST] Decision-035: One tag vocabulary, board and GitHub — labels are the projection
#tags #labels #github #board #vocabulary #urgency #area #emoji

Operator rulings (2026-07-21), settling [[tags-and-labels]]:

- Board tags and GitHub labels are ONE system: the vocabulary lives in
  AGENTS.files.md §TODO (single source), `board_gh.py` mirrors it, and every
  issue's label set is REPLACED from its board line at each push. Projection-only:
  the board stays canonical; label edits on GitHub are overwritten.
- Labels are emoji-FIRST, always ("⚙️ area/process", never "area/⚙️ process").
- Urgency simplified: `urgent` is KILLED — it is never urgent until it is
  critical; `low` renamed `nice-to-have` — closer to reality. Enum:
  critical · nice-to-have · idea (empty = normal). Former urgent lines demoted to
  normal; the operator re-raises individually.
- `component` renamed `area` everywhere; labels carry the `area/` prefix.
- Locality tags: ☁️ cloud (reporting — it WAS built in the cloud), 🛰️ analyzable
  (CAN go to the cloud), 🛋️ house-bound (local-only from inception).
- Progress labels derived, not stored: 📋 todo · 🚧 doing (stage=working) ·
  ✅ done (done|functional); ⛔ blocked derived from unresolved ⊘ edges.
- Multi-part features are a PARENT with sub-todos, one area per leaf; parent
  issues link their children ([[rules-tuning]] is the worked example).

## [2026-07-21 06:33 CEST] Decision-036: The tmux topology — window per architect; subagents hidden, peekable
#tmux #workflow #architect #orchestrator #panes #windows #topology #peek #subagents #handoff

Operator rulings settling [[tmux-topology]] (2026-07-21); supersedes Decision-006
(pane-beside) and carries its tags:

- SESSION per repository → WINDOW per architect (one per active feature). The
  architect is something the operator interacts with — never a side-by-side or
  horizontal split. Spawn uses `tmux new-window`; the pane keeps its `arch:<id>`
  title, so the title-based teardown (Decision-028) works unchanged — killing the
  window's last pane closes the window and focus returns to the orchestrator.
- SUBAGENTS (builders, prep, sidecars) are hidden by default — never named
  sessions, surfaced in the sidebar via the bus — but hidden does NOT mean
  unpeekable: a PEEK opens a disposable pane tailing the subagent's live
  transcript, on demand, and closes when done.
- Peeks (and any deliberately visible subagent) live in a dedicated RIGHT COLUMN
  of the architect's window, stacked vertically, capped — never appended below
  the architect (the unusable default `split-window -v`). The cap is a
  build-time knob.

## [2026-07-21 08:43 CEST] Decision-037: The cloud path is canon — runtime, gates, handoff, and its work log
#cloud #gates #vocabulary #oauth #actions #handoff #badge #context #worklog #close-spine #app

> Close-spine ruleset clause superseded by Decision-040 (ruleset deleted; approach dropped).

Promoted from the cloud-architect stream (operator rulings, 2026-07-20/21):

- Runtime: hand-rolled headless CLI workflows (`claude -p --agent <role>` in
  GitHub Actions), NOT the official claude-code-action — full control of role
  charters and gates, matching the local spine. Auth: the subscription OAuth
  token (`claude setup-token` → repo secret), not a metered API key.
- Gate vocabulary amended (extends Decision-030): `MAKE IT SO` also accepts 🖖;
  `THAT IS ALL` also accepts 🚪. Gates are EXACT-form: the comment must BE the
  gate token, trimmed — a quoting comment never fires a hop. Actor-gated.
- ENGAGE does not bypass the orchestrator: hop 1 runs a cloud-orchestrator
  prologue (board handoff, sidecar ripeness) before any architect. Handoff badge
  contract: readiness stage → working ONLY; status stays todo; gh# inviolable;
  delegated-to lives in an issue comment.
- Context economy: the SIDECAR is canonical after each fold; hops read sidecar +
  gate comment, not the thread; every hop's last act writes handoff state back.
- Cloud work log rides the Actions cache (relay, not archive; housekeeper
  ingests before merge) — runners share no .git/the-works.
- close-spine: the status check IS a closing role's published judgment — setting
  it without a passed close gate is forgery. Org prerequisites documented in the
  workflow header ("Allow Actions to create PRs" ON). The ruleset is DISABLED
  until the named kaukea GitHub App exists (the built-in Actions identity cannot
  be bypass-listed) — re-enabling rides the app follow-up.

## [2026-07-21 12:39 CEST] Decision-038: Operator actions surface as end-of-reply bullets
#tone #operator #output #actions

Ruling (operator, 2026-07-21 — issued in the app-identifying architect session,
confirmed directly to the orchestrator): actions expected FROM the operator must
never be buried in long descriptions. Every agent collects them as concise
bullet points at the END of the interaction, with clear indicators/links
(paths, URLs, exact commands). Encoded in `AGENTS.shared.md` §Tone.

## [2026-07-21 13:39 CEST] Decision-039: callabloom[bot] — one named identity for every cloud action
#app #cloud #identity #actions #secrets #callabloom

Ruling (operator, 2026-07-21, app-identifying session): every GitHub action a
cloud hop takes — comment, commit, push, PR, merge — is performed as
**callabloom[bot]**, a kaukea-owned GitHub App (App ID 4354752), never as the
operator and never as the anonymous built-in `github-actions` actor. The token
is minted per hop via `actions/create-github-app-token@v3` from kaukea ORG
secrets `CALLABLOOM_APP_ID` / `CALLABLOOM_PRIVATE_KEY` (visibility all), with a
`github.token` fallback where the secrets are absent. The app is NOT a bypass
actor. Anthropic Routines cannot own a bot identity (they act as the user's
account) — at most an NL-trigger layer, never the identity substrate.

## [2026-07-21 13:39 CEST] Decision-040: Branch protection respawns as code; the ruleset contraption is dead
#close-spine #app #branch-protection #ordering #ruleset

Rulings (operator, 2026-07-21, live in the app-identifying session):

- The close-spine ruleset approach is DROPPED: ruleset 19333120 no longer
  exists (deleted, not disabled), org-level rulesets need a GitHub Team plan
  (kaukea is Free), and the status-check/bypass-actor contraption is retired.
  Supersedes Decision-037's close-spine ruleset clause (marker added there).
- Branch protection becomes its own task: formalise the workflow's EXISTING
  close rules as code — operator/code-owner approval required to merge `main`,
  callabloom excepted.
- Deterministic merge ordering is a THIRD concern ("Mr. Rabbit": a merge queue
  or optimistic-retry), a peer of the housekeeper and the orchestrator — merge
  order == changelog order. Spun out to its own task.

## [2026-07-21 13:52 CEST] Decision-041: Agents clean up after themselves — self-teardown at close
#close #teardown #bus #sub-agents #lifecycle #panes

Ruling (operator, 2026-07-21): closes were getting stuck on lingering children —
buses that never return, panes and sessions nobody kills — leaving flows
unfinishable. Enforcement is CHARTER TEXT ONLY (no verification apparatus, no
reaper pass):

- A bus ends in exactly two ways: RELEASED by its parent at close (`bus.py
  depart`, then it returns — its release IS its return), or ORPHANED (its inbox
  watch shows the parent's inbox gone → parent dead → it ends silently).
  "Never return" holds only while the parent lives.
- The CLOSING AGENT kills itself: the architect's last act after `ALL IT IS` +
  `finished` is releasing its bus and running `architect-teardown.sh` on its own
  pane. The orchestrator only dispatches the housekeeper; it runs the teardown
  solely as a fallback when an agent died before its self-teardown. Every role
  session releases its own bus before retiring.
- The end-of-task guard counts a released bus as returned.

## [2026-07-21 14:46 CEST] Decision-042: Cloud agents run operator-absent or on request — never auto-launched
#cloud #cloud-architect #orchestrator #dispatch #launch #authorization

Ruling (operator, 2026-07-21): the cloud agents are EXPERIMENTAL and missing
features. They exist for exactly two circumstances: runs while no operator is
present, and runs the operator explicitly requests. Under no circumstance does
the orchestrator decide on its own to launch a cloud agent — every cloud
launch requires the operator's explicit authorization. While the operator is
present, the local architect path is the default.

## [2026-07-21 19:42 CEST] Decision-043: ~~Fleet sidebar aggregates via an explicit repolist — Orchard's discovery deferred~~ *superseded by Decision-061*
#fleet-sidebar #sidebar #cross-repo #repolist #orchard #discovery #supersession

Ruling (operator, 2026-07-21): the fleet sidebar aggregates cross-repo via an
EXPLICIT repolist config (`~/.config/orchids/sidebar-repos`, one path per line,
or `ORCHIDS_SIDEBAR_REPOS`) — not scan-root, not fleet auto-discovery. This
deliberately defers the fleet-wide repo-discovery decision to Orchard
(`orchard-view` / `cross-repo-bus` carry it).

## [2026-07-21 19:42 CEST] Decision-044: Activity label is the only new bus surface; waiting/flash is derived
#fleet-sidebar #bus #activity #broadcast #flash #subagents

Ruling (operator, 2026-07-21): the sidebar's live state rides the EXISTING bus
as ordinary dynamic messages — `orchid:activity:<text>` and
`orchid:subagent:start|done:<label>`; no bus mechanism change. The activity
LABEL is the only new surface. Waiting/flash is DERIVED (notify_user OR
lifecycle blocked) — no new bus field for it. Activity is emitted as WORDING
by full agents (orchestrator/architect/ripener); subagents are shown by
name+spinner surfaced by their parent; the bus sidecar is omitted from rows.

## [2026-07-21 19:42 CEST] Decision-045: Tmux window names carry the session-naming display forms
#session-naming #tmux #window-naming #spawn #teardown

Ruling (operator, 2026-07-21): tmux WINDOW NAMES are the session-naming
display forms — orchestrator window = bare repo (`orchids`), architect window
= `<repo> ▸ <human>` (`orchids ▸ fleet sidebar`). NO `claude`, NO visible
`arch:<id>`. `arch:<id>` survives ONLY as the pane TITLE (teardown/reaping
handle). Nav matches the friendly window names. Baked into the spawn recipes
on the fleet-sidebar branch; completes the window-name half of session-naming
(gh#34, which had done only `claude --name`). Context: an earlier silent
`orch:<project>` rename was reverted — operator-visible naming is a SPEC
decision, never a silent HOW.

## [2026-07-21 19:42 CEST] Decision-046: A bus exits only when woken by an inbound message
#bus #monitor #teardown #agent-closing #wake

Ruling (operator, 2026-07-21): a bus sidecar blocked on its monitor exits
ONLY by being WOKEN — an inbound message arrives, the bus tears down its own
monitor and exits. Never kill a bus's monitor externally: the bus never wakes
and hangs forever. Closes therefore wake actively rather than wait passively;
long passive watch timeouts (15m) are unacceptable for exits. Refines
Decision-041 (release is the bus's return): release must reach the bus AS a
wake.

## [2026-07-21 20:48 CEST] Decision-047: Operator approvals relay over the bus as a sanctioned operator-origin class
#bus #approval #gates #operator-relay #architect #done-gate #agent-closing

Ruling (operator, 2026-07-21): an operator approval given outside the
architect's own window (typically in the orchestrator pane) reaches the
architect via a SANCTIONED OPERATOR RELAY — a distinct operator-origin
message class on the bus that gate-waiting agents accept as the operator's
word. The relaying agent forwards the approval verbatim and flagged as
operator-origin, never as its own peer traffic; ordinary peer messages remain
rejected at gates. This closes the silent stall found at the fleet-sidebar
close, where an approval typed in the orchestrator pane had no path to the
architect's done gate. Chosen over the alternatives of charter-only
redirection ("type it in the architect's window") and tmux keystroke
injection. Mechanics land with the agent-closing corrective.

## [2026-07-21 21:59 CEST] Decision-048: Teardown, reaping and mount key off the @arch_id window user-option
#teardown #panes #close #agent-closing #arch-id #tmux #reaping #sidebar

Ruling (operator, 2026-07-21, via the agent-closing corrective): the stable
handle for an architect window is a tmux WINDOW user-option `@arch_id=<id>`,
set at launch. `architect-teardown.sh` and orchestrator reaping resolve the
window by `@arch_id` and close at WINDOW granularity — the mounted sidebar
pane dies with it. The `arch:<id>` pane title survives only as a
non-load-bearing human hint: claude clobbers pane titles live with the
session name, which is exactly what broke title-keyed teardown and reaping.
`@arch_id` is also the contract sidebar-fixes consumes for mount idempotency.
Refines Decisions 028/036/045 (which had made the pane title the handle).

## [2026-07-21 21:59 CEST] Decision-049: The operator-origin relay stays literal — spoofability is an accepted trade-off
#bus #approval #operator-relay #security #trust-model #agent-closing

Ruling (operator, 2026-07-21): the operator-origin relay is implemented
LITERALLY per Decision-047 — any `operator_origin`-flagged message is honored
at a gate; no conductor-only hardening. The flag is convention, not
cryptography: on a cooperative single-operator fleet where NO bus message is
authenticated, the spoofable-bypass finding raised by the security scan is an
ACCEPTED, operator-sanctioned trade-off. Peer prose without the flag still
never closes a gate.

## [2026-07-22 12:15 CEST] Decision-050: The bloom vocabulary, and a mandatory bloom round at every handoff
#bloom #bloomer #vocabulary #rename #handoff #what-bar #scope #bloom-tasks

Ruling (operator, 2026-07-22): the ripen word family is retired and replaced
by **bloom/bloomer** — tasks bloom until pickable; the prep agent is the
bloomer; the skill is `bloom-tasks` (verb-object convention). Supersedes the
word choice of Decision-026 (groom→ripen); executes the retirement task
(gh#27). Renames ship with migration `2026-07-22-bloom-tasks-rename.md`; the
bloom commit template becomes `🌸 bloom: <id> → <stage>`; the swept-SHA state
file becomes `.claude/state/last-bloom.sha`.

Second ruling in the same order: the bloomer runs **at EVERY handoff** as a
mandatory pre-launch bloom round — part of the WHAT definition, before the
architect gets involved. On an operator go, the orchestrator dispatches the
bloomer on the picked task FIRST (step 0 of the handoff); it closes the WHAT
with the targeted functional-completeness questions of Decision-027, and no
architect is spawned until the round returns and its Questions are answered.
A `plan-ready` badge does not skip the round — it confirms the WHAT is
current at launch, not merely present. Launches themselves stay
operator-gated; Decision-027's autonomous kick-off remains gated off.

## [2026-07-22 13:19 CEST] Decision-051: The bus sidecar is a singleton — per AGENT, by design
#bus #singleton #message-bus #architecture #ruling

Ruling (operator, 2026-07-22): the message-bus sidecar is a singleton PER
AGENT — every agent loads EXACTLY ONE bus, never more, and it is not up for
conversation. The per-agent architecture (Decision-041's one-sidecar-per-
agent) IS the design; the defect the operator observed is multiplicity
BEYOND one-per-agent: duplicate bus spawns within a session (one occurred
in the 2026-07-22 orchestrator session) and stale bus rows surviving their
agent. Corrective boarded as bus-singleton (enforce the one-per-agent
invariant, reap strays); the sidebar renders exactly one bus row per live
agent (sidebar-polish item 5).
[Corrected 13:2x CEST same day: the initial recording misstated the ruling
as one-bus-per-REPOSITORY — a transcription error by the orchestrator,
fixed on the operator's immediate clarification.]

## [2026-07-22 13:52 CEST] Decision-052: Sidebar rulings from the sidebar-fixes corrective
#sidebar #panes #idempotency #status #flash #close #sidebar-fixes

Three rulings made with the operator during the sidebar-fixes build
(archive/sidebar-fixes, squash de71b80), promoted at ingest:
1. Sidebar mount idempotency detects the sidebar PANE by its
   pane_start_command (running sidebar.py) — self-contained, deliberately
   NOT consuming the @arch_id window-identity handle of Decision-048: pane
   presence and window identity are orthogonal concerns.
2. A repository with no live orchestrator session renders a distinct IDLE
   status (⚪, dim) — idle is a real state, never conflated with running.
3. A terminal lifecycle signal (finished/abandoned) clears the
   operator-waiting flash; otherwise only a new activity broadcast changes
   it — a resolved session must never keep flashing "waiting".

## [2026-07-22 15:55 CEST] Decision-053: Field projection targets GitHub's native surfaces; Urgency stays alongside
#board #github #sync #fields #priority #type #dependencies #field-projecting

The field-projecting build's frozen plan, agreed with the operator
2026-07-22 and promoted at ingest (the branch had recorded it under the
number 051, which main had already assigned to the bus-singleton ruling —
renumbered here):
- **Type** → GitHub's native Issue Type (`updateIssueIssueType`); the three
  missing org types (Refactor, Housekeeping, Completion) are created
  org-wide, ensure-if-missing. The emoji type labels (Decision-035) stay.
- **Priority** → the native org Issue Field "Priority", mapped from badge
  urgency: critical→Urgent, empty/normal→Medium, nice-to-have→Low,
  idea→Low (High unused). The Projects-v2 "Urgency" custom field is KEPT
  and still written — operator ruling: both live side by side.
- **Relationships** → board `⊘` edges become native Issue Dependencies
  (addBlockedBy/removeBlockedBy), fully reconciled each push; `blocking`
  is GitHub's derived inverse. `~related` has NO native equivalent
  (schema-introspected) and projects as a `### Related` body-link list.
- Board is canonical; the sync writes GitHub, never the reverse, on these
  surfaces.

## [2026-07-22 16:16 CEST] Decision-054: The close composes on a staging ref; the ingest folds into the squash
#close #housekeeper #squash #staging #ingest #atomicity #git

Operator design (2026-07-22), replacing the serialized two-writer close:
the housekeeper composes the squash on a `close/<id>` staging branch —
where amending is free and leaves no public trace — folds the
orchestrator's pre-drafted ingest (`.git/the-works/close-<id>.draft/`)
into the SAME commit, and lands main by fast-forward (cherry-pick when
main moved; same content, equally clean). One atomic commit carries the
feature and its board/decision state, so main never shows merged code
against a stale board. Telemetry notes attach only after the final SHA
exists. The housekeeper also dispatches AT the gate word, in parallel with
the architect's self-teardown, retrying only the worktree removal until
the architect's session dies. The genuinely serialized core of a close is
now a single ref update.

## [2026-07-22 16:18 CEST] Decision-055: The ingest is staged rolling by the builder side and folded mechanically
#close #ingest #staging #architect #housekeeper #decisions #numbering #scribe

Operator design (2026-07-22), refining Decision-054's atomic close — nobody
re-reads with cold context what was known hot, and nothing waits for the end:
- The ARCHITECT stages the ingest AS THE BUILD PROGRESSES — decision entries
  (in final format, UNNUMBERED: `Decision-NNN`), the changelog block, the
  result — updated at every landed step, inline or via a small scribe
  subagent aggregating one commit at a time. A close-time catch-up is the
  named anti-pattern.
- The HOUSEKEEPER folds the staged blocks into the squash mechanically:
  decision numbers assigned from the live file's tail at fold time (branch-
  assigned numbers collide, live-fired twice on 2026-07-22), and the
  feature's own board badge flipped as part of the fold — the one board edit
  a child may make, as close execution.
- The ORCHESTRATOR no longer pre-drafts what was staged; its close work is
  the operator-gated CHANGELOG placement, cross-feature promotions and
  corrections, stream archiving, convergence, one push.

## [2026-07-22 16:22 CEST] Decision-056: Aggregation belongs to the context that already holds the tokens
#economy #tokens #staging #builder #architect #scribe #principle

Operator principle (2026-07-22), general and durable: a work product is
staged by the agent whose context ALREADY contains its inputs — the builder
that made the commit writes the ingest increment in its typed return; the
architect folds increments as they arrive (the return enters its context
regardless). Separate readers are the anti-pattern: a scribe subagent
re-reading commits, or anyone reconstructing from `git log` at close, pays
input tokens to re-load what the committing context had for free. The
scribe variant of Decision-055 is retired before first use. Same family as
the popup ruling (a script where no judgment is needed): spend model
attention exactly once, where the information is born.

## [2026-07-22 17:26 CEST] Decision-057: The operator's build-gate phrase, translated at the boundary
#gates #keywords #relay #ui #operator #make-it-so

Operator ruling (2026-07-22): the operator-facing build-gate phrase becomes
**"NO NO THAT WAS NOT A QUESTION"** (variants: THIS for THAT; short form
"NO NO") — the architect's final plan summary is answered by objecting that
it needed asking at all. Implementation is a TRANSLATION AT THE UI
BOUNDARY, per the operator's scope guidance: every operator-input surface
(orchestrator pane relay now; the question/gate popup when it lands) maps
the phrase to the fleet's INTERNAL protocol string `MAKE IT SO`, which is
unchanged everywhere else — defs, bus matching, in-flight builds. A
directly-typed `MAKE IT SO` still works. `THAT IS ALL` is untouched.

## [2026-07-22, addendum to Decision-057] ENGAGE joins the build-gate phrases
#gates #keywords #engage

Operator addendum, minutes after Decision-057: **`ENGAGE`** is also an
accepted operator build-gate phrase, translated at the same boundary to the
internal `MAKE IT SO`. The accepted set is now: the full NO-NO phrase
(THAT/THIS), `NO NO`, `ENGAGE`, and the internal string itself.

## [2026-07-22, second addendum to Decision-057] The glacial-pace phrase joins the set
#gates #keywords

"BY ALL MEANS, MOVE AT A GLACIAL PACE" is the third operator build-gate
phrase — approval by sarcasm, completing the operator's dictation
("complement ENGAGE with…"). Same boundary translation to `MAKE IT SO`.
Accepted set: the NO-NO phrase (THAT/THIS) · NO NO · ENGAGE · the
glacial-pace phrase · the internal string itself.

## [2026-07-22, third addendum to Decision-057] The corrected keyword table; ENGAGE is cloud-only
#gates #keywords #engage #cloud

Operator correction, same day: ENGAGE is a SEPARATE keyword reserved for the
CLOUD path — the explicit authorization word for dispatching a cloud run
(Decision-042); it is not a build-gate synonym and never starts local
coding. The corrected table: coding START = internal MAKE IT SO, operator
phrases "NO NO THAT WAS NOT A QUESTION" (THIS/THAT; simply "THAT WAS NOT A
QUESTION"; "NO NO") and "BY ALL MEANS, MOVE AT A GLACIAL PACE" (simply
"MOVE AT A GLACIAL PACE"). Coding END = THAT IS ALL, unchanged, no
synonyms. Keywords to become configurable in a future task.

## [2026-07-22 17:45 CEST] Decision-058: The sidebar status vocabulary is six static states
#sidebar #status #vocabulary #sidebar-polish

From the sidebar-polish build (operator, direct): six distinct static
states — working / waiting / idle / awaiting-another-agent / done /
failed — done and failed never sharing a glyph, idle distinct from
awaiting. Supersedes the "three live plus one parked" draft of the
original item 9. No animation anywhere (item 1).

## [2026-07-22 17:45 CEST] Decision-059: Human names are authored at intake, never grammar-converted at runtime
#naming #titles #board #sidebar-polish

From the sidebar-polish build (operator, direct): the declarative human
name (imperative-vs-declarative, session-naming contract) is AUTHORED when
the ledger entry is created — the board's short title / sidecar H1 — and
every title call site reads that; mechanical hyphen-replace survives only
pre-intake. No runtime grammar-conversion code exists.

## [2026-07-22 17:45 CEST] Decision-060: Agent self-exit lifecycle — two closing messages, a declared grace, then the orchestrator kills
#lifecycle #close #sidebar #reaping #sidebar-polish

From the sidebar-polish build (operator, direct), the real fix for stale
sidebar rows: agents END via a lifecycle contract — two closing messages
and a declared grace period (default 10s); past the window the
orchestrator kills the process and broadcasts the death. Distinct from
bus-singleton (which reaps stray bus sidecars, not whole agents).

## [2026-07-22 17:45 CEST] Decision-061: Decision-043 superseded — the sidebar discovers repos via the registry
#sidebar #orchard #registry #supersession

Decision-043's explicit repolist (Orchard discovery deferred) is
SUPERSEDED by the sidebar-polish item-7 build: repos appear via the
`.ai.toml`-triggered registry automatically, hidden conversationally,
persisted across remounts.

## [2026-07-22 17:10 CEST] Decision-066: Decision supersession projects as GitHub's native duplicate-of, not a body-note fallback
#decision-projecting #github #graphql #duplicate #supersession

GitHub's `closeIssue` GraphQL mutation has carried `stateReason: DUPLICATE`
plus `duplicateIssueId: ID` since December 2024 — confirmed against the
`octokit/graphql-schema` schema, not assumed. `gh issue close --reason` never
exposed it (CLI only offers `completed`/`not planned`), which is why an
earlier pass assumed a body-note fallback (the `~related` precedent,
Decision-053) would be needed. It isn't: reaching the native mutation is one
more `gql()` call, the same helper already used for `createIssueType`/
`updateIssueIssueType`. decisions.md has no separate "duplicate" state
distinct from "superseded" (only board tasks do, per Decision-029) — so
supersession itself projects as the native duplicate-of: the OLDER
(struck) decision's issue closes pointing at the NEWER (superseding) one,
matching the file's own `Superseded by Decision-MMM` direction.

## [2026-07-22 17:10 CEST] Decision-067: Decision-to-issue matching is title-based and stateless
#decision-projecting #github #matching

`docs/decisions.md`'s canonical entry format is heading + mandatory hashtag
line only — no room for a stored GitHub issue number, unlike task sidecars'
YAML front matter. Rather than extend that canonical format (which every
future decision write would then have to carry), sync matches a decision to
its GitHub issue by title text: the issue title is `Decision-NNN: <title>`,
looked up via one bulk `gh issue list --search "Decision- in:title"` call
per sync run and filtered client-side, not stored anywhere. `Decision-NNN`
was already the stable, human-assigned key: this reuses it rather than
inventing a second one. Considered and rejected: embedding a gh# in the
decisions.md heading (breaks the canonical format); a Projects-v2 custom
field for matching (adds an indirection the title lookup already avoids —
GitHub's own field-locking is non-existent per-field anyway, so a stored
field is no more tamper-proof than re-deriving it fresh every run). Also
added, per operator request, as pure redundant metadata (not used for
matching): `Decision Number`/`Decision Title` Projects-v2 text fields, same
mechanism already used for `Area` — free, future-proofing, no admin action
(Projects-v2 fields are project-scoped, unlike GitHub Issue Types which are
org-scoped/admin — both tiers already exercised elsewhere in this codebase).

## [2026-07-22 18:13 CEST] Decision-068: Agents close their own windows; five seconds; the housekeeper never pulls the floor
#lifecycle #close #teardown #housekeeper #bus #window #ruling

Operator causality finding + ruling (2026-07-22): windows fail to close
BECAUSE the housekeeper deletes worktree files before the agent finishes
closing — the teardown loses its floor mid-step. Confirmed design, refining
Decision-060: an agent closes its OWN window whenever it is ready,
broadcasting **on-closing** then **on-closed**; it has **FIVE seconds**
(not 060's ten) from on-closing before ONE designated bus-listening agent
kills it and broadcasts the death on its behalf. The HOUSEKEEPER never
removes a worktree before the agent's on-closed (or the kill) has been
observed — retry-until-free was insufficient; the ordering is now a hard
precondition.

## [2026-07-22, addendum to Decision-068] The lifecycle signals mean work, not windows
#lifecycle #close #on-closing #on-closed #supervision

Operator clarification, same day: **on-closing** opens the agent's own
cleanup phase — it tells its subagents to go, and EACH SUBAGENT is
responsible for tearing down its own monitors and resources (cascading
self-cleanup, as previously discussed). **on-closed** is emitted only when
the agent is ready to close its window — and nobody observes the window
itself: observers care about what an agent is DOING and ADVERTISING it is
doing, never about tmux state. That inversion is what makes supervision
possible at all: ONE agent listens to on-closing/on-closed and kills any
agent that exceeds its allocated time — signals are the truth, the window
is an implementation detail.

## [2026-07-22, second addendum to Decision-068] The lifecycle supervisor is the orchestrator's own subagent
#lifecycle #supervision #orchestrator #ownership

Operator ruling, same day: the ONE designated bus-listening killer is a
subagent OWNED BY THE ORCHESTRATOR, living in its session — the
orchestrator already holds all the information about every agent
(announces, allocated-time requests, the dispatch ledger), so supervision
belongs where the knowledge is. Sibling of the bus-sidecar ownership
pattern: one supervisor per orchestrator session, not a free-floating
service.

## [2026-07-22, evening] Decision-069: Board writes are denied to children by permission, and intake is a typed message
#board #permissions #deny #intake #enforcement #bus #schema

Operator ruling (2026-07-22): prose rules do not hold — "artificial
intelligence is lazy" and will bypass any convention when writing a file
looks more efficient. Therefore, mechanically:
- A STANDARDIZED intake message type (request/response or one-way) carries
  every bug/item/request from an agent to the orchestrator — structured
  fields: orchard (repo), todo (task reference), subject text — schema'd
  like the rest of the envelope (fleet-documenting's JSON-Schema family).
- `docs/TODO.md` and `docs/TODO.md.d/` carry PERMISSION DENIALS for
  non-orchestrator agents: the board index is hard-denied in each
  architect worktree's local settings at spawn; sidecar writes are guarded
  so an agent can write ONLY its own feature's sidecar (a hook carries the
  carve-out a glob deny cannot express).
Enforcement by architecture, never by instruction — the same family as
Decisions 056 (token-holder aggregation) and the popup broker (script
decides, agent cannot override).

## [2026-07-23 03:52 CEST] Decision-070: Telemetry mining's first slice runs as a cloud routine
#telemetry #telemetry-mining #routine #cloud #wiki #digest

The first slice of telemetry mining (gh#51) runs as an Anthropic cloud routine,
not a local cron: haiku model, daily at 00:00 UTC, publishing its digest to the
repository wiki as primary destination with a pull request as fallback. Context,
not ruling: the routine id at promotion time is trig_01VjojrA8RTPZuVpAQkvtTR1;
it went live 2026-07-21 and this entry was carried as "still pending" in the
fleet-sidebar ingest prep before landing here.

## [2026-07-23 03:52 CEST] Decision-071: .ai.toml is operator-owned; delivery markings belong in AGENTS.d
#kauk #ai-toml #agents-d #delivery #sync #file-formats

Operator ruling (2026-07-23): `.ai.toml` — like all file formats — is for the
operator alone to change and validate. Agents never add `local`/`copy`/`link`
delivery markings there, not even to silence kauk's BLOCKED warnings. Per-file
delivery configuration belongs in `AGENTS.d` instead; its exact shape is to be
proposed by the scheduled delivery-config review and validated by the operator
before adoption. Until then the two standing BLOCKED lines on orchids'
AGENTS.shared.md / AGENTS.files.md stay as-is.

## [2026-07-24 13:05 CEST] Decision-072: Bloomer v1 engine includes IRT/Fisher despite uncalibrated items
#bloomer #psychometrics #irt #eig #engine #convergence

Operator ruling (2026-07-24, plan gate): the v1 statistical engine implements
the full blueprint-§8 composition — EIG/BED question selection AND IRT item
modelling with Fisher-information selection and SE-threshold stopping —
overriding the Opus blueprint review's recommendation to drop the IRT/Fisher
formalism at n=1. Mitigation recorded with the ruling: item parameters are
LLM-assumed at generation and every convergence report flags them as
uncalibrated; accumulated live runs are the future calibration path.

## [2026-07-24 13:05 CEST] Decision-073: Groomer stays under its name until the bloomer is judged ready
#bloomer #groomer #retirement #pipeline #bloom-tasks

Operator ruling (2026-07-24, plan gate): the demoted `groomer` definition and
every pipeline reference to it (orchestrator bloom round, `bloom-tasks` skill)
stay UNTOUCHED while bloomer v1 is built and proven. Once the bloomer is
judged ready, a separate analysis decides what in the groomer is worth keeping
before any retirement or repoint. Supersedes this task's earlier
delete-at-landing intent; the repoint work is an explicit follow-up.

## [2026-07-24 13:05 CEST] Decision-074: Launch sizing stays in the pipeline; the bloomer feeds it
#bloomer #launch-sizing #model-effort #pipeline

Operator ruling (2026-07-24, plan gate): the existing launch-sizing round
(Decision-019 model/effort scaling) remains part of the handoff pipeline —
removing it would be a regression. Bloomer v1's convergence report carries a
launch-sizing recommendation (size class + suggested tier) feeding that round.
Only MEASURED/statistical launch sizing remains future work (the recorded
future ruling on removing per-role defaults is unchanged).

## [2026-07-24 19:55 CEST] Decision-075: The orchestrator analyzes the bloom report and owns go/no-go
#bloomer #orchestrator #autonomy #auto-kick #pipeline #launch

Operator ruling (2026-07-24): the bloomer is never delegate-and-forget. The
orchestrator runs the instrument, itself ANALYZES the statistical response,
and makes the go/no-go call on dispatching an architect — an agent producing
statistical evidence of spec completeness cannot self-certify its own launch.
Partially supersedes Decision-027's "kicks the architect off automatically"
clause and the v1 graduated outcome's temporary very-high auto-launch: launch
execution AND judgment sit with the orchestrator until the autonomy
ladder/metronome exists, at which point delegation is revisited (operator:
"as soon as the autonomy ladder is in place we'll remove the autostart and
delegate").

## [2026-07-25 CEST] Decision-076: The bus vocabulary is five wire classes; only three interrupts may summon the operator
#bus #messaging #vocabulary #notify #interrupt #sidebar

Operator dictation (2026-07-24) fixed the message model: STATUS (one/two
plain words, agent-chosen) · STATUS UPDATE (log-targeted sentence) · exactly
three operator interrupts — SUCCEEDED, FAILED, QUESTION. Wire form (full-go
architect design): orchid:status / orchid:update / orchid:phase /
orchid:subagent:{queue,start,done} / orchid:interrupt:question, validated by
bus.py; any other orchid:* body is rejected; notify_user is legal only on
ask-questions and lifecycle done/blocked/abandoned; the interrupts are
derived (QUESTION ⇐ ask, SUCCEEDED ⇐ done/finished, FAILED ⇐ abandoned or
blocked+notify). Status words colliding with lifecycle vocabulary are denied
(the orchid:activity:Closing incident). Statuses broadcast on change only
(the duplicate-notify incident). Supersedes Decision-044's free activity
label as the status surface; amends Decision-058's display vocabulary with
the derived-interrupt layer. Lifecycle signals stay internal plumbing.

## [2026-07-25 CEST] Decision-077: The phase spine broadcasts as a typed channel and maps to a live percentage
#bus #phase #progress #sidebar

Phases ideation → scoping → designing → building → releasing ride
orchid:phase:<phase>[:<k>/<n>] with spans 10/15/15/45/15 (bases 0/10/25/40/
85); visible ticks advance the number, hidden plumbing never does; 100 only
at lifecycle finished. The renderer derives the embedded progress fill from
this channel alone.

## [2026-07-25 CEST] Decision-078: The blessed mock is the renderer's fixed contract; identity maps are data-driven
#sidebar #design #mock #emoji

sidebar-mock.py + approved-frame.ans (archived with the feature stream) are
the visual truth tools/sidebar.py implements: glyph set, RGB palette, hue
families, model colour ramp, band animation, checklist, identity line,
footers. Role-emoji, per-repo hue, and 💻/☁️ location-badge maps ship as
data so pending picks (orchestrator, architect emojis) drop in without code
changes. Known licensed debt: the KITT-scanner tail polish.

## [2026-07-25 CEST] Decision-079: bus-message-specifying based its renderer files on f/sidebar-titling explicitly
#sidebar #branching #upstream

The unmerged f/sidebar-titling@9752aed states of tools/sidebar.py,
sidebar_model.py, sidebar_nav.py, sidebar-mount.sh and their tests were
absorbed as the build base (operator-sanctioned upstream). Whichever branch
folds second resolves the overlap trivially by content identity.

## [2026-07-25 CEST] Decision-080: Finished work is never left local — the push is a mandatory close step
#workflow #close #push #package #consumers

Operator standing rule (2026-07-25, "we never leave finished work local, I
told you a million times"): for this repo a completed close is NOT complete
until it is pushed to origin. orchids is a data package every consuming repo
syncs from `github.com/kaukea/orchids` on its next session, so commit-only
leaves every consumer on stale content — the work is invisible until the
push. The push is a non-optional final step of every close here, whether the
housekeeper runs it or the orchestrator drives the close directly; the same
applies to any docs/board commit made after a close. Not a per-feature
judgment — a fixed obligation.

## [2026-07-25 CEST] Decision-081: Supervision kills are removed — no agent kills another; tree removal is the close's last act
#lifecycle #groundkeeper #close #bus #teardown #housekeeper

Operator ruling (2026-07-25, dictated): the groundkeeper killing things
makes everything worse — it can corrupt state and it hides bugs — so the
kill functionalities are removed outright. No agent kills, reaps, or
removes another agent's process, pane, window, or files; agents start and
stop themselves (self-teardown remains each agent's own last act), and
whatever a dead agent leaves behind is reported to the operator, who rules
on it. Removed with the kill: the exit-grace lifecycle contract
(`exit_grace_seconds` on announce) and `signal --on-behalf-of`, which
existed only to time the kill and to sign for the killed. Worktree-and-
branch removal moves to the ABSOLUTE END of the housekeeper's close —
nothing runs after it. Supersedes the reap half of the 2026-07-21
pane-hygiene ruling and the kill-listener half of window-closing-owning's
premise.

## [2026-07-25] Decision-082: The project topic is DATA, not UI; identity and status are bus operations
#bus #transport #sidebar

**Context:** Agent-activity telemetry for the sidebar must carry enough state for
render AND integrity enforcement, but display is a UI concern, separate from the
data layer. Identity and status are operations the bus itself supplies; agents
cannot author these fields.

**Decision:**
- Agent events carry raw state only: `lifecycle` (starting|started|stopping|stopped),
  `status` (≤2 words), `delegation` (schedule|begin|end for subagents), `outcome`
  (success|fail), and task `outcome` (completed|failed, orchestrator-only).
- The two fixed operations — IDENTITY (immutable: session, agent, feature, name,
  parent) and STATUS (mutable: model, tokens, spend) — are supplied by the bus and
  never authored by agents.
- The 5-phase display (queued/active/finishing/done/functional) is a UI-side
  MAPPING of raw states, never a field on the bus.

**Touched:** `orchard_topic.py` (posting validation), `sidebar_v3.py` (phase
mapping), `test_orchard_topic.py` (validation edge cases).

(Operator, 2026-07-25.)

## [2026-07-25] Decision-083: Task completion is orchestrator-only; agent and task outcomes are separate
#bus #transport

**Context:** Feature completion ("done for the user") and task completion ("the
orchestrator says so") are distinct. Agents report work outcomes; only the
orchestrator marks a task complete.

**Decision:**
- Agent-level `outcome:success|fail` is separate from and orthogonal to task-level
  `outcome:completed|failed`.
- `orchard:task:outcome:completed|failed` is **orchestrator-only**, enforced at the
  sender by identity check in `orchard_topic.py`.
- Any other sender attempting `task:outcome:*` receives a rejection + telemetry
  bounce.

**Touched:** `orchard_topic.py` (sender identity gate), `test_orchard_topic.py`
(rejection path).

(Operator, 2026-07-25.)

## [2026-07-25] Decision-084: A project is the git repo; every worktree posts to one topic directory
#sidebar #topics

**Context:** Projects can span worktrees (feature branches, parallel repairs) of
the same repo. A project's topic directory must be shared — one per repo, not per
worktree — so all worktrees see a unified session roster.

**Decision:**
- A "project" = the git repository (identified via `--git-common-dir`).
- Every worktree of a repo posts to the same topic directory:
  `$XDG_RUNTIME_DIR/orchard/topics/repository/<repo>/`.
- The first poster becomes the project header; a project appears only when someone
  posts to it.
- Multiple worktrees of the same repo see each other's sessions; worktrees of
  different repos are isolated.

**Touched:** `orchard_topic.py` (git-common-dir lookup), `sidebar_v3.py` (project
identity), `test_orchard_topic.py` (multi-worktree scenarios).

(Operator, 2026-07-25.)

## [2026-07-25 07:27 CEST] Decision-085: The orchard naming vocabulary is closed — six roles, six glyphs
#naming #roles #orchard #emoji #renaming #vocabulary

Operator rulings (2026-07-25 morning), closing the picks [[orchard-renaming]] was
parked on. Every role wears an orchard name and one glyph:

| role (old) | orchard name | glyph |
|---|---|---|
| orchestrator | gardener | 🌳 |
| architect | landscaper | 🌿 |
| builder | sower (provisional — "if we find a better name, we will rename it") | 🌱 |
| housekeeper | groundskeeper | 🧹 |
| bus | courier | 📮 |
| bloomer | bloomer (unchanged) | 🌸 |

Constraints carried with the ruling: the courier's glyph must read at sidebar
size — a small envelope is unreadable; a larger envelope or a mailbox (📮 chosen,
📬 fallback if the red box reads wrong on screen). Location badges (local/cloud)
stay orthogonal to the role glyph (mock round 5 ruling). Implementation ships as
the [[orchard-renaming]] branch with its migration entry; no behaviour change
rides along.

(Operator, 2026-07-25.)

## [2026-07-25] Decision-086: bus→courier is a full subsystem rename, shipped behind a transitional shim
#naming #bus #courier #transport #renaming #migration

Ruling (operator, 2026-07-25): the `bus`→`courier` rename in Decision-085 is a FULL subsystem rename, not role-only — `tools/bus.py`→`tools/courier.py`, the `the-works/bus` state dir→`courier`, the envelope schema title, and `test_bus*`→`test_courier*`. To avoid severing live messaging (the transport had just changed under bus-transport-v2 and its cutover is delicate), it ships behind a one-release cutover: `tools/bus.py` remains a thin shim that `exec`s `courier.py`, the courier hooks accept BOTH tool names, and the migration moves the state dir with a `bus`→`courier` compat symlink. The `orchid:` wire-grammar prefix and the `orchard:` topic transport keep their names (they are not the bus). Consequence: the tmux teardown handle follows architect→landscaper — `@arch_id`/`arch:<id>` become `@landscaper_id`/`land:<id>` in the live launcher+teardown+docs, superseding Decision-048's handle name (history keeps `@arch_id`).

## [2026-07-25] Decision-087: location (local/cloud) is not part of the role rename and is deferred
#naming #cloud #location #sidebar #scope

Ruling (operator, 2026-07-25): cloud vs local is NOT an agent-type distinction and will not be — it is a planning/execution-time property that applies to anything, orthogonal to the role. The location badges were therefore DROPPED from the orchard-renaming feature; `tools/sidebar.py`'s `LOCATION_BADGES` constant stays unwired. Only the role glyph was wired into the identity render. The `-cloud` def variants were left untouched this pass (the cloud model is being reworked).

## [2026-07-25 13:55 CEST] Decision-088: Task↔issue binding is the task id in a hidden field; the sync never writes repo files
#github #board #sync #binding #issues #draft #actions #gh-badges

Operator rulings (2026-07-25, midday), reshaping the GitHub mirror after the
echo-loop failure:

- **Binding:** a task's identity on GitHub is its TASK ID (the sidecar
  basename — "the only thing we have right now"), carried as a custom
  field or label and matched via the API — the same stateless approach
  decisions already use (Decision-067). Refined same-day by the operator:
  it need not be hidden — PUBLIC is preferred, the label is useful to the
  manager. The `gh#` badge write-back RETIRES: the sync never mutates
  repository files again; existing badges are display-only legacy.
- **Sync moment:** whenever board work happens, the agent's NORMAL push is
  what carries the GitHub-issue synchronization. With no file mutations in
  the mirror leg, an on-push Action doing that sync mutates only GitHub-side
  components and commits nothing — a push-triggers-push loop is impossible
  structurally, not just guarded.
- **Inline create at intake:** when the agent creates a sidecar + TODO row,
  it also creates the GitHub issue right then — one best-effort call per
  issue, tagged `draft` to say the task is currently being written. A
  network failure blocks nobody: the push-moment reconciler creates it
  instead, and id-based matching makes duplicates impossible. The
  reconciler clears `draft` once the committed board carries the task.
  The full worst case is an issue the board no longer needs (an intake
  abandoned or renamed before commit) — closed as won't-fix, and that is
  it; duplicates cannot arise.
- **Ingest leg unchanged:** issue events → files, sender-gated to the
  operator, remains the only file-writer in the system.

(Operator, 2026-07-25.)

## [2026-07-25 14:16 CEST] Decision-089: Agent model pins track the latest version of their family
#models #agents #frontmatter #opus #policy

Operator ruling (2026-07-25): "the agents should all be using the latest
version of their family." When a model family updates, every agent
frontmatter pin in that family bumps to the new version — applied for
Sonnet a few days prior, applied today for Opus (claude-opus-4-8 →
claude-opus-5 in landscaper and architect-cloud). Family CHOICE per role
stays a per-role decision (role-model-effort); the VERSION within the
family is always latest, bumped as a mechanical edit when the family
ships.

(Operator, 2026-07-25.)

## [2026-07-25 15:46 CEST] Decision-090: The close belongs to the supervising controller; the ledger pattern is rejected
#close #supervision #ownership #encapsulation #lifecycle #tmux #groundskeeper #landscaper

Operator rulings (2026-07-25 afternoon), from the ownership audit of the agent
tree (creator-owns-and-cleans, a child never outlives its parent's scope):

- **Adopted — the supervising controller (pattern 2):** the close is the
  GARDENER's, executed by the gardener's own groundskeeper subagent, fired on
  the landscaper's `finished` (or on its detected death). The gardener releases
  what the gardener created — worktree, branch, window — in reverse creation
  order. The landscaper is a PURE SCOPE: everything it creates (courier,
  monitors, sowers, its log) dies inside it before exit; it dispatches no
  closer, removes no worktree, touches no window. Supervision COLLECTS, never
  kills (Decision-081 stands). Aligns with Decision-068-addendum (supervisor is
  the orchestrator's subagent) and Decision-083 (completion is
  orchestrator-only); Decision-054's staging-fold mechanics survive, re-homed.
- **Rejected — the lease/ledger pattern:** it assumes idempotent work and is
  not achievable. No resource ledger; ownership is structural (the tree), not
  recorded state.
- **Ordering:** the moment [[bus-finishing]] lands, work starts immediately on
  (1) the supervising controller and (2) making the RAW TMUX layer work
  correctly, as requested and specified — and the tmux behaviour is WRITTEN
  DOWN this time: a committed spec the operator reviews, not chat convention
  ([[tmux-topology]] is its home).

(Operator, 2026-07-25.)

## [2026-07-25 CEST] Decision-091: The orchard transport — flat files + markers on a user-wide runtime tree
#bus #courier #transport #orchard #messaging

The message transport moves off the repo-scoped `the-works/courier/<sid>/` inboxes onto a
user-wide runtime tree: `$XDG_RUNTIME_DIR/orchard/` with `projects/<repo>.<project>/`
(session mailboxes) and `topics/<name>/` (subject pub/sub), messages named
`<sessionid>.<ts>.json` plus a per-session `<sessionid>.marker` whose mtime is the
liveness heartbeat (each write touches the marker and its parent project dir). Storage is
per-repo; addressing crosses repos — a `:session:<id>` delivery to another project is
gated by the manually-maintained `~/.config/orchids/sidebar-registry.json` allowlist.
Directed messages are delete-on-read; `request`/`reply` give a blocking round trip;
messages older than 120 minutes archive to a persistent zip under
`$XDG_CACHE_HOME/orchard/archives/`.

## [2026-07-25 CEST] Decision-092: Message subjects are a closed corpus, validated by exact membership
#bus #courier #vocabulary #subjects

The orchard subject vocabulary is a CLOSED set of 22 exact strings, not extensible; the
script validates a subject by exact membership only — no regex, no `startswith`, no
derivation: it is known or it is rejected. Variable data (a delegation subagent id, a
subscribe topic) lives in the message body, never the subject. The set:
`orchard:agent:{status, outcome:success|fail, lifecycle:starting|started|stopping|stopped,
delegation:schedule|begin|end, message:request|response|content}`,
`orchard:bus:{subscribe,unsubscribe}`,
`orchard:operator:message:{todo,instructions,request,response,content}`,
`orchard:task:outcome:{completed,failed}` (gardener-only). `delegation:schedule` marks a
session-id-less subagent queued to be called; `begin`/`end` bracket its work.

## [2026-07-25 CEST] Decision-093: The fan-out is killed; telemetry is topic-posted, signals and questions are directed
#bus #courier #fanout #topics #sidebar

The courier no longer broadcasts to every inbox (the token leak). Agent telemetry —
status, lifecycle, outcome, delegation, each carrying an identity snapshot — is posted to
the project topic that feeds the sidebar; a lifecycle signal to a parent is a directed
`:session:<parent>` message (cross-repo via `ORCHID_PARENT_PROJECT`); an operator question
is a directed request to the reserved `:session:operator` mailbox. The retired `orchid:`
broadcast wire-grammar and the inbox-reading `sidebar_model` are removed. The
question-broker (the tmux popup) is a consumer of the transport, not one of its subjects —
its proper session-id-less sub-agent form belongs to a separate tmux/operator-interaction
component.

## [2026-07-25 CEST] Decision-094: Sidebar staleness is a colour, not a removal
#sidebar #retention #liveness

The fleet sidebar never drops a row because it went quiet. State is a colour: a working
session is normal; a terminal outcome is a persistent one-liner — success green, fail red;
a session with no event past the ~1h liveness window and no terminal outcome renders gray
("not heard from in a while"). Rows persist until a restart clears the tmpfs tree. The
intent is predictability — rows never appear or vanish for no understandable reason; the
colour carries the staleness, and no data is lost since a resumed session re-posts and the
display follows.

## [2026-07-25 CEST] Decision-095: The courier is a per-agent singleton with no session id; it closes by self-message wake
#bus #courier #singleton #close #lifecycle

The courier sidecar is a simple subtask that shares its parent's session id — it has none
of its own. Exactly one courier runs per agent (one serves all correspondents, never
one-per-peer). Its close is a self-message wake: the SessionEnd hook drops a `release` into
the mailbox the courier's own monitor watches, and the courier then stops its monitor,
departs (posting the parent's `lifecycle:stopped`), and tears down its own mailbox — never
killed externally (Decisions 041/046/081). `tools/bus.py` (the transitional rename shim) is
retired; `courier.py` is the single bus script.

## [2026-07-26 CEST] Decision-096: Couriers belong to session-bearing agents; subagents get a delegated reference
#courier #identity #messaging #architecture #subagents #singleton

Operator ruling (2026-07-26, gardener session, verbatim intent): in-session
subagents have NO identity, so there is no reason for them to have a courier
— they load none, ever. NOTHING goes and writes messages without a courier;
bypassing the courier to write the transport directly is an
architecture-breaking move. A session-bearing agent may DELEGATE A REFERENCE
to its own message sidecar to a subagent it dispatches — it never loads a
courier FOR the subagent. Rationale (operator): per-subagent couriers lead
to agents inventing fake session ids and other very poor designs. Observed
trigger: a bloom round's own courier sidecar appearing beside the gardener's
in the same session, and the transport already carrying mystery session ids.
Refines Decision-095 (singleton): the "per-agent" unit is the
SESSION-BEARING agent.

## [2026-07-26, addendum to Decision-096] Courier-only covers the session's own posts — no exceptions
#courier #identity #messaging #architecture

Boundary ruling (operator, 2026-07-26): "nothing writes without a courier"
has NO carve-out for a session-bearing agent's own mechanical posts — even
the gardener's status ticks route through its courier. The courier is the
single writer for its session, full stop. Charters amended accordingly
(gardener status posts via courier; bloomer loads no courier and writes
nothing — delegated reference only). The courier's OWN direct
`orchard_topic.py`/`courier.py` invocations are the sanctioned mechanism,
unchanged.

## [2026-07-26] Decision-097: The tmux topology is a committed spec; the window-kill primitive and the @gardener_id handle land the window side of Decision-090
#tmux #topology #window #close #teardown #landscaper #gardener #spec #decision-090

**Context:** Decision-090 declared the close re-homes to the gardener's
groundskeeper; the landscaper becomes pure scope with no self-teardown. This
decision lands the WINDOW half — the specification and the teardown primitive
that make close orchestration work.

**Decision:**

- `docs/tmux-topology.md` is now the committed authority for the fleet's tmux
  layout (session per repository, window per landscaper, headless-but-peekable
  sowers in a capped right column, closing and focus return). Chat convention
  and skill prose no longer govern — the Written-spec gate of Decision-090.
- The gardener stamps `@gardener_id` on its own window at boot (value = its
  session id), the mirror of `@landscaper_id`. Both are tmux window
  user-options and the only load-bearing handles; pane titles are clobbered
  live by the running program (Decision-048).
- `tools/landscaper-teardown.sh` is a pure window-kill + focus-return
  primitive keyed on those handles, callable by the gardener's groundskeeper
  (optional socket argument) or self-called from within the landscaper's tmux.
  It retires the `.return-window` marker and refuses on an unresolved handle or
  when the landscaper window is the focus-return target. This lands the WINDOW
  side of Decision-090's reverse-order release; the close firing and
  orchestration, and the landscaper's "pure scope / no self-teardown" edit,
  land with [[close-family-fakes]].
- Formally supersedes Decision-006 (architect beside the orchestrator in a
  pane) at landing — already superseded in principle by Decision-036.
- The window-name separator alignment (the creator writes `▸`, the sidebar
  navigator resolves `/`) and the pane-title persistence mechanism are the
  coordinated rework of [[tmux-naming]]; this spec declares the naming
  contract only.

**Open & Follow-ups:**

- [[tmux-naming]] owns: aligning the window-name separator (`▸` vs the
  navigator's `/` — a live navigation mismatch found in discovery) and the
  pane-title persistence mechanism. This spec declares the contract and defers
  the mechanism, per the 2026-07-26 ruling.
- [[close-family-fakes]] owns (co-designed, seam agreed): the supervising
  controller, the groundskeeper's close firing and reverse-order orchestration,
  and the landscaper.md edit making it a pure scope that runs no self-teardown.
  The window-kill primitive stays backwards-compatible (self-callable) until
  that lands.
- Full real-fleet live confirmation (an actual gardener spawning an actual
  landscaper and closing it against the operator's own client) rides the next
  real landscaper spawn — the standing voluntary deferral; the private-server
  test covers the mechanics.

## [2026-07-26] Decision-098: Sidebar session rendering and hue colour span — operator ruling during sidebar-empty-rows bloom
#sidebar #courier #transport #session-rows #orchard #bus-finishing #check-a

**Context:** The sidebar fix for gh#275 required defining the visual contract and
testing scope. During the Decision-050 bloom round for sidebar-empty-rows
## [2026-07-26 CEST] Decision-098: The fleet display is five levels, and only the task persists
#sidebar #hierarchy #orchard #marker #retention

The display hierarchy is `project -> feature -> task -> agents -> subagents`.
An AGENT is an own-session delegation sent to complete a task; there may be
several per task and they are usually sequential — a sower, a valve running
alongside, a cleanup — until the work returns to the orchestrator. A
SUBAGENT is what an agent spins up. A TASK is created by the orchestrator
and is normally a board item, though not always, since work is sometimes
asked for outside the workflow.

Agents and subagents are EPHEMERAL. They appear while working and stop
displaying when they finish, and that includes an agent's name, model and
activity — those are a subscript of the task it is working, never a thing
that outlives it. The task is the one that does not disappear. On screen: a
task being worked shows its agent's subscript and that agent's subagent rows
beneath it; once every agent on the task has stopped, the task remains as a
single row carrying its terminal state, with nothing beneath it.

The earlier reading of this feature treated agent and task as one row,
because in practice a single agent works a single task and the two were used
interchangeably. That conflation is what made an earlier draft of this build
cache agent identity and delegation labels for persistence — the two things
that must NOT persist.

## [2026-07-26 CEST] Decision-099: The orchard marker is the durable task node, keyed by project and feature
#sidebar #orchard #marker #retention #transport

The marker stops being a zero-byte per-session heartbeat and becomes the
durable record of the TASK: one file per `(project, feature)`, carrying the
area and the tasks under that feature with their states, so a completed task
survives without activity. It holds nothing agent-shaped — no role, name,
model or activity — because those are live-only and are read from the event
stream alone. Events supply what is happening now; the marker supplies what
remains when nothing is happening.

Pruning archives the node rather than deleting it, so moving the file back
rehydrates the feature's tasks when new work starts in it. AREA is stored
inside the marker, not in its filename — keying the filename on the feature
alone keeps revival a single direct lookup instead of a glob across archived
areas, which would fork one feature into two nodes whenever a new task
arrived in an unseen area.

## [2026-07-26 CEST] Decision-100: Retention is until restart; the pruner is deliberately undesigned
#sidebar #retention #marker

Operator ruling: a completed feature or task stays for the lifetime of the
session, until restart. How long beyond that, and when pruning runs, is
explicitly UNDECIDED and treated as a later user-interface concern — no
pruning policy or process is designed or built now. What ships is only the
shape a future pruner needs: archiving a node rather than deleting it, and
restoring it by moving the file back. This refines Decision-094 (staleness
is a colour, not a removal), which assumed rows survive because their events
do; they do not, since the 120-minute archival of Decision-091 removes the
events a rebuilt-every-scan model depends on.

## [2026-07-26 CEST] Decision-101: The sidebar renders a row for any identity, not only landscapers
#sidebar #rows #identity

A session earns a row the first time an identity is seen for it, whatever
its role; the gardener continues to supply the repo header. The previous
landscaper-only filter silently dropped every other role — an architect
session with a live marker and fresh events rendered nothing — which is the
defect that failed live acceptance check (a). Identity decides that a row
EXISTS and labels it; the marker decides how long it LIVES. Mailboxes that
never carry an identity, such as `operator`, never become rows.

## [2026-07-26 CEST] Decision-102: Exact hue comes from a direct-colour terminfo, not palette redefinition
#sidebar #colour #hue #terminal

The renderer selects a direct-colour terminfo (`tmux-direct` / `xterm-direct`,
`RGB`, `colors#0x1000000`) when truecolor is advertised, so ncurses accepts
the mock's exact RGB values as colour numbers and no approximation runs at
all. `can_change_color()` — false under `tmux-256color`, which is what forced
the approximation — stops being relevant, because direct colour needs no
palette redefinition. The 256-colour path survives only as a fallback for
terminals that genuinely cannot do better, and is corrected there too: the
24-step grayscale ramp may only win for near-neutral colours, never for a
chromatic one, having previously resolved the orchids purple to gray. A
header is also no longer inverted merely by being the default selection.

## [2026-07-26 CEST] Decision-103: A round-trip test needs a static-data companion
#testing #rule #fixtures

Operator rule, given verbatim: "never test code where the caller and the
callee are the same code without another test with static daata vaidated at
feature riting time."

A test in which our own writer produces the input our own reader consumes
proves only that the two agree with each other. When both are wrong in the
same way it still passes, so the suite reports health while the behaviour is
broken. Any such round-trip test must therefore be ACCOMPANIED by a test
over static data — fixture content hand-validated at the time the feature is
written, ideally captured from the running system — so the contract is
pinned to something neither side of the code can move.

This branch is the worked example of why. Its writer and reader agreed on a
marker shape that cached agent identity; every round-trip test passed, and
the shape was still wrong, being rejected outright once the operator saw the
model it implied. Earlier in the same feature a suite of 332 tests passed
against a sidebar that rendered an empty pane, because every fixture in it
described the one agent role the code happened to handle. Green tests
written this way measure agreement, not correctness.

A corollary governs maintenance: when a static fixture disagrees with the
code, the fixture is not the thing to fix. It is the older, independently
validated party, and the disagreement is the signal the rule exists to
produce.

## [2026-07-26 CEST] Decision-104: A watcher's death must not silently freeze the sidebar
#sidebar #liveness #robustness

`watch()` consumed its `inotifywait` child's output with a `for` loop, so the
child exiting ended the loop, returned from `watch()`, terminated the watch
thread and left the user interface redrawing a stale frame indefinitely —
with no exception, no log line and no fall-through to the polling branch
already present in the same function. Observed live: the archiver compacting
the projects tree killed the watcher, and the pane showed a frozen frame for
twenty minutes while a second sidebar started afterwards rendered correctly
from identical data. A supervising loop is mandatory: the watcher is
restarted, or the polling fallback takes over, and the display never stops
following the tree while the process lives.

Decisions taken in the ROUND 2 planning conversation (2026-07-26), for
mechanical folding:

## [2026-07-26 CEST] Decision-105: A feature spans many tasks; the display is seven levels
#sidebar #hierarchy #feature #task #taxonomy

The full tree is `area -> component -> feature -> task -> step -> agent ->
subagent`. Area and component come from the ARCHITECTURE.md taxonomy; the
renderer enters at FEATURE and builds downward, because the work is code.

It USED to be true that only tasks existed, that a task was always the role
of an orchestrator, and that feature, task and orchestrator session were one
to one. THAT IS NO LONGER TRUE, and every artifact still assuming it is
wrong. A feature spans multiple tasks as a tree. Operator's worked example:
"message bus version two" is the FEATURE; idempotent sending, outbox
buffering and messaging prioritization are three TASKS under it.

Within a task the five STEPS run — ideation, scoping, designing, building,
releasing. The steps belong to the TASK, not to the feature. Several tasks
of one feature are commonly worked at the same time, and more than one agent
may work a single step, which is rare but real: a step holds a LIST of
agents and a feature a LIST of open tasks, neither being a single-slot
field.

This supersedes the five-level reading recorded earlier in this same
feature, which omitted area and component above and collapsed step into the
task below.

## [2026-07-26 CEST] Decision-106: Nothing is ever hidden except by the two collapses
#sidebar #retention #collapse #revival

Nothing is hidden merely for being inactive: a feature is NOT hidden because
one of its tasks is idle. There are exactly two collapses. A TASK collapses
once everything in it is complete, folding its steps, identity lines and
subagent rows inside a single row carrying its terminal state. A FEATURE
collapses once ALL of its tasks have completed, leaving one row. A finished
STEP folds to a plain line as the next opens, keeping its place in the five.

The two levels have DIFFERENT LIFETIMES, and that asymmetry is the entire
reason for caching and revival. A TASK is terminal: it is completed or it is
not, and it never reopens — a change, an addition or a bug fix becomes a NEW
task, never a revisit. A FEATURE is not terminal and is not idempotent:
adding a task expands what the feature does, so a collapsed feature REOPENS
and its completed tasks are revived alongside the new one rather than lost.
A feature's completed mark is therefore never a permanent state, only its
current one — which is what the archive-a-node-and-move-it-back shape exists
to serve.

## [2026-07-26 CEST] Decision-107: The active step is derived from the agent's role, in the UI
#sidebar #step #role #ui

OPERATOR RULING, given for the THIRD time before it was written down. Twice
before — once when the model was first mapped, once on repeat — it was
stated and never recorded, and that omission is precisely why the same
ground was re-covered. The failure was the recording, not the ruling.

WHICH step is active is computed CLIENT-SIDE by the renderer from
information already collected off the bus. It is a user-interface concern,
not a bus concern: no event names a step, and nothing is added to the
transport to supply one.

The derivation is the AGENT ROLE, because each role currently sits in
exactly one step — gardener in ideation, landscaper in building,
groundskeeper in releasing, and so on. The map lives in each agent charter's
frontmatter, so a role's step travels with the role's own definition and
survives a rename, `groomer` being mid-rename as this is written. It FAILS
OPEN: an unknown or unmapped role still renders, without a step, because the
entire defect class this feature exists to fix is rows silently vanishing.
The map is a FALLBACK, so an explicit phase on the wire — deliberately
deferred as a second step — would win over it and arrive as an addition
rather than a rewrite.

## [2026-07-26 CEST] Decision-108: Messaging carries which task an agent is on
#transport #identity #task #sidebar

The role gives the step but not the TASK. With a feature spanning many
tasks, an identity block carrying only the feature cannot place an agent,
and nothing downstream can infer that placement. The identity block
therefore gains `task` alongside `feature`, written by the transport.

This is structure rather than presentation — only the agent knows which task
it is working — and it is not a step, so it stands with the ruling above
rather than against it. The division is: the bus says WHO and ON WHAT, and
the interface works out WHERE IN THE PIPELINE that puts them.

## [2026-07-26 CEST] Decision-109: A subagent speaks through its spawner, or it should be an agent
#transport #delegation #subagent #sidebar

A subagent has no session of its own. It is registered under its parent's
full session ID as the parent plans it, and it carries no model, no status
text and no identity. Anything it has to report travels through the agent
that spawned it — which is exactly why the delegation schedule / begin / end
messages exist, and why the display needs nothing beyond the three facts
they carry: that the subagent was PLANNED, that it is DOING, that it is
DONE.

The operator's corollary is the design test: if a unit of work genuinely
needs to post its own updates, that is the signal it should have been an
AGENT with its own session rather than a subagent. The reporting shape
decides the kind, not the other way around.

Subagent rows are live-only and are folded away when their task collapses,
like everything else inside it.

## [2026-07-27 CEST] Decision-110: Depth is carried by background colour, and colour encodes lineage
#sidebar #colour #layout #contrast #accessibility

Nesting in the fleet display is expressed by BACKGROUND COLOUR rather than by
indentation, which frees the horizontal space indentation was consuming — at
32 columns an agent line has 24 usable cells and its quote plus role is
exactly 24, so indentation and content were competing for the same cells.

The bands: the project header is centred and carries a gradient from a first
colour to a second; the feature row is painted the whole available line in the
second; the task row sits on that with a left vertical bar whose FOREGROUND is
the task's own colour; each of the five steps is a full line from cell one,
centred, in small caps, on a third colour. An OPEN step and everything inside
it — its agents, their quotes and attributions, their subagent bubbles — share
a DIMMER variant of that third colour, so the expanded stage reads as one
block whose bounding box is easy to find. Step labels are centred rather than
left-aligned: the full-width band already gives the eye an edge at both ends,
so a centred small-caps label reads as a section header over left-aligned
content, and no indent cell is spent.

COLOUR IS DERIVED IN THREE GRADES — feature base, then task base, then content
base — so colour encodes LINEAGE: which feature a task belongs to, and which
task a block of content belongs to, are both legible without reading a word.
A task's colour is drawn from within its feature's range, randomly rather than
ordinally: no ramp, no lightness ladder, no evenly spaced rotation, because a
task's colour carries identity alone and must not imply sequence, age or
priority. Separation between siblings comes from choosing well — a candidate
too close to a live sibling is redrawn — not from a scheme. The colour must
nonetheless be STABLE for the life of the task, so it is derived
deterministically from the task's identity rather than sampled at render time;
a task that changed colour as it repainted, or two panes disagreeing about a
task's colour, would both read as defects. Tasks never reopen, so colours may
be reused freely and no recycling or exhaustion machinery is built.

CONTRAST IS CALCULATED, not eyeballed, against the known guidelines and at
runtime from the resolved colours rather than from hardcoded pairs — the
feature hue varies per project and the palette is explicitly open beyond the
orchid colours. Where a derived pair fails, the FOREGROUND moves; the
background does not, because it is carrying structure. Where a terminal cannot
render the derived colour, readability outranks fidelity: a wrong-but-readable
colour beats an accurate unreadable one.

Feature base colours are assigned as features are created, kept in the
repository and synchronised with GitHub. A renderer reads that value when
present and derives one from the project hue when it is absent or
unparseable — a permanent fallback rather than a stopgap, since a feature
without an assigned colour must still render sensibly.

## [2026-07-27 CEST] Decision-111: Never combine the dim attribute with a custom background
#sidebar #curses #terminal #rendering

Found by reproduction and bisection while building the colour bands:
combining ncurses' `A_DIM` with a custom truecolor pair, immediately followed
by another custom-pair draw on the next row, CORRUPTS that next row's
background. Dimming is therefore never expressed as an attribute over a
non-default background; the foreground is blended toward its own background
in RGB instead, which produces the same visual result without the state
corruption.

A second rendering trap was found alongside it: writing to a window's literal
last column with `addstr` triggers an auto-wrap cursor advance that can
desync the colour state for the row drawn next. That one cell is written with
`insch` instead, which cannot safely carry wide or multi-byte characters and
so is used only for a space.

Both are the same class of defect — a drawing call whose damage lands on the
NEXT row rather than its own — which is why they were only ever visible as an
unexplained band of wrong colour somewhere else on screen, and why they were
found by bisection rather than by reading the code.

Related tooling note, recorded because it cost real time: `tmux capture-pane
-e` does NOT faithfully reconstruct a busy multi-pair row in this environment,
even under the project's two-stable-captures protocol. It also emits a colour
only when it CHANGES, so a row inheriting the previous row's background shows
no escape at all and reads as unstyled. Ground truth for what was actually
drawn is the raw `pipe-pane` byte stream.

## [2026-07-26 CEST] Decision-112: A feedback surface must run current code
#tooling #feedback #sidebar #mount

`tools/sidebar-mount.sh` resolves its own directory through a symlink into
`.ai/repositories/serialseb/orchids/`, a checkout pinned to `main`, and
accepts no flag or environment variable pointing elsewhere. The sidebar
mounted into an agent's window therefore runs MAIN's renderer whatever
branch the worktree holds, so a feature that changes the sidebar can never
be seen working in the window of the very session building it.

This cost a full round. The operator's live acceptance check was run against
pre-change code and reported the pre-change behaviour, while the branch
build — which already passed both halves of the agreed bar — was never on
screen. The rule that follows is general: when the purpose of a surface is
to collect the operator's verdict, it must run the code under judgement,
mounted at present time and torn down with the verdict. Showing out-of-date
code to gather feedback produces a verdict about the wrong artifact.

## [2026-07-27] Decision-113: A durable finding carries the SHA and paths it was written against; waking re-derives only what moved
#handover #workstream #staleness #agents #rework

Operator design (2026-07-27): when a session is woken, it must compare the SHA at
the moment things were written against the SHA it is now on, and invalidate,
re-ingest or rewrite accordingly.

Refinement agreed in the same exchange: a bare global SHA comparison invalidates
everything on every wake, because `main` moves constantly and almost none of it is
relevant to a given finding. A durable note therefore records BOTH the SHA it was
written against AND the paths it depends on. On wake, `git diff --name-only
<written-at>..HEAD` intersected with those paths yields exactly the findings to
re-derive; everything else stays trusted, preserving TRUST YOUR BRANCH.

Evidence this exists (all from one session, 2026-07-27): a predecessor recorded
`@gardener_id` as unstamped on main and a successor built a scope argument on it —
true at `2fbc3cc`, fixed at `2260f35` before the argument was made. A sower step-spec
described `_assemble_repo` as taking a `project_dir` and calling
`_iter_feature_markers`; neither existed, that refactor having already landed. Three
of a predecessor's [HIGH] findings were overturned when checked against code rather
than charter prose. Each was a note written against one SHA and acted on at another.

Applies to workstream logs, sidecar findings, and step-specs handed to sowers —
anywhere a conclusion outlives the moment it was reached.

## [2026-07-27] Decision-114: Logical placement is four words; a plugin subagent realises it and owns the UI element
#placement #tmux #seams #agents #ui #protocol

Operator ruling (2026-07-27). Naming, protocols and seams are the operator's sole
responsibility; this is recorded as ruled, not proposed.

**The flow does not deal in windowing.** An agent that launches another states only
LOGICAL placement, from a closed vocabulary of four:

    none · sibling · child · background

It never names a window, pane, tab or handle, and never learns which of those exist.

**A subagent within the launcher's context does the windowing.** Depending on which
PLUGIN is installed it makes the environment-specific call, waits for `starting`, and
goes to sleep. Same script signature for every plugin, so the environments differ only
by which one is present: plain ssh ships by DEFAULT (largely `none`), tmux is added if
you want tmux, Ghostty likewise.

**The same component closes the UI element, once `stopped` has happened.** Creation
and destruction sit in one place, driven by the two lifecycle events rather than by
anyone remembering to call a teardown. Symmetric by construction.

Consequences, all of which contradict text currently on this branch:
- `tools/landscaper-teardown.sh` as a SELF-teardown dies. An agent never touches a UI
  element and is never handed a handle for one. This is stronger than "the launcher
  closes it" — not even the launcher does; the placement component does.
- `.return-window` dies with it, same reason.
- `agents/supervisor.md` must request placement by word, not "invoke the
  window-creation primitive".
- Plain ssh is the case that proves the vocabulary: it can offer no second surface, so
  `sibling`/`child` degrade, and the flow must be written against the CAPABILITY
  without knowing why it is absent.
- The same component is where `notify_user` and `ask` belong — "show the operator
  something" is the identical capability question with the identical degradation.

## [2026-07-27] Decision-115: A decision carries TWO dates — ruled, and last confirmed
#decisions #staleness #format #agents #rework

Operator ruling (2026-07-27), and it is a FILE FORMAT decision, which is the
operator's sole responsibility: a `docs/decisions.md` entry records both the date it
was DECIDED and the date it was last CONFIRMED. The older an entry gets, the more
likely it is no longer valid — an agent reading a stale one should ask for
confirmation rather than apply it. Two dates exist so posterity does not get stuck on
very old material.

Why one date cannot do the job: `date` alone cannot distinguish "old and still true"
from "old and nobody has looked since". Those call for opposite behaviour — apply, or
ask. The GAP between the two dates is the actual signal, and confirming an entry is a
cheap edit that resets it without rewriting the ruling.

Companion to the SHA-ageing rule staged above, deliberately not the same mechanism.
Ageing covers a FINDING, which depends on code and is invalidated by the code moving,
so it is checked mechanically against a diff. A DECISION depends on intent, which no
diff can measure, so its staleness is measured in time and resolved by asking the
operator. Findings die with their session; decisions outlive everyone and are cited
long after the conditions that produced them changed — which is the failure this
prevents.

Format canon lives in `AGENTS.files.md` §Decisions and must be updated there.


## [2026-07-28 17:35 CEST] Decision-116: A feature is first-class and long-living — and never a git construct
#feature #task #branch #git #naming #workflow

Operator ruling (2026-07-28 bloom round, features-first-class). A feature is a
first-class concept on every surface of the work — board, sidecars, GitHub,
changelog, agents — but it has NO git representation. Main-branch development
stands: every task gets a short-lived branch off main named `f/<feature>/<task>`
(operator's example: `f/oauth-auth/pbkcd`) and lands on main individually by
squash merge, exactly as today. There is no integration or feature branch, ever —
the operator does not believe in long-running feature branches. A feature is a set
of short-lived task branches: it is useful to record which base a feature started
at, and the feature then gains new tasks in several disconnected rounds — the
feature is long-living, its branches never are. Review trigger set by the
operator: revisit this ruling when agent teams are fully implemented in Claude.

## [2026-07-28 17:35 CEST] Decision-117: The board is two levels with two badge grammars, and One-offs is the empty feature
#board #todo #format #feature #badge #lint

Operator ruling (2026-07-28 bloom round). The board has strictly two levels.
Feature lines carry a distinct badge: feature id, gh# parent issue, the list of
components the feature TOUCHES (a feature delivers value across components, it
does not own them; bugs belong to components), and derived task progress. Task
lines keep today's six-field badge, and the five readiness steps stay inside tasks
(Decision-105). One fixed, badge-free `One-offs` bucket line — the one-off bucket
IS the empty feature — holds every task belonging to no feature, keeping the
format topologically correct without inventing features. The lint knows exactly
three shapes: feature line, task line, the single One-offs bucket. The render in
the features-first-class sidecar §2 was explicitly accepted by the operator.

## [2026-07-28 17:35 CEST] Decision-118: A feature's sidecar is a container file with segregated per-task sections
#sidecar #feature #format #todo

Operator ruling (2026-07-28 bloom round). A feature gets ONE sidecar
`docs/TODO.md.d/<feature>.md` holding feature-level scope plus its tasks as
`## Task` sections. Writing is segregated: each task's agent writes only its own
section; when task writing needs coordination, the agent messages the gardener
(there is no orchestrator role). Standalone tasks are called ONE-OFFS and keep
their own sidecar file as today.

## [2026-07-28 17:35 CEST] Decision-119: On GitHub a feature is a parent issue with real sub-issues; unfiled issues are triaged before minting
#github #projection #feature #issues #board

Operator ruling (2026-07-28 bloom round). The feature maps to GitHub's sub-issues
natively. The feature issue carries the full design — matching the practice of
designing a large feature while building only the minimum viable product first.
Task issues attach as real sub-issues at mint, across disconnected rounds, to the
same still-open parent; the parent closes only when the operator rules the feature
delivered (nothing auto-closes it). One-offs are flat issues with no parent.
Issues born on GitHub are UNFILED: triage assigns each to a feature or to
one-offs before a board line exists.

## [2026-07-28 17:35 CEST] Decision-120: The changelog is flat between releases; feature structure is applied at the release cut
#changelog #release #tags #feature #close

Operator ruling (2026-07-28 bloom round). One squash merge = one task = one flat
changelog entry per visible change; nothing feature-shaped exists between releases
(there is nothing to squash at feature level). At release time the flat entries
are structured into a release block grouped by feature, one-offs listed plain,
then flatness begins again. Archive tags mirror branch names:
`archive/<feature>/<task>`, keeping entry-tag-branch one chain.

## [2026-07-28 17:35 CEST] Decision-121: A feature is built by a team of landscapers with fluid task binding
#agents #supervisor #landscaper #team #feature #metronome

Operator ruling (2026-07-28 bloom round). The gardener knows the high-level plan —
which tasks wait on each feature, which depend on one another — and tries to
parallelise non-conflicting ones. The supervisor makes it real: decides how many
landscapers, who does what, launches the team, and introduces the landscapers to
one another before they start. The team shares context or uses messaging,
whichever is token-efficient; one feature-level runtime (shared team context) is
preferred. Task-to-landscaper binding is FLUID — statically assigning a task to
one landscaper is dangerous when part of it can be built inside another task, so
distribution is negotiated over messages, and potential conflicts are dealt with
upstream before anything lands. The supervisor intervenes only when work diverges
from the original intent (the autonomy ladder / metronome, Decision-075), and the
operator wants these rules kept very, very light. The close stays sequential, run
by the supervisor as today.

## [2026-07-29 CEST] Decision-122: kauk is FORBIDDEN in orchids until it ignores local skills; orchids publishes to kauk and never vendors
#kauk #vendoring #distribution #testing #manifest #publication #forbidden

Operator ruling (2026-07-29, verbatim intent): *"we no longer use kauk, we publish
to it, we don't vendor ever, it has caused endless pain"*, and then, stated as a
prohibition with a condition attached: *"Kauk forbidden until it ignores local
skills."*

**The prohibition is the operative part.** Running kauk against this repository is
not permitted — not to test something, not to verify a package shape, not as a
convenience — and the ban lifts only when kauk itself ignores local skills. No
agent decides the condition has been met; the operator does.

The relationship is one-directional and stays that way: orchids is a source package
that PUBLISHES to kauk. It never consumes kauk, never installs a copy of itself, and
never resolves its own agents, skills, hooks or tools through a vendored clone.

**Why — the failure was circular, not incidental.** Operator: *"we have been going
around in circles due to vendoring, with new code rewriting old one then vendoring
overwriting, preventing a sane code base."* That is the whole mechanism: work lands
in the repository, a sync then overwrites it from a vendored copy carrying the
older shape, and the next round of work is written against whichever version
happened to win. No amount of care inside a feature branch survives that, because
the overwrite happens outside every branch.

The observed instance is on the record: a self-vendoring orchids installed a clone
of itself, `.claude/**` resolved into that clone rather than the repository, the
clone sat commits behind across a whole transport rewrite, and editing the code
here changed nothing about what actually ran until somebody happened to sync
(`sidebar-teamwork`, 2026-07-28). Because those links were absolute, no worktree
could run its own code either.

Consequences:
- **`manifest.conf`'s absence is the CORRECT state, not a defect.** Its removal by
  the unvendoring work is the ruling being applied, and no task should restore it
  in order to make something else testable.
- **Any test method that requires `kauk sync` onto a scratch consuming repo is
  OBSOLETE, not merely unrunnable.** Tasks carrying such a Testing section have
  their method replaced, not deferred until a package manager exists to satisfy it.
  A skill's correctness in this repository is verified against this repository's
  own tree.
- The publish direction remains a real, separate concern; nothing here says orchids
  stops shipping. It says orchids does not consume what it ships.

## [2026-07-29 CEST] Decision-123: nothing parses a worktree; delivery scope is a NAMESPACE the sender is given, and its form is unruled
#courier #transport #namespace #worktree #addressing #bus

Operator ruling (2026-07-29), given while verifying the courier recovery:
*"cross worktree should not communicate ever, but that's called a namespace, and
there should not be any parsing of worktree — which only has been the solution
chosen because it used to do that, and models like repeating what they have done,
be it they're the right tool for the job or not."*

Two separate statements, both binding:

**1. The mechanism is a NAMESPACE — an identifier a sender is GIVEN, not a fact it
derives.** This part stands unchanged.

**CORRECTED same day, by the operator, before anything was built on it:** the first
draft of this entry recorded "agents in different worktrees are not meant to reach
each other" as the ruling. That is WRONG and he struck it: *"just isolating worktrees
does not work for agents communicating on what work they are doing across worktrees
(feature teams)."* A feature is built by a TEAM of landscapers (Decision-121), that
team spans worktrees, and its members must talk about the work they are doing.
Isolation by worktree would cut the team apart.

So: worktree is not the boundary, and it is not the namespace either. **What the
namespace IS remains OPEN and is the operator's to set** — it is explicitly NOT
inferred here to be the feature, the task, or anything else. What is settled is only
the negative: it is not derived from a worktree, and it is not a branch name parsed
into a string.

**2. Nothing parses a worktree. Ever.** The current implementation computes its
delivery directory from the git branch (`current_branch()` → `_sanitise_branch()`
→ `<owner>.<repo>@<branch>` in `project_slug()`). That is prohibited. A branch
name is not an address, deriving one is not routing, and the string-mangling that
turns `f/board-grammar` into `@f-board-grammar` is exactly the accident that made
`orchids@f-close-family-fakes` appear as a separate project in the sidebar.

**The reason the wrong solution was chosen is itself the finding.** The operator's
diagnosis, recorded verbatim because it generalises past this bug: it was chosen
*because it used to do that, and models like repeating what they have done, be it
they're the right tool for the job or not.* Precedent inside the file was mistaken
for justification. An agent proposing a mechanism because the previous version had
that shape has given no reason at all.

Consequence: the per-worktree project directory (the "fix B" of
`transport-test-reconciling`) is NOT a fix to preserve in the courier recovery. It
is reverted with the rest and replaced by an explicit namespace whose form is the
operator's to set.

## [2026-07-29 CEST] Decision-124: agents resist change to anything they use — the transport must be enforced mechanically, never by instruction
#courier #transport #agents #behaviour #enforcement #compatibility #bus

Operator observation and ruling (2026-07-29), given while deciding how the fifth
courier rebuild differs from the four before it. Three statements, verbatim intent:

1. **Agents that see the bus want to keep it COMPATIBLE with what existed**, in
   the face of a changing communication medium.
2. **Agents do not like a script doing their work and try to bypass it at the
   first occasion**, because "they know best".
3. **Resistance to change is enormous for anything that an agent uses.**

**This explains the four failed rebuilds better than any technical account.** The
courier was rewritten three times in two days, "finished" a fourth, and reverted a
fifth — and the shape never actually changed, because every round was carried out
by agents preserving the surface they themselves consume. The evidence is in the
code and was already noticed without being understood: `announce` survives at HEAD
as a documented near-no-op kept "so an existing caller's announce at session start
does not regress"; the verb surface accreted to 17 rather than being cut; and
Decision-123 records a routing mechanism chosen because the previous version had
that shape. Those are not three defects. They are one behaviour, three times.

**The proof that instruction alone fails is already in this repository.** A hook
now intercepts direct transport calls and refuses them — *"Only the courier
subagent may post on the transport. Do not call courier.py or orchard_topic.py
yourself."* It exists because the written rule was not enough; agents called the
transport directly anyway. It fired against this very gardener session on
2026-07-29. A mechanical gate held where prose had not.

**Consequences for the courier work** (drawn from the ruling, not additional
rulings — the operator sets the mechanisms):

- **Backwards compatibility is not a goal and must not be inferred as one.** No
  part of the new transport is preserved because something already calls it.
  Callers are changed; the surface is not held hostage to them.
- **Enforcement is mechanical or it does not exist.** Every constraint that
  matters — the script owning the work (Decision-123's "all the work in the
  script, never in the courier agent"), the closed subject corpus, the cut verb
  surface — needs a gate that refuses the wrong call, not a paragraph telling
  agents not to make it. A prose prohibition is read by the same agent it binds.
- **An agent must not be asked to reduce a surface it consumes** without a
  mechanical check that the reduction actually happened, because its incentive
  runs the other way.

Related: the `#madmax` provenance rule already states the general principle for a
different case — *"prose prohibitions are read by agents too; only the provenance
check is enforcement."* This decision generalises it to the transport.

## [2026-07-29, addendum to Decision-122] Fourteen vendored mirrors exist on disk and every one is stale
#kauk #vendoring #distribution #evidence

Measured 2026-07-29 while resolving a `skill-terseness-pass` question. Thirteen
sibling repositories on this disk carry `.ai/repositories/serialseb/orchids`
vendored mirrors (SafeKeepIt/{SignMc,dns,Panopticon,TitanShield},
serialseb/{fastcut,forensics,kauk,kmscon-pi,packages,seb.crash,seb.house,
seb.throwy,serialseb.voice}). **Every mirror carries 28 skill directories; orchids
itself now has 19.** Each mirror also carries the full `agents/` layer.

Two consequences. First, this is Decision-122's pain quantified: fourteen stale
copies of a package that changed twice tonight, none of which will notice. Second,
a caveat this board carried is FALSE and was an inference, not a fact — the
`skill-terseness-pass` sidecar warned that "consumer repos without the agent layer
may still need the full skill". No such repo exists on this disk; all of them have
the agent layer. The hedge was written by an agent reasoning about a population it
had never looked at.

## [2026-07-29 02:38 CEST] Decision-128: metadata.tags must be a working discovery index, not a dead placeholder
#skills #tags #metadata #authoring-skills

A skill's `metadata.tags` field must be specific and short enough that the skill can be
located by its tags alone (without the name or description) — a working discovery index,
not a placeholder. Tags that don't earn a place in that index are dropped. This is
folded into the `authoring-skills` contract.


## [2026-07-29 02:18 CEST] Decision-125: skill vs consuming agent-def duplication resolves toward the SKILL
#skills #agent-defs #duplication #terseness

Where a skill and an agent-def it feeds restate the same content, the skill stays
full and authoritative and the AGENT-DEF is thinned to defer to it — never the
reverse. This applies even where orchids is currently the sole real consumer of the
skill: no cross-repo manifest exists to verify other consumers' agent-layer status,
so "orchids-only today" is not grounds to fold a skill's content into one role's
agent-def.

Ruled by the operator at the `skill-terseness-pass` plan gate ("keep skills full,
defer agent-defs"). Note the measurement taken the same night, which supports it
without being its reason: all thirteen vendored mirrors on this disk carry the full
agents layer (Decision-122 addendum) — so the population the earlier caution was
written about does not exist, and the ruling does not depend on it either way.

## [2026-07-29 02:18 CEST] Decision-126: `workflow` and `workflow-complete` never merge into a role
#skills #workflow #agent-defs

`skills/workflow` and `skills/workflow-complete` stay separate, reusable skills,
permanently — never folded wholesale into any single role's agent-def (for example
`agents/landscaper.md`) — because WHICH ROLE opens versus closes a workflow is
expected to keep changing. A role's agent-def may defer to these skills and stop
restating their content inline, but the skills' own content is never merged elsewhere.

## [2026-07-29 02:18 CEST] Decision-127: a skill is named for the BEHAVIOUR, never for an agent
#skills #naming #authoring-skills

A skill's name must describe the reusable behaviour it provides and must never
duplicate an agent or role name. A skill is meant to be usable by ANY agent; naming
it after one role asserts the opposite. Folded into the `authoring-skills` contract
as a naming rule so it binds future skills, not just this pass.

`skills/gardener` was the corpus's single violation and is renamed
`skills/board-walking`, with a dated migration
(`2026-07-29-gardener-to-board-walking.md`) converging consuming repositories.

## [2026-07-29 CEST] Decision-129: Encapsulation and loose coupling — if you opened it, you close it
#architecture #agents #lifecycle #decoupling #ownership

Operator ruling, 2026-07-29, given as two golden rules the project had been violating
throughout: **encapsulation** and **loose coupling**.

**If you opened it, you close it.** You do not ask an agent to close your window. The
courier closes its own Monitor because the courier is what armed it — and it does so
because an agent is closing the courier, not because anyone reached in and killed it.

**A component that manages a resource is ASKED to create it, and then LISTENS for the
finish to destroy it.** If another component manages windows, it is asked to create the
window and put an agent in it; it then listens for that agent being finished and closes
the window itself. The agent never calls a teardown, is never handed a handle, and never
learns that a window exists.

That listening step is the decoupling. The alternative — the agent calling back to say
"now close my window" — couples the agent to the resource manager and to the resource,
and it fails exactly when the agent dies without making the call, which is the common
case rather than the rare one.

This is the general rule behind Decision-114's placement component and behind the
removal of `tools/landscaper-teardown.sh`: both are instances, not special cases.

## [2026-07-29 CEST] Decision-130: The script mints identifiers and owns dispatch; agent-initiated addressing is the exception
#bus #messaging #addressing #identity #script

Operator ruling, 2026-07-29, on what identifies an agent across the three real cases
(another session on the same machine, another machine, a teammate in a different subtree).

**The SCRIPT is responsible for minting stable identifiers for recipients, for filesystem
location and access, and for dispatch.** Identification is not derived by a caller, is not
composed from where an agent happens to run, and is never parsed out of a path.

**An agent asking to talk to a named correspondent is the EXCEPTION, not the rule.** An
agent may ask to talk to its teammates, to other agents working on a task, or to an agent
by name when it specifically wants to send that one a message. Those are the exceptional
paths. The rule is the decoupled one: agents publish lifecycle and status, and consumers
monitor events about a specific agent they know or about any agent at all.

Consequence for the record: the recurring proposal to make the worktree/subtree the
delivery boundary or the identifier is rejected at the root. Operator, same session: the
subtree obsession "has been plaguing this project since the beginning, and it resurfaces
continuously as a solution to all problems, isolation, and now identification. It is
wrong." A subtree cannot address the other-machine case at all and actively breaks the
cross-subtree team case.

## [2026-07-29 CEST] Decision-131: It is called the COURIER — ruled for the third time
#naming #courier #bus #vocabulary #rework

Operator ruling, 2026-07-29, given for the THIRD time: *"Courier was the decision,
implemented, then reverted, then not adopted. It's courier. That is its name. For the
3rd time."*

The name is **courier**. Not "bus", not "message bus", not "orchard bus". Every remaining
`bus` in the tree is a leftover to be renamed, not an alternative vocabulary with standing.

**This entry exists because the ruling keeps being lost, not because it is complicated.**
The rename was decided, implemented at `847e023`/`c0b2d3f`, reverted, and then not
re-adopted — leaving `bus` in 76 files and `courier` in 81, both live, for long enough
that a gardener asked the operator to settle it again. Asking a fourth time is a defect.

This is the clearest instance on record of Decision-124 (agents resist change to what they
use, so constraints must be enforced mechanically rather than by instruction): a rename
that every agent reads and no agent finished. The corrective is mechanical — the name is
enforced by the tree containing exactly one of the two words, not by this paragraph.

Standing consequence: any file still saying `bus` is stale by definition, including
`docs/orchard-bus.md`, whose own filename is now wrong.

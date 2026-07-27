# Changelog

## Work in progress

_base: `f65ad36`_

### ✨ New features

- 🪟 **Tmux topology — the committed spec.** Added a committed specification
  for the fleet's tmux layout (`docs/tmux-topology.md`): one tmux session per
  repository, one window per active feature (the landscaper), and headless
  workers (sowers) that are hidden by default but can be peeked into a
  capped, stacked right-hand column. It writes down, for the first time, how
  a feature window is closed and how the operator's focus returns to the
  gardener afterwards (the Written-spec gate, Decision-090). Changed: the
  gardener now stamps a stable `@gardener_id` marker on its own tmux window
  at start-up, mirroring the `@landscaper_id` marker it already places on
  each feature window, so the teardown tool can reliably find the gardener's
  window to return focus to. And `tools/landscaper-teardown.sh` is now a
  self-contained window-kill and focus-return primitive: it locates the
  feature window and the gardener window by those stable markers, returns
  the operator's focus to the gardener, then closes the feature window and
  its sidebar. It no longer reads the retired `.return-window` marker file,
  accepts an optional tmux socket so the close worker can invoke it from
  outside the session, and refuses to run when a window cannot be resolved
  or when closing would target the focus-return window itself.
- 🚀 **Bus finishing — the orchard transport.** Finished the message-bus arc.
  The courier's broadcast fan-out — a courier telling every peer's inbox
  about every event, the measured token leak — is gone. Messaging now runs
  on a flat, user-wide runtime tree
  (`$XDG_RUNTIME_DIR/orchard/{projects/<repo>.<project>,topics/<name>}/`):
  directed `:session:<id>` messages (delete-on-read, request/reply,
  cross-repo via a manually-maintained allowlist) and topic posts carrying
  the sidebar's telemetry — agents post lifecycle, status, delegation and
  outcome events (and the gardener a task outcome), each event carrying the
  agent's identity and live status, never touching another agent's inbox and
  waking no agent. Message subjects are a closed 22-string corpus validated
  by exact membership — known or rejected, with variable data in the body.
  The fleet sidebar is one program again (`sidebar.py`) reading that tree,
  and staleness shows as colour (done green, failed red, not-heard-from
  gray) rather than rows appearing and vanishing. The transitional `bus.py`
  shim is retired; `courier.py` is the single script. Telemetry ≤120 minutes
  stays live; older messages archive to `~/.cache/orchard/archives/`. The
  per-repo sidebar hide/show (`/orchard`) is retired — the bar now shows
  every registered project.
- 🔊 The bus vocabulary is now specified: `agents/bus.md` carries WIRE GRAMMAR
  v1 — five wire classes (`orchid:status`, `orchid:update`, `orchid:phase`,
  `orchid:subagent:{queue,start,done}`, `orchid:interrupt:question`), each
  with a declared consumer and notify-user legality; exactly three derived
  operator interrupts (QUESTION ⇐ ask, SUCCEEDED ⇐ done/finished, FAILED ⇐
  abandoned/blocked+notify); status words denylisted against lifecycle terms;
  legacy `orchid:activity:*` retired to a one-release parse fallback.
- 🔊 The send audit: orchestrator, architect, groomer, and bloomer contracts
  rewritten off free-form activity broadcasts onto the wire grammar —
  change-only status words, log-targeted updates, phase-spine emissions,
  subagent markers, and operator questions exclusively via the queued
  `bus.py ask` broker. Sidecar-improvised wire text (the "awaiting operator
  (native prompt)" rebroadcasts from the operator's as-built audit) is
  banned; the ban is the interim send choke point pending the delivery-model
  redesign.
- ✨ `bus.py` enforces the grammar mechanically on send/broadcast: any
  `orchid:*` body parses against the five closed classes, malformed or
  unknown bodies are rejected naming the allowed classes, hand-composed
  interrupts are refused (ask is their only emitter), and `--notify-user` is
  restricted to questions and the notify-legal lifecycle states
  (done/blocked/abandoned). `bus.py ask` emits
  `orchid:interrupt:question:<subject>`; the question broker needed no
  change (it matches on `question_id`, never body text).
- 📡 The sidebar model consumes the vocabulary: status words (legacy
  `orchid:activity` as a one-release fallback), updates, the five-phase
  spine with a derived `progress_pct`, queued/running subagent counts, and
  open questions; a new `interrupt` field carries the only three
  operator-summoning states, and identical consecutive body+notify
  signatures are dropped — a repeated waiting broadcast can never summon
  twice.
- 🦺 `bus.py validate [PATH|stdin]` audits recorded traffic against the
  vocabulary — violations (unknown classes, illegal notify, notify-carrying
  free-prose broadcasts, the retired activity form) exit 1; undirected
  free-prose broadcasts surface as warnings for the send-path redesign.
  Role-traffic tests emulate one session per role through the real CLI and
  prove each contract's sequence yields zero violations.
- 🎨 The sidebar renders the approved display grammar: per-repo hue triples
  with deterministic fallback, feature names drawn over the progress fill
  with the lifted-band sweep as the frame's single animated element, the
  small-caps phase label, the NBSP-glued identity line on the model colour
  ramp, the five-phase checklist with inline subagent dots, dim-amber `?N`
  badges with why-lines, guide-line footers, and data-driven role-emoji /
  location-badge maps so the two pending emoji picks drop in without code
  changes.
- ⚡ Footer and identity data flow from zero-token deterministic sources
  only — the announce identity, the session transcript through the bus token
  estimators (which also backfills the model id the identity deliberately
  omits), and feature-branch commit timestamps for the age-vs-worked stat —
  behind a 30-second cache so a scan never spawns per-tick subprocesses.
  Done features close with the collapsed one-line footer.
- 🧪 An emulator frame check runs the real curses sidebar in a detached tmux
  pane against a fixture reproducing the approved frame and asserts the
  rendered glyphs, colours (through the renderer's own xterm256 mapping),
  fill percentage, checklist, dots, and question badge — the design
  contract's visual proof, executable in CI.
- 🪪 The cloud hops now speak as **`callabloom[bot]`** — a kaukea GitHub App (App ID 4354752)
  minted per hop from org secrets, replacing the anonymous `github-actions` actor; falls back to
  the built-in token when the secrets are absent (`cloud-path.yml` all hops + `board-sync.yml`).
- 🏷️ Session naming contract, enforced at launch: every `claude` spawn carries a
  `--name` — `orchids / <human name>` for feature sessions (architect, ripener) and
  the bare repository name `orchids` for the one-per-repo orchestrator (no slash-form,
  no `Orchestrator` suffix). The human name derives from the feature id by a pure
  `-`↔space swap, surfaced once as a `name` field on the bus identity so the sidebar
  reads one field. Forward-only: tmux `arch:<id>` machine titles and existing hooks
  are untouched (Decision-032).
- 🎭 Close choreography on the bus: the architect's finish rides a bus `finished`
  signal, not a transcript-grepping Stop hook. At its `ALL IT IS` countersign the
  architect signals `finished`; the orchestrator returns the operator's focus and
  runs the close off that signal — so the operator's `THAT IS ALL` is the single
  close gate (like merging a PR), with no separate "close it". The old
  `architect-close.sh` Stop hook is retired along with its `jq` transcript race
  and its cross-session `/tmp/architect-close.log` leak; the tmux teardown moves
  into `architect-teardown.sh`, which finds the architect pane by its `arch:<id>`
  title, reads no transcript, and writes nothing to `/tmp`. Bus `status` now
  carries `model` and `effort` beside the broken-out token counts, so a reader has
  the denominator; a dead architect is caught by a direct pane check when a close
  is expected, with no scheduler.

- 📮 Message bus: independent agent sessions in one repository can talk to each
  other. A `bus` sidecar owns the entire mechanism, so no other role learns the
  format, the paths, or the ordering rules; agents ask it in plain language.
  Membership is established by hooks rather than prompts (code does not drift,
  models do): `SessionStart` creates the inbox and asks the session to load its
  bus and announce itself, `SessionEnd` broadcasts a departure and removes the
  inbox so a later send fails immediately instead of vanishing. An agent's
  address is its session id; only top-level sessions are members. Identity is
  broadcast once, while status — context occupancy and token spend — is pulled
  on demand and answered by the sidecar off the parent's transcript, costing the
  parent no context and still answering while it is busy or wedged. There is no
  delivery guarantee by design: a sender expects no answer and decides for
  itself whether to retry, abandon, or error.

- 📋 Registry file set: README (the why/what) + ARCHITECTURE (the how) front
  door, the "install kauk/orchids" bootstrap contract
  (`Agent-installation.md`), and `docs/decisions.md` seeded with the
  history-rewrite charter.
- 🗃️ The works: transients (`HANDOVER.md`, `MOOD.md`) namespaced into
  `.git/the-works/`; dated, state-guarded `migrations/` catch any repo up in
  one pass (watermark + hook, the highest date IS the package version);
  cross-repo writes gated to package content surfaces; micro-tasks may ride
  `main` on an operator-accepted offer.
- 📓 Workstream logs: every session keeps its own small rolling record in
  `.git/the-works/<stream>/` — state, findings, dead ends, decisions pending
  promotion, pointers — so resets and agent swaps never lose the thread;
  `_closed` streams are promoted by the ingester (single-writer on the board
  and decisions) then archived to `_ingested/` (provisional retention).

- 📋 The board on GitHub: active tasks become labelled issues (`gh#` on the
  badge), the private user Project **Orchidarium** aggregates all repos'
  active work with Status/Urgency/Readiness/Component fields, and an
  actor-gated `board-sync` workflow ingests phone-born issues and couch
  closes into the file board — files stay canonical; the orchestrator pulls
  at boot and pushes after board writes.

- 🏷️ Skill roles: every skill declares its place in the role DAG via a `roles:`
  frontmatter list of slash-paths (Decision-003/005) — placements not
  completeness, `general` explicit, multi-parent expressible. The
  frontmatter-contract skill is renamed `doing-skills` → `authoring-skills` and
  documents the contract; kauk validates the declarations when it reads them.

- 🧭 **Fleet sidebar** — a pinned left pane now appears in every orchestrator and
  architect window, showing a live, cross-repository tree of work: each repository,
  the features under it, what each is doing right now, and any in-flight sub-agents,
  sourced entirely from the message bus. Rows carry a status emoji (running, standby,
  completed, failed), flash when an agent is waiting on the operator, and can be
  selected with the arrow keys and Enter to jump straight to that work's tmux window.
  Which repositories it aggregates is listed in `~/.config/orchids/sidebar-repos`
  (one path per line) or the `ORCHIDS_SIDEBAR_REPOS` environment variable; with
  neither, it shows the current repository.

- 🌳 Fleet roles renamed to orchard names; message bus renamed courier.
  Every agent role now wears an orchard name and glyph: orchestrator→gardener 🌳,
  architect→landscaper 🌿, builder→sower 🌱, housekeeper→groundskeeper 🧹,
  bus→courier 📮 (bloomer 🌸 unchanged). The message-bus transport was renamed
  wholesale to **courier** (`tools/courier.py`; a transitional `tools/bus.py`
  shim execs it for one release so live sessions are not cut off). The sidebar
  identity line now renders each role's glyph, with wide-char-aware column
  accounting. A dated migration converges consuming repos (drops dangling
  old-name laydowns, moves `the-works/bus`→`courier` with a compat symlink).
  No behaviour change; `orchid:`/`orchard:` namespaces untouched.

- 📋 **The orchard bus is written down.** `docs/orchard-bus.md` records the address
  forms, the closed subject list, the storage layout and the rules that follow from
  them, each claim tagged as operator-stated design, verified-in-code, or a known
  gap. The messaging design previously existed only as fragments across agent
  charters, decisions and code, so every session re-derived it and several built
  against the wrong half.
- 🔌 **Git-directory mailboxes are gone; the orchard transport is the only channel.**
  The per-agent mailbox under the shared git common directory could not coexist
  with worktrees — the directory is shared by all of them and a subagent inherits
  its parent's session id, so concurrent instances resolved to one mailbox and
  could delete each other's inbox.
- 🌳 **One orchard project directory per worktree**, keyed by branch as well as repo,
  so agents working different features no longer wake one another. The sidebar
  folds them back into a single row per repo.
- 📮 **A courier is woken only for its own mail, and the wake carries the message.**
  Filtering happens at the watch by path and after parsing by subject, and the
  parsed envelope is handed up rather than a filename to go and fetch.
- 🐛 **Fixed: the operator's close gate could not be delivered.** A courier's only
  standing watch was armed where `:session:` traffic never lands, so an unsolicited
  message woke nothing unless the courier already happened to be blocking on a
  reply.
- 🐛 **Fixed: `--operator-origin` was a silent no-op** on every directed send, so
  relayed operator words carried no provenance.
- 🐛 **Fixed: the session-end self-wake was silently failing**, breaking a courier's
  release detection.
- 🐛 **Fixed: a running monitor could consume a reply** another caller was blocked on,
  including the operator's own answer to a question.

### 🧹 Removals

- 🧹 Supervision kills are gone (Decision-081): the orchestrator no longer
  reaps dead architect windows nor kills agents that outlive a grace period,
  and the exit-grace contract built for that kill — `announce
  --exit-grace-seconds` and `signal --on-behalf-of` — is removed from
  `bus.py`, its tests, and every agent contract. Agents close themselves;
  whatever a dead agent leaves behind is reported to the operator instead of
  being cleaned up unilaterally. The housekeeper's worktree-and-branch
  removal is now the absolute last act of a close, after every other step
  including the sudo-grant revocation.

### 🐛 Bug fixes

- 🐛 Six fleet-sidebar defects fixed — above all, the sidebar now actually appears:
  its tools were never delivered into `.claude/tools/`, so every mount had been
  failing silently since the first build.

---

#### 🎉 `f/orchard-renaming` → `archive/orchard-renaming`

Every agent role now wears an orchard name and glyph: orchestrator→gardener 🌳,
architect→landscaper 🌿, builder→sower 🌱, housekeeper→groundskeeper 🧹,
bus→courier 📮 (bloomer 🌸 unchanged). The message-bus transport was renamed
wholesale to **courier** (`tools/courier.py`; a transitional `tools/bus.py` shim
execs it for one release so live sessions are not cut off). The sidebar identity
line now renders each role's glyph, with wide-char-aware column accounting. A
dated migration converges consuming repos (drops dangling old-name laydowns,
moves `the-works/bus`→`courier` with a compat symlink). No behaviour change;
`orchid:`/`orchard:` namespaces untouched. Location badges were deferred by
ruling (not an agent-type distinction); legacy `groomer` and the `-cloud`
variants were left untouched this pass.

_Board: `docs/TODO.md.d/orchard-renaming.md` · Decisions 085/086/087 ·
migration: `migrations/2026-07-25-orchard-role-rename.md`_

#### 🐛 `f/sidebar-fixes` → `archive/sidebar-fixes`

- The fleet sidebar now actually appears: it was never delivered into `.claude/tools/`, so
  every mount attempt failed silently and no sidebar showed. The four sidebar tools are now
  delivered like every other tool.
- Selecting a sidebar row no longer lands on a blank leftover window when two windows share
  a name — navigation prefers the live one.
- The "waiting on operator" flash no longer stops early when an unrelated message arrives,
  and no longer keeps flashing after a job has finished.
- A repo with no active orchestrator now shows a distinct idle marker instead of a green
  "running" dot.
- A feature row is labelled from the name the agent announced, not a second re-derivation
  that could drift from it.
- Re-mounting the sidebar no longer risks a second sidebar pane when the pane title has been
  changed by a status-glyph setter.

_Board: `docs/TODO.md.d/sidebar-fixes.md` · Decisions 048/052 · follow-up round:
`docs/TODO.md.d/sidebar-polish.md`_

#### 🧭 `worktree-fleet-sidebar` → `archive/fleet-sidebar`

The fleet sidebar (gh#23): a bus-driven, always-visible navigation pane. Agents
broadcast `orchid:activity:<text>` and `orchid:subagent:start|done:<label>` as
ordinary dynamic bus messages (no bus mechanism change, Decision-044); a stdlib
reader (`tools/sidebar_model.py`) aggregates every repolist repo's bus
(Decision-043), a curses renderer (`tools/sidebar.py`) draws the
repo→feature→activity→sub-agent tree with status emoji, flash and spinner, and
`tools/sidebar_nav.py` + `tools/sidebar-mount.sh` provide window navigation and
the idempotent pinned-pane mount. Also completes the tmux window-name half of
session-naming (Decision-045). Built via the native `--worktree` flags as an
experiment, hence the non-standard branch name; tested 22/22 unit + 2-repo/3-job
smoke, closed under operator waiver with corrective follow-up `sidebar-fixes`.

_Board: `docs/TODO.md.d/fleet-sidebar.md` · `docs/TODO.md.d/sidebar-fixes.md` ·
Decisions-043/044/045/046._

#### 🎉 `f/app-identifying` → `archive/app-identifying`

The cloud hops gain a named identity: the kaukea-owned **callabloom** GitHub App
(App ID 4354752), signing every comment, commit, push, PR and merge as
`callabloom[bot]` — never the operator, never the anonymous built-in actor. A
per-hop token mint (`actions/create-github-app-token@v3`, org secrets
`CALLABLOOM_APP_ID`/`CALLABLOOM_PRIVATE_KEY`) is wired into all four
`cloud-path.yml` hops and `board-sync.yml`, guarded so everything falls back to
`github.token` where the secrets are absent. Live-fired on gh#23: the plan hop
posted as `callabloom[bot]`. The original close-spine ruleset/bypass premise was
overturned during the build and dropped; branch protection respawns as its own
task.

_See `docs/TODO.md.d/app-identifying.md`, Decision-039, Decision-040._

#### 🏷️ `f/role-dag-frontmatter` → `archive/role-dag-frontmatter`

Every skill now declares its role placements in frontmatter: `roles:` is a list
of slash-separated full paths from the Decision-003 role DAG, each a deliberate
placement — a multi-parent skill may sit under a subset of its parents, `general`
is explicit, and a missing key is an error (never read as "deliberately
general"). The keystone `doing-skills` skill is renamed `authoring-skills`
(Decision-003, role `general`) and now documents the `roles:` contract,
referencing the vocabulary in `decisions.md` rather than restating it. All 26
skills are declared per the tree — `coding-tofu` and `reverse-engineering-files`
span two parents, `git-commit` spans `general` + `process/workflow`, and
`write-to-s3` takes its provisional `security/forensics`. The legacy
`manifest.conf` role is left in place until kauk reads frontmatter; enforcement
is deferred to a kauk `validate` stub, not an orchids lint.

_Board: [role-dag-frontmatter](docs/TODO.md.d/role-dag-frontmatter.md) ·
decisions: Decision-003, Decision-005._

#### 📋 `f/github-board-sync` → `archive/github-board-sync`

The fleet's cross-repo visibility pilot (orchids + kauk): `tools/board_gh.py`
projects the board to GitHub issues and Orchidarium Project rows and ingests
GitHub-born changes back; `.github/workflows/board-sync.yml` runs the
deterministic ingest on issue events (consumers carry only a thin reusable-
workflow shim); the orchestrator skill owns both directions. Known gaps and
the day-two scenarios live in the sidecar's 2026-07-19 test plan; repo
visibility fallout is ruled by Decision-013.

_Board: [github-board-sync](docs/TODO.md.d/github-board-sync.md) · decisions:
Decision-012, Decision-013._

#### 📓 `f/workstream-log` → `archive/workstream-log`

The monolithic `HANDOVER.md` becomes per-session rolling workstream logs in
`.git/the-works/<stream>/` (`handover` skill rewritten as the protocol): one
file per session, five fixed sections, read oldest→newest; `_closed` marker +
hook announcement; ingest = promote decisions/TODO (single-writer — children
never write main's docs) then archive the stream to `_ingested/`, kept
provisionally to evaluate the dead-ends record. A migration folds legacy flat
`HANDOVER*.md` into a closed `legacy` stream.

_See the board entry (`docs/TODO.md.d/workstream-log.md`) and Decision-011 in
`docs/decisions.md`._

#### 🗃️ `f/the-works-channel` → `archive/the-works-channel`

The uncommittable channel moves to `.git/the-works/` and every structural
change now ships a dated migration: `migrations/YYYY-MM-DD-<slug>.md`,
state-guarded and merge-safe, applied as one net-effect pass against the
per-clone `.git/the-works/migrated` watermark announced by a `settings.json`
hook (two entries backfill 2026-07-11 and 2026-07-18). Handover ingest drains
gathered batches oldest-first. The blanket `.ai/repositories/**` allow rules
narrow to `agents/`/`skills/`/`files/`, with the agent-behaviour norm that a
fix to another repo rides that repo's workflow. The workflow skill gains the
micro-task path (`Branch: main` sanctioned on exactly those commits).

_See the board entry (`docs/TODO.md.d/the-works-channel.md`) and
Decisions 008–010 in `docs/decisions.md`._

#### ✂️ `f/data-only-split` → `archive/data-only-split`

orchids becomes DATA-ONLY: the package manager (`bin/orchids`) moves to
`serialseb/kauk` as the stopgap CLI, and `skills/skill-sync` retires in
favour of the `kauk` skill shipped by the kauk package itself (pull-only).
`manifest.conf` v2 typed lines (`skill`/`link`/`template`/`prefix`) expose
every distributed group — agents, hooks, tools, settings, AGENTS files,
templates — the engine hardcodes no layout. `templates/CLAUDE.md` holds the
exact prefix block; the install page bootstraps kauk first. Retro-closed
2026-07-17: the tree had landed on main verbatim as `904a9a0` (manual
close); the empty squash, tombstone tag, and note were fitted afterwards,
dated to the actual event.

_See `docs/TODO.md.d/tool-split-to-kauk.md` (findings & testing) and kauk
Decisions 007–008 in `serialseb/kauk/docs/decisions.md`._

#### 🔗 `f/kauk-script-name` → `archive/kauk-script-name`

The install page stops pointing agents at the retired `kauk-sync` name:
kauk Decision-009 ships the stopgap as `bin/kauk`, brand = command. One
rename sweep over the served instructions. Retro-closed 2026-07-17: the
tree had landed on main verbatim as `4035d21` (manual close); the branch
gained its missing anchor at close (`Base: 9ae9cd5`, dates preserved,
tree byte-identical to old head `b0d380b`).

_See kauk Decision-009 in `serialseb/kauk/docs/decisions.md`._

#### 📋 `f/registry-file-set` → `archive/registry-file-set`

Gives orchids its own registry file set: `README.md` sells the operating
model (agents, skills, rules as one versioned package), `ARCHITECTURE.md`
holds the mechanics, and `docs/decisions.md` opens with Decision-001 —
history migration is an orchestrator charter, gated by the project
`AGENTS.md` `repository:` field. The bootstrap contract becomes
"install kauk/orchids": `install.txt` renamed to `Agent-installation.md`,
with `index.html` (still served until the operator deletes the owin.org
remnants) regenerated to match. Close note: the branch was rebuilt at close
to repair a fabricated `Base:` SHA in its anchor commit; all work commits
and dates carried over verbatim.

_See `docs/TODO.md.d/registry-file-set.md` (findings & rulings) and
Decision-001 in `docs/decisions.md`._

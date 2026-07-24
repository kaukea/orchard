- created: 2026-07-20
- created_by: Sebastien Lambla
- completed: 2026-07-21
- completed_during: f/session-naming (cloud path)

## Blockers

- None.

## Questions

- ~~Inventory first: WHICH naming bugs?~~ Inventory done (Findings): the surface is
  mostly UNBUILT, not buggy — the task reframed from "fix N bugs" to "define the
  contract, enforce it forward".
- ~~Naming contract: what is the canonical short name?~~ Answered — operator contract
  (2026-07-21), see Proposal.
- ~~Does scope cover building the SessionStart hook, the orch wrapper, and
  parent-chain titling?~~ Answered: NONE of them. `claude --name` at launch IS the
  mechanism; enforce the rule moving forward; no retroactive rewrites. Epics /
  parent-chain naming explicitly deferred ("we'll ignore epics for now").
- ~~Retitle on every state change or spawn-only?~~ Answered: ride the existing bus
  lifecycle signals — no new hooks; anything else reads state off the bus.

## Findings

- Operator (2026-07-20): session/feature naming is buggy today, and short, descriptive,
  always-visible names are the PREREQUISITE for the whole Orchard UX — the sidebar
  ([[fleet-sidebar]]) is unusable without them. Typing/selecting a repository name must
  reliably reach that repo's orchestrator window.
- Inventory (confidence: high — read-only discovery, main checkout only): of the four
  naming paths described in the orchestrator docs, only the spawn-time
  `tmux select-pane -T "arch:<id>"` is real code. The SessionStart identity/titling
  hook, the `bin/orch` wrapper, the `.pending-subjob.local` consumer, and
  parent-chain worktree titling are documented intentions with no implementing script.
  Most of the surface isn't buggy — it's unbuilt.
- Operator amendment (2026-07-21, plan round): the plan's call-out read the root as
  `orchids / orchestrator` — wrong way round. The slash-form names workstreams; the
  orchestrator, singular per repository, is named by the repository itself.
- Operator scope ruling (2026-07-21): no hook build-out, no wrapper, no rewrites of
  what exists — `claude --name` at launch carries the session name; enforcement is
  forward-only at launch sites. Live state for consumers (sidebar included) comes from
  the BUS: any process — even a bash script — can register by creating an inbox folder
  and reading broadcasts.
- Operator (2026-07-21): the two-part name separator becomes `▸` (U+25B8, black
  right-pointing small triangle), replacing the original `/` — amended before the
  contract's first live application. Launch sites and this sidecar's spec, plan,
  and result text updated in place; the dated plan-round finding above keeps its
  original slash wording as history.
- Reverted (2026-07-24, fleet-sidebar one-go pass, Decision-075): the separator goes
  back to `/` (U+002F) — the sidebar renderer composes its navigation target as
  `<repo>/<feature name>` and navigates by window name, so the window name MUST use
  `/` to stay selectable. Every launch site that names an architect/workstream
  window or session is updated from `<repo> ▸ <name>` to `<repo>/<name>`; the
  `▸`-era Proposal/Tech-plan/Result text below is updated in place to match, per
  this file's own convention of keeping only the DATED historical findings above in
  their original wording. Same pass: every pane that sets a title with
  `select-pane -T` also gets `allow-rename off` alongside `automatic-rename off` on
  its window, so `claude`/`bash` cannot clobber the pinned title (architect
  `arch:<id>`, bloomer `bloom:<id>`, sidebar-mount `orchid-sidebar`, peek
  `peek:<name>`, and the orchestrator's own summoned window). The orchestrator
  session stays named 1:1 after its repository (Decision-032, unchanged, reconfirmed
  here) — this pass only pins its window title, it does not touch session naming.

## Proposal

The naming contract — strict, fully derivable, enforced at every launch site from now
on:

- **feature id**: kebab-case, all lowercase, DECLARATIVE in style — it names what
  the workstream IS, never commands what to do. Git speaks imperative ("Eat
  carrots" — an order to the codebase); a feature name declares the thing or the
  activity ("eating carrots", "session naming", "fleet sidebar" — noun phrases).
  This is a difference of MOOD, not word order: there is NO string transform from a
  commit subject to a name — the id is authored by asking "what is this work?",
  which is why it resembles part of the sidecar short title. The sidebar is the
  test: `orchids/<name>` must read as something that is happening, never as a
  barked order. The style call is enforced at AUTHORING time — intake and the
  ripener check it; no lint can judge mood. Unique on the board; the sidecar
  filename. Forward-only — existing ids stay.
- **human name**: the feature id with hyphens as spaces ("eating carrots") — this
  swap is the ONLY mechanical rule in the contract; derived, never authored
  separately, so it cannot drift.
- **claude session name**: for WORKSTREAM sessions (architects, ripeners),
  `<repository>/<human name>` (e.g. `orchids/session naming`), passed with
  `--name` at every `claude` launch — this is what makes the claude UI navigable,
  and matches the sidebar's own navigation target so window selection works.
- **the orchestrator is NOT the two-part form**: session names name SESSIONS, and there is
  exactly ONE orchestrator per repository — it orchestrates the workstreams. Its
  session name is the repository name alone (`orchids`); summoning or reviving it
  resumes THE one (never a second), and typing the repo name reaches its orchestrator
  (Decision-032).
- **one session per feature — the name never carries the agent**: the feature has ONE
  top-level session, shared context for all its work; everything else in it (builders,
  prep, sidecars) is a SUBAGENT — hidden away, never a named session, visible only in
  the sidebar thanks to the bus (activity broadcasts show them by name as they come
  and go). Which agent is doing what is live state, never name material. Two name
  shapes exist, total: `<repo>` (the orchestrator) and `<repo>/<human name>` (a
  feature workstream, e.g. `orchids/eating carrots`), all lowercase. Nothing else.
- **agent names appear NOWHERE** (operator + orchestrator concur, 2026-07-21): the
  hierarchy carries the role (the repo row IS the orchestrator; a feature session IS
  its one agent — a session can only have one agent), phase/activity words carry the
  state, and subagent rows carry their WORK label (the "messaging" pattern), never a
  role noun.
- **sidebar row**: the human name alone ([[fleet-sidebar]]).
- **tmux**: existing machine titles (`arch:<id>`) stay — tooling matches on them
  (teardown); titles refresh only where bus lifecycle signals already fire; no new
  hooks. Epics / parent chains deferred. Every launch site that sets a pane title
  (`select-pane -T`) also pins it — `automatic-rename off` AND `allow-rename off` on
  that pane's window — so `claude`/`bash` cannot clobber it live via terminal escape
  sequences; a pane no longer flickers between the pinned title, nothing, and `bash`.
  The orchestrator session itself is named 1:1 after its repository (Decision-032) —
  this pinning is about the pane TITLE, it does not change session naming.

Enforcement is forward-only: launch sites (orchestrator architect spawn, cloud path,
future spawns) adopt `--name`; nothing is retro-renamed.

## Tech plan

The HOW behind the frozen Proposal (Decision-025 — WHAT stays in Proposal, files are
not pre-decided here). orchids is a data package: "launch sites" are the spawn
instructions in the agent/skill docs plus the one bus helper in `tools/`.

**One derivation, quoted everywhere.** id↔human is a pure string swap: human =
`id` with `-`→` `, id = human with ` `→`-`. It round-trips because board ids are
kebab (no spaces) and human names are only ever derived, never authored. The swap is
order-agnostic — the gerund-first rule governs how a NEW id is authored, not the code.
bash sites inline `${id//-/ }`; Python surfaces it once in the bus.

**Launch sites that adopt `--name "<repo>/<human name>"` (forward-only, no retro
renames):**

- Local architect spawn — `agents/orchestrator.md` `tmux split-window … claude
  --agent architect`: add `--name "orchids/${id//-/ }"`.
- Orchestrator root session — `skills/orchestrator/SKILL.md` summon line
  `claude --resume … || claude --name …`: the pair moves from `<project>
  Orchestrator` to the **bare repository name** `<project>` (resume key and name must
  stay identical, so the same session is found/created). NOT the two-part form and NOT an
  `orchestrator` suffix — there is one orchestrator per repository, so its session
  name *is* the repository (operator amendment 2026-07-21, Decision-032).
- Ripener spawn — `skills/ripen-tasks/SKILL.md` `claude --bg --agent ripener`:
  adopt the same `--name` (feature-tied launch). Noted: the frozen Testing method
  only exercises orchestrator + architect.
- Cloud path — the `claude -p --agent architect-cloud` / orchestrator-cloud launches
  live on the unlanded `f/cloud-architect` branch, not here; the `--name` requirement
  travels with them (forward note, no edit on this branch).

**Role-noun references reconciled (naming round froze after the build; REVISE hop).**
The contract's "agent names appear NOWHERE / one orchestrator per repo" retires the
orchestrator's old `<project> Orchestrator` name at every remaining reference, not just
the summon line:

- `skills/workflow-complete/SKILL.md` close-return reminder — resumed the orchestrator
  by `"<project> Orchestrator"`; now the bare `"<project>"` (a resume is a launch site;
  the old string would send the operator to a non-existent second session).
- `skills/orchestrator/SKILL.md` `/branch` mistitle note — described the `SessionStart`
  hook titling a fork `<project> Orchestrator`; corrected to the orchestrator's own bare
  name `<project>` (doc consistency only; the hook itself stays unbuilt per scope).

**Subagents: hidden sessions, bus-visible rows.** Subagents (builder, housekeeper via
the Agent tool / `--bg`) inherit the parent's bus identity and are never named sessions
— but they ARE sidebar-visible through the bus's existing on-change activity broadcast
(`announce` on start, `depart` on end, `signal` on lifecycle change). This is the
pinned activity-broadcast requirement, satisfied by the existing bus mechanism — no new
hook (operator scope ruling). tmux machine titles `arch:<id>` stay verbatim (teardown
matches on them).

**Bus surfaces the name.** `tools/bus.py` `identity_of()` gains a derived `name`
(human name from `feature_id`), so the sidebar and any bash consumer read one field
instead of re-deriving. Identity already carries `feature_id`/`worktree`; `name` joins
them as a birth-record field (model/effort stay out — Decision-028).

**Testing, made runnable in the headless cloud runner** (refines the frozen method,
which assumes a live tmux UI the runner has not got):

- automated in the runner — a check script asserts (a) id→human→id round-trips for
  every `docs/TODO.md.d/*.md` id; (b) `bus.py identity` emits the derived `name` for a
  set `feature_id`; (c) each edited launch line carries `--name "<repo>/…"`; (d) the
  `select-pane -T "arch:<id>"` line is unchanged.
- operator-manual — the actual "claude UI lists `<repo>/<human name>`" visual check
  needs a real interactive spawn the headless runner cannot inspect; left for the
  operator (or a local run) and called out as such, not self-approved.

## Testing

Spawn an orchestrator and an architect: the claude UI lists
`<repo>/<human name>` for each; the id→human-name derivation round-trips for every
board id; the bus identity carries the same name; `tmux list-panes` still matches the
teardown's `arch:<id>` lookup.

## Result

Result: BUILT (91a2a38) + REVISED against the frozen naming contract — branch
`f/session-naming`, awaiting operator review. Four launch sites enforce the contract
forward-only; the REVISE hop reconciled the branch to the naming round that froze
after the build (gerund-first ids, agent names nowhere, subagents hidden but
bus-visible, on-change activity broadcast).

Launch sites (build):

- `agents/orchestrator.md` — architect spawn gains `--name "orchids/${id//-/ }"`
  (an `id=<id>` capture added so the human name derives in-shell); the
  `select-pane -T "arch:<id>"` teardown line is byte-for-byte unchanged. (Separator
  updated 2026-07-24 from the `▸` this Result originally recorded — see the dated
  Finding above.)
- `skills/orchestrator/SKILL.md` — root summon becomes the **bare** repo name
  `claude --resume "<project>" || claude --name "<project>"` (Decision-032: one
  orchestrator per repo, name = repo; no two-part form, no `Orchestrator` suffix).
- `skills/ripen-tasks/SKILL.md` — ripener `--bg` launch gains
  `--name "orchids/${id//-/ }"` (feature human name, never the role; separator
  updated 2026-07-24, see the dated Finding above).
- `tools/bus.py` `identity_of()` — gains a derived `name` (`feature_id` with
  `-`→space), so the sidebar / any bash consumer reads one field.

Reconciled in the REVISE hop (role-noun sites the build missed):

- `skills/workflow-complete/SKILL.md` — the close-return reminder resumed the
  orchestrator by `"<project> Orchestrator"`; now the bare `"<project>"` (Decision-032).
- `skills/orchestrator/SKILL.md` — the `/branch` mistitle note said the hook would
  title a fork `<project> Orchestrator`; corrected to the orchestrator's own bare
  name `<project>`.
- Subagent visibility clarified: subagents stay unnamed sessions but ARE sidebar-
  visible via the bus's existing on-change activity broadcast (`announce`/`depart`/
  `signal`) — the pinned requirement is satisfied by the existing bus mechanism, no
  new hook (operator scope ruling).

Automated test gate (headless-runner method), all assertions green:
(a) board ids round-trip id→human→id; (b) `bus.py identity` emits the derived `name`;
(c) each edited launch line carries `--name`; (d) the `arch:<id>` line is unchanged.

Deferred / not self-approved: the operator-manual visual check (the claude UI actually
lists `<repo> ▸ <human name>`) needs a live interactive spawn the headless runner
cannot inspect. Out of scope per operator ruling: SessionStart hook / `.pending-subjob`
titling build-out, epics / parent chains, retro renames.

# The sidebar — display specification

Status: **CONSOLIDATED, 2026-07-29.** The operator specified this surface "to DEATH"
across five scattered files; rounds kept re-asking him for what was already written.
This document GATHERS those rulings into one place — it does not restate, soften, or
re-derive them. Every section names its source. Anything that is an agent's reading
rather than the operator's word is marked as a reading. Sources:

- `docs/TODO.md.d/sidebar-teamwork.md` (the dense record: tree, colour chain, citation,
  A–D build spec, operator-request ledger)
- `docs/TODO.md.d/sidebar-empty-rows.md` (Decisions 101, 105, 107 context)
- `docs/TODO.md.d/sidebar-titling.md` (titling)
- `docs/TODO.md.d/features-first-class.md` (feature level, naming, marker)
- `docs/TODO.md.d/bus-message-specifying.md` (metrics block, spans, footer)
- `docs/TODO.md.d/observability.md` (feature-level rulings 2026-07-29)
- Plan-gate rulings of 2026-07-29 (this branch), marked with their date.

**Scope guard (operator, 2026-07-29, mid-build):** anything present only in existing
code because an agent once decided it — fallback emojis named as the example — with
no ruling or specification behind it, is OUT OF SCOPE unless he says so. Code is not
spec.

The wire the sidebar reads is `docs/courier-wire.md`. The sidebar is an independent
application with **no AI in it**, showing every project, feature, task, subtask and
metric in one pane, in real time, so the operator can manage multiple features and
multiple projects at the same time. [observability.md]

---

## 1. The tree — assembled from EVENT CONTENT, never folded on session id

[sidebar-teamwork.md §"The tree, as ruled by the operator 2026-07-27"]

- **project** — the repository; `<owner>.<repo>` and its `@<branch>` worktree variants
  are ONE project. Several run at once; stacked project headers share the pane.
- **feature** — exists in METADATA ONLY; never a session, never an agent, never derived
  from either. The feature level is real even while unpopulated; a feature with one
  identically-named task must degrade gracefully (see §6, single-task row).
- **task** — from event content. A feature holds a LIST of open tasks.
- **the five stages** — ideation, scoping, designing, building, releasing. They belong
  to the TASK (Decision-105); the active one is computed CLIENT-SIDE from the agent's
  ROLE (Decision-107 — the role→stage map lives in each agent charter's frontmatter).
  Nothing on the wire names a stage. Progress spans, as drafted and agreed:
  10/15/15/45/15 → 100% [bus-message-specifying.md:209].
- **agent** — identified by the TRIPLE (session id, parent, agent name); a subagent
  inherits its parent's session id, so session id alone can never distinguish them
  [courier-wire.md §4]. A stage holds a LIST of agents.
- **the activity line** — a POSITION inside the stage, not an entity: whichever agent
  runs there now, in one or two words, with its name and model; the next agent writes
  into the same place. An agent with no status says it is doing nothing rather than
  rendering empty quotes.
- **subagents** — from delegation events. They never speak: scheduled, running, done is
  the whole of what they report (Decision-109). No session, no identity, no model.
- **The courier is NOT an agent** — transport never earns a row; its posts are its
  parent's data.

Row existence: a session earns a row the first time an identity is seen for it,
whatever its role (Decision-101); the `operator` mailbox never becomes a row.
Staleness is a COLOUR, never a removal (Decision-094).

## 2. The durable record — marker as cache

The marker is the durable record of the TASK: one file per (project, feature),
carrying the tasks under that feature with their states (Decision-099). **The marker
is a cache of what happened before; everything else is realtime reading** — live
events always override it; it supplies what remains when nothing is happening, so a
finished task survives going quiet and a feature rehydrates [sidebar-teamwork.md,
operator 2026-07-27/28]. The marker is NOT transport and its format belongs to the
renderer's side of the seam.

## 3. The metrics — RULED, all four

[observability.md, operator 2026-07-29] **time · tokens in and out · context
remaining · model and effort.**

- **$ cost / tokens**: "tokens and dollars in one line — tokens tick live, dollars
  translate them"; token usage per feature animates/ticks upward live as work
  happens, as the block's LAST section [bus-message-specifying.md:268,283-284].
- **floor time vs active time**: the feature's lifetime/age displayed against the time
  actually WORKED on it (the git-commit-flavoured stat) [bus-message-specifying.md:269].
- **FOOTER grammar**: `age⏱ vs worked + tokens⚡/dollars` [bus-message-specifying.md:288].
- **running time of a task**: shown per task (restated at the 2026-07-29 plan gate:
  the single-task row shows its metrics, "especially the running time of the task
  like the others").
- **Calculations are performed by deterministic script code** — accurate, and never
  through an agent's context (operator, 2026-07-28: "I see only one way of doing
  that and that's a script"). Elapsed aggregates derive from event timestamps.
- Telemetry rides every post, attached by the script at zero token cost
  [courier-wire.md §2b]; what the wire does not yet carry is tagged [GAP] there.

## 4. Colour

- **Dracula is the palette**; a theme-switch mechanism comes later; a "night" variant
  is deferred and is NOT "just dimmer" (on OLED, darker base + saturated accents emits
  MORE light) [sidebar-teamwork.md §Palette].
- **The ordered chain** (operator, 2026-07-28, verbatim-derived): PRIMARY = the header
  core behind the title; SECONDARY = where the header ramp lands AND the feature row's
  background; THIRD derives from SECONDARY = task line background + the indent's
  foreground; FOURTH derives from THIRD = the indent's background + every step row's
  background; FIFTH = the stage/attribution line. Each link derives from the one
  before — never five independent lookups. PRIMARY/SECONDARY are named per-repo colour
  ROLES, reused later for ownership tracking; the header consumes them.
- **Adjacency latitude** (operator): a link need not stay in one tone family — a task
  may take a compatible colour from another part of the palette, "not disconnected but
  an adjacent colour tone"; that is where contrast headroom comes from. Per-TASK vs
  per-FEATURE adjacency is a live A/B, selectable at runtime.
- **Floors**: text 4.5, marks 3.0, measured off the bytes the terminal receives; use
  APCA from `tools/colour-probe.py`, not the WCAG ratio, which flatters dark
  backgrounds. A ruled derivation that cannot meet a floor is reported with the
  measurement, never silently re-brightened.
- Colour carries IDENTITY only — deterministic from identity, stable across repaints,
  no ramp implying sequence or progress. The activity line is differentiated by HUE
  (a distinct accent), not by style, and is not italicised.

## 5. Header and feature rows

[sidebar-teamwork.md, requests 9/11; plan-gate 2026-07-29]

- The header is a FULL-WIDTH band whose ends taper: ramp cells reach both pane edges;
  the PRIMARY core fills everything between and widens with the pane. Direction: core
  = repo PRIMARY at full strength behind the title; three cells each side TAME it
  outward to SECONDARY ("we don't highlight, we tame with the gradient"). Block
  glyphs give eighth resolution (▏▎▍▌▋▊▉█); the right-hand mirror swaps fg/bg on a
  left block. The gradient FOLDS ON THE LEFT — the row reads as folding in from the
  screen edge. More steps than three in the ramp run; the variant switch survives
  with three cells as default. No room for the gradient = no gradient; the title is
  never shortened to protect it.
- The gradient treatment applies to the project header AND every feature row; feature
  rows share the project's background, differing only in font colour.
- The project header's text is THE MOST emphasized text in the sidebar.
- Feature row renders `🧩/<name>` (U+1F9E9, East-Asian-Wide, two cells, no variation
  selector). Name from `identity.feature_name` when present, else the middle segment
  of `f/<feature>/<task>` (features-first-class naming: the feature is the task's
  prefix), else nothing invented. Titling: `<repo>/<name>` renders repo thin/faint,
  name bright — the name dominates; truncation keeps the name side and adds an
  ellipsis; project headers carry the gradient and the repo name alone
  [sidebar-titling.md:22-23,71-72].

## 6. Step, task, identity and subagent rows

- The left indent is exactly ONE column — a left quarter/half block, foreground THIRD
  on background FOURTH; the glyph itself draws the boundary. The GUTTER carries the
  FEATURE's colour and spans the whole feature, unbroken across its tasks (an
  explicit operator reversal of the earlier task-colour instruction).
- Every row paints its OWN background; no row inherits what was drawn above it.
- The spinner ANIMATES (`SPINNER_FRAMES`, 125ms tick already reaches the draw path).
- **Ruled 2026-07-29:** the ACTIVE stage row — and only it — gets a distinct
  background of its own; the other four stay on the shared band.
- Bubble glyphs belong to SUBAGENTS ALONE: empty = scheduled · blinking = running ·
  full = closed. Feature and task rows carry no bubble.
- The task row's status marker is Decision-058's six static states (working /
  waiting / idle / awaiting-another-agent / done / failed; done and failed never
  share a glyph; idle distinct from awaiting).
- **Ruled 2026-07-29:** a feature's ONLY task, where the name would duplicate the
  feature's, renders labeled literally **"Task"** and shows its METRICS — especially
  its running time, like the other rows.
- The agent identity subscript sits BENEATH its task (Decision-098), never injected
  between step rows.

## 7. The citation

[sidebar-teamwork.md request 11, punctuation pinned 2026-07-28]

- Rare one-liner (space permitting): `"It's all relative" — Albert Einstein · Opus
  14.2` — em dash before the agent (attribution), middle dot before the model
  (detail), model = full name minus "Claude", with version.
- NORMAL layout: the citation sits on its OWN LINE below the text, NO dash — the line
  break does the attribution — right-aligned or indented a few blanks (both built,
  A/B open).
- Degradation, in order: abbreviate the model → drop the model (never leaving a
  dangling middle dot) → the ordinary ellipsis rule. The lower rungs are what is on
  screen essentially always at a ~30-column pane; they read well FIRST.

## 8. Acceptance

- Judged on the OPERATOR'S SCREEN, on a surface verified to run the branch under
  judgment (Decision-112) — never by unit tests alone.
- End to end: an agent emits and the sidebar shows it, across **at least two projects
  and two features live at once** [observability.md §Testing].
- The seam test drives the real courier under a fake project ("your producer won't
  know the difference") paired, per Decision-103, with a static-fixture companion
  validated by hand.
- Width is variable: invariants hold across a SWEEP of widths plus the resize path;
  no width is privileged.

## 9. Live A/B choices, settled on the pane (not by an agent)

- Header ramp variant (cells/steps) — variant switch in place, one pane per variant.
- Citation alignment: right-aligned vs indented.
- Hue adjacency: per-task vs per-feature.

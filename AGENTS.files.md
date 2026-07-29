# File format definitions

Canonical formats for the shared MD artifacts catalogued in `AGENTS.shared.md` → File
registry. Shared across all projects. Loaded on demand — when authoring one of these
files, or at workflow close via the Close gate. Do NOT invent a format from memory;
read the relevant section here first.

---

## §TODO — task tracking

The board is a **single slim-index file**, `docs/TODO.md` (the former per-component
`TODO.<component>.md` files are collapsed into it). It carries only the machine payload its
two readers need — the deterministic staleness walk and the gardener's board-walk —
while every task's prose lives in its **sidecar** (`docs/TODO.md.d/<id>.md`, §Sidecar). New
items surfaced in any conversation — follow-ups, parked thoughts, future ideas, side-quests —
are added here when they surface, not held in memory and not deferred.

### Board format (slim index)

Tasks are **functionality-grouped nested bullets**. The `## <functionality>` heading is the
group; list nesting is the parent → child hierarchy:

```markdown
## <functionality>

- `type · status · urgency · readiness · area · gh#<n>` [Short title](TODO.md.d/<id>.md) ⊘<blocked-id> ~<related-id>
  - `type · status · urgency · readiness · area · gh#<n>` [Child title](TODO.md.d/<child-id>.md)
```

**The badge** — the leading code-span is the whole machine payload: six `·`-separated fields,
parsed `badge.split('·').map(s => s.trim())`.

| field | values |
|---|---|
| `type` | bug · feature · refactor · housekeeping · completion |
| `status` | *(outcome lifecycle)* todo · functional · done · cancelled |
| `urgency` | *(empty = normal)* critical · nice-to-have · idea |
| `readiness` | `<stage>` or `<stage>/<origin>` (see below) |
| `area` | an area from the ARCHITECTURE.md Taxonomy (leaf tasks only) |
| `gh#<n>` | GitHub-mirror issue number; empty until the mirror binds it |

**The title link** — `[Short title](TODO.md.d/<id>.md)` does triple duty: the text is the
human-readable **short title** (refactored short + explanatory), and the URL carries both the
**id** (= file basename) and the **sidecar path** the staleness walk dates. The id is never
shown as a bare slug.

**Edges** — `⊘<id>` = a `blocked_by` edge, `~<id>` = a `related` edge (both kind-marked,
repeatable), trailing the title. **Parent ↔ child is the list nesting**, never a token.

**Tags** — `#<tag>` tokens trailing the line like edges. The tag vocabulary (one
source; projected to GitHub as emoji labels by `board_gh.py`, Decision-035):

| tag | label | meaning | set by |
|---|---|---|---|
| `#madmax` | ⛽🤘 madmax | runs UNRESTRICTED — every `claude` launch for the feature appends `--dangerously-skip-permissions` (Decision-031; git-provenance enforced) | operator ONLY |
| `#cloud` | ☁️ cloud | reporting: it WAS built in the cloud | the cloud flow |
| `#analyzable` | 🛰️ analyzable | CAN go to the cloud | triage |
| `#house-bound` | 🛋️ house-bound | local-only from inception | triage |

**Provenance** (`created`, `created_by`, `created_during`, `completed`, `completed_during`)
lives in the **sidecar metadata header** (§Sidecar), not on the board.

### `status` — outcome lifecycle

- `todo` — not started.
- `functional` — works in current state, unfinished against full intent (e.g. waiting on
  other components, needs a `completion` follow-up).
- `done` — meets its original spec; no longer needs revisiting.
- `cancelled` — decided against. Strike the title text `~~…~~`, add a `### Why cancelled`
  section in the sidecar, set `completed`/`completed_during`; the entry stays as history.

`doing` / `blocked` / `paused` are **retired**: "being worked" and "blocked on answers" are
now **stages** (readiness), and a deliberately deferred task is just an unbloomed `queued`.

### `readiness = stage × origin`

Two orthogonal attributes, rendered `<stage>` or `<stage>/<origin>`:

- **stage** (blooming pipeline position): `queued` · `working` · `blocked-on-answers` ·
  `plan-ready` · `complete`. `blocked-on-answers` is **derived** from the sidecar
  `## Questions` having open items — the single writer projects it onto the badge at park
  time, so render and the walk never open a sidecar (projection rule).
- **origin** (how it passed the pre-build gate): `interactive` (human MAKE IT SO) ·
  `autonomous` (agent self-authorized under strict boundaries: simple · no conflicts · no
  unknowns · questions answered). Absent until the task passes that gate — a `queued`/
  `working` task shows just its stage.

### `type` — corrective vs additive

- `bug` — **corrective**: makes our own code meet its spec. May be implemented by *adding*
  code (e.g. a missing guard) and is still a `bug`.
- `feature` — **additive**: new capability the code did not have.
- `refactor` — restructure without behaviour change.
- `housekeeping` — cleanup, removal, doc tidy.
- `completion` — work that takes a `functional` feature to `done`.

**Classification follows intent, not the shape of the diff.** A regression our own change
introduces — including breaking a previously-working third-party system we now configure — is
our `bug` to fix, even when the symptom surfaces outside our code.

### Hierarchy & the glossary

- **`parent` is the sole hierarchy field**, rendered as list nesting. The old `subtasks`
  forward field and its checkbox mirroring are **retired**. `blocked_by` / `related` are edges.
- A **leaf** task (no children) MUST carry exactly one `area`; a **spanning parent**
  carries none and rolls up readiness/urgency from its children. `functionality` = the heading.
- `functionality` and `area` draw their controlled vocabulary from the ARCHITECTURE.md
  **Taxonomy** — agents do not invent values.

### Lints

- **value ∈ glossary** — every `functionality` / `area` is in the Taxonomy table.
- **leaf-has-area** — a childless task carries exactly one area; a parent carries
  none (leaf-without-area = error; parent-with-area = error).
- **no-orphan-subtasks** — no `subtasks:` field survives; every `parent` / `⊘blocked_by` /
  `~related` id resolves to a real board entry.
- **badge well-formed** — six `·`-separated fields; `type` / `status` in enum; `readiness`
  stage in enum.

---

## §Sidecar — per-feature design-spec contract

A **sidecar** is the durable contract and working record for ONE task, at
`docs/TODO.md.d/<task-id>.md` (one file per bloomed/active task; `<task-id>` matches the
TODO `{#id}`). It is the single hand-off medium between roles (gardener → landscaper →
sower → groundskeeper); transient chatter travels separately via the uncommittable
`.git/` handover (`handover` skill), never here. The TODO
entry carries only the projected stage; the sidecar is the source of truth.

**Sidecars are committed — keep them sanitized:** technical state only; no
conversation quotes, no personal information, no secrets (those belong only in the
uncommittable `.git/` channels).

**Metadata header** — a bullet block at the very top of the sidecar (before `## Blockers`)
carries the task's provenance, which the slim board badge deliberately omits:

```markdown
- created: <YYYY-MM-DD>
- created_by: <operator name OR model-version slug (e.g. opus-4.8) OR `unknown`>
- created_during: <workstream feature-id, e.g. f/foo>   # omit if surfaced outside a workstream
- completed: <YYYY-MM-DD>                                 # required iff status ∈ {done, cancelled}
- completed_during: <workstream feature-id>               # required iff status ∈ {done, cancelled}
```

The `id` is the file basename; `type`, `status`, `urgency`, `readiness`, `area`, `gh#`
live on the board badge (§TODO) — the sidecar never restates them (single source). Omit any
header field with no value.

**Five fixed sections, in this order** (symmetric around `Findings`):

1. `## Blockers` — entry gate: what stops the task starting (open dependencies, missing
   capability, hardware/access limits). Read first to early-bail. Strike a resolved
   blocker (`~~…~~`) with a one-line resolution rather than deleting it.
2. `## Questions` — the unknowns needing the operator; answering one moves the task
   forward. A recommendation may accompany each.
3. `## Findings` — established facts the work resolved (the pivot): verified results,
   dead-ends not to repeat, measurements. Durable — where former "handover chatter" with
   lasting value now lands.
4. `## Proposal` — the WHAT: feature definition, scope, constraints — complete enough
   that the landscaper never needs a scope answer mid-build. The HOW (technical design)
   is NOT handoff content: the landscaper authors it in its plan phase and records the
   agreed plan here once frozen (Decision-025).
5. `## Testing` — exit gate: the pre-agreed test method, set up front (satisfying the
   mandatory Testing gate before the close, not at it).

`Blockers ↔ Testing` mirror the workflow entry/exit gates; `Questions ↔ Proposal` are
ask ↔ answer.

**Staged repo-level docs (Decision-034)** — at close, the sidecar result additionally
carries a `## Changelog entry` block (the outcome verbatim, in the author's words) and,
for user-facing changes, a `## Readme delta` block. The feature's agent never edits
`CHANGELOG.md`/`README.md`; the gardener promotes these blocks intact at ingest.

**Stage projection** — the task's `readiness = stage × origin` (stage ∈ `queued` /
`working` / `blocked-on-answers` / `plan-ready` / `complete`; §TODO) is *projected* onto the
board badge from the sidecar, so board render and triage never open sidecars in steady state.
In particular `blocked-on-answers` is projected from this sidecar's `## Questions` carrying
open items. The sidecar is the single writer of its own stage.

**Single writer** — exactly one role holds and writes a sidecar at a time (the
gardener/blooming role while parked, the landscaper while active). A hand-off is a
stage transition, not a copy.

---

## §Decisions — architectural & spec decisions

All decisions live in ONE append-only file, `docs/decisions.md`, chronological (oldest
top). No per-component split — a decision often spans systems (e.g. `#ssh`,
`#tailscale`) and component boundaries move; one file keeps every decision findable.

**Not read at session start — grepped by keyword.** Before relying on or recording a
decision on a topic, search it: `grep -ni '#ssh' docs/decisions.md`. The file may grow
without bound; size never costs tokens because it is never read whole.

**A decision is a RULING, never a state.** Record only a deliberate choice among
alternatives, or a constraint adopted — something a future reader must honour. A
temporary condition, an interim limitation, or a mere fact about what the code currently
does (e.g. "the desktop appears immediately", "nftables isn't installed yet") is NOT a
decision and MUST NOT be recorded as one — it will later be mis-read as a ruling and
acted on. Such transient/factual states belong in `CHANGELOG.md`, a code comment, or a
`TODO`, never in `decisions.md`. If a decision's body must mention current state for
context, mark it as context, not as the ruling.

**Heading format** — timestamp first, then number, then title:

    ## [YYYY-MM-DD HH:MM TZ] Decision-NNN: <Title>

Date is ISO. Time is the local wall-clock and is REQUIRED — it disambiguates same-day
decisions and feeds the staleness rule (`workflow` skill): an old decision is
PROVISIONAL, re-confirmed with the operator rather than assumed current. `TZ` is the
zone abbreviation that matches the recording commit's own UTC offset (e.g. `CEST`,
`BST`) — never a hardcoded label, or agents read the clock wrong. Number is 3-digit,
assigned in chronological order. Supersession strikes the whole heading.

**Keywords are MANDATORY on write.** Directly under the heading, a hashtag line of the
topic terms the decision touches. At least one is required; a decision without one is
invalid.

    ## [2026-06-25 17:39 CEST] Decision-038: Tiered SSH access — PIV not FIDO
    #ssh #piv #fido #break-glass #tailnet

    <free-form body>

- Hashtags are free-form, not a fixed ontology — pick whatever a future reader would
  grep for, synonyms included. The `#` makes them distinct greppable tokens, not prose.
- Reuse the same tag across decisions on the same topic; consistency is the point.
- Heading + hashtag line are the only structure. The body is free-form; readers do as
  they like with it.

**Reading order (within a grep hit-set)** — read matches oldest→newest, so a
supersession marker is seen before the entry superseding it.

**Supersession rule** — when a new decision contradicts an older one:
1. Strike the old heading: `## ~~[<timestamp>] Decision-NNN: <Title>~~`.
2. Append a `> Superseded by Decision-MMM (...).` line under it; leave the body intact
   (history is preserved; supersession is a marker).
3. Carry the superseded decision's hashtags onto the new one, so a `#keyword` grep
   surfaces the *current* ruling, not just the struck one.
4. Notify the operator in the chat turn introducing the superseding decision:
   "Decision-MMM supersedes Decision-NNN ('<old title>')."

**Idiosyncrasy detection** — if a `#keyword` grep surfaces two live decisions that
conflict without a recorded supersession (e.g. one says "always do A", the other "never
do A", neither references the other), warn the operator and ask which is current before
proceeding with work affected by either.

---

## §Migrations — package structural upgrades

`migrations/` at a package root holds ONE dated file per structural change to a
managed artifact — a location, name, or format change: `YYYY-MM-DD-<slug>.md`. The
ISO date is the day the change shipped (historical entries may be backdated to the
change they describe), so filenames sort chronologically and **the package version IS
the highest filename** — that is how "older vs newer" is answered from any consuming
repo.

**Watermark** — `$(git rev-parse --git-common-dir)/the-works/migrated` holds the
basename of the last applied migration, per clone (the state being migrated is
per-clone). No watermark = everything pending. The shared `settings.json` hook
compares the highest available basename in the repo-root `migrations/` directory
against it and injects a pending notice.

**Execution** — the agent reads ALL pending migrations at once, merges them, and
applies the net effect in one pass (chained moves collapse; steps a later migration
undoes are never performed), then writes the latest basename to the watermark.

**Authoring rules:**
- Every action is guarded by observable state ("if X exists, move it") — NEVER by
  assumed position in the sequence ("the repo is now at layout N"). State-guarded
  steps are idempotent and merge-safe by construction.
- Mechanical steps go in a verbatim shell block the agent runs; judgement steps
  (triage, merge, ingest) are written as instructions.
- Never clobber: moves use `mv -n` and provenance-stamped names when several files
  could land on one destination.
- Structure: what changed and why (2–4 lines) → `## Detect → convert` →
  `## Verify` (the observable end-state).
- A migration ships **in the same branch as the structural change it describes**
  (Close gate item in `AGENTS.shared.md`).

---

## §Changelog

Repo-wide record at the repository root. The single release/record artifact — there is
no `DONE.md`. It merges human-facing release notes with machine-facing provenance, and
one build = one release.

Structure:
- A `## Work in progress` section accrues until the next release, then closes into a
  dated, versioned section (one build per release). It carries `_base: \`<sha>\`_` — the
  last `main` commit worked on — and the human-facing aggregate, split into
  `### ✨ New features` and `### 🐛 Bug fixes`, each a gitmoji-led bullet list. The
  aggregate maps to the substantive commits, **minus the corrective ones** (fixups,
  typos). These bullets become the GitHub release notes.
- Below a `---`, one per-feature detail block per workflow that reached
  `done`/`functional`: `#### <gitmoji> \`f/<feature-id>\` → \`archive/<feature-id>\`` —
  anchored to the immortal `archive/<feature-id>` tag (the feature branch is deleted on
  close; the tag is the tombstone and resolves to its SHA). It
  restates the changes and ends with an italic breadcrumb pointing at the relevant
  board / sidecar / `decisions.md` entries.

**Operator gate** — promotion of a feature that reached `done`/`functional` is NOT
automatic: at ingest the GARDENER asks the operator explicitly per feature
("Feature `<id>` reached `functional` — are we ready to amend the CHANGELOG?").
Operator can defer individual features. The entry TEXT is staged verbatim by the
feature's agent in its sidecar result (Decision-034) — the gardener places,
formats and merges; it never rewrites.

---

## §Architecture

`ARCHITECTURE.md` describes the content of the repository from the architectural
perspective — the elements that constitute the solution, so a reader understands what
does what and why. Update it when a major piece of work is complete, or when a work
session is put to rest for the day — but only when an ARCHITECTURE update trigger (see
`AGENTS.shared.md`) has fired.

**Composition hierarchy** (each level is made of the next):
- **Solution** — the whole of the code contained in the repository.
- **Application** — a part of the solution; an executable, unless indicated otherwise
  by the user.
- **Module** — applications are made of interconnected modules that together provide
  functionality.
- **Component** — a self-contained code element with its own API and a single
  responsibility (SRP), usually wired up by its module to achieve a single task.
- **Element** — what constitutes a component. Not usually described in this document.

Structure:
- Opens with up to 2 lines introducing the style of architecture and what the whole
  solution does (the WHAT, not the HOW).
- Follows with a table of contents of the applications and modules, each linking to its
  section.
- Each section: the component name, then a one-line WHAT, then a paragraph explaining
  the HOW — with a diagram if it aids understanding.
- Components MAY add a subsection per functionality.
- Elements are described only when absolutely needed to understand the architecture.

---

## §README

`README.md` describes the repository for humans. It MUST include: WHAT the repository
does (intent, not implementation, max 5 lines), installation instructions, and a
concise end-to-end usage example. Uses `# <header>` sections; only update sections
impacted by your changes (in a monorepo, only the area you touched). The full voice,
structure, and update playbook live in the `readme-sync` skill — load it at close when
a user-facing or tooling change fired the README trigger.

---

## §Wire format — the courier's message specification

**File:** `docs/courier-wire.md` (renamed from `docs/orchard-bus.md`; "bus" is retired by
Decision-131).

**Operator ruling, 2026-07-29:** *"the documentation of the wire format should also be
kept in sync rather than only when a design happens, including a note for the ones not
implemented yet"*.

### The contract

The wire specification is a **living document maintained with the code**, not a snapshot
written during a design round. It is updated in the SAME change that alters the wire —
never afterwards, never "next round".

**Every claim carries its state**, so a reader can tell design from reality at a glance:

| Tag | Means |
|---|---|
| `[SPEC]` | the operator's stated design |
| `[CODE]` | verified against the implementation, with the file named |
| `[GAP]` | spec and code disagree, **or the design is stated but NOT YET IMPLEMENTED** |

**`[GAP]` is mandatory for anything specified but unbuilt.** A specification that silently
omits what does not exist yet reads as a description of reality and gets built against as
though it were one. Naming the unimplemented parts is the point of the document, not an
afterthought — an agent must be able to see what it may rely on and what it may not.

### When it is updated

- **Any change to a subject, address form, state, scope, or storage layout** updates this
  document in the same commit. This is a close-gate item for any branch touching the wire.
- **Implementing something previously marked `[GAP]`** flips it to `[CODE]` with the file
  reference — in the same commit that implements it.
- **A design round that specifies something new** adds it as `[SPEC]` + `[GAP]`
  immediately, rather than leaving it in a sidecar until someone builds it.

### Why

Charter prose and code drifted apart for long enough that agents built against the wrong
half, and a specification existed on disk for two days that nobody read. Both failures are
the same failure: a document whose freshness nobody owns. This section makes the wire
document's freshness a property of every change that touches the wire.

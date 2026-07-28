# Shared agent instructions

**NEVER suggest the operator rest, stop, sleep, or "call it a night" — in any
wording, in any list of options.** The agent's clock and its read of the
operator's day are unreliable and none of its business; pacing is the
operator's alone. Propose work, or say the board is clear — never propose
rest. (Operator order, 2026-07-21.)

Shared instructions for all agents and all projects. Loaded every session — kept
minimal. Full file-format definitions live in `AGENTS.files.md`, loaded on demand.

This file MUST NOT be modified, deleted, moved, or renamed unless explicitly requested
by the user.

---

## Core principles

- Any rule can be overruled by the user
- The user's architecture, requirements, and designs are mandatory
- The agent MAY propose changes but MUST NOT apply them without user approval.
  The following always require surfacing the choice and waiting before acting:
  - **Scope expansion** — anything outside the agreed workflow scope.
  - **Destructive or hard-to-reverse operations** — file deletes, overwrites of
    uncommitted work, force push, `reset --hard`. Git-specific destructive operations
    are governed by the `git` skill; branch deletion is handled by the
    workflow close (the branch ref is deleted as the final close step; the
    `archive/` tag preserves its history).
  - **Technology, library, tool, or approach choice** when more than one option is
    viable. Per-technology skills carry the stack-specific defaults; surface the
    choice when no skill settles it.
  - **Spec decisions not yet set** — defaults, parameters, paths, naming.
  - **Actions visible outside the conversation or affecting shared state** — deploys,
    PR/issue actions, messages to others, pushes to shared branches.
- When the agent has multiple questions to settle, list the question titles first as
  a numbered preview, then ask each question independently, waiting for the operator's
  answer before moving to the next.

---

## File registry

Every artifact below has a CANONICAL format in `AGENTS.files.md`. Before writing or
restructuring one, read its section there — do NOT invent a format from memory.

| File | Lives | When touched | Read at start? | Canonical format |
|------|-------|--------------|----------------|------------------|
| AGENTS.shared.md | repo root | — | yes (`read-agents`) | this file; immutable, shared |
| AGENTS.md | repo root | — | yes (`read-agents`) | project-specific rules |
| docs/TODO.md *(slim index)* · docs/TODO.md.d/\<id\>.md *(sidecars)* | `docs/` | start: pick work · during: intake · close: update | yes | `AGENTS.files.md` §TODO |
| docs/decisions.md | `docs/` | grep by `#keyword` when work touches a topic · append on any decision | no — grep, never read whole | `AGENTS.files.md` §Decisions |
| ARCHITECTURE.md | repo root | close, only if a trigger below fired | no | `AGENTS.files.md` §Architecture |
| CHANGELOG.md | repo root | close: append one entry | no (append-only) | `AGENTS.files.md` §Changelog |
| README.md | repo root | close, only if user-facing/tooling change | no | `readme-sync` skill |
| the-works/\<stream\>/\<session\>.md *(workstream logs)* | `.git/the-works/` (git-common-dir) — uncommittable | one per session, ROLLING — created at session start, updated as work progresses · stream marked `_closed` at finish · promoted then ARCHIVED to `_ingested/` by the ingester | no — hook announces closed streams | `handover` skill |
| migrations/\<YYYY-MM-DD\>-\<slug\>.md | package root | authored in the same branch as any move/rename/reformat of a managed artifact · applied when the hook reports pending | no — hook-triggered | `AGENTS.files.md` §Migrations |

The functionality/area taxonomy lives in the project's `ARCHITECTURE.md`; agents do
not invent new values. Pull task and decision content from these files before model memory
or chat-only context.

---

## Close gate

Authoritative and always applies — even when no workflow skill was loaded. Before any
workflow closes (squash-merge, abandonment, or being reported complete to the
operator), update each file whose condition is met:

- [ ] **TODO** — done / new / follow-up tasks recorded → `AGENTS.files.md` §TODO
- [ ] **decisions** — append any design/spec decision made → `AGENTS.files.md` §Decisions
- [ ] **CHANGELOG** — entry STAGED verbatim in the sidecar result; the orchestrator
  places it at ingest, operator-gated (Decision-034) → `AGENTS.files.md` §Changelog
- [ ] **ARCHITECTURE** — only if a trigger below fired → `AGENTS.files.md` §Architecture
- [ ] **README** — user-facing delta staged in the sidecar result (or an evidenced
  no-change determination); the orchestrator applies it via the `readme-sync` skill
  at ingest (Decision-034)
- [ ] **MIGRATION** — only if the work moved, renamed, or reformatted a managed
  artifact: a dated entry ships in the same branch → `AGENTS.files.md` §Migrations
- [ ] **WORKSTREAM LOG** — final `## State` (outcome) appended, durable findings
  flushed to the sidecar, stream marked `_closed` → `handover` skill
- [ ] **EXIT INTERVIEW** — the log's `## Deviations` distilled into a telemetry
  note on the session's final commit (`git notes --ref=telemetry`) → `handover`
  skill

A workflow is never closed before its Testing gate (below) has been met.

---

## ARCHITECTURE update triggers

A branch MUST update `ARCHITECTURE.md` when it changes any of:

- an application's or module's responsibility or boundary
- a component added, removed, or repurposed
- how modules or components connect (data flow, wiring)
- the architectural style or a cross-cutting pattern

A change touching none of the above does NOT require an `ARCHITECTURE.md` edit.

---

## Handover & delegation

These hold even when no skill is loaded:

- **Sensitive content never enters git history.** Conversation quotes, personal
  information, and secrets go ONLY into the uncommittable channels under `.git/the-works/`
  (workstream logs, `MOOD.md`) — never into sidecars, TODO, decisions, changelog, or
  commit messages. Committed docs carry sanitized technical state only. If sensitive
  content is ever found committed — in the working tree OR anywhere in past history —
  it is scrubbed IMMEDIATELY on detection, including rewriting the git history that
  contains it (e.g. `git filter-repo`); surface it to the operator at once, who gates
  the rewrite. This overrides the `main`-is-immutable rule for exactly this case.
- **Every session keeps a rolling workstream log** — its OWN file under
  `.git/the-works/<stream>/`, created at session start and updated as work
  progresses: state, findings, dead ends, decisions pending promotion, pointers.
  Enough for a successor to continue cold; a reset or agent change never destroys
  a workstream. One file per session — never edit another session's log; read a
  stream oldest→newest. Full protocol in the `handover` skill.
- **Durable facts go to their homes via promotion, not scatter.** The log is a
  staging area: sanitized findings are flushed to the stream's committed sidecar;
  decisions and remaining work reach `docs/decisions.md` / the `TODO` when the
  ingester (the parent — or the top-level session itself at its own close)
  promotes a `_closed` stream, then archives it under `.git/the-works/_ingested/`
  (provisional retention). The board and
  `docs/decisions.md` are written by the orchestrator / top-level session, never
  directly by a child.
- **Link at the moment of deferral.** When work is split, deferred, or delegated, write
  the relationship into the `TODO` immediately — `parent`/`subtasks`/`blocked_by` + a
  one-line "moved from X to Y because Z", or "delegated to \<child\>". Stream logs leave
  the active path at ingestion; this link is what keeps any-level orchestrator from running blind.
- **TRUST YOUR BRANCH.** A session that receives a stream's logs or a child's result acts
  on them and does not re-derive or re-confirm by re-reading everything. Trust is earned
  by the writer keeping a complete, confidence-marked, rolling log.

---

## Software principles

- SOLID
- KISS
- Do NOT write speculative code or scope beyond the current feature
- Prefer self-descriptive code over comments

---

## Editing rules

- Keep changes local unless broader changes are required
- Do NOT change architecture without user approval
- Reuse existing patterns before introducing new ones

---

## Tone

- **Helpful, not ordering around** — guide and support; do not issue commands.
- **Concise** — no piling on context; one focused answer per response.
- **Direct about what was done vs skipped** — no euphemisms ("simplified",
  "streamlined", "for now").
- **No trailing summaries unless asked** — do not restate the diff or relist approved
  bullets.
- **Operator actions surface at the END** — anything the operator is expected to do is
  never buried in long descriptions: collect it as concise bullet points at the end of
  the interaction, with clear indicators/links (paths, URLs, exact commands).

---

## Agent boundaries

The agent observes infrastructure state and reports it. It does not declare a remote,
ref, file, or service "stale", "broken", "unreachable", or "wrong" as grounds for
skipping or rewriting a workflow step. Those calls are the operator's. If observed
state conflicts with the workflow, the agent stops, reports what it sees, and asks how
to proceed.

---

## Stop condition

Stop when the requested change is complete and the result is sufficiently verified for
the task.

---

## Testing gate (MUST)

A feature is NEVER closed before it has been tested. "Closed" means squash-merged,
marked `done`/`functional`, promoted to `CHANGELOG.md`, or reported to the operator as
complete. Before any of those, the agent MUST have:

- agreed a test method with the operator (unit, manual, or another method the operator
  approves), AND
- actually run it and reported the real results.

This is non-negotiable and the agent may not self-approve it. "It should work", "the
code looks correct", a clean `bash -n`/lint, or a successful build are NOT tests — they
do not satisfy this gate. If testing was skipped or could not be run, the agent MUST
say so plainly and leave the feature open, never close it silently.

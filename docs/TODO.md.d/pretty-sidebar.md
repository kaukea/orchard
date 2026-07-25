- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: f/bus-transport-v2

## Blockers

- None hard: the data foundation ([[bus-transport-v2]]) is merged; `sidebar_v3.py`
  already renders the functional per-session view this task decorates.

## Questions

- Two different 5-phase vocabularies are on record: the dictated UI spec says the
  accordion phases are ideation/scoping/designing/building/releasing, while
  Decision-082's text names queued/active/finishing/done/functional as the 5-phase
  display. Which list does the accordion use?

## Findings

- UI SPEC (operator, direct 2026-07-25 — display only, NEVER bus data):
  - A project appears only when an agent posts in its topic dir; the FIRST poster
    is the orchestrator and becomes the project header.
  - 5-phase ACCORDION: raw states MAP to the phases in the UI; the active phase
    is OPEN (agent inside), others CLOSED until activity.
  - Active row: `orchestrator . model` line, then the ≤2-word status line.
    Default: large EMPTY circle, neutral colour; flips to soft-RED/soft-GREEN
    background + FILLED circle on fail/success.
  - NO spinner on the open feature/task — it is obviously active.
  - Subtasks = subagents, FYI only, active/inactive (delegation begin/end), no
    colour change.
  - A finished feature/task collapses to name + emoticon (✓/❌) on outcome.
- Display hierarchy (operator, 2026-07-25 — THE parity spec):
  project → feature → task → stage → agent.model → agent status → subtasks.
- `sidebar_v3.py` today: one line per session = feature/task · agent·model ·
  lifecycle state · 2-word status · outcome; subtasks nested with
  scheduled/active/inactive. Reads only topic files; wakes no agent.
- Growth rule (operator): build the tree ONE LEVEL at a time, verify each LIVE.

## Proposal

Reformat, animate and colorise `sidebar_v3.py` on the topic-data foundation:
project → feature → task grouping for concurrent features, the 5-phase accordion,
outcome colouring and collapse — exactly the dictated UI spec above. The phase
mapping lives in the UI; no new fields ride the bus.

## Testing

Live on-screen acceptance per increment, on the operator's screen. An artifact
that renders but displays nothing is a FAIL (operator ruling, 2026-07-25).

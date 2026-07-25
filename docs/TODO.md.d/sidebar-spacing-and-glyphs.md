# Sidebar spacing and glyphs: gaps found on the first live pass after sidebar-polish merged

- created: 2026-07-22
- created_by: claude-sonnet-5

## Blockers

- None. Depends on sidebar-polish (merged, `archive/sidebar-polish`) — this is
  a direct continuation of that same live-pass feedback loop, filed as its
  own task because sidebar-polish had already closed by the time it surfaced.

## Questions

- None yet — raw operator feedback, not yet bloomed/clarified. The bloomer
  or the next landscaper should confirm each point against the live sidebar
  before planning (some may already be partially true and just need a fix;
  others may need a design choice, e.g. the exact circle glyphs below are a
  suggestion, not a ruling).

## Findings

- Surfaced verbatim (operator, 2026-07-22, direct, immediately after
  sidebar-polish's close) as a numbered follow-up list — this sidecar exists
  only to capture it before it's lost; not yet triaged or planned.

## Proposal

The operator's list, transcribed from dictation (lightly cleaned up, substance
verbatim):

1. **Blank line between title and first feature** — the project header
   (gradient title bar) currently has no visual separation before the first
   feature row beneath it; needs an empty line between them.
2. **Distinguish active vs. idle subagents** — subagent rows currently don't
   show whether a subagent is actually doing something versus doing nothing
   (e.g. waiting on a monitor/external process) — they need a visible
   difference, not a uniform "working" look. (Likely ties to `flatten()` in
   `tools/sidebar.py` hard-coding `status="working"` for every subagent
   regardless of its real state — worth checking first.)
3. **Title gradient not actually showing** — the half-vertical-bar 3D-bevel
   gradient effect (built in sidebar-polish item 10) doesn't appear to be
   rendering as intended; needs live investigation of why, not just a
   re-read of the code.
4. **Glyph suggestion — filled vs. unfilled circle**: a filled white circle
   (●) for an active/pending ask, an unfilled white circle (○) for an
   inactive one. Needs clarifying exactly which indicator this replaces or
   supplements (candidates: the ❓ operator-question marker, or something at
   the courier-row level) before building — don't guess.
5. **Running vs. complete feature indicator** — some visible indication is
   missing for a feature that is currently running, distinct from its
   success/fail state once complete. NOTE: sidebar-polish deliberately
   removed ALL animation (item 1/9, operator's own explicit ruling) — this
   point needs reconciling with that ruling before building anything that
   looks like motion; it may just mean the existing static 🚧/✅/❌ glyphs
   aren't actually showing at the FEATURE row level the way they show
   elsewhere, not a request to bring animation back. Confirm with the
   operator rather than assuming either reading.
6. **Blank line between active and pending projects** — a visual separator
   is missing between the "active" project group and the "pending" one.
7. **Blank line before each repo when there are multiple repos** — when
   more than one repo is shown, a newline is missing before each repo's
   block (visual separation between repo groups).

The operator's closing framing: "that would complete the work" — i.e. this
is experienced as finishing touches on sidebar-polish's own intent, not new
scope.

## Testing

Operator visual pass on the live sidebar, same method that produced this
list and sidebar-polish's own list — no unit-testable claim should be
reported as done without a live look, per this same feature's own recent
experience (two real popup bugs that passed unit tests but failed live).

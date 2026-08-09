- created: 2026-08-09
- created_by: serialseb
- created_during: gardener session (inbox-outbox scope round)

# Transition cues: a big visual before every on-screen handoff

## Blockers

None.

## Questions

- Rendering surface beyond the chat turn — tmux popup? pane banner?
  sidebar row highlight? (operator: "a little visual being displayed")
- Does the cue gate (wait for acknowledgment) or just announce?

## Findings

- Operator, 2026-08-09, verbatim intent: at each transition where
  something will happen on his screen (gardener → arborist → landscaper →
  …), BEFORE the flow starts, display a big visual cue: "Next step is
  the <role>" plus a summary of what it is going to do — "visual clues
  and big ones … that should be a good first start when handing over."
- Refined same day: the summary is the WHAT — the work that will be
  done — never the mechanics ("I don't really care that it opens its
  own window"). It may note that additional technical questions can
  come back as a follow-up.
- First application: the gardener renders the cue in its own reply
  before starting any role session — in effect immediately, no build
  needed for the minimum form.
- Related: lexicon (the roles named in cues must use the ruled names),
  operator-interacting (gh#219), sidebar work (glyph vocabulary
  Decision-085/140).

## Proposal

Minimum now (no build): every component that starts another on-screen
role renders a banner first — glyph, role name, one-line summary of what
it will do. Richer surfaces (popup, sidebar) are this task's scope round.

## Testing

To be agreed at scope round.

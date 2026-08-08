# Operator interacting: questions, gates and summaries as one typed exchange

- created: 2026-07-22
- created_by: Sebastien Lambla

## Blockers

- Sequencing only: builds on the question ask-path landing in
  [[sidebar-polish]] item 12 (the courier-message question with numbered
  options is the first kind of this envelope).

## Questions

- Envelope kinds and their sidebar markers: question (❓, numbered options),
  gate request (plan → MAKE IT SO, done → THAT IS ALL — which glyph?),
  summary/presentation (which glyph?). Others (progress reports, blockers)?
- ~~Rendering surface?~~ RULED direction (operator, 2026-07-22, "let's try
  it and see if it works"): the broker is a SCRIPT, not an agent — a
  question message on the courier triggers a token-free tool drawing a native
  tmux popup (numbered options) over the operator's CURRENT window; the
  keypress returns over the courier to the asker.
  INPUT RULE (operator, 2026-07-22, after the live demo landed mid-typing):
  the popup responds ONLY to its defined option keys and IGNORES every
  other keypress — no default pick, no dismiss-on-any-key — so a question
  arriving while the operator is typing can never consume in-flight
  keystrokes as an answer. This kills the operator's biggest frustration
  with the harness dialogs (choices demanded mid-typing).
  TIMING RULE (operator, 2026-07-22): while the operator has input in
  flight, the question does NOT pop — only a passive notice shows ("I have
  a question", plus the sidebar ❓); the popup renders when the in-flight
  message is SENT (or the operator goes idle). Deferral first,
  option-keys-only as the remaining guard.
  ENFORCEMENT PRINCIPLE (operator, 2026-07-22): the deferral and input
  rules live in the SCRIPT, so no agent can override them — behaviour is
  enforced by the architecture, never by instructions an agent might
  ignore. This is the template for the whole envelope: presentation
  discipline is the broker's, not the model's. Subagents have no harness-UI
  surface, so an agent broker would render via tmux anyway while paying
  tokens for zero judgment. First live trial ships with [[sidebar-polish]]
  item 12; this task generalises the envelope to gates and summaries once
  the trial holds.
- Fallback when tmux is absent, and whether gate requests ever render only
  in the agent's pane.
- Does the operator's ANSWER travel back over the courier too (operator types in
  the gardener pane, relay carries it operator-origin per Decision-047),
  making the whole exchange symmetric?
- Enforcement: same pattern as the question tools — presentation habits
  stripped from agent defs and replaced by the typed send?

## Findings

- OPERATOR RULING (2026-07-26, scope round): operator interaction is
  designed SEPARATELY — this task specifies WHAT it does, and the transport
  can be tmux OR plain OR any other interaction transport. The
  [[tmux-topology]] spec stays silent on popups; tmux is at most one
  transport this design may choose. (Refines the 2026-07-22 "broker is a
  script drawing a native tmux popup" direction: that becomes one candidate
  transport, not the definition.)
- Operator direction (2026-07-22): the enforced question path generalises —
  "this could unify the MAKE IT SO for example, that each agent decides to
  ask differently, or the multiple choice questions, or for that matter
  summaries." One protocol, uniform display, no per-agent invention.
- The operator-origin relay (Decision-047/049) already carries gate words
  upstream; this task gives the downstream half the same typed shape.

## Proposal

**Folded in 2026-08-08, from the courier-messaging questioning:** the design
of the operator ASK lands here. Operator ruling, same day: an ask is simply a
request/response with a SPECIFIC FORMAT that is defined by specification and
not by the agent. `session-messaging` delivers only the blocking
request/response transport the ask rides; this task owns the ask's format,
presentation, and broker behaviour (deployment bug stays in
`question-broker-dead.md`).


One typed operator-interaction envelope on the courier: kind (question | gate |
summary), payload, numbered options where applicable. Agents SEND the
envelope instead of inventing presentation; the gardener renders all
kinds uniformly in the operator's pane; the sidebar marks the waiting kind
with its glyph. Gate SEMANTICS are untouched — MAKE IT SO and THAT IS ALL
remain the operator's words, exactly as ruled; only their request and
display unify.

## Testing

To agree at readiness: one live feature driven end-to-end through the
envelope — a discovery question, a plan gate request, and the done summary
all arriving uniformly in the gardener pane with correct sidebar
markers, and the operator's answers/gate words flowing back unchanged.

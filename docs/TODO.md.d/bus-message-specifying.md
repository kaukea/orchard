- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

- None.

## Questions

- Which message classes make up the specified vocabulary — lifecycle signals
  (announce/done/finished/abandoned), activity states, subagent start/done,
  notify-user flags, operator-origin relays — and are any missing or
  superfluous?
- Where does the specification live: the bus agent definition, a channel
  schema per [[fleet-documenting]] (which already envisions channels with
  JSON Schemas), or both — and does this task fold into fleet-documenting or
  precede it as the tightening pass?
- What does "more appropriate" rule out — free-form activity wording, ad-hoc
  labels, duplicate waiting-state broadcasts?

## Findings

- Operator intake (2026-07-24): bus messages need tightening, cleanup and a
  specification of what each message DOES; what each agent actually sends
  diverges from any common shape and must be audited and fixed alongside the
  spec.
- Live example from today's session: the architect's waiting state arrived
  twice in a row as identical `awaiting operator (native prompt)` notify
  broadcasts; activity labels are free-form prose.
- Second live example (successor architect, 2026-07-24 close): its
  `orchid:activity:Closing` broadcast was read by its own bus as a
  session-departure signal — free-form activity wording collides with
  lifecycle vocabulary.
- Operator dictation (2026-07-24 evening, first message of the spec — more
  to come): agents carry (a) a STATUS — one or two plain words for what
  they are doing now (reading, writing, messaging, concluding, thinking…),
  each agent choosing its own word, unlike the Claude UI's invented terms;
  and (b) a STATUS UPDATE — the sentence describing current work, aimed at
  the log/main pane, never at the operator. Only ONE main agent is
  interactive with the operator at a time; agents follow one another.
- Operator dictation, message 2: exactly THREE interrupt classes may break
  his flow visually — SUCCEEDED, FAILED, QUESTION. Everything else is
  already covered by status/status-update and must not interrupt. Concrete
  offender: every tmux window continuously flashes its activity flag
  (possibly his rainbow/fabulous plugin) as if everything were interesting —
  it is not: "I like seeing how the soup is made, but I am here to eat the
  soup."

## Proposal

(to shape at bloom) One specified bus-message vocabulary — every message
class named, its purpose, payload and consumer defined; every agent's actual
sends audited against it and corrected so the sidebar and orchestrator read
one dialect.

## Testing

To agree when bloomed — expected shape: a session of each role runs and its
bus traffic validates against the specification with no unspecified message.

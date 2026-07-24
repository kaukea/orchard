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

## Proposal

(to shape at bloom) One specified bus-message vocabulary — every message
class named, its purpose, payload and consumer defined; every agent's actual
sends audited against it and corrected so the sidebar and orchestrator read
one dialect.

## Testing

To agree when bloomed — expected shape: a session of each role runs and its
bus traffic validates against the specification with no unspecified message.

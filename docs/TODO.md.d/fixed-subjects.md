- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Fixed list of subjects any agent may send, no exception

## Blockers

None.

## Questions

None open.

## Findings

- The closed subject vocabulary exists in both specs
  (`ORCHARD_VALID_SUBJECTS`); the branch spec flags the `bus` literals
  (Decision-131 name retirement) as awaiting the operator's word since he
  dictated those exact strings.

## Proposal

Scenario as dictated 2026-08-08: a fixed list of subjects able to be sent by
any agent, no exception.

**Ruled, 2026-08-08 (operator, dictated during session-messaging
questioning):** subjects are a series of NOUNS identifying the kind of
message. An agent message is a message from an agent; an operator message is
an operator's message relayed by an agent. The specializations
(todo|instructions|request|response|content) are used by the SCRIPT to
understand how to interact with the prompt of its owner agent, and they also
impact routing. One family, specialized within: a TREE where each leaf has
specific properties but shares the properties of the root.

**Ruled, 2026-08-08 (operator):** the purely technical messages are named
SYSTEM MESSAGES — their own family in the tree, alongside agent and operator
messages; answered by the script without breaching the AI boundary
(`technical-messages.md`).

**Ruled, 2026-08-08 (operator):** the subject list gets a REVIEW at build
time — very likely it stays the same. The existing 22-subject corpus
(Decision-092) is the base under review; the `bus` literals are reviewed
with it.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.

- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Documentation for other components: decoupling through events

## Blockers

None.

## Questions

None open.

## Findings

- The archived wire spec §7 already states the event rules (state is read,
  never inferred; two-event ending; creator-closes). This scenario writes the
  documentation OTHER components consume to integrate through events.

## Proposal

**Ruled, 2026-08-08 (operator):** the readers are AGENTS THAT WRITE AGENTS,
and humans who want to understand how decoupled, asynchronous agents
function. The subject is TELL, DON'T ASK: react to the events and messages
you receive to make decisions, instead of going to probe some agent you
think you know. It lowers coupling, increases reliability, and is what makes
the system function. The cautionary example: the old caretaker killing files
before agents could clean themselves up.

**Ruled, 2026-08-08 (operator) — location:** a new `docs/patterns/`
subfolder: `docs/` today holds the WHAT IS; patterns holds the WHAT SHOULD
BE, the guides to development. This document lands there, and `AGENTS.md`
gains a pointer naming it the way one writes code — agentic code — in this
project. Deliberately NOT added to `AGENTS.files.md`: it is specific to this
project and the operator's way of coding. (Folder and pointer are created
when this scenario is built, not at task creation.)

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.

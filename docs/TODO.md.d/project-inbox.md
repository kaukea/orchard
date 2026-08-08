- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Project inbox

## Blockers

None.

## Questions

None open.

## Findings

(none yet)

## Proposal

**Ruled, 2026-08-08 (operator):** working in one project, you conceive
tasks or changes for ANOTHER project — possibly offline — or hold documents
that do not belong in your repository (the forensics TOOLING repo vs the
CASES repo carrying actual data). Today agents write the other project's
TODO directly, copying the style they find — making the orchestrator's life
awful. The PROJECT INBOX replaces that: a place to send a message, a file,
or a TASK to a project, for the GARDENER to ingest when it is ready — in
real time if the project is running, or when the project is next started in
a new Claude instance. Arriving items are cleaned up and sorted by the
gardener; a foreign agent never writes the target board.

Build-order position: not yet assigned.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.

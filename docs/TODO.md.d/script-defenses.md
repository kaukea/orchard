- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Defensive practices by the script against any deviation

## Blockers

None.

## Questions

None open.

## Findings

- The governing principle stands in the retired experiment's record: the
  script already enforced format and subject absolutely; enforcement lives in
  code, never prose.

## Proposal

**Ruled, 2026-08-08 (operator):** messaging is a HIGHLY SENSITIVE component —
it can reach the inside from the outside. Anything that does not come from
another script VETTED by the current script is a security danger: usable for
data exfiltration, or to cause crashes or token burn that damage the user's
account. The script therefore defends against ANY deviation: file location,
file format, content length, missing fields — probably even an allowlist of
process IDs.

**The body is formalized too:** not free text only, and validated. Validation
is DOUBLE-CHECKED at two layers — STRUCTURAL by the script (schema, location,
format, length, fields, sender vetting) and LOGICAL by the courier subagent:
for the free-text part, the courier validates that the content matches the
INTENT of the message.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.

- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Defensive practices by the script against any deviation

## Blockers

None.

## Questions

None open.

## Findings

- Operator, 2026-08-08: we are knowingly building a CLASSIFIER in multiple
  places (the courier's logical validation, the breach triage) — accepted;
  there is no way around doing it ourselves.
- Operator, 2026-08-08: components and agents have had a TENDENCY to bypass
  the courier agent altogether and call the script directly. The defense
  layer must treat a bypass attempt as the normal case, not the exception —
  and a cheap courier (see token-sacrifice) removes the incentive to cheat.

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

**Ruled, 2026-08-08 (operator) — the breach response:** structural is the
script's responsibility; it rejects anything malformed before anyone sees
it. The courier subagent validates ONLY the fields carrying another agent's
free speech: a question that could be dangerous, has nothing to do with the
topic, or does not look like a question an agent would ask — seeded with a
short set of examples, grown or shrunk over time by experience. Quarantine
is for FORENSICS and is not the response: a breach is a problematic event
and nothing continues as if nothing happened. THREE LEVELS:

1. **Questionable** — the user is asked: does this question, from that
   agent, look right to you?
2. **Warning** — the message is ignored and announced loudly: "the
   following message was ignored as it was deemed dangerous" (big yellow
   letters, in spirit).
3. **Error** — the downright error: stops the current process altogether.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.

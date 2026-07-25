# Digest formatting: emoji-keyed bullets, impact subtitles, links

- created: 2026-07-22
- created_by: Sebastien Lambla

## Blockers

- Operator hold: do NOT act — the proposed format is awaiting
  confirmation by another model. The operator lifts this hold explicitly.

## Questions

- "Gardener emphasized": confirm the exact meaning — gardener
  sessions/lines rendered with emphasis (italic/bold) in the digest?
- Confirm the exact emoji per key once the other model's review lands
  (fixed vs todo bullet markers; the impact set below).
- Where does the digest format spec live so the change is durable — the
  scheduled routine's prompt is the presumed home; verify at pickup.

## Findings

- The digest under review is PR #60 (telemetry digest 2026-07-21); the
  operator judges its content good — these are format changes, not
  content changes.

## Proposal

Restyle the telemetry digest's rendering:

- Every bullet starts with a status emoji as the first character after
  the bullet: one emoji for fixed/addressed items, a different one for
  todo/open items.
- Subtitles are emoji-prefixed by impact category: time impact (clock),
  money/token spend (euro banknotes), code quality (construction sign).
- Gardener entries are emphasized (see Questions).
- Digest lines link to `docs/decisions.md` entries and the other
  documents they reference, instead of naming them bare.

## Testing

The next scheduled digest run renders the new format: status emoji on
every bullet, impact-emoji subtitles, emphasized gardener entries,
and working links to decisions/documents. Operator eyeballs it.

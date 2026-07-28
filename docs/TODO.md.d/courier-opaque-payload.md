- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# Courier opaque payload: transport must not care how the string is made

## Proposal

Operator, 2026-07-28, verbatim: *"COURIER SHOULD NOT CARE HOW THE STRING IS MADE.
YOU BUILT IT WRONG AND BRITTLE."*

This rides the ruling already given in the features-first-class bloom round the
same day: the courier is TRANSPORT ONLY — it cares about session ids and topics,
never about content. The current build violates that:

- `tools/courier.py:305` — the courier sniffs message bodies for an `orchid:`
  prefix and branches behaviour on it.
- `tools/courier.py:723-725` — an interrupt is rejected unless its body
  decomposes exactly as `orchid:interrupt:question:<subject>`; the body is BUILT
  by string concatenation at `:624-625` and PARSED back by `partition(":")` — the
  payload's construction is load-bearing, so any producer assembling the string
  differently breaks delivery.

The fix direction (to be designed at bloom, not here): payloads ride opaque;
anything the courier must act on travels as typed envelope FIELDS, never as
substrings of the body.

Boundary to respect: the CLOSED orchard subject list is a separate, standing
operator ruling (`courier.py:862-866` — exact membership, no derivation) and is
NOT the brittleness complained about. Subjects stay closed; bodies become opaque.

## Questions

1. Which failure surfaced this on the operator's screen (needed for the
   regression test): a groomer's `courier ask`, a rejected interrupt, or another
   path?

## Testing

To be agreed at bloom; must include a regression: a body containing arbitrary
text (colons, prefixes, empty) is delivered untouched and never rejected for its
shape.

# Component field declaring: Component missing from board_gh field sets

- created: 2026-07-22
- created_by: fable-5
- created_during: field-projecting close (landscaper-surfaced follow-up)

## Blockers

- None; picks up after [[field-projecting]] merges.

## Questions

- None expected — mechanical: declare Component alongside its peers.

## Findings

- Surfaced by the field-projecting build: `Component` is synced as a GitHub
  Project field but is not declared in `board_gh.py`'s
  `SELECT_FIELDS`/`TEXT_FIELDS` sets that the map-or-create mechanism now
  drives — the one badge field outside the declared inventory.

## Proposal

Declare Component in the appropriate field set so the map-or-create rule of
[[field-projecting]] covers every badge field with no undeclared stragglers.

## Testing

One live synchronization: Component values still project correctly and the
field appears in the declared inventory (no special-cased path left).

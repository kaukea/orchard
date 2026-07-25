- created: 2026-07-25
- created_by: gh-ingest
- created_during: interactive

## Blockers
- None known yet.

## Questions
- Ingested from GitHub issue #232 — needs triage: type, component,
  urgency, scope.

## Findings
- Filed on GitHub (https://github.com/kaukea/orchids/issues/232); original body preserved below.

#decision-projecting #github #matching

`docs/decisions.md`'s canonical entry format is heading + mandatory hashtag
line only — no room for a stored GitHub issue number, unlike task sidecars'
YAML front matter. Rather than extend that canonical format (which every
future decision write would then have to carry), sync matches a decision to
its GitHub issue by title text: the issue title is `Decision-NNN: <title>`,
looked up via one bulk `gh issue list --search "Decision- in:title"` call
per sync run and filtered client-side, not stored anywhere. `Decision-NNN`
was already the stable, human-assigned key: this reuses it rather than
inventing a second one. Considered and rejected: embedding a gh# in the
decisions.md heading (breaks the canonical format); a Projects-v2 custom
field for matching (adds an indirection the title lookup already avoids —
GitHub's own field-locking is non-existent per-field anyway, so a stored
field is no more tamper-proof than re-deriving it fresh every run). Also
added, per operator request, as pure redundant metadata (not used for
matching): `Decision Number`/`Decision Title` Projects-v2 text fields, same
mechanism already used for `Area` — free, future-proofing, no admin action
(Projects-v2 fields are project-scoped, unlike GitHub Issue Types which are
org-scoped/admin — both tiers already exercised elsewhere in this codebase).

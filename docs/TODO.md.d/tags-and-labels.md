- created: 2026-07-21
- created_by: Sebastien Lambla
- completed: 2026-07-21
- completed_during: gardener session

## Blockers

- None.

## Questions

- Which badge fields project as labels alongside the tags — type, urgency,
  component, all three?
- Emoji mapping: fixed per label in the vocabulary table (single source), and who
  picks them?
- Round-trip: does `board_gh pull` ingest label changes made on GitHub back onto
  the board line, or are labels projection-only (board stays canonical)?
- Label colors: derived per family (urgency reds, component blues, tags amber)?

## Findings

- Operator ruling (2026-07-21): board tags and GitHub labels are ONE AND THE SAME
  system — defined once, projected everywhere — with emojis on the GitHub side.
- Current state: `#madmax` is the first and only board tag (AGENTS.files.md §TODO,
  Decision-031, operator-set with git-provenance enforcement); `board_gh.py push`
  applies only a generic `board` label; urgency/component/type live in the badge
  and are invisible on GitHub.

## Proposal

Define the tag vocabulary and its governance in AGENTS.files.md §TODO (each tag:
name, emoji, meaning, who may set it — the single source, per the Taxonomy
pattern). `board_gh.py` ensures the emoji-prefixed labels exist and projects each
issue's labels from the board line: its tags plus the chosen badge fields. Board
stays canonical; projection direction per the round-trip answer.

## Testing

To agree when bloomed — expected shape: a board line carrying a tag and an
urgency projects to an issue wearing the matching emoji labels; the label set on
GitHub equals what the board line says, for every projected issue.

### Resolution (2026-07-21)

Built and live-verified 2026-07-21 (Decision-035): 21 labels ensured, all issues relabelled exactly from their board lines (18 created, 15 updated, 3 closed; project 45 rows); gh#23 carries board/feature/area-process/todo/blocked, gh#34 carries bug/area-process/doing.

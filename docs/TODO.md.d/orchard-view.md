- created: 2026-07-20
- created_by: Sebastien Lambla

## Blockers

- ⊘[[orchard-summary]] — nothing to consolidate until repos publish summaries.

## Questions

- Entry point: inside Claude (an agent/skill launched by `orchard`) or outside it (a
  standalone CLI that parses the summary files with no model at all)? Operator explicitly
  deferred this ("to be discussed"). A dumb parser is cheaper and always available; an
  agent can narrate and answer follow-ups.
- Repo discovery: how does Orchard know which repositories exist and where? (A fleet
  registry file, a scan root, or the kauk install index?)

## Findings

- Operator (2026-07-20): callable from ANYWHERE. Presents at a high level: what projects
  exist, how many pressing / broken / blocked issues each carries, and cross-repository
  dependencies (worked example: manifest-by-convention re-homed orchids→kauk). From that
  view the operator chooses where to engage.
- Presentation-only by ruling: Orchard renders what gardeners prepared
  ([[orchard-summary]]) — it never scans repos or re-derives priorities.
- [[github-board-sync]] (functional) already aggregates the fleet on GitHub (Orchidarium
  Project); Orchard is the local terminal counterpart — same data, different surface.

## Proposal

An `orchard` command presenting the consolidated fleet: per-repo headline (counts,
top prepared tasks, staleness of the summary), cross-repo dependency edges, and a
selection step that hands the chosen repositories to [[orchard-launch]]. Shape of the
command (agent vs plain CLI) settled by the entry-point Question.

## Testing

With ≥2 repos publishing summaries (one containing a cross-repo edge), `orchard` renders
the fleet correctly from outside any repo, flags a deliberately stale summary, and the
selection hands off the right repo list.

- created: 2026-08-07
- created_by: Sebastien Lambla
- created_during: f/delivery-restoring

# DEFCON-1 delivery restoring: consumers re-attached to latest main via the conventional manifest path

## Blockers

- EXTERNAL: the CI leg of the Testing gate needs kauk installable on a fresh
  runner. Ruled 2026-08-08: kauk is consumed as its published Debian package
  only — its own repository builds and ships it; orchids never reaches into
  kauk's repository for any purpose. No such package is published yet (the
  packages.serialseb.net pool is empty; kauk's own board carries the apt-host
  task as its gh#13). Until upstream ships, the workflow's install step is
  deliberately, honestly red. The local leg is green with the machine's
  installed kauk.

## Questions

None permitted: the operator ordered the restore executed without questions.
Judgement calls taken under that order are recorded in Findings and reversible.

## Findings

- **The breakage** (diagnosed 2026-08-07): the de-vendoring commit `ceca7ae`
  (2026-07-28, Decision-122) deleted `manifest.conf` — the index every consumer's
  kauk stopgap lays `.claude` links from (`serialseb/kauk bin/kauk`: no manifest →
  "nothing to lay"). Consumers' `.ai.toml` origins point at this repository's
  path directly. Measured damage: SignMc synced 2026-08-07 14:40 → fresh mirror,
  57 of 196 links dangling (renamed/removed skill paths); dns, fastcut,
  seb.throwy, seb.house frozen on stale pre-rewrite mirrors, links intact.
- **Role mapping** (call taken): skills now carry hierarchical `roles:`
  frontmatter; the manifest grammar takes one token of `dev|infra|org|all`.
  Mapping: `general` → `all`, `process/*` → `org`, `development/*` → `dev`,
  `infrastructure/*` → `infra`; the first listed role decides (matches the old
  hand-written manifest, e.g. coding-tofu → dev).
- **Anti-drift** (call taken): `manifest.conf` is not hand-typed again — it is
  emitted by `tools/manifest_gen.py` from the tree, and the integration test
  fails if the committed manifest differs from a regeneration. This kills the
  recorded silent-drift failure mode (2026-07-19: four committed files
  distributed to nobody for four missing manifest lines).
- **Component boundary** (operator ruling, 2026-08-08, superseding the CI
  credential plans tried first): orchids never accesses the kauk repository —
  not by deploy key, not by app token. kauk builds and publishes its own
  Debian package; orchids consumes the installed binary (`kauk` on PATH),
  which is also exactly what the test now uses locally. The earlier
  credential attempts (deploy key — blocked by the harness; callabloom token
  — app not installed on serialseb/kauk, run 31222381352) are dead ends,
  recorded so they are not repeated.

## Proposal

Restore the conventional consumer path exactly as it always worked — clone +
`manifest.conf` + laid links — with the index now derived from the tree:

1. `tools/manifest_gen.py` — deterministic generator: `skill` lines from
   `skills/*/` with roles mapped from frontmatter; `link` lines mirroring every
   real file in `agents/`, `hooks/`, `tools/` (excluding caches) plus
   `settings.json`, `AGENTS.shared.md`, `AGENTS.files.md`; `template` lines for
   `templates/AGENTS.md` and `templates/board-sync-shim.yml`; `prefix` for
   `templates/CLAUDE.md`.
2. `manifest.conf` — the generator's output, committed at the package root.
3. `tools/delivery-integration-test.sh` — creates a brand-new scratch project,
   runs the real `kauk install` against a snapshot of this repository, and
   verifies: every manifest entry lands resolving at its destination, the
   template is substituted, the prefix is present, no dangling link exists
   anywhere under the consumer's `.claude`, the committed manifest matches a
   regeneration from the tree, and a second `kauk sync` is green (idempotence).
4. `.github/workflows/integration.yml` — runs the integration test on pushes and
   pull requests; kauk is fetched with the scoped deploy key.

## Testing

Dictated by the operator: the integration test above, run by a GitHub Actions
workflow, and no further work until it passes. Local run green, then the
workflow run green on the pushed branch, then green again on main after the
squash-merge.

## Changelog entry

- Restored consumer delivery: `manifest.conf` is back at the package root,
  now generated from the tree (`tools/manifest_gen.py`) instead of hand-typed,
  and guarded by an integration test (`tools/delivery-integration-test.sh`,
  `.github/workflows/integration.yml`) that installs the package into a fresh
  project with kauk and verifies every file lands in position.

## Readme delta

- README's consumer/install section must state: the package is installed the
  conventional way (`kauk install serialseb/orchids <origin>`); `manifest.conf`
  is generated — edit the tree, run `tools/manifest_gen.py`, never hand-edit
  the manifest; the integration test is the gate for distribution changes.

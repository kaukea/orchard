- created: 2026-08-08
- created_by: Sebastien Lambla
- created_during: f/delivery-restoring

# Kauk successor adapting: read its documentation, repoint the delivery pipeline to the renamed package

## Blockers

- EXTERNAL: the upstream work is the operator's own, in the kauk repository,
  and has not shipped: additional features, fixes, a RENAME, removal of the
  parts he judges dead weight, and documentation. Nothing on this task moves
  until that lands.

## Questions

None until the upstream documentation exists — every value this task needs
(the new name, the apt repository URL and signing arrangement, the install
one-liner) is read off that documentation, never guessed in advance.

## Findings

- Announced by the operator, 2026-08-08: he implements the successor himself —
  features, fixes, rename, cleanup, documentation the agents will read. The
  Debian package will be published on a CUSTOM apt repository, so consumers
  (and the CI workflow) add that repository to apt sources before installing.
- The delivery-restoring workflow already has the add-repo-then-install shape,
  with the repository URL and package name parameterized at the top of
  `.github/workflows/integration.yml`, marked as owned by the upstream
  documentation.

## Proposal

When the upstream ships:

1. Read the successor's documentation IN FULL before touching anything.
2. Update `.github/workflows/integration.yml`: repository URL, signing key
   handling (replace the interim `trusted=yes` with the documented key), and
   the package's new name.
3. Update `tools/delivery-integration-test.sh` if the binary name changed.
4. Sweep orchids for the old name where the documentation says it changed
   (skills, agent definitions, tools that shell out to it), each reference
   updated to what the documentation actually specifies.

## Testing

The delivery-integration workflow green on a fresh runner that installs the
renamed package from the custom apt repository — the same gate
delivery-restoring already owns, exercised through the new values.

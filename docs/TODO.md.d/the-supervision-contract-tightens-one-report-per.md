- created: 2026-08-18
- created_by: gh-ingest
- created_during: interactive

## Blockers
- None known yet.

## Questions
- Ingested from GitHub issue #300 — needs triage: type, component,
  urgency, scope.

## Findings
- Filed on GitHub (https://github.com/kaukea/orchard/issues/300); original body preserved below.

Three operator rulings from the 2026-08-18 kauk fleet run need to become part of the standard workflow definitions. They were exercised live that evening and are recorded as gardener memory in kauk, but the workflow files themselves still carry the old behaviour. The operator holds this as part of a larger feature he wants built — treat this issue as intake for that work, not as three little edits to rush through.

What the rulings say:

1. The beekeeper reports exactly once per feature: the resolution, success or failure, when the feature is done. No interim status messages, flags, or questions to the gardener. Deaths and wedges the beekeeper detects are its own to resolve — a fresh redispatch carrying the ratified sizing, or firing the close — never a question upward. (Live failure: during the kauk run the beekeepers streamed status to the gardener, who relayed it to the operator; both ends of that were wrong.)

2. Time the operator spends at an interactive gate — a plan gate, MAKE IT SO, THAT IS ALL, any question — is their own pacing. It is never a stall, a pattern, or an input problem to flag or report, by any agent. This extends the standing "never suggest rest" rule in the shared instructions to response time.

3. Model and effort sizing for agent launches is the gardener's own call, made from sized difficulty and stated in passing — never put to the operator as a question. Only substituting a different agent type still goes to the operator before launch.

Files that would carry them: the beekeeper and gardener agent definitions, and the shared agent instructions for the pacing rule. A direct amendment was made and reverted the same evening (c6dbc7c / 67e9d64) at the operator's direction — the diff there shows one concrete shape, but the feature owns the final wording.

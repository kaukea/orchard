- created: 2026-07-19
- created_by: fable-5
- created_during: f/status-channel

## Blockers

- Depends on the repo-scoped courier landing first ([[status-channel]]) — this extends it,
  it does not replace it.

## Questions

- Is the cross-repo hop live (a courier that spans repos) or a relay between two repo-scoped
  couriers? The latter keeps each repo's courier unchanged and confines the new part to the hop.
- Addressing across repos: an agent ID is unique within a repository, so a cross-repo
  address needs the repo as a qualifier. What is the canonical repo identifier?
- Broadcast semantics across repos — does a broadcast stop at the repo boundary? (Almost
  certainly yes; crossing it by default would be surprising.)

## Findings

- Content moved out of the [[orchard]] sidecar 2026-07-20 when the operator re-pointed
  the Orchard codename at the fleet workbench (Decision-024); this task keeps the live
  cross-repo MESSAGING scope unchanged.
- Messaging is REPO-SCOPED by design: agents, gardeners and third-party local agents
  are all scoped by repository, so the courier is too ([[status-channel]]).
- Distinct from [[cross-repo-inbox]]: that is the OFFLINE, durable delivery of requirements
  and knowledge between projects. This is the LIVE messaging path. Same boundary, two
  different mechanisms — do not merge them (operator).
- Motivating instance: on 2026-07-19 work was discovered in seb.tv that belonged to orchids,
  with no channel to deliver it — so it was edited into a vendored clone and pushed straight
  to main, bypassing the workflow. The wrong path was the only path.

## Proposal

Extend agent messaging across repository boundaries. Scope to be set once the repo-scoped
courier is proven in use.

## Testing

To agree when the task is bloomed — expected shape: an agent in one repository addresses an
agent in another and the message is delivered, with broadcast still confined to its own repo.

## Wall item promoted from the courier build (2026-07-19)

- **Phase-two lean HELLO + lazy metadata fetch.** The courier announces identity eagerly at load,
  which is fine at small n. Once membership is large and interest is sparse — the cross-repo
  case — announcing everything to everyone stops paying. Fetch metadata on demand instead.
  Left for the cross-repo layer because it only bites at that scale.

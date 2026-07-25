- created: 2026-07-19
- created_by: fable-5
- created_during: f/status-channel

## Blockers

_None._

## Questions

- Which delivery mechanisms actually guarantee content reaches an agent INTACT — agent
  definitions (system prompt), hook-injected context, skills, or files an agent is told to
  read? Each needs verifying rather than assuming.
- How much current doctrine depends on the weakest of those?

## Findings

- **Agents skip and summarise what they are told to read.** The operator has repeatedly had
  agents admit they did not read `AGENTS.shared.md` and relied on a subagent's summary
  instead. Corroborated in-session on 2026-07-19: a landscaper logged that it "treated a
  subagent's summary of `lg-cec-protocol.md` as sufficient instead of reading the document."
- The distinction is PUSH vs PULL. Content already in context (system prompt, hook injection)
  cannot be skipped. Content an agent must choose to open can be skimmed, deferred, or
  delegated to a subagent that returns a lossy summary — and the loss is silent.
- Skills sit in between: intact when invoked, but invoking is itself a pull.
- Volume makes it worse: the longer the file, the likelier it is summarised. So adding more
  instruction to fix instruction-skipping is self-defeating (operator).
- Compliance is a separate failure from delivery: an agent may read an instruction and
  override it anyway. Gates bind where instructions do not — especially gates that withhold
  something the agent needs.

## Proposal

Full review of skill injection and agent-file injection: establish which channels deliver
intact, measure how much load-bearing doctrine currently rides the weak ones, and re-home
what matters onto push channels or gates. Getting more pressing as the rule set grows.

## Testing

To agree when bloomed — expected shape: evidence that a given instruction was actually in an
agent's context (not summarised) at the moment it mattered.

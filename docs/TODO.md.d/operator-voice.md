- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

- None; scope round pending.

## Questions

- Confirm the two languages (presumed French and English) and whether the
  voice differs per audience (personal mail vs disclosure mail vs PR/review
  prose) or is one voice everywhere.
- Source material: which of the operator's real writing (sent mail, PRs,
  comments, docs) may be mined to derive style, rhythm and vocabulary — and
  does that wait for [[corpus-indexing]] or start from a hand-picked sample?
- Enforcement shape: guidance the agent reads (extend `skills/writing`), a
  review pass over outbound text, or both?

## Findings

- Operator intake (2026-07-24): current writing artifacts miss his writing
  STYLE, RHYTHM and VOCABULARY, in the two languages he writes email in.
  This is not an email-skill concern: it applies to any prose written under
  his name — pull requests, comments, email, everything outward — and must
  represent what he normally does, so nothing signed with his name reads as
  written by a robot with the vocabulary of a four-year-old.
- The existing `writing` skill governs the right surface set (commit bodies,
  PR descriptions, issue/review comments, sidecar and CHANGELOG prose) but
  only enforces plain-English-over-shorthand — it carries no voice.
- The writing-emails bloom round (2026-07-24, on f/psychometric-discovery)
  explicitly deferred "voice/tone/style content" as unmeasured; that
  deferral resolves HERE, not in the email skill's plan phase — cross-link
  at ingest.
- Same principle as the sent-AS-me identity ruling: identity covers what an
  agent may claim in his name; this task covers how it must SOUND.

## Proposal

(to shape at its scope round) The operator's voice — style, rhythm,
vocabulary, per language — captured as a durable artifact extending
`skills/writing`, loaded wherever an agent authors prose that carries his
name.

## Testing

To agree when scoped — expected shape: side-by-side reads of agent-authored
text before/after, judged by the operator as passably his.

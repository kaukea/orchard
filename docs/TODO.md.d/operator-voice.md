- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

- None; scope round pending.

## Questions

- Confirm the two languages (presumed French and English) and whether the
  voice differs per audience (personal mail vs disclosure mail vs PR/review
  prose) or is one voice everywhere.
- ~~Source material: which of the operator's real writing (sent mail, PRs,
  comments, docs) may be mined to derive style, rhythm and vocabulary — and
  does that wait for [[corpus-indexing]] or start from a hand-picked sample?~~
  Answered (operator, 2026-07-24): mine NOW — git history plus historical
  email; do not wait for the corpus.
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

- Fingerprint derivation DISPATCHED (2026-07-24 evening, background
  subagent, operator-ordered): sources are hand-written git commits across
  the fleet (agent-authored commits excluded via the `Agent:` /
  `Co-Authored-By` trailer filter) and a time-spread sample of sent mail via
  the Gmail connector. Classification is derived from the data — expected
  registers professional/formal/casual across his two languages — one
  compact fingerprint per class, distilled once so later use costs almost
  nothing. Outputs stage in the UNCOMMITTABLE channel
  (`.git/the-works/operator-voice/`): email-derived exemplars are flagged
  PRIVATE and never enter git; the operator gates what the eventual skill
  ships.

- Mining round COMPLETE (2026-07-24 evening; deliverables staged in
  `.git/the-works/operator-voice/`: inventory, four fingerprints, classifier,
  method — email-derived exemplars flagged PRIVATE). Sampled: 1,018
  hand-written GitHub commits 2009–2025, 509 issue comments, 13 PR bodies,
  15 pre-agentic local commits, but only 8 substantive sent emails — the
  connected Gmail mailbox is the NEW secure@ identity (9 sent threads, all
  July 2026); no historical or personal mail is reachable through it.
- Classes derived: `commit-en` HIGH confidence (subject-only 93.5%, mixed
  verb moods, typos shipped unamended) · `discussion-en` HIGH (verdict-first,
  median 20 words, em-dashes in only 1.6% of comments — a strong
  anti-Claude tell) · `casual-fr` LOW (n=1: tutoiement, accents dropped at
  speed) · `formal-fr` CONTAMINATED (assessed agent-drafted — its exact
  phrases co-occur in captured transcripts; kept only as an
  operator-approved template, never as hand voice). No authentic
  formal-English class was derivable.
- Contamination findings (method-level, reusable by [[corpus-indexing]]):
  trailer absence is NOT proof of hand authorship — 743 trailer-free
  fleet-era commits matching the house gitmoji style were excluded
  wholesale; the agentic era begins ~Dec 2025, not June 2026
  (`Co-authored-by: Junie` commits caught in older repos); perfect
  typography in the formal-French letters is itself the assistance
  signature.
- OPEN: French voice and genuine email voice need a real historical-mail
  source (Thunderbird account or a local archive) — the operator picks the
  source; see session notes.

## Proposal

(to shape at its scope round) The operator's voice — style, rhythm,
vocabulary, per language — captured as a durable artifact extending
`skills/writing`, loaded wherever an agent authors prose that carries his
name.

## Testing

To agree when scoped — expected shape: side-by-side reads of agent-authored
text before/after, judged by the operator as passably his.

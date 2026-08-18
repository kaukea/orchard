---
name: writing-prose
description: Use whenever authoring prose a human will read outside the session — commit bodies, PR descriptions, issue and review comments, sidecar and CHANGELOG text. Enforces plain English over session shorthand — full sentences, jargon expanded, written for a reader with zero session context.
categories: [authoring]
metadata:
  tags: [writing, prose, english, commit, pull-request, comment, jargon]
  share: github
---

# Intent (writing)

Agents compress; readers do not share the session. Everything written into a durable,
human-facing artifact is read later — often months later, often by the operator —
without the conversation in anyone's head. This skill makes those artifacts read as
English rather than as leaked session notes.

## Checklist

- [ ] Full sentences — a subject and a verb; no fragment chains
- [ ] Every insider term expanded on first use, or replaced with the plain word
- [ ] Passes the stranger test: readable with zero session context
- [ ] References anchored to artifacts (issue number, decision, file), not to
      conversation moments
- [ ] Emoji only where a format mandates one (gitmoji subject prefix)

## Rules

- **Write for the stranger.** The reader has not seen the session, the plan round, or
  the courier. If a sentence only makes sense to tonight's participants, rewrite it.
- **Full sentences.** Fragments chained with semicolons and dashes are notes, not
  writing. Titles and subjects may compress; bodies may not.
- **Expand or drop insider vocabulary.** "hop", "gate", "cold-start", "frozen", "the
  WHAT/the HOW" — either say what the term means where it appears, or use the plain
  phrase instead. A term of art earns its place only after it is introduced.
- **Compression is not concision.** Concision removes what adds nothing; compression
  removes the grammar the reader navigates by. Cut ideas, not connective tissue.
- **No session deixis.** "this once", "as ruled earlier", "per the round" — anchor to
  the artifact instead: "issue #34", "Decision-032", "the operator's review comment".
- **The operator may override any of this per session.**

## Worked example (incident, 2026-07-21)

PR #36 shipped this body:

> Built by the cloud path (plan + build hops on issue gates); tests green in the
> build run; close docs authored on the branch.

Three fragment chains of session shorthand — "hops", "gates", "close docs" — opaque to
any reader outside that night's session. What it should have said:

> This change was planned and built by the cloud automation, driven by the operator's
> gate comments on issue #34. The tests passed in the build run. The closing
> documentation was written on the feature branch.

Same facts, three sentences, no insider vocabulary.

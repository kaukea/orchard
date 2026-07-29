---
name: occasions
description: MUST be read by any agent that communicates through its courier — the fixed list of OCCASIONS on which it speaks: lifecycle open and two-event close, status changes (including the two ruled wait words), delegation around a sub-agent, outcome, and requests. Teaches WHEN, never HOW — no verb, subject, address, path, or JSON; the courier owns the mechanism entirely.
roles: [general]
metadata:
  tags: [occasions, status-words, questioning-vs-waiting, lifecycle-two-events, delegation, outcome, request, courier-occasions]
  share: github
---

# Intent (occasions)

Every agent that can communicate knows two things: plain language, and the occasions on which it
is expected to speak (`docs/TODO.md.d/observability.md`: "it knows the occasions, never the
mechanism"). This skill is the second half — the fixed list of WHEN. It never says HOW: no verb,
subject, address, path, or JSON appears below, and none belongs in a future edit of this file
either — the mechanism is the courier's alone. Ask your courier for each occasion in plain
language; it translates.

## Checklist

- [ ] Told your courier you are starting, once, right after it is loaded
- [ ] Posted a status word only when your activity actually CHANGED — never a repeat
- [ ] Used `questioning` while an answer you asked for is outstanding (the operator's own
      done-gate included), `waiting` while you are waiting on another agent — never the other
      word for the other case
- [ ] Told your courier when a sub-agent is planned, when it is dispatched, and when it returns
- [ ] Announced you are ending BEFORE releasing anything, then announced you have ended, with
      your outcome, as the very last act
- [ ] Asked, rather than assumed, whenever you needed an answer — the operator included

## The occasions

**Lifecycle — the open, and the two-event close.** Tell your courier you are starting as your
first act. Ending is always TWO occasions, never one: tell it you are ending BEFORE you release
anything you depend on (courier, monitors, sub-agents, temporary files); only once everything is
actually released do you tell it you have ended, carrying whether you succeeded or failed as the
very last thing you say. An agent that skips the first announcement, or never reaches the second,
is a lost handover to anyone watching.

**Status — one or two words, on change only.** Tell your courier your current activity in a word
or two, in plain language, whenever it actually changes — never repeat an unchanged word; a
repost is noise, not a heartbeat.

Two of those words are RULED and each carries a specific meaning — use the one that is actually
true, never the other for the other case:

- **`questioning`** — an answer you asked for is outstanding. This includes the operator's own
  gate: an agent waiting at its done-gate for the operator's word is waiting on an answer, and
  says `questioning`.
- **`waiting`** — you are waiting on another AGENT, not on an answer to a question you asked.

**Delegation — around a sub-agent.** Tell your courier when you plan a piece of work you intend
to hand to a sub-agent, when you actually hand it off, and when it comes back — three distinct
moments, not one.

**Outcome — the last act.** When your work is over, tell your courier whether it succeeded or
failed. This rides alongside the second lifecycle announcement above, not as a separate occasion.

**Requests — whenever you need an answer.** Asking a question, of a peer or of the operator, is
ordinary and normal — you are still working, not stuck. The operator is a recipient like any
other; there is no separate class of "asking the operator" versus asking anyone else. When asked
to carry the operator's own words to another agent, relay them verbatim and say so plainly — do
not paraphrase them into your own voice.

## Rules

- **WHEN, never HOW.** No verb, subject, address, path, or JSON belongs in this file. If a future
  edit is tempted to add one, it belongs in the courier's own definition instead, not here.
- **Nothing here is invented.** Every occasion and every word above is a standing ruling
  (`docs/courier-wire.md`, `docs/TODO.md.d/bus-addressing.md` §Decision entries) — an occasion
  this skill does not name is not one an agent invents on its own; ask your courier in plain
  language and let it say if the occasion doesn't exist yet.
- **On change only.** A status word repeated unchanged, or a lifecycle/outcome announcement made
  twice, costs a wake for no new information.

- created: 2026-07-25
- created_by: gh-ingest
- created_during: interactive

## Blockers
- None known yet.

## Questions
- Ingested from GitHub issue #226 — needs triage: type, component,
  urgency, scope.

## Findings
- Filed on GitHub (https://github.com/kaukea/orchids/issues/226); original body preserved below.

#gates #keywords #relay #ui #operator #make-it-so

Operator ruling (2026-07-22): the operator-facing build-gate phrase becomes
**"NO NO THAT WAS NOT A QUESTION"** (variants: THIS for THAT; short form
"NO NO") — the architect's final plan summary is answered by objecting that
it needed asking at all. Implementation is a TRANSLATION AT THE UI
BOUNDARY, per the operator's scope guidance: every operator-input surface
(orchestrator pane relay now; the question/gate popup when it lands) maps
the phrase to the fleet's INTERNAL protocol string `MAKE IT SO`, which is
unchanged everywhere else — defs, bus matching, in-flight builds. A
directly-typed `MAKE IT SO` still works. `THAT IS ALL` is untouched.

## [2026-07-22, addendum to Decision-057] ENGAGE joins the build-gate phrases
#gates #keywords #engage

Operator addendum, minutes after Decision-057: **`ENGAGE`** is also an
accepted operator build-gate phrase, translated at the same boundary to the
internal `MAKE IT SO`. The accepted set is now: the full NO-NO phrase
(THAT/THIS), `NO NO`, `ENGAGE`, and the internal string itself.

## [2026-07-22, second addendum to Decision-057] The glacial-pace phrase joins the set
#gates #keywords

"BY ALL MEANS, MOVE AT A GLACIAL PACE" is the third operator build-gate
phrase — approval by sarcasm, completing the operator's dictation
("complement ENGAGE with…"). Same boundary translation to `MAKE IT SO`.
Accepted set: the NO-NO phrase (THAT/THIS) · NO NO · ENGAGE · the
glacial-pace phrase · the internal string itself.

## [2026-07-22, third addendum to Decision-057] The corrected keyword table; ENGAGE is cloud-only
#gates #keywords #engage #cloud

Operator correction, same day: ENGAGE is a SEPARATE keyword reserved for the
CLOUD path — the explicit authorization word for dispatching a cloud run
(Decision-042); it is not a build-gate synonym and never starts local
coding. The corrected table: coding START = internal MAKE IT SO, operator
phrases "NO NO THAT WAS NOT A QUESTION" (THIS/THAT; simply "THAT WAS NOT A
QUESTION"; "NO NO") and "BY ALL MEANS, MOVE AT A GLACIAL PACE" (simply
"MOVE AT A GLACIAL PACE"). Coding END = THAT IS ALL, unchanged, no
synonyms. Keywords to become configurable in a future task.

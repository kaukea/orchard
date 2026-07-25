# Popup finishing: the operator's round-2 requests, finished and live-proven

- created: 2026-07-22
- created_by: Sebastien Lambla

## Blockers

- None.

## Questions

- None — the operator specified each item during the sidebar-polish live
  rounds (recorded there as item 12g); this task exists because the close
  flagged them "unit-tested, no dedicated live pass" instead of handing
  them over as follow-ups.

## Findings

- Process gap worth telemetry: requested-but-unverified work must surface
  at close as FOLLOW-UP TASKS, never as a coverage footnote inside a
  "all items built" result. The operator had to ask where his requests
  went.
- The courier envelope already carries title/summary fields (observed in the
  round-2 trial relays); what lacks proof is the RENDERED behaviour.

## Proposal

Finish and LIVE-PROVE, with the operator pressing keys, each of:
1. **Multi-select mode** — digits toggle membership with visible `[x]`/`[ ]`
   redraw, a confirm key commits; single-select stays instant-on-digit;
   the two modes visually distinct at a glance.
2. **Escape = continue-the-conversation** — a distinct sentinel over the
   courier; the asking agent treats it as "pause and keep talking", NEVER as
   declined/cancelled (the AskUserQuestion dismissal failure mode must not
   recur).
3. **Always-available gate keywords** — the popup special-cases the gate
   words regardless of the question, honouring the Decision-057 operator
   phrase table (the NO-NO and glacial-pace phrases, THAT IS ALL), each
   broadcasting its gate signal directly.
4. **Title + short summary** rendered above the question text.
5. **Pretty and colored** — no more plain uncolored text.
6. **Size to content** — never a fixed fraction of the screen.

## Testing

One live operator session driving every path on the real popup: a
multi-select toggled and committed, an Escape that resumes conversation at
the asker, a gate phrase spoken through the popup landing as its gate
signal, title/summary/colors/sizing eyeballed. Nothing closes on unit
tests alone — that is the gap this task exists to correct.

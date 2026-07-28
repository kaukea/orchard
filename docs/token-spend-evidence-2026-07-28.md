# Token spend evidence — measured 2026-07-28

Recorded at the operator's instruction for an account migration. Every figure
below is read directly from the local Claude Code transcripts under
`~/.claude/projects/*/*.jsonl`, summing the `usage` block of each assistant
message: `input_tokens + output_tokens + cache_creation_input_tokens +
cache_read_input_tokens`. No estimation, no sampling, no extrapolation.

Transcripts are per machine and per project directory. They cover local Claude
Code sessions only; anything run elsewhere is not in this dataset.

## Headline

**16.74 billion tokens across all projects on this machine.**
**2.65 billion of them in `serialseb/orchids` alone (15.8%), over 14 days.**

**97.3% of every token spent was a cache READ** — re-reading context that
already existed. Output, the only part that produced anything, was **0.6%**.

## Spend by kind, all projects, all history

| kind | tokens | share |
|---|---|---|
| cache read | 2,580.1M | 97.3% |
| cache write | 56.0M | 2.1% |
| output | 16.2M | 0.6% |
| input | 0.2M | 0.0% |

(Figures in this table are for `orchids`; the same shape holds machine-wide.)

The ratio is the finding. For every 1 token of output produced in this project,
roughly 160 tokens were re-read. Cost here is not driven by how much work was
done — it is driven by how many times the accumulated context was re-sent.

## Per-project totals (this machine, all history)

| project | tokens | share |
|---|---|---|
| `rescue` | 3,459.1M | 20.7% |
| **`src/serialseb/orchids`** | **2,652.4M** | **15.8%** |
| `src/SafeKeepIt/SignMc` | 1,280.6M | 7.7% |
| `home/sudoku` (root) | 952.1M | 5.7% |
| `src/gemalto` | 648.5M | 3.9% |
| `fixfiletransfer` | 640.5M | 3.8% |
| `rescue/digsig-cert-reissue` | 571.3M | 3.4% |
| `src/serialseb/seb-tv` | 513.3M | 3.1% |
| `orchids/.claude/worktrees/cloud-a…` | 495.6M | 3.0% |
| `src/serialseb/signmc` | 484.9M | 2.9% |
| `src/serialseb/serialseb-voice` | 403.6M | 2.4% |
| `research` | 359.7M | 2.1% |
| **all projects** | **16,740M** | **100%** |

Note that an `orchids` worktree appears as its own project line (495.6M); the
true orchids-family total is therefore above the 2,652.4M headline.

## Per-day, `orchids` only

| date | tokens | by model |
|---|---|---|
| 2026-07-14 | 146.5M | opus-4-8 89M, fable-5 58M |
| 2026-07-15 | 496.0M | opus-4-8 363M, fable-5 133M |
| 2026-07-16 | 413.2M | opus-4-8 349M, fable-5 64M |
| 2026-07-17 | 186.8M | opus-4-8 147M, fable-5 40M |
| 2026-07-18 | 106.9M | fable-5 107M |
| 2026-07-20 | 65.2M | fable-5 65M |
| 2026-07-21 | 58.8M | fable-5 59M |
| 2026-07-22 | 294.1M | fable-5 292M, sonnet-5 2M |
| 2026-07-23 | 9.0M | fable-5 9M |
| 2026-07-24 | 294.0M | fable-5 239M, opus-4-8 55M |
| 2026-07-25 | 245.9M | fable-5 216M, opus-5 30M |
| 2026-07-26 | 125.5M | fable-5 126M |
| 2026-07-27 | 77.0M | opus-5 53M, fable-5 24M |
| 2026-07-28 | 133.6M | fable-5 68M, opus-5 66M |

## By model, `orchids`, all history

| model | tokens |
|---|---|
| claude-fable-5 | 1,499.9M |
| claude-opus-4-8 | 1,002.7M |
| claude-opus-5 | 148.0M |
| claude-sonnet-5 | 1.8M |

**94% of this project's spend was on the two most expensive tiers** (Fable 5 and
Opus 4.8). Sonnet accounts for 1.8M — under one tenth of one percent — despite
several agent roles being pinned to it in their definitions.

## Heaviest individual sessions, `orchids`

| tokens | session |
|---|---|
| 574.7M | af56c9b9-1912-4f26-b85e-5a7c4d0e43e6 |
| 311.9M | d86acb68-287a-4406-8f6f-dc0eee0c28c7 |
| 284.7M | 1709158c-e6d7-49f2-9b5d-e244827672e8 |
| 217.9M | cc895f40-f9d6-404e-aa2e-66bdf2b8feda |
| 155.8M | 9790baec-b44e-4894-a2e6-d5fde3ab3afe |
| 138.4M | ff6384b1-5cab-478a-9ec0-0dc3f5136914 |
| 118.0M | 1e6b83cc-f7b1-4010-a66a-6be5951d21aa |

41 sessions carry usage. **One session cost 574.7M tokens — 22% of the entire
project's 14-day spend.** Seven sessions account for over 1.8B of the 2.65B.

## Mechanism

Cost scales as *context size × number of turns*, and today neither is bounded.

Worked example from the session that measured this, on 2026-07-28:

- baseline context at session start: the system prompt alone carries 45 skill
  descriptions, 15 agent definitions and 88 deferred tool schemas, before any
  file is read
- boot then loads `AGENTS.shared.md` (10KB) and `docs/TODO.md` (31KB)
- by call 266 the context had reached **224k tokens**
- every one of those 266 calls re-read the whole context

That single session: 41.2M tokens, of which 35.9M were cache reads and 295k were
output. Turn 260 pays again for everything that happened in turns 1–259, so a
long session is not marginally worse than a short one — it is quadratically
worse.

## Two defects found while measuring

1. **A `/model` switch does not change a running session.** On 2026-07-28 the
   operator set the model to Opus 5 and instructed that Fable not be used. The
   live process (`--session-id 0c374ecc…`) continued running with an explicit
   `--model claude-fable-5` flag, because the flag was fixed when the process was
   resumed. Every turn after the instruction was still billed at the Fable tier.
   Only restarting the session applies the change.

2. **Two agent definitions pin the most expensive tier in frontmatter** —
   `agents/bloomer.md` and `agents/gardener.md` both carry
   `model: claude-fable-5`. `tools/bloomer-launch.sh:50` invokes
   `claude --agent bloomer` with no model flag, so a script-launched bloomer
   takes the pinned tier regardless of any session-level choice.

## Standing operator ruling not yet enforced

A budget ruling was dictated on 2026-07-28 and is staged, unpromoted, in
`docs/TODO.md.d/sidebar-teamwork.md` (`## Decision entries`): every subagent
launch must carry a written token budget, the budget is a checkpoint that stops
and reports rather than a ceiling to run past, and a budget is never guessed
from what previous over-running agents happened to spend. It was staged after
two sowers each approached 300k tokens on a single assignment, against roughly
20–24k for a courier over an entire day.

Nothing in the tooling enforces it today.

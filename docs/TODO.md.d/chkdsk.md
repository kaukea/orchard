- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# chkdsk: sweep the whole orchid system for orphans and errors, detect and correct

## Blockers

None. Every surface it would check exists today and is readable.

## Questions

1. **Detect only, or detect and correct?** He said *"detect and correct them"*, so
   correction is in. The open part is which corrections an agent may apply on its own.
   A stale gitignore entry and a missing timestamp are mechanical; a board badge that
   disagrees with git could be either side being wrong, and picking one is a judgement.
   *Recommendation: correct the mechanically unambiguous, report the rest with a proposed
   fix. The write-lock from `decisions-restructuring` applies — anything touching an
   operator decision is proposed, never applied.*

2. **Skill, tool, or both?** A skill is instructions an agent follows; a tool is a script
   that runs and exits. `board_lint.py` already exists as the tool half for one surface.
   *Recommendation: both — a script that finds what is mechanically findable and exits
   non-zero, and a skill that tells an agent how to interpret and act on what it reports,
   including the parts no script can judge.*

3. **When does it run?** On demand only, at close, at gardener boot, or on a hook. Note
   that `board_lint.py` exists, works, and found a real error the moment it was run today
   — because nothing runs it automatically. A checker nothing invokes is the very defect
   class this task is about. *Recommendation: decide this before building, not after.*

4. **This repository only, or the fleet?** He said *"globally on the whole repository"*,
   which reads as this repo entire rather than across repos. The sidebar already reads a
   cross-repo registry at `~/.config/orchids/sidebar-registry.json`, so the fleet-wide
   version is reachable later. *Recommendation: this repo first; fleet-wide as a follow-up.*

## Findings

**Named after the Windows tool** (`chkdsk`, Windows 3.x / 95) — a whole-volume scan that
finds orphaned and inconsistent structures and repairs them. The analogy is exact: the
orchid system is a set of cross-referencing artifacts with no referential integrity
enforced anywhere, and the equivalent of lost clusters and cross-linked files accumulates
in it silently.

**The evidence below was collected in a single morning, without looking for it.** Every
item was found incidentally while doing other work; none was reported by any check. That
is the argument for the task — not that defects exist, but that nothing finds them.

1. **Dangling cross-references in sidecar prose.** Five sidecars defer scope to
   `metronome`, which has no task, no sidecar and no id. `board_lint.py` validates the
   `~related` and `⊘blocked_by` references on the board badge, but not names appearing in
   sidecar prose, and not `[[wikilink]]` forms. So a deferral written as prose points
   nowhere and nothing notices.

2. **Board disagreeing with git.** `close-family-fakes` was merged at `dd9586a` and
   tagged `archive/close-family-fakes` on 2026-07-27; its board badge still reads
   `todo · critical · plan-ready`. Nothing reconciles the board against the refs.

3. **Un-ingested closed streams.** `.git/the-works/close-family-fakes_closed/` has been
   sitting since 2026-07-27 with decisions pending promotion. The hook announces closed
   streams; nothing escalates one that is never ingested.

4. **Orphaned tooling — built, tested, documented, wired to nothing.**
   `orchard-question-broker.py` carries 60 tests, is listed in `ARCHITECTURE.md`, has a
   mount script, and is invoked by no hook and no agent. It had never run, so every
   agent's `courier.py ask` path was silently dead — and the failure surfaced only as a
   charter deviation in one landscaper's log.

5. **Stale ignore entry after a rename.** `.gitignore` carried
   `.claude/orchestrator-mode.local` for a file that had been renamed to
   `gardener-mode.local` when the role was renamed. The new name was ignored by nothing
   and dirtied the working tree in every session since, against a rule requiring the
   gardener to keep it clean.

6. **Structural corruption inside a committed artifact, undetected across three
   commits.** A scripted edit spliced one section of a sidecar into another and destroyed
   two more; three further commits were made on top before anyone looked at the file's
   shape. `board_lint.py` checks that a sidecar FILE exists; nothing checks that its five
   fixed sections are present and in order, though `AGENTS.files.md` §Sidecar defines
   exactly that.

7. **A register that does not conform to its own written format.** In `docs/decisions.md`:
   eleven entries carry a date with no time though the spec makes it required; exactly one
   heading is struck through against twenty-five lines discussing supersession; and
   Decision-115's two-date heading contract is honoured by one entry out of 115. See
   `decisions-reviewing`.

8. **Operator-authored files sitting untracked for a day.** Two specification documents
   in `docs/SPECIFICATIONS.md.d/` were neither committed nor ignored, and would have been
   lost to any clean operation.

9. **The one checker that exists is not run.** `board_lint.py` reported a real error on
   its first invocation today. It is 131 lines and covers the board index alone: badge
   field count and vocabulary, taxonomy membership, sidecar file existence, and badge
   reference resolution. Everything in items 1–8 is outside its reach.

**Scale for sizing:** 145 tasks on the board, 117 decision entries, 19 tools, 11 agent
definitions, and the uncommittable stream directory.

## Proposal

A whole-system integrity check for orchids — `chkdsk` — that sweeps every artifact and
the relationships between them, reports what is orphaned, inconsistent or malformed, and
corrects what can be corrected unambiguously.

The premise is that the orchid system is a set of artifacts that reference each other
across file boundaries — board to sidecars, sidecars to each other, decisions to tasks,
agents to skills, tools to hooks, streams to ingests, git refs to board status — with
referential integrity enforced at exactly one of those boundaries and by nothing at the
rest. Defects therefore accumulate silently and are found by accident, which is how all
nine findings above were found.

### Candidate check families

Drawn from the evidence; the reviewer is expected to add to it rather than treat it as
the list.

- **Orphans** — sidecars with no board row; board rows with no sidecar; tools invoked by
  nothing; agent definitions no role dispatches; skills nothing references; streams never
  ingested; decisions referencing tasks that do not exist.
- **Dangling references** — names and wikilinks in prose that resolve to nothing, in
  sidecars, decisions, agent definitions and skills alike, not only on badge fields.
- **Desync between the board and reality** — a task marked open whose branch is merged
  and tagged; a task marked done with a live branch or worktree; a `gh#` badge pointing at
  a closed or missing issue.
- **Structural conformance** — each artifact against its definition in `AGENTS.files.md`:
  the sidecar's five fixed sections in order, the decision heading and mandatory keyword
  line, the metadata header fields.
- **Wiring** — a tool that exists and is documented but that no hook, agent or skill
  invokes; a hook registered for a script that is absent.
- **Ignore and delivery hygiene** — ignore entries for paths that no longer exist,
  tracked files that should be ignored, untracked files that should be tracked.

### In scope

- The check families above and whatever the build adds to them.
- The correction path, and the boundary between what is corrected and what is reported.
- How and when it is invoked — see Question 3, which must be settled before the build.
- This repository in full.

### Out of scope

- Cross-repo sweeping; a follow-up once this one works.
- Re-litigating the content of anything it finds — `chkdsk` reports that a reference
  dangles, not what the reference should have said.
- The decisions register's own content and provenance audit; that is
  `decisions-reviewing`, and `chkdsk` should check the register's FORM only, so the two do
  not overlap.

## Testing

To be agreed before the build. Proposed method: **the nine findings above are the test
corpus.** They are real, they are all present in the repository's recent history, and none
of them was found by any existing check.

`chkdsk` is run against the repository at a commit where each defect was live, and must
find it. A check that reports eight of nine has a named, understood gap rather than an
unknown one. Conversely it is run against the repository after those defects are fixed and
must report them clean — a checker that cries wolf is one nobody runs, which is item 9's
failure mode arriving by a different route.

Its corrections are proven by applying them to a scratch copy and re-running the check to
green, with the diff read by the operator before any correction path is enabled on the
real tree.

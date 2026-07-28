- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# Board grammar: two levels, two badges, One-offs — Decisions 117 and 118 built

## Proposal

Task of feature **Feature creation**. Implement Decision-117 (the board is two
levels with two badge grammars, One-offs is the empty feature) and Decision-118
(a feature's sidecar is a container file with segregated per-task sections).

Scope:
- `AGENTS.files.md` §TODO and §Sidecar rewritten to the ruled shapes, including
  the operator-accepted render in the features-first-class sidecar §2.
- `tools/board_lint.py` knows exactly three line shapes: feature line, task line,
  the single One-offs bucket. Feature badge: id, gh# parent issue, touched
  components, derived task progress. Task badge: today's six fields.
- `docs/TODO.md` migrated: existing lines regrouped under feature lines or the
  One-offs bucket, with a dated `migrations/` entry shipped in the same branch
  (the board is a managed artifact being reformatted).
- Feature container sidecars per Decision-118; one-offs keep their files.

Out of scope: branch/tag naming (branch-and-close), the GitHub projection
(github-projection), the team runtime.

### HOW — implementation plan against the real files

**1. `tools/board_lint.py` (currently one shape at every depth, `:70-79`, `:96-112`):**
- `parse_board` grows a feature-line regex distinct from the task-line regex.
  Proposed feature badge shape, matching the accepted render (features-first-class
  §2): `` `{#<id>}` `❘gh#<n>❘` `⟶ <comp>, <comp>, …` `` plus a derived progress
  suffix (`◾◾⬜ 2/3`, computed from child task statuses — never authored).
- Task-line regex under a feature keeps today's six-field badge but the delimiter
  in the accepted render is `❘` (pipe-with-serif), not `·` — confirm this is a
  deliberate second grammar, not a transcription slip (folded into the Question
  below).
- The literal `One-offs` bucket (`📦 One-offs`) is a fixed, badge-free, always-
  present heading line; one-off tasks keep the CURRENT six-field `·`-delimited
  badge unchanged (today's shape survives untouched for one-offs — no dual
  parsing burden there).
- `has_child`/`is_leaf` logic (`:87-93`, `107-112`) collapses: depth is now
  binary (feature / task, or bucket / task), so the parent-must-have-empty-area
  check becomes "feature lines never carry `area`" and "task lines always do" —
  a simpler, non-recursive check.
- Progress derivation reads each feature's child task `status` fields (`todo` /
  `functional` / `done` / `cancelled`) and renders `◾`×done `⬜`×remaining — pure
  function over already-parsed tasks, no new state.
- Sidecar-existence check (`:113-114`) applies once per feature (its container
  sidecar) and once per task id (its `## Task` anchor exists inside the
  feature's container, OR the one-off's own file exists) — two different checks
  replacing the current uniform one.

**2. `AGENTS.files.md` §TODO** — replace the single nested-bullet grammar
(`:19-29`) with the three-shape grammar above; §Sidecar (`:123-186`) gains a
"container sidecar" subsection: one file per feature holding shared frontmatter
+ N `## Task <id>` sections, each internally following the existing five-section
shape (Blockers/Questions/Findings/Proposal/Testing) unchanged — only the
container wrapper and per-task write-segregation (Decision-118) are new.

**3. Migration script** (`migrations/2026-07-28-board-grammar.md` + a one-shot
script, not hand-edited) — walks today's flat/nested `docs/TODO.md`, groups
existing task lines under the proposed features below (see Question 1), emits
the new three-shape file, and a count-based round-trip check (every pre-
migration task id appears exactly once post-migration, scripted, per Testing).

### Proposed grouping (answers Question 1 — needs operator confirmation)

Reading today's board (`docs/TODO.md`), the items that already carry nested
children are the natural feature candidates — everything else becomes a leaf
under the `One-offs` bucket. Proposed:

| feature id (proposed) | gh# | current parent line | children folding in |
|---|---|---|---|
| `feature-creation` | — | *(new)* | features-first-class, board-grammar, branch-and-close, github-projection |
| `orchard` | gh#25 | Orchard: the fleet workbench | orchard-summary, orchard-view, orchard-launch, tmux-topology, fleet-sidebar (+ its 9 children: cloud-event-feed, sidebar-fixes, sidebar-polish, popup-finishing, sidebar-spacing-and-glyphs, install-detecting, sidebar-titling, sidebar-empty-rows, popup-adopting, pretty-sidebar), session-naming, handover-contract, cloud-architect (+ its 5 children), app-identifying, branch-protecting, merge-ordering, merge-queue-investigating, launcher-subagent, delta-commenting, routine-triggering, diagnostic-channel, psychometric-discovery (+ its 3 children: bloom-administering, bloomer-repointing, bloom-subset-posterior) |
| `github-board-sync` | gh#13 | Cross-repo board view | sync-ingest-failing, field-projecting, decision-projecting, component-field-declaring, ingest-echo-loop, sync-automating |
| `bus-finishing` | gh#264 | Bus finishing | bus-relay, fanout-cutover, cross-repo-bus, bus-close-cleanup, bus-singleton |
| `close-family-fakes` | gh#263 | Close-family fakes | window-closing-owning, zombie-revival, sidebar-witnessing |
| `rules-tuning` | — | Rules tuning | telemetry-collecting, digest-identity, digest-formatting, telemetry-mining, prompt-optimizing, rules-abtesting |
| `decisions-restructuring` | — | Decisions restructured | decisions-reviewing |
| `role-delivery` | gh#16 | Role-based delivery | role-dag-frontmatter, agents-first-class, skill-renames-and-splits, skill-terseness-pass |

Everything else (Publication section, remaining Process machinery leaves like
groundskeeper-verify-hardening / close-permission-blocking / chkdsk /
injection-integrity / message-bus family not already folded above / Skills
section / the entire "Future (dot.ai)" section, etc.) has no existing children
and folds flat into `One-offs`, keeping its current six-field badge untouched.

Recommendation: accept this grouping as-is for the first migration pass —
it's mechanical (only items that are ALREADY nested become features, nothing
new is invented) and matches Decision-117's "don't invent features where there
are none." Renaming/re-scoping which cluster deserves feature identity can
happen in a later bloom round once the shape exists.

## Questions

Both prior open questions are resolved — verified against the live tree in
this bloom round (2026-07-29), no operator input needed:

1. **Badge delimiter, resolved: `❘` stands.** Re-checked the accepted render
   in `features-first-class.md` §2 (lines 38-42): every feature line and every
   nested task line under a feature uses `❘` consistently (`{#oauth-auth}
   ❘gh#40❘ ⟶ …`, `{#refresh-tokens} ❘seeded❘feature❘m❘auth❘gh#71❘`). The lone
   `·` near that file (line 119) is prose separating enum values in a
   sentence, not a badge delimiter — no conflicting precedent exists. `❘` is
   the deliberate second grammar; closed as recommended.
2. **Grouping table, resolved: accept as-is.** Re-scanned `docs/TODO.md` live:
   63 nested bullet lines, 89 top-level lines, and the 8 candidates in the
   table above remain the only lines with children — the "convert only
   already-nested items" heuristic still covers the whole board with no
   ambiguous middle case. No drift since the table was drafted. Closed as
   recommended.

## Findings

The full inventory of feature==task assumptions is in the feature sidecar
(`features-first-class.md` §Findings), with `board_lint.py` line references.
Confirmed against the live tree: `docs/TODO.md` has 8 `##` functionality
headings and ~150 board lines; only 8 lines currently carry nested children
(the candidates in the grouping table above) — everything else is already a
leaf, so the "convert only nested items" heuristic covers the whole board with
no ambiguous middle case.

## Testing

`board_lint.py` clean over the migrated board (three shapes only, glossary
lints unaffected). Round-trip check: script every pre-migration task id against
post-migration ids — same set, each exactly once (scripted count, not
eyeballed). Manual spot-check: the `orchard` feature (largest candidate, 20+
descendants) renders with correct derived progress and touched-components list.

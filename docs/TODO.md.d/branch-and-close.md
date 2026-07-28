- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# Branch and close naming: f/<feature>/<task>, archive tags to match — Decisions 116 and 120 built

## Proposal

Task of feature **Feature creation**. Implement Decision-116 (short-lived task
branches off main named `f/<feature>/<task>`, no feature branches ever) and
Decision-120's tag half (archive tags mirror branch names,
`archive/<feature>/<task>`; changelog stays flat between releases).

Worktree directory scheme (recommendation, Question 1 below): NESTED,
`.claude/worktrees/<feature>/<task>`, mirroring the branch name segment for
segment. Every file below assumes this pending the operator's confirmation;
if flattened is chosen instead, every `<feature>/<task>` worktree path becomes
`<feature>--<task>` and `tools/courier.py`'s split logic changes from
`.parent.name`/`.name` to a `str.split("--", 1)` — everything else in this plan
is unaffected.

File-by-file plan:

- **`skills/workflow/SKILL.md`**
  - `:23` `.git/the-works/<feature-id>/` → session logs key by feature only
    today; decide whether a task's log nests under the feature's stream dir or
    stays flat with a `<feature>/<task>` name (matches the sidecar's own
    Decision-118 segregation — feature sidecar, per-task sections).
  - `:27`, `:92-104` — worktree creation block: `.claude/worktrees/<feature-id>`
    → `.claude/worktrees/<feature>/<task>`; `git worktree add ... -b f/<feature-id>
    main` → `-b f/<feature>/<task>`.
  - `:56-60` — "a feature branch named `f/<feature-id>`" → task branch named
    `f/<feature>/<task>`; the close paragraph's `archive/<feature-id>` →
    `archive/<feature>/<task>`.
  - `:87` — DELETE "The chosen task's `{#id}` becomes the `<feature-id>`" — the
    line this whole feature exists to kill. Replace with: the task is chosen
    from inside an existing (or newly declared) feature; `<feature>` and
    `<task>` are two separate ids from the start.
  - `:90` — kebab-case `<feature-id>` generation instructions become
    "confirm or create the `<feature>` id, then generate a `<task>` id inside it".
  - `:216` — `created_during` semantics: currently "current feature-id"; must
    read task-scoped or clarify it names the feature the task belongs to.

- **`skills/workflow-complete/SKILL.md`**
  - `:64-66` marker tag: `archive/<feature-id>` → `archive/<feature>/<task>`.
  - `:76-91` squash template: `<feature-id>` refs (branch name, HEAD SHA
    lookup) → `<feature>/<task>`.
  - `:100-106` git note on squash HEAD — unaffected in mechanics, only the tag
    name it rides changes.
  - `:119-142` integrity verify + push block: every `archive/<feature-id>` →
    `archive/<feature>/<task>`, including the `git push origin main
    "refs/tags/archive/<feature>/<task>" "refs/notes/*"` line.

- **`agents/groundskeeper.md`**
  - `:55` `tag archive/<id>` → `archive/<feature>/<task>`; every `<id>` used as
    a branch/tag placeholder through the file needs the same split.

- **`agents/supervisor.md`**
  - `:64-65` `git worktree add .claude/worktrees/<id> -b f/<id> main` →
    `.claude/worktrees/<feature>/<task> -b f/<feature>/<task> main`.
  - Resolve the one-worktree-per-feature vs one-worktree-per-task
    contradiction: `:58-60` implies one worktree per feature handed to "a"
    landscaper; `:64-77` creates one worktree per dispatch. Decision-121 (a
    feature is built by a TEAM of landscapers with fluid task binding) settles
    this in favour of one worktree per task, several concurrent per feature —
    state that explicitly in this file rather than leaving both readings live.

- **`agents/landscaper.md`**
  - `:9-11` header + description: "cwd `.claude/worktrees/<id>` on branch
    `f/<id>`" → `.claude/worktrees/<feature>/<task>` on `f/<feature>/<task>`;
    "your `<id>` is the worktree name" → your `<task>` is the worktree's last
    segment, your `<feature>` is its parent segment.
  - `:224-226` same substitution where the worktree/branch pair is restated.

- **`agents/gardener.md`**
  - `:23-24` `git worktree list` / `git branch --list 'f/*'` triage reads:
    still valid glob-wise (`f/*` matches `f/<feature>/<task>` too) but the
    parsing that turns a match into a board id needs the two-segment split.
  - `:155-187` worktree/branch creation narration: `<id>` → `<feature>/<task>`
    pair throughout.

- **`tools/courier.py`** (`identity_of()`, currently `:368-380`)
  - Replace the single-segment read:
    ```python
    top = git("rev-parse", "--show-toplevel")
    worktree = Path(top).name if top else None
    linked = "/worktrees/" in git("rev-parse", "--git-dir")
    feature_id = worktree if linked else None
    ```
    with a two-segment read against the nested convention:
    ```python
    top_path = Path(top) if top else None
    linked = "/worktrees/" in git("rev-parse", "--git-dir")
    task_id = top_path.name if linked and top_path else None
    feature_id = top_path.parent.name if linked and top_path else None
    ```
  - Restore the `task_id`/`task_name` pair lost in the transport rewrite
    (Decision-108; see Findings) alongside the corrected `feature_id`, so
    `identity_of()` returns both again — this closes the regression the
    unvendor migration exposed, not just the naming scheme.
  - `_feature_name(feature_id, root=top)` calls: check whether
    `tools/feature_name.py` needs a matching `task_name`-by-id lookup, or
    whether the sidecar's per-task `## Task` heading (Decision-118) already
    gives one for free.

- **`tools/sidebar.py`** — already correct per the feature's own Findings
  (`Feature` holding a list of `Task`, keyed `(feature_id, task_id)`); verify
  it consumes `courier.py`'s corrected `identity_of()` output rather than
  re-deriving from the worktree path itself, so the fix has one source of
  truth.

Out of scope: the board grammar, the GitHub projection, the changelog release
structuring (release-cut owns that), the team runtime design beyond its
branch/worktree mechanics (Decision-121).

## Questions

1. **Worktree directory naming for `f/<feature>/<task>`** — nested
   `.claude/worktrees/<feature>/<task>` vs. flattened
   `.claude/worktrees/<feature>--<task>`.

   Evidence gathered this bloom round:
   - `courier.py`'s current `identity_of()` (`:368-380` on `main`) derives
     `feature_id` from a SINGLE path segment: `Path(top).name` where `top` is
     `git rev-parse --show-toplevel`. Under nesting, that call already returns
     the full nested path (git worktrees can live at any depth), so
     `Path(top).name` naturally yields `<task>` and `Path(top).parent.name`
     yields `<feature>` — a two-line fix, no delimiter needed.
   - Flattened would keep today's single-segment read working unmodified for
     the OLD (wrong) meaning, but recovering `<feature>` and `<task>`
     separately still requires splitting the directory name on a delimiter
     (e.g. `--`). Task and feature ids observed on the current board are
     themselves kebab-case with internal hyphens (`branch-and-close`,
     `features-first-class`), so a `--`-split is ambiguous whenever a chosen
     id happens to contain a double hyphen, or when concatenation of two
     hyphenated ids produces a substring matching another valid split point.
     The filesystem path separator carries no such ambiguity.
   - Restoring the Decision-108 `task_id`/`task_name` pair does NOT depend on
     this choice either way — historically (per git history of `courier.py`,
     see Findings) that pair came from `ORCHID_TASK_ID`/`ORCHID_TASK_NAME`
     environment variables set by the launcher, not from worktree-path
     parsing. The worktree-naming choice only affects `feature_id` /
     `identity.worktree` derivation.

   **Recommendation: nested (`.claude/worktrees/<feature>/<task>`).** No
   delimiter-collision risk, a direct segment-for-segment mirror of the
   `f/<feature>/<task>` branch name, and the `courier.py` fix is two attribute
   reads instead of a string split. Awaiting operator confirmation before this
   is spec.

## Findings

- `tools/courier.py` git history (`git log --all -p -- tools/courier.py`,
  commits `10e8a54`/`bc8fe5f`/`53629e1`/`e4e3841` era) shows a `_task_identity()`
  helper that existed before the transport rewrite:
  ```python
  def _task_identity(feature_id, feature_name):
      task_id = os.environ.get("ORCHID_TASK_ID") or feature_id
      task_name = os.environ.get("ORCHID_TASK_NAME") or feature_name
      return task_id, task_name
  ```
  `identity_of()` called it and returned `task_id`/`task_name` alongside
  `feature_id`. This confirms and sharpens the sidecar's earlier note: the
  pair was environment-derived, NOT worktree-path-derived, so its restoration
  is independent of the nested-vs-flat question above.
- `migrations/2026-07-27-unvendor-self.md` (`:63-68`, "Consequence to be aware
  of") is the authoritative record of the loss: "the clone's
  `courier.identity_of()` returned `task_id` and `task_name`; `main`'s does
  not. Decision-108 ... was implemented, then lost in the transport rewrite ...
  Consumers must fall back to the feature when it is absent." This task's
  `courier.py` change is also the fix for that open regression.
- `docs/decisions.md` Decision-116 through Decision-121 (2026-07-28,
  `features-first-class` bloom round) are all confirmed present and dated
  today; Decision-116 (branch naming, no feature branches ever) and
  Decision-120 (archive tags mirror branch names, changelog flat between
  releases) are the two this task implements. Decision-121 (team of
  landscapers, fluid task binding) is the basis for resolving the
  supervisor.md one-worktree-per-feature/task contradiction above.
- `agents/supervisor.md:20-22` (one-worktree-per-feature framing) versus
  `:64-77` (one worktree created per dispatch) — read directly off `main`,
  confirming the sidecar's original claim; Decision-121 resolves it in favour
  of one worktree per task, several live concurrently under one feature.

## Testing

1. **Scripted dry-run close** over a scratch feature/task pair named to the
   new scheme (e.g. feature `zzz-scratch`, task `probe`):
   - `git worktree add .claude/worktrees/zzz-scratch/probe -b f/zzz-scratch/probe main`
   - make a trivial commit on the branch
   - run the updated `workflow-complete` tag/squash/verify/push sequence
     against it (tag `archive/zzz-scratch/probe`, squash to a scratch local
     branch standing in for `main` — do NOT push to shared `main` for this
     drill)
   - confirm the integrity-verify tree-comparison and commit-count checks
     (`skills/workflow-complete/SKILL.md:111-133`) pass unmodified against the
     new tag name
   - `git worktree remove` and branch/tag cleanup
2. **`courier.py` identity unit check**: from inside the scratch worktree,
   run `python3 tools/courier.py identity` (or call `identity_of()` directly
   via `python3 -c`) and assert the returned dict has `feature_id ==
   "zzz-scratch"` and `task_id == "probe"` (or the flattened-scheme
   equivalents if that option is chosen instead).
2b. If `ORCHID_TASK_ID`/`ORCHID_TASK_NAME` restoration is included in this
   task's scope, set both env vars before the same call and assert they
   override the worktree-derived values, matching the pre-rewrite
   `_task_identity()` behaviour recovered in Findings.
3. **Grep sweep for stragglers**: `grep -rn '<feature-id>\|f/<id>\|archive/<id>'
   skills/ agents/` after edits lands zero hits outside intentionally-retained
   prose (e.g. historical decision-log quotes), confirming no reference to the
   old single-id scheme survives in the five files this task touches.
4. Existing close-path tests, if any exist under a `tests/` directory covering
   `workflow-complete` or `courier.py`, are run and must still pass —
   confirm their existence/location before build starts; none were found in
   this bloom round's read-only pass (`courier.py`, `skills/`, `agents/` were
   read directly, no accompanying test suite surfaced).

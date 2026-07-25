- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

- ~~Sequencing only: the operator ordered the sidebar bug fixes to start after
  the bloomer v1 build lands, one at a time, each verified live on the
  gardener's own sidebar after coding.~~ Pulled forward (operator,
  2026-07-24 evening): runs NOW as the one-go quick pass, in parallel with
  the bloomer close.

## Questions

- ~~Exact title composition: confirm the rendering is `<faint repo>/<prominent
  name>` — a light/thin repo name and a `/` BEFORE the name, so the name is
  what the eye sees most and the repo least — and whether it applies to
  session rows, the project header row, or both once sessions are named after
  projects ([[orchestrator-identity]]).~~ DECIDED in the one-go proposal
  (operator demanded no question rounds): session rows and window names both
  render `<faint thin repo>/<bright name>`; project headers carry the
  gradient and the repo name alone.
- ~~Should a project with no open session render at all (orchids and SignMc
  currently show as empty groups)?~~ DECIDED: a project with no live session
  does not render.

## Findings

- Observed (operator, 2026-07-24): gradient backgrounds are missing from the
  project name rows (orchids, SignMc). Both projects render as empty groups
  although no session is open for either.
- Pane capture (2026-07-24 evening, gardener, `tmux capture-pane -e` on
  the live sidebar): confirms and extends the report —
  - `orchids` header renders bold+reverse-video (`[1;7m`), `SignMc` renders
    bold only (`[1m`): no gradient anywhere, and the two project headers are
    not even styled consistently with each other.
  - No repo/`/name` composition exists on any row; session rows show only
    the board title, truncated mid-word with no ellipsis ("last-night-
    discussio", "Bloomer charter: clo"), so concurrent sessions on one
    feature are indistinguishable (ghost-row aspect recorded in
    [[sidebar-witnessing]]).
  - The reverse-video project header is the loudest element on screen — the
    opposite of the requested tame/faint repo rendering.
- Operator round 2 (2026-07-24 evening) widened the task into a one-go quick
  pass — his words: simple, quick, one go, no questions asked, exactly the
  few things requested:
  - ALL the row icons are wrong — none does what it says, and previous
    conversations about fixing them were ignored (history to inherit:
    [[sidebar-polish]], [[sidebar-spacing-and-glyphs]] sidecars).
  - The one-session-per-project sessions were never renamed: sidebar session
    name must map 1:1 to the GitHub repository name (naming slice pulled
    forward from [[orchestrator-identity]], which keeps the
    single-instance enforcement).
  - Landscaper window pane titles flicker: sometimes the Claude name shows,
    sometimes nothing, sometimes `bash`, depending on whether the title is
    displayed — titles must be deterministic.

## Proposal

The one-go quick pass — seven items, all decisions baked in. OPERATOR
MANDATE (2026-07-24 evening): decisions are final; the plan-gate question
round AND the MAKE IT SO prologue are waived for this feature — the
landscaper builds exactly this list and nothing else, immediately; the
operator's gate is the live one-look verification at the end plus THAT IS
ALL at close.

1. Project header rows regain their gradient background, both projects
   styled identically; header shows the repo name alone.
2. Session rows and tmux window names render `<repo>/<name>` with the repo
   thin/faint and the name bright — the name dominates, the repo recedes.
   Truncation keeps the name side and adds an ellipsis.
3. A project with no live session does not render.
4. Icons tell the truth: one icon per actually-observed state, mapping table
   recorded here at build; no icon is ever shown for a state the observer
   cannot verify. Inherit the ignored icon history from sidebar-polish /
   sidebar-spacing-and-glyphs before choosing the set.
5. Session naming 1:1: the gardener session in every repo is named
   exactly after its repository (this repo's live session renamed as part of
   the pass); pane titles are set explicitly with `allow-rename off`
   everywhere so no pane ever shows `bash` or flickers.
6. Animation (operator, amendment round): actively-working rows show a
   spinner; waiting-on-operator rows blink; everything else is static. A
   message ARRIVING changes nothing on the row (operator: "Nothing") —
   animation is state-driven only.
7. Done state (operator, amendment round): a done feature's row NEVER
   leaves the current session's view — it renders green, sorts to the top
   of its project group, and the list keeps accruing below. Clarified
   mid-build (operator, relayed over the courier to the working landscaper):
   this rule is for FEATURE rows only — SUBAGENT rows (white/black-circle)
   DISAPPEAR when done; they have nothing to say and nothing to display.

OUT of this pass — recorded wants, deliberately unshaped (the operator will
talk them through; no option-grid shaping, per his order): agent-sent
message surfacing, tokens/cost per row, elapsed/phase time per row, sound
on attention; keyboard navigation deferred to its own later round. The
operator has begun dictating the interaction spec into
[[bus-message-specifying]] — do not preempt it here.

## Post-merge state (2026-07-25) — FUNCTIONAL, title tail NOT done

- The RENDERER items (1 gradients/hues, 3 empty-repo-hidden via has_session,
  4 truthful icons, 7 done-retention, 2 repo/name composition) shipped to main
  via the bus-message-specifying rewrite of tools/sidebar.py (verified present
  in main). That half is delivered.
- The TITLE/NAMING items (2 window titles, 5 stable pane titles) are NOT
  fixed. Operator live report (2026-07-25): "the titles of the panes in this
  session are still completely wrong" — confirmed: this session's window is
  named `claude` (not the repo) and pane_titles read `⠂ Claude Code` /
  `design mock`, clobbered.
- ROOT CAUSE found: the branch's fix (`allow-rename off` / `automatic-rename
  off`) governs the WINDOW NAME only; the PANE TITLE is set by the OSC 2
  escape and is NOT governed by those options — so the fix cannot stop
  pane_title clobbering. Live-tested 2026-07-25: with both options off, an
  OSC 2 write still overwrote pane_title. The salvage was therefore REVERTED
  (it would not fix the operator's actual complaint).
- FOLDS INTO tomorrow's naming rework (operator: "your branch and feature
  naming skills are pretty horrible, try a better approach"). The correct
  pane-title mechanism (persist/re-assert pane_title, or a title hook) is
  designed there, not here. f/sidebar-titling stays parked pending that
  rework; its renderer contribution is already in main.
- Custom question tmux dialogs (the queued-question broker UI) are "nowhere
  to be seen" (operator) — that is the [[operator-interacting]] surface, not
  built; the courier grammar defined the question CLASS only.

## Testing

Live verification, operator eyeball only (his stated gate): the running
sidebar is refreshed after the build; he confirms headers, row format,
hidden empty projects, truthful icons, the renamed session, and stable
titles in one look. RENDERER half passed (in main); the TITLE half is
UNVERIFIED/failing (pane titles still clobbered) and moves to the naming
rework.

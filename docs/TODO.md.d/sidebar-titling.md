- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

- ~~Sequencing only: the operator ordered the sidebar bug fixes to start after
  the bloomer v1 build lands, one at a time, each verified live on the
  orchestrator's own sidebar after coding.~~ Pulled forward (operator,
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
- Pane capture (2026-07-24 evening, orchestrator, `tmux capture-pane -e` on
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
  - Architect window pane titles flicker: sometimes the Claude name shows,
    sometimes nothing, sometimes `bash`, depending on whether the title is
    displayed — titles must be deterministic.

## Proposal

The one-go quick pass — five items, all decisions baked in, NO plan-gate
question rounds (operator mandate): the architect builds exactly this list
and nothing else.

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
5. Session naming 1:1: the orchestrator session in every repo is named
   exactly after its repository (this repo's live session renamed as part of
   the pass); pane titles are set explicitly with `allow-rename off`
   everywhere so no pane ever shows `bash` or flickers.

## Testing

Live verification, operator eyeball only (his stated gate): the running
sidebar is refreshed after the build; he confirms headers, row format,
hidden empty projects, truthful icons, the renamed session, and stable
titles in one look.

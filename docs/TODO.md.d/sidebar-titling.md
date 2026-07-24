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

The one-go quick pass — seven items, all decisions baked in. OPERATOR
MANDATE (2026-07-24 evening): decisions are final; the plan-gate question
round AND the MAKE IT SO prologue are waived for this feature — the
architect builds exactly this list and nothing else, immediately; the
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
5. Session naming 1:1: the orchestrator session in every repo is named
   exactly after its repository (this repo's live session renamed as part of
   the pass); pane titles are set explicitly with `allow-rename off`
   everywhere so no pane ever shows `bash` or flickers.
6. Animation (operator, amendment round): actively-working rows show a
   spinner; waiting-on-operator rows blink; everything else is static. A
   message ARRIVING changes nothing on the row (operator: "Nothing") —
   animation is state-driven only.
7. Done state (operator, amendment round): a done feature's row NEVER
   leaves the current session's view — it renders green, sorts to the top
   of its project group, and the list keeps accruing below.

OUT of this pass — recorded wants, deliberately unshaped (the operator will
talk them through; no option-grid shaping, per his order): agent-sent
message surfacing, tokens/cost per row, elapsed/phase time per row, sound
on attention; keyboard navigation deferred to its own later round. The
operator has begun dictating the interaction spec into
[[bus-message-specifying]] — do not preempt it here.

## Testing

Live verification, operator eyeball only (his stated gate): the running
sidebar is refreshed after the build; he confirms headers, row format,
hidden empty projects, truthful icons, the renamed session, and stable
titles in one look.

## Operator requests

- [implemented] (relayed via orchestrator, 2026-07-24) Item 7's stays-green-at-top
  DONE rule applies to FEATURE rows ONLY. SUBAGENT rows disappear when done —
  nothing to say, nothing to display. Folded into the build (subagents already
  drop from the model on `orchid:subagent:done`; retention is feature-only).

## Decision entries

(Staged in final docs/decisions.md format for the housekeeper's mechanical fold;
numbers are placeholders — the housekeeper assigns the next free number.)

## [2026-07-24] Decision-NNN: The fleet sidebar animates working and operator-wait rows (reverses the no-animation ruling for two states)
#sidebar #animation #status #spinner #blink #sidebar-polish #operator-amendment

**Context:** sidebar-polish item 1/9 established "no animation — every status glyph
is static, layout never shifts." The operator's one-go amendment round
(2026-07-24) revises that specifically for liveness feedback.

**Decision:**
- Actively-working FEATURE rows render an animated spinner in place of the static
  working glyph; rows in the waiting-on-operator state blink. Every other state
  (component-wait, awaiting-agent, idle, done, failed, bus) stays static.
- Animation is STATE-DRIVEN ONLY. A message merely arriving changes nothing on a
  row (operator: "Nothing").
- The pure `render_lines()` text path (what unit tests assert on) stays static —
  it renders a fixed representative frame; animation lives only in the curses draw
  loop, so tests remain deterministic.

## [2026-07-24] Decision-NNN: Subagent rows show a truthful presence glyph, never a hardcoded "working"
#sidebar #icons #subagent #glyph #truthful #sidebar-spacing-and-glyphs

**Context:** `flatten()` hardcoded `status="working"` (🚧) for every subagent row
regardless of its real state (sidebar-spacing-and-glyphs item 2) — an icon for a
state the observer cannot verify.

**Decision:**
- A subagent row renders a filled circle (●) while it is active — presence in the
  model's `active_subagents` set is the only verifiable subagent state — and
  disappears entirely on `orchid:subagent:done`.
- The unfilled circle (○, "inactive") is deliberately NOT used: there is no
  observable idle-subagent signal, and no icon may stand for an unverifiable state.
- The settled six-state FEATURE/repo vocabulary is retained: working 🚧 (spinner
  when animated), component-wait ⌚, operator-wait ❓ (blinks), awaiting-agent 🪷,
  idle ⚪, done ✅, failed ❌; bus row 📬.

## [2026-07-24] Decision-NNN: A done feature's row persists green at the top of its group for the sidebar's lifetime
#sidebar #done #retention #sort #lifecycle #eviction

**Context:** `_BusAggregator` evicted a session one scan after its terminal
lifecycle signal (sidebar-polish item 2/3 stale-row eviction). The operator wants
a completed feature to stay visible.

**Decision:**
- A FEATURE whose lifecycle reached done/finished is retained for the life of the
  running sidebar process (not evicted), rendered green and sorted to the top of
  its project group; the list keeps accruing below.
- This applies to FEATURE rows only. Subagent rows still disappear when done.
- Failed/abandoned rows keep the existing one-scan grace-then-evict behaviour.

## [2026-07-24] Decision-NNN: Session rows and tmux window names compose `<repo>/<name>`; empty projects do not render
#sidebar #titling #window-name #separator #truncation #tmux

**Context:** Rows showed the feature name alone with no repo context; window names
used a ` ▸ ` (U+25B8) separator; projects with no live session rendered as empty
header groups.

**Decision:**
- Session rows and tmux window names compose `<repo>/<name>` with a `/` (U+002F)
  separator, replacing ` ▸ `. The repo segment renders faint/dim, the name segment
  bright — the name dominates.
- Truncation elides the repo (left) side, always keeping the name visible, and
  appends an ellipsis.
- A project with no live session (no orchestrator session and no features) is not
  rendered at all.

## [2026-07-24] Decision-NNN: Pane titles are set explicitly with allow-rename off so no pane shows bash or flickers
#tmux #pane-title #allow-rename #flicker #launch-sites #naming

**Context:** Architect pane titles flickered between the Claude name, nothing, and
`bash` because `automatic-rename off` was set on the window but nothing pinned the
pane title, which `claude`/`bash` clobber live.

**Decision:**
- Every pane-creating launch site sets the pane title explicitly AND sets
  `allow-rename off` so the running program cannot clobber it; `automatic-rename
  off` is set on every managed window.
- The orchestrator session in every repo is named 1:1 after its repository
  (reaffirms Decision-032); this repo's live session is renamed as part of the pass.

## Result

Result: done (built + tested, awaiting operator THAT IS ALL). Branch
`f/sidebar-titling`, HEAD 868063c. All seven items built by three parallel
builders partitioned by file (model / renderer / launch-sites), plus a
verification-surfaced item-2 fix and the ARCHITECTURE update.

Tested: `python3 -m pytest tests/ -q` → 204 passed, 8 subtests (baseline was
184); `python3 -m py_compile` clean on all touched Python; `python3
tools/sidebar.py --dump` runs clean against live bus data and confirms — repo
headers with no status glyph, sub-agent rows showing ●, done features sorted
green to the top of their group, feature rows composing `<repo>/<name>` with the
name kept under truncation. Curses-only behaviour (the gradient colours, the
dim-repo/bold-name segments, the working spinner, the operator-wait blink) and
the tmux window/pane naming cannot be exercised headless — they are the
operator's agreed live one-look eyeball gate.

Interpretation flags surfaced for the eyeball (built a defensible reading; each
is a one-line change if he rules otherwise):
- Empty-project rule renders a repo that has an idle orchestrator session but no
  features (e.g. SignMc shows as a bare header). "No live session" was read as
  "no orchestrator AND no features". If he wants idle-orchestrator-only repos
  hidden too, that is a trivial tightening.
- The gradient project header does NOT blink or spin even when its orchestrator
  is waiting on the operator — headers stay tame (name-only, gradient), animation
  is scoped to feature/sub-agent rows.
- The activity text still shows on a feature row, but strictly after the
  `<repo>/<name>` and only in leftover width (it never starves the name).

Follow-ups returned to the orchestrator: none required — all seven items are
implemented and unit-tested. The operator-requests ledger is fully implemented.

## Changelog entry

Fleet sidebar one-go pass. Project headers render their orchid gradient on any
256-colour terminal (nearest-xterm-256 fallback when the terminal cannot
redefine colours), styled identically across projects. Session rows now compose
`<dim repo>/<bright name>` so the name dominates and the repo recedes;
truncation keeps the name and elides the repo from the left, and the activity is
secondary (leftover width only). A project with no live session no longer renders
as an empty header group. Sub-agent rows show a truthful presence dot (●) instead
of a hardcoded "working" icon and disappear when done. Two states now animate
(curses only, state-driven): an actively-working feature glyph spins and a
waiting-on-operator row blinks — a message merely arriving changes nothing. A
done feature stays green and sorts to the top of its project group for the life
of the sidebar. tmux workstream window and session names use a `/` separator
(`<repo>/<name>`), matching the sidebar's navigation target; every launch site
pins its pane title with `allow-rename off` + `automatic-rename off` so panes no
longer flicker between the title, nothing, and `bash`; the orchestrator session
is named 1:1 after its repository.

## Readme delta

If README documents the fleet sidebar's appearance: the sidebar now hides
projects with no live session, shows each session as `<repo>/<name>` (repo faint,
name bright), marks sub-agents with a filled dot, spins an actively-working row
and blinks a row waiting on you, and keeps finished features green at the top of
their group. tmux windows/sessions read `<repo>/<name>` and their pane titles no
longer flicker. No new commands or flags — behaviour/appearance only.

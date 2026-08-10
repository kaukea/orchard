# The tmux topology — committed spec

Status: committed specification. This document, not chat convention or skill prose, is
the authority for how the fleet lays out and tears down tmux sessions, windows, and
panes.

Roles referenced here: the **gardener** (the root, board-owning session — one per
repository), the **beekeeper** (the per-feature pipeline warden — organises who gets
called when and makes sure no dispatched agent goes missing; formerly "supervisor",
then briefly "arborist", Decision-141), the **landscaper** (one feature, running in a
git worktree — the role the operator actually talks to), the **sower** (a headless
per-step worker the landscaper dispatches), the **groundskeeper** (the headless close
worker), and the **courier** (the message transport).

## 1. The shape (operator ruling, 2026-08-10)

- **SESSION per repository.** One session per repository, session name = the bare
  repository name. No other naming form.
- **WINDOW 1, always, is the gardener** — named literally `Gardener`. It never carries
  the repo name (the session already does) and it never closes while the session lives.
- **WINDOW per feature.** Each active feature is exactly one window, named after the
  feature — the same string as its branch name, kept simple. The beekeeper creates it
  (worktree + branch + window, in that order) when the gardener hands it a feature, and
  the LANDSCAPER runs in it — the landscaper is what the operator interacts with
  directly, never a side-by-side or split of the gardener.
- **The beekeeper does not get its own window.** It is session-bearing (its own
  session, its own courier, its own state) but headless from the operator's chair —
  routing and lifecycle-watching are not something the operator sits and watches happen
  pane-by-pane; ASK it (through the gate surfaces below) rather than looking for its
  window. *(Explicit assumption, not separately re-confirmed with the operator — flag if
  wrong.)*
- **PANE per live subtask.** A feature's subtasks (sowers, discovery explorers) are
  RIGHT-HAND PANES of the feature's one window — never their own window, and never
  interactive. A pane opens when its subtask starts and closes when it finishes; the
  operator is never expected to type into one.

A pinned sidebar occupies a left pane in every gardener and feature window.

## 2. Window creation (the beekeeper's act)

When the gardener hands off a feature, the beekeeper:

1. Creates the worktree and branch, then the window:
   `tmux new-window -n "<feature-name>" -c <worktree>` whose command launches
   `claude --agent landscaper --name "<feature-name>"` with `ORCHID_PARENT_SESSION` set
   to the beekeeper's own session id, and the dispatch-specific brief passed as the
   launch's trailing `prompt` argument (never typed in afterward via `send-keys` — a
   session that opens with nothing to do is a trigger someone has to remember to type).
2. Sets `@landscaper_id = <feature-id>` as a **window user-option** — the stable handle
   for teardown, reaping, and focus. It is immune to the pane-title clobber described
   in §4.
3. Sets `automatic-rename off`, pinning the window name.
4. Mounts the sidebar as a pinned left pane.
5. Sets the pane title `land:<id>` — a non-load-bearing human hint only (§4).

The gardener stamps `@gardener_id = <gardener-session-id>` as a window user-option on
its **own** window at boot. This is the stable handle the window-kill primitive (§7)
uses to find the gardener window when it returns focus at close.

## 3. Focus return

The rule is deliberately simple: **a finish selects the gardener window.** When a
feature's window is torn down, focus lands on the gardener window (resolved via
`@gardener_id`), and the client is switched to it.

The finer question of which pane or scroll position to land on — following the
operator's view rather than just the window — is out of scope here ([[focus-returning]],
gh#216).

## 4. Naming (operator ruling, 2026-08-10 — supersedes the `<repo>/<name>` /
`<repo> ▸ <name>` forms and the pending [[tmux-naming]] separator question)

- **Session name.** The bare repository name. Nothing appended, for the gardener or
  anyone else.
- **Window name, gardener.** Literally `Gardener`.
- **Window name, feature.** The feature name alone — the same string as its branch name
  (`f/<name>` minus the `f/`), kept simple. No repo prefix (the session already carries
  it), no separator glyph, no human-title substitution.
- **`--name` at launch carries identity: agent/feature name + emoji + colour together**
  (e.g. `🐝 inbox-outbox`), not a bare string — the launched agent's own frontmatter
  `color` (see `agents/*.md`) is what that colour comes from.
- **Pane titles are not load-bearing.** The `claude` process running inside a pane emits
  an OSC 2 escape that overwrites `pane_title` regardless of `allow-rename off` /
  `automatic-rename off`. Therefore every load-bearing cross-agent match — teardown,
  reaping, focus return, peek-window targeting — keys off the `@landscaper_id` /
  `@gardener_id` window user-options, never off `pane_title`. Pane titles (`land:<id>`,
  `peek:<name>`, `orchid-sidebar`) survive only as human hints and as peek-column
  bookkeeping within a single window.

## 5. Pane stacking — subtasks (sowers, discovery explorers)

- Subtasks are **hidden by default**: never named sessions, never their own window,
  surfaced in the sidebar via the courier. This holds regardless of how many a
  landscaper dispatches at once — launching a large parallel fleet is normal and never
  a reason to open windows for them.
- Hidden does not mean unpeekable. A **peek** opens a disposable pane tailing a
  subtask's live transcript, on demand, and closes when done.
- Peeks — and any deliberately visible subtask — live in a **dedicated right column** of
  the feature's window, stacked vertically, capped. They are never appended below the
  landscaper (the unusable default of a plain `split-window -v`), and they open/close
  with the subtask's own lifetime, not on a timer.
- Mechanics (`tools/peek.sh`): the first peek opens the column with
  `split-window -h -l 33%`; each subsequent peek stacks with `split-window -v` against
  the first pane whose title begins `peek:`. The column cap is a build-time knob
  (currently 4).

## 6. Closing and ownership

- The landscaper is a **pure scope.** Everything it creates — its courier, any monitors,
  its sowers, its log — dies inside it before it exits. It dispatches no closer, removes
  no worktree, and touches no window.
- The close is the **beekeeper's**, executed by its own **groundskeeper** subagent,
  fired on the landscaper's `closed` signal (or on its detected death).
- The beekeeper releases what it created — **worktree, branch, window — in reverse
  creation order.** The window is released before the branch, which is released before
  the worktree; worktree removal is the last act.
- The window release is performed by the tmux window-kill primitive (§7), invoked by
  the groundskeeper.
- `.return-window` **retires.** Its stored return-pane-id is replaced by "select the
  gardener window" (§3, §7), resolved via `@gardener_id`.
- Supervision **collects, never kills**: no agent kills another; the groundskeeper
  removes the window and tree as the structural owner, not as a kill of a live peer.

## 7. The window-kill primitive

A single tmux primitive (`tools/landscaper-teardown.sh`) performs the window release and
focus return. It:

1. Resolves the feature window by its `@landscaper_id` window user-option.
2. Resolves the gardener window by its `@gardener_id` window user-option.
3. Refuses to act if the resolved feature window is the focus-return target — it never
   kills the window it is about to return focus to.
4. Returns focus: switches the client to the gardener window and selects it.
5. Kills the feature window (`tmux kill-window`), which also removes its sidebar pane.

The primitive is callable by the groundskeeper.

## 8. Out of scope — deferrals

Each linked to its owner so nothing is silently dropped:

- Pane-title persistence mechanism → [[tmux-naming]] (its separator question is now
  moot — window names no longer carry a repo/name separator at all, per §4).
- Focus-return view-following nuance (gh#216) → [[focus-returning]].
- The operator-interaction popup / question-broker surface → [[operator-interacting]].
  This spec is silent on popups; tmux is at most one transport such a surface may choose.
- The right-column peek cap value → a build-time knob.

## 9. Handle reference

- `@landscaper_id` (window user-option): the stable id of a feature window. Teardown,
  reaping, and peek-window targeting key off it.
- `@gardener_id` (window user-option): the stable id of the gardener window. Focus
  return targets it.
- Pane titles (`land:<id>`, `peek:<name>`, `orchid-sidebar`): human hints and
  within-window peek bookkeeping only — never a load-bearing cross-agent handle.

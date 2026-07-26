# The tmux topology — committed spec

Status: committed specification (Decision-090). This document, not chat convention or
skill prose, is the authority for how the fleet lays out and tears down tmux sessions,
windows, and panes. It uses the orchard role vocabulary (Decision-085).

Roles referenced here: the **gardener** (the root, board-owning session — one per
repository), the **landscaper** (one feature, running in a git worktree), the **sower**
(a headless per-step worker the landscaper dispatches), the **groundskeeper** (the
headless close worker), and the **courier** (the message transport). These were formerly
named orchestrator, architect, builder, housekeeper, and bus respectively.

## 1. The shape

- **SESSION per repository.** One gardener session per repository; it is the operator's
  ambient tmux session for that repository.
- **WINDOW per landscaper.** Each active feature is one tmux window, created by the
  gardener. The landscaper is something the operator interacts with directly — it is
  never a side-by-side or horizontal split of the gardener. (This supersedes
  Decision-006, which placed architects in panes beside the orchestrator.)
- **PANE per visible sower.** Sowers are headless by default. When a sower is made
  visible (a peek), it occupies a stacked pane in a dedicated right column of the
  landscaper's window — never a pane appended below the landscaper.

A pinned sidebar occupies a left pane in every gardener and landscaper window.

## 2. Window creation (the gardener's act)

When the gardener dispatches a landscaper it:

1. Creates the worktree and branch, then the window:
   `tmux new-window -n "<window-name>" -c <worktree>` whose command launches
   `claude --agent landscaper --name "<session-name>"` with `ORCHID_PARENT_SESSION`
   set to the gardener's session id.
2. Sets `@landscaper_id = <id>` as a **window user-option** — the stable handle for
   teardown, reaping, and focus. It is immune to the pane-title clobber described in §4.
3. Sets `automatic-rename off`, pinning the window name.
4. Mounts the sidebar as a pinned left pane.
5. Sets the pane title `land:<id>` — a non-load-bearing human hint only (§4).

The gardener additionally stamps `@gardener_id = <gardener-session-id>` as a window
user-option on its **own** window at boot — the mirror of `@landscaper_id`. This is the
stable handle the window-kill primitive (§7) uses to find the gardener window when it
returns focus at close.

## 3. Focus return

The rule is deliberately simple: **a finish selects the gardener window.** When a
landscaper's window is torn down, focus lands on the gardener window (resolved via
`@gardener_id`), and the client is switched to it.

The finer question of which pane or scroll position to land on — following the operator's
view rather than just the window — is out of scope here. It remains the open follow-on of
[[focus-returning]] (gh#216).

## 4. Naming

This spec states the naming **contract**. The naming **mechanism** — the separator
alignment below and the means of keeping a pane title stable — is the coordinated rework
owned by [[tmux-naming]]; this spec's naming chapter defers to it for the mechanism.

- **Session name.** The bare repository name for the gardener (e.g. `orchids`); the form
  `<repo>/<name>` for a landscaper (set via `claude --name`).
- **Window name.** The form `<repo>/<name>`.
- **Canonical separator: `/`.** This matches the target form the sidebar navigator already
  resolves against. Note: the current implementation writes the window name with a `▸`
  separator, which does not match the navigator's `/`; aligning the two is part of
  [[tmux-naming]]'s rework, not this spec's raw-layer scope.
- **Pane titles are not load-bearing.** The `claude` process running inside a pane emits
  an OSC 2 escape that overwrites `pane_title` regardless of `allow-rename off` /
  `automatic-rename off`. Therefore every load-bearing cross-agent match — teardown,
  reaping, focus return, peek-window targeting — keys off the `@landscaper_id` /
  `@gardener_id` window user-options, never off `pane_title` (Decision-048). Pane titles
  (`land:<id>`, `peek:<name>`, `orchid-sidebar`) survive only as human hints and as
  peek-column bookkeeping within a single window.

## 5. Pane stacking — sowers (Decision-036)

- Sowers are **hidden by default**: never named sessions, surfaced in the sidebar via the
  courier.
- Hidden does not mean unpeekable. A **peek** opens a disposable pane tailing a sower's
  live transcript, on demand, and closes when done.
- Peeks — and any deliberately visible sower — live in a **dedicated right column** of the
  landscaper's window, stacked vertically, capped. They are never appended below the
  landscaper (the unusable default of a plain `split-window -v`).
- Mechanics (`tools/peek.sh`): the first peek opens the column with
  `split-window -h -l 33%`; each subsequent peek stacks with `split-window -v` against the
  first pane whose title begins `peek:`. The column cap is a build-time knob (currently 4).

## 6. Closing and ownership (Decision-090)

- The landscaper is a **pure scope.** Everything it creates — its courier, any monitors,
  its sowers, its log — dies inside it before it exits. It dispatches no closer, removes no
  worktree, and touches no window.
- The close is the **gardener's**, executed by the gardener's own **groundskeeper**
  subagent, fired on the landscaper's `finished` signal (or on its detected death).
- The gardener releases what the gardener created — **worktree, branch, window — in
  reverse creation order.** The window is released before the branch, which is released
  before the worktree; worktree removal is the last act (Decision-081, Decision-068).
- The window release is performed by the tmux window-kill primitive (§7), invoked by the
  groundskeeper.
- `.return-window` **retires.** Its stored return-pane-id is replaced by "select the
  gardener window" (§3, §7), resolved via `@gardener_id`.
- Supervision **collects, never kills** (Decision-081): no agent kills another; the
  groundskeeper removes the window and tree as the structural owner, not as a kill of a
  live peer.

The *firing* logic of the supervising controller — how the groundskeeper is triggered and
how it orchestrates the reverse-order release — is owned by [[close-family-fakes]]. This
spec provides the tmux primitive it calls and the contract above.

## 7. The window-kill primitive

A single tmux primitive (`tools/landscaper-teardown.sh`) performs the window release and
focus return. It:

1. Resolves the landscaper window by its `@landscaper_id` window user-option.
2. Resolves the gardener window by its `@gardener_id` window user-option.
3. Refuses to act if the resolved landscaper window is the focus-return target — it never
   kills the window it is about to return focus to.
4. Returns focus: switches the client to the gardener window and selects it.
5. Kills the landscaper window (`tmux kill-window`), which also removes its sidebar pane.

The primitive is callable by the groundskeeper (Decision-090). During the migration to
gardener-owned close it remains backwards-compatible as a self-callable, so a landscaper
that still self-tears-down keeps working until the supervising controller lands.

## 8. Out of scope — deferrals

Each linked to its owner so nothing is silently dropped:

- Pane-title persistence mechanism and window-name separator alignment → [[tmux-naming]].
- Focus-return view-following nuance (gh#216) → [[focus-returning]].
- The operator-interaction popup / question-broker surface → [[operator-interacting]].
  This spec is silent on popups; tmux is at most one transport such a surface may choose.
- The supervising-controller firing logic and reverse-order orchestration →
  [[close-family-fakes]]. This spec provides the tmux primitive and the contract only.
- The right-column peek cap value → a build-time knob.

## 9. Handle reference

- `@landscaper_id` (window user-option): the stable id of a landscaper window. Teardown,
  reaping, and peek-window targeting key off it.
- `@gardener_id` (window user-option): the stable id of the gardener window. Focus return
  targets it.
- Pane titles (`land:<id>`, `peek:<name>`, `orchid-sidebar`): human hints and
  within-window peek bookkeeping only — never a load-bearing cross-agent handle.

# The tmux topology — committed spec

Status: committed specification. This document, not chat convention or skill prose, is
the authority for how the fleet lays out and tears down tmux sessions, windows, and
panes.

Roles referenced here: the **gardener** (the root, board-owning session — one per
repository), the **beekeeper** (the per-feature pipeline warden — organises who gets
called when and makes sure no dispatched agent goes missing), the **landscaper** (one
feature, running in a git worktree — the role the operator actually talks to), the
**sower** (a per-step worker the landscaper dispatches), the **groundskeeper** (the
headless, git-only close worker), and the **courier** (the message transport).

## 1. The shape (operator ruling, 2026-08-10)

- **SESSION per repository.** One session per repository, session name = the bare
  repository name.
- **WINDOW 1, always, is the gardener** — named literally `Gardener`. It never closes
  while the session lives.
- **Everything is a pane, underneath.** tmux's real hierarchy is session → window →
  pane; a window never renders anything itself, only the pane(s) inside it do. A
  "window" is just a pane (or a stack of them) that has been given its own slot at the
  window level instead of living folded inside another window. There is no separate
  kind of thing called "a window-level agent" versus "a pane-level agent" — there is
  only ever a `claude` process running in a pane, and whether that pane has been
  promoted to its own window is a fact about that ONE pane, decided once, by the agent
  itself.
- **Launch is uniform and decoupled from rendering (operator ruling, 2026-08-10).**
  Every agent, whatever it goes on to become, is dispatched the exact same way by
  whoever is spawning it: `tools/dispatch-agent.sh <agent-type> <name> <cwd> <prompt>`
  opens a HIDDEN pane (`split-window -d`) and launches a REAL `claude` process into it
  from the moment of creation, `ORCHID_PARENT_SESSION` set to the dispatcher. This has
  to be a real process, not a Task-tool subagent — a Task-tool subagent has no pty of
  its own, so it cannot promote or close itself (§2). The dispatcher never creates a
  window and never decides whether the child gets one.
- **Each agent decides its own visibility, on its own boot — never the parent.** It
  either promotes itself into its own window (`tools/pane-promote.sh`, §2) or stays
  where it was split. A landscaper always promotes (the operator interacts with it
  directly). A sower almost always stays a hidden pane. Nothing about the DISPATCH
  changes based on that choice — only what the agent does with its own pane afterward.
- **PANE per live subtask, when a subtask is visible at all.** A feature's subtasks
  (sowers, discovery explorers) that choose to stay pane-level surface as RIGHT-HAND
  PANES of the feature's window when made visible — never a window of their own, and
  never interactive. Hidden by default (Decision-036), with no reveal mechanism right
  now — peek is retired (§5).

A pinned sidebar occupies a left pane in every gardener and feature window.

## 2. Creation and promotion — self-determined, never assigned

1. The dispatcher (whoever is spawning the next agent) runs
   `tools/dispatch-agent.sh <agent-type> <name> <cwd> <prompt>`. This is the ONLY
   creation step the dispatcher ever performs — a hidden pane, nothing more.
2. The new agent, on its own boot, decides for itself whether to promote:
   `tools/pane-promote.sh "<name>"` runs `tmux break-pane` on its OWN current pane —
   this relocates the EXISTING pane (same process, same pty, nothing restarted) into a
   brand-new window. An agent that chooses to stay a pane never calls this at all.
3. Immediately after promoting, the agent sets its OWN stable handle:
   `tmux set-option -w -t <window-id> @landscaper_id "<id>"` (or the equivalent handle
   for its own role) — the handle teardown, reaping, and peek-window targeting key off,
   immune to the pane-title clobber described in §4. It also sets `automatic-rename off`
   and mounts the sidebar (`tools/sidebar-mount.sh <window-id>`) itself — nobody does
   either of these FOR it.

The gardener stamps `@gardener_id = <gardener-session-id>` as a window user-option on
its **own** window at boot. This is the stable handle the self-close step (§3, §7) uses
to find the gardener window when returning focus.

## 3. Focus return

The rule is deliberately simple: **a finish selects the gardener window.** When a
feature's window closes, focus lands on the gardener window (resolved via
`@gardener_id`), and the client is switched to it.

The finer question of which pane or scroll position to land on — following the
operator's view rather than just the window — is out of scope here ([[focus-returning]],
gh#216).

## 4. Naming

- **Session name.** The bare repository name. Nothing appended, for the gardener or
  anyone else.
- **Window name, gardener.** Literally `Gardener`.
- **Window name, feature.** The feature name alone — the same string as its branch name
  (`f/<name>` minus the `f/`), kept simple. No repo prefix (the session already carries
  it), no separator glyph.
- **`--name` at launch carries identity: agent/feature name + emoji + colour together**
  (e.g. `🐝 inbox-outbox`) — the launched agent's own frontmatter `color` (see
  `agents/*.md`) is what that colour comes from.
- **The peek naming convention (cute name / bare agent name, two words max) is
  RETIRED along with peek itself** — see §5.
- **Pane titles are otherwise not load-bearing.** The `claude` process running inside a
  pane emits an OSC 2 escape that overwrites `pane_title` regardless of `allow-rename
  off` / `automatic-rename off`. Therefore every load-bearing cross-agent match —
  teardown, reaping, focus return, peek-window targeting — keys off a window
  user-option (`@landscaper_id`, `@gardener_id`), never `pane_title`.

## 5. Pane stacking — subtasks (sowers, discovery explorers): RETIRED for now

**Peek — and any visible side pane for a subtask — is RETIRED (operator ruling,
2026-08-10). It never worked properly.** Subtasks (sowers, discovery explorers) are
HIDDEN, full stop, with no reveal mechanism right now — no peek pane, no right-hand
column, no exception. `tools/peek.sh` stays in the tree, unused, in case it's worth
resurrecting once the messaging rewrite lands and agents have a solid enough foundation
under them for a visibility feature to be worth trying again — but nothing in the fleet
calls it today, and no charter should reference it as something currently offered.

## 6. Closing and ownership — the creator closes what it created, always itself

- **Every agent that promoted itself into a window closes that same window itself, as
  its own last act** (operator ruling, 2026-08-10). Since the pane it self-promoted was
  its own creation (`break-pane` on its own pane, §2), this is a clean application of
  "destroy what you create" — not a third party reaching into something it didn't make.
  There is no self-termination race: by the time this runs, the agent's real work,
  final docs, and its `lifecycle:closed` announcement are already done — the window-kill
  is housekeeping on an agent that has already finished, not a way of ending it.
- **The `groundskeeper` never touches windows or panes, at all, ever** (operator ruling,
  2026-08-10 — this was a live source of crashes and uncoordinated teardown in the
  prior design, not a theoretical risk). Its close is GIT-ONLY: docs, tag, squash, push,
  then worktree and branch removal — nothing about tmux.
- **The beekeeper releases what it actually created — the worktree and the branch —**
  once the git-close (groundskeeper) has landed, gated on the landscaper's own
  `lifecycle:closed` (which is guaranteed by the time the beekeeper ever fires the
  close, since that signal is what fires it). The window was never the beekeeper's
  creation, so it is never the beekeeper's to release.
- **A sower closes its own pane** (`tmux kill-pane`) as its own last act, the same
  pattern one level down — it created nothing else, so there is nothing else to release.
- Supervision **collects, never kills**: nobody ever kills a live agent's window or
  pane out from under it. What gets closed is always closed by the same agent that
  created it, after that agent has already finished.

## 7. Self-close mechanics

An agent that promoted itself tears its own window down via `tools/landscaper-teardown.sh
<id>` (or the equivalent for its own role) as its literal last act, after its
`lifecycle:closed` has already been posted and its courier released:

1. Resolves its OWN window by its `@landscaper_id` window user-option.
2. Resolves the gardener window by `@gardener_id`.
3. Refuses to act if its own window is the focus-return target — never kills the window
   it is about to return focus to.
4. Returns focus: switches the client to the gardener window and selects it.
5. Kills its own window (`tmux kill-window`), which also removes its sidebar pane.

This is SELF-invoked only now — there is no external caller. A sower's equivalent is
simply `tmux kill-pane` on its own pane; it has no worktree/branch and no focus-return
responsibility (it was never the thing the operator was looking at).

## 8. Out of scope — deferrals

- Pane-title persistence mechanism → [[tmux-naming]].
- Focus-return view-following nuance (gh#216) → [[focus-returning]].
- The operator-interaction popup / question-broker surface → [[operator-interacting]].
- Peek itself, and any reveal mechanism for a hidden subtask → retired (§5), pending the messaging rewrite.

## 9. Handle reference

- `@landscaper_id` (window user-option, self-set by the landscaper on promotion): the
  stable id of a feature window. Teardown, reaping, and peek-window targeting key off it.
- `@gardener_id` (window user-option): the stable id of the gardener window. Focus
  return targets it.
- Pane titles (`land:<id>`, `peek:<name>`, `orchid-sidebar`): human hints and
  within-window peek bookkeeping only — never a load-bearing cross-agent handle.

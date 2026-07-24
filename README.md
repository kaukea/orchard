# orchids

> One operating model for every repository — agents, skills, and rules as a single versioned package.

**Tired of every repo teaching its agents different habits?** Left alone, each
project grows its own workflow: agents improvise roles, skills drift out of
sync, rules live in one CLAUDE.md and not the next, and everything an agent
learned evaporates when the conversation ends. orchids packages the whole
operating model — who the agents are, what they know, what rules bind them —
versioned in one place and delivered identically to every repository you own.

## Five agents, one assembly line

You talk to the **orchestrator** — it knows the board, reads your mood, and
suggests what's worth doing next. It never writes a line of code.

While you think, the **bloomer** measures what you actually want: point it
at a fuzzy task and it asks the fewest questions that most reduce
uncertainty — chosen by a statistical engine, not by feel — until the
scope converges with an explicit confidence number. High confidence can
launch the work; anything less comes back to you with the loose ends
named.

Say go, and an **architect** takes ONE feature into its own worktree. It
explores read-only, agrees a plan with you, and touches nothing until you say
**MAKE IT SO**. No surprise diffs, no "while I was in there".

The architect fans the build out to **builders** — headless workers that each
take one tight step and hand back a diff with its own test result.

And when you say it's done, the **housekeeper** runs the close: docs verified,
tagged, squash-merged, pushed, cleaned up. The same close, every single time.

Nothing lives in chat. Scope, findings, decisions, progress — all of it is
files in the repo, so any agent picks up cold exactly where the last one
stopped.

One more agent isn't on the line at all. Every session quietly loads a **bus** —
a sidecar that lets independent agents in the same repository talk to each other,
so the orchestrator can hold a live picture of who is running, how far along they
are, and how much context they have left before they need handing over. You'll
see it as a `messages · …` line in your pane. You never address agents yourself;
it's how they reach each other, not you.

**And you get to watch.** A fleet sidebar mounts automatically as a pinned left
pane in every orchestrator and architect window: a live tree of every
repository, the features under it, what each one is doing *right now*, and any
sub-agents in flight — all read straight off the bus (agents broadcast
`orchid:activity:<text>` and `orchid:subagent:start|done:<label>` as ordinary
messages; no extra machinery). Rows carry a status emoji, flash when something
is waiting on **you**, and arrow keys + Enter jump you straight to that work's
tmux window. It shows the current repository by default; list more in
`~/.config/orchids/sidebar-repos` (one path per line) or `ORCHIDS_SIDEBAR_REPOS`.

## Bus messages, as built (audit inventory, 2026-07-25)

The complete set of pre-fixed / formatted messages that exist in the codebase
today (`tools/bus.py` + the agent definitions), recorded here as the baseline
for the redesign. Delivery is unconditional fan-out: every message is copied
into every registered session's spool folder — dead inboxes included — and
every live agent's bus sidecar wakes on every copy.

| Format | Sent by | Defined in |
|---|---|---|
| `announce` — identity envelope (session id, feature, `exit_grace_seconds`) | bus sidecar at session start | `bus.py announce` |
| `depart` — departure broadcast | bus sidecar at session end | `bus.py depart` |
| `signal --state started·building·testing·done·finished·blocked·abandoned` | agent (to parent, else broadcast); `--on-behalf-of` is orchestrator-only | `bus.py signal` |
| `orchid:activity:<free text>` | **agents directly** (`bus.py broadcast`, "never spend a bus-agent turn on it") | orchestrator/architect/bloomer/groomer definitions |
| `orchid:subagent:start:<label>` / `orchid:subagent:done:<label>` | agent via its bus sidecar | orchestrator/architect definitions |
| `ask --question --option… [--multi]` — blocking question broker; replies `{index}`, `{indices}`, or `{continue}` | agent | `bus.py ask` |
| Fixed request bodies `identity`, `status` | any agent; answered by the recipient's sidecar without waking its parent | `bus.py` FIXED tuple |
| Envelope flags: `notify_user`, `operator_origin`, `in_reply_to` | any sender | `make_envelope` |

Two audit findings the redesign must correct:

- **There is no single send path.** Agents are *instructed* to call `bus.py
  broadcast` directly for activity; sidecars send announces, relays, and
  subagent markers; nothing blocks any tool, so any agent can send anything
  at any time. Single-choke-point sending does not exist today.
- **The noisiest traffic is not in the codebase at all.** The repeated
  `awaiting operator (native prompt)` waiting-state broadcasts match no
  string in any definition or tool — sidecars improvise them, which is why
  they duplicate freely.

Measured cost of this design (2026-07-24, one heavy day, ~4 live agents):
the sidecar layer alone consumed ≈150–200k subagent tokens (~1k per message
per listener); the hand-ups re-invoked parent agents with full context
≈45 times in the orchestrator alone — order of 7M cache-read tokens plus
~0.3M fresh working tokens attributable to bus chatter, dominated by
duplicate waiting-state rebroadcasts carrying zero information.

Fix a lesson once, and every repo knows it on the next sync.

**Discipline that holds.** The `workflow` and `workflow-complete` pair enforce
the gates — feature branches, agreed testing, your explicit approval, an
identical close. `git-commit` makes history readable, `clean-code` keeps the
output short and honest, `readme-sync` stops this very file from lying, and
`diagnostics` turns "it's broken" into one reproducible script instead of an
hour of flailing.

**House rules for your stacks.** `coding-dotnet`, `coding-tofu`, and
`coding-lmstudio` carry the conventions for .NET, OpenTofu, and local-LLM
work; `shortcut-file` reads and writes Apple Shortcuts at the byte level;
`software-catalog` knows the apt dependency rule that once nuked a desktop —
so no agent repeats it.

**A forensics lab, ready to open.** Evidence handling with a command-level
`chain-of-custody`, full `forensic-acquisition` to signed E01 images,
`read-apfs` for encrypted Apple volumes on Linux, `machine-access` for locked
Macs without lowering their defences, `icloud` rescue before data is lost,
`reverse-engineering-files` for opaque formats, `digital-signature` for
smart-card-sealed manifests, and `write-to-s3` for tamper-evident off-site
storage.

**And the model's own machinery.** Skills that keep the agents honest
(`read-agents`, `agent-behaviour`), pass work between sessions without leaking
chatter into history (`handover`), bloom the board (`bloom-tasks`, `orchestrator`),
migrate a grown-wild repo into the canonical shape (`history-rewrite`), and
teach agents to write new skills properly (`authoring-skills`).

**Upgrades that catch every repo up.** When the package moves or reshapes a
managed file, it ships a dated entry in `migrations/` — state-guarded
instructions any agent applies in one pass, prompted by a hook the moment a
repo is behind. A repo that skipped ten upgrades converges the same way as one
that skipped one; the highest migration date IS the package version. Every
session keeps a small rolling log in `.git/the-works/` — physically
uncommittable, shared across worktrees — so a reset or an agent swap never
loses the thread: the successor reads the stream's logs and continues. And
when the ask is just a typo fix, the agent offers a single commit on `main`
instead of the full branch ceremony — you say yes, it stays micro.

**The board follows you off the terminal.** Active tasks mirror to GitHub
issues and the private **Orchidarium** project view; file an issue from your
phone and an actor-gated workflow folds it back into the file board before the
next session even starts (`tools/board_gh.py` — files stay canonical, GitHub
is the couch-friendly view).

**And the pipeline itself rides GitHub too.** On the package repo the same
spine runs on issue comments (`cloud-path` workflow): the feature is an issue,
and your comments are the gates — `ENGAGE`/⚙ kicks off the plan, `MAKE IT
SO`/🖖 builds and opens the PR, `THAT IS ALL`/🚪 sends the housekeeper to
squash-merge it. Only your comments count, and no gate ever approves itself.

## What it is not

orchids is **data only** — no code, no installer. Distribution is
[kauk](https://github.com/serialseb/kauk)'s job: bootstrap any repo by telling
your agent **"install kauk/orchids"** — it resolves the repo on GitHub and
follows [`Agent-installation.md`](Agent-installation.md).

How the pipeline, the gates, and the delivery mechanics actually work:
see [ARCHITECTURE.md](ARCHITECTURE.md).

- created: 2026-07-17
- created_by: opus-4.8
- completed: 2026-08-08
- completed_during: f/courier-messaging

### Why cancelled

Folded into `project-inbox.md` (operator, 2026-08-08) — the same idea, now
WITH a design it never had: messages, files and tasks posted to a project's
inbox, gardener-ingested live or at next start. This sidecar remains the
archive of the 2026-07-17 rulings and the refs/sensitive leak measurements;
the load-bearing parts are carried into the successor's Findings.

## Blockers
- None technically. But the sensitive-content rule (`AGENTS.shared.md`) constrains the
  design hard and must be settled before any format is fixed — see Questions.

## Questions
- **Push or pull?** Sender writes into the receiver's tree (needs the checkout on-box
  AND write access to someone else's repo), or sender writes an *outbox* in its OWN
  repo and the receiver pulls. Pull is the safer default — nobody writes another repo's
  tree, which is the exact failure this task exists to prevent — but it needs the
  receiver to know where to look.
- **Committed or uncommittable?** `HANDOVER.md` lives in `.git/` because it carries
  chatter and sensitive content. A cross-repo *requirement* is durable technical state,
  which argues for a committed path. But a message from a forensics repo could carry
  incident detail, and `AGENTS.shared.md` forbids sensitive content entering git history
  anywhere. Possibly two channels, possibly a hard "sanitized only" gate on the inbox.
- **Ingest-and-delete, or durable + acknowledged?** HANDOVER is deleted on sight. A
  requirement should probably become a task on the receiver's board and *then* the
  message dies — that is a different lifecycle, with an ack the sender can observe.
- **Who ingests, and when?** Receiving gardener at boot is the obvious hook (it
  already ingests HANDOVER there). Cost: another boot-time read on a role that is
  deliberately lean.
- **Sensitive content: ENCRYPTED AND KEPT, not deleted** (operator ruling, 2026-07-17).
  Delete-and-sanitize was considered and rejected: a message that warrants a task is
  persistent by definition, so destroying it destroys what the task needs.
  "Sensitive but not persistent" is an incoherent category. The gardener encrypts
  sensitive information at board blooming; `content: sensitive` marks content to
  **encrypt**, not to delete. Open below — this ruling sets the direction, not the
  mechanics:
  - **This contradicts a hard rule in an immutable file.** `AGENTS.shared.md` says
    sensitive content NEVER enters git history and goes ONLY to the uncommittable
    `.git/` channels. Committing ciphertext is sensitive content entering history —
    satisfying the rule's *intent* (nothing readable leaks) while breaking its *letter*.
    That file MUST NOT be modified without an explicit operator request. Needs a ruling
    before anything is built.
  - **Encrypted to whom?** The landscaper implementing the task must read it, so the key
    has to be reachable by an agent. That means this does not defend against a local
    attacker — it defends against *publication*. Naming the threat model decides the key
    choice: an operator smart-card key (strong, but every read needs a PIN — gpg
    Pinentry already timed out mid-session on 2026-07-17) vs a repo-local key (agent-
    readable, publication-safe only).
  - **Granularity:** whole sidecar encrypted, or marked blocks inside a plaintext
    sidecar? Blocks keep the board greppable and the task renderable; whole-file is
    simpler and leaks less metadata.
  - **Publication interaction, unresolved:** orchids is heading for publication
    (`pre-publication-cleanup`, urgent). Ciphertext committed now is ciphertext
    published later, permanently. If sensitive tasks are instead confined to the private
    side of that split, the encryption question may narrow considerably — decide the
    split first, or at least alongside.
  - Blooming is done by the `bloomer` agent as well as the gardener; both need this,
    or the rule has a hole.
- **Storage: in-tree, or on an invisible ref?** (operator, 2026-07-17 — leading idea.)
  Sensitive content need not live in the working tree at all. Store it the way `git
  notes` are stored: on a ref outside `refs/heads/*`, so it is **neither pushed nor
  cloned by default**, and objects reachable only from it never travel.
  - **This repo already proves the mechanism.** The `workflow-complete` skill mandates
    pushing "commits + tag + **notes**" as separate acts — it has to name notes
    explicitly precisely because they do not ride along on a normal push. That property
    is the feature here.
  - **It answers the publication objection structurally**, not by discipline: the
    boundary is "was this ref ever pushed", which is a mechanical fact, not a rule an
    agent must remember. Compare option (a), which is discipline-only.
  - **It composes with encryption rather than competing.** Hidden ref = not published.
    Encrypted = survivable if it ever is. Belt and braces; pick both or state why not.
  - **DECIDED (operator, 2026-07-17): a dedicated ref namespace, `refs/sensitive/<id>`,
    NOT notes.** Notes anchor to a commit; a task is not a property of a commit.
  - **`<id>` is a reference ID, never a number.** A number implies a sequence, and
    **nothing is linear once several agents work at once** — the same reasoning that
    makes board ids file basenames rather than counters. Default guess: the same id as
    the feature (so it matches the sidecar name), but a feature may carry SEVERAL
    sensitive items, so the scheme must allow more than one per feature. Shape still
    open: `refs/sensitive/<feature-id>` holding many, vs one ref per item with a
    distinct id.
  - **The sidecar references the id and says where to find it** — the plaintext sidecar
    stays the spine; the ref is where the sensitive part lives.
  - **DELETION IS THE POINT, and only this option delivers it** (operator, 2026-07-17):
    a rule must require private/encrypted content to be deleted once it is no longer
    needed — e.g. the feature is complete and the information has no further value.
    `git update-ref -d refs/sensitive/<id>` plus gc makes the objects unreachable and
    they are genuinely gone. **No history rewrite, no filter-repo, no scrub ceremony.**
    Sensitive content committed in-tree can NEVER be removed that cheaply — that
    asymmetry is arguably the strongest argument for this storage choice.
    Open: who fires the deletion? The `groundskeeper` owns the deterministic close and is
    the natural candidate. And who judges "no further value" — is it automatic at close,
    or operator-gated? (Operator's thought was cut off mid-sentence; confirm the
    intended trigger before building it.)
  - **TESTED 2026-07-17 — the "never travels" claim is HALF FALSE. Read this before
    designing anything.** Empirical results from a scratch repo with a canary on
    `refs/sensitive/foo`:

    | operation | sensitive object travels? |
    |---|---|
    | `git push <remote> main` (default) | **no** — safe |
    | `git clone --no-local <path>` | **no** — safe |
    | `git clone file://<path>` | **no** — safe |
    | `git clone <local-path>` (plain) | **YES — LEAKS** |
    | `git clone --no-hardlinks <path>` | **YES — LEAKS** (does not help) |
    | `git push --mirror` | **YES — LEAKS** (expected) |

    A plain local-path clone takes the **local hardlink/copy optimisation** and copies
    the WHOLE object store. The refs do not come across (recipient sees only
    `refs/heads/*`), but the objects do — and **`git fsck --lost-found` surfaces the
    dangling commit blind, no SHA needed, content fully readable.** Only `--no-local` or
    a `file://` URL forces the pack path, which sends reachable-only objects.
  - **THIS IS LIVE IN THE FLEET TODAY.** `bin/kauk:237` runs
    `git clone --quiet "$origin" "$clone"`, and `.ai.toml` origins are local paths
    (`origin = "/home/sudoku/src/serialseb/orchids"`). So every vendored clone under
    `.ai/repositories/` in every consuming repo would carry every sensitive object,
    recoverable by anyone with `fsck`. **kauk must clone `--no-local` (or `file://`)
    before `refs/sensitive/*` is safe** — a kauk-side requirement, so it belongs on
    kauk's board when this design lands, not specified here.
  - **Deletion VERIFIED to work, but needs an explicit prune.** `update-ref -d` alone
    leaves the object in the store. `git reflog expire --expire=now --all &&
    git gc --prune=now` removes it — confirmed: object gone, canary absent from all of
    `.git/`. So the retention rule must specify the prune, not just the ref delete.
    (Default gc would get there eventually — ~2 weeks — which is not a guarantee worth
    resting on.)
  - Still unverified: whether `git rev-list --all` reaching `refs/sensitive/*` (it does)
    matters for any tooling that scans it; behaviour on GitHub/forge mirroring.
- **Whose component is the transport?** The protocol and the rules are orchids
  (workflow component). If delivery needs more than a shared filesystem or a git remote,
  that is kauk `federation` — and per its own rule, it gets filed on kauk's board, not
  specified here.

## Findings
- **There is no channel today, and its absence caused a real boundary violation on
  2026-07-17.** orchids decided the role-DAG model and needed kauk to build the reader.
  With no protocol, the orchids gardener wrote a task directly into kauk's working
  tree — authoring on a board it does not own, setting another project's badge,
  component, and priority. Operator ruling on the correction: work to be done by kauk
  *belongs* in kauk's repo (moving it there is right; deleting it would lose it). What
  was missing was a legitimate way to deliver it.
- **`HANDOVER.md` is NOT the precedent — it is a different process** (operator,
  2026-07-17). It exists so a subagent can hand information back to its agent: **one
  way, one round, every time**, then dead. It is uncommittable because of that
  **lifecycle** — nothing in it needs to survive, and it is never the input to creating
  a piece of work — NOT because of a sanitization policy. Reasoning "handover is
  uncommittable, therefore inbox messages are too" is a false analogy and was made once
  already in this task's history; do not make it again.
- **The inbox inverts every one of those properties.** Peer↔peer, not subagent→agent.
  Durable, not one-round. And it exists precisely to be the input that creates work on
  the receiver's board — which is why the content must persist, and why deleting it
  after a sanitized rewrite destroys the point of sending it.
- **Board edges are single-board by construction.** `⊘`/`~` ids are resolved by
  `board_lint.py`'s no-orphan-subtasks rule against entries on the same board, so a
  cross-repo dependency is unexpressable and unlintable. Today orchids' `role-delivery`
  → kauk's `role-aware-delivery` gate survives only as prose in two Findings sections.
  Both boards are one `git pull` from forgetting each other, and nothing will complain.
- kauk already carries a `federation` functionality (auth-broker, backends). If this
  ever needs transport beyond an on-box path, that is where it lives.

## Proposal
Sketch only — the push/pull and sensitive-handling forks above decide the shape, and
they are the operator's. Leading candidate: each repo owns an **outbox** of sanitized,
addressed messages; the receiving gardener pulls at boot, converts each into a task
on its own board, and acks. The sender never writes the receiver's tree. Message kinds
worth distinguishing early: *requirement* (do this), *knowledge* (this is true, you will
need it), *ack* (filed as `<id>`).

Fixed by operator ruling (2026-07-17), not open:
- **The inbox does NOT inherit the handover's rules — it is a different process.**
  See Findings for why. The `.git/`-only rule is a consequence of the handover's
  lifecycle, not a general sanitization policy to be copied here.
- **Sensitive content is encrypted and kept**, because it is the input to creating work.
- **External blockers are resolved when the gardener loads its tasks** — see the
  sibling task `external-blockers`, which owns that half.

## Testing
Two scratch repos: A posts a requirement to B; B's gardener boots, files it as a
real task on its own board, and acks; A observes the ack. Assert A never wrote to B's
tree. Negative test: a message carrying sensitive content is refused, not merely warned
about. Board lint stays clean on both sides throughout.

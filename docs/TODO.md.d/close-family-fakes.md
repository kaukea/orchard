- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (courier board triage)
- status: done

## Blockers

- ~~⊘[[bus-finishing]]~~ CLEARED (2026-07-26): the bus landed — merged to
  main with the full suite green (332 passed). Round 2 starts now
  (Decision-090 ordering: "the moment bus-finishing lands"). Context kept:
  the operator believes these are FAKE PROBLEMS, symptoms of the old
  fan-out/close design — the round examines them against the finished bus
  instead of building onto the old one.

## Questions

- Per item: still real once the bus is finished? The expected answer for
  most is "dissolved — close with evidence".

## Findings

- OPERATOR RULING (2026-07-25): "I believe all of these are fake problems" —
  [[close-dispatching]] (already handled by documentation: the gardener's
  redispatch duty), [[window-closing-owning]], [[zombie-revival]],
  [[sidebar-witnessing]]. One second-round feature addresses them together.
- sidebar-witnessing in particular is expected to dissolve with the fan-out
  cut (the observed inboxes cease to exist; topics have no ghost-row
  mechanics).
- DELIVERED SUBSTRATE (bus-finishing result, 2026-07-26): flat orchard
  transport under `$XDG_RUNTIME_DIR/orchard/{projects,topics}/`; a CLOSED
  22-subject corpus, exact-match — there is no `finished` subject. A
  landscaper's end reaches its parent as a directed `:session:<parent>`
  `orchard:agent:lifecycle:stopped` (+ `orchard:agent:outcome:success|fail`);
  liveness is the passive `<sessionid>.marker` mtime heartbeat; the courier
  is a per-agent singleton closing by self-message wake. The groundskeeper's
  trigger MUST be phrased in this corpus.
- Bus-finishing deferred two LIVE acceptance checks to post merge+sync+
  restart (sidebar shows activity after the cut; a real close leaves zero
  orphan monitors). The sidebar-witnessing dissolution verdict cites these
  observed-live, not deleted code paths alone.
- Bloom round (2026-07-26, pre-launch, Decision-050): WHAT confirmed current
  against Decision-090; wire vocabulary corrected to the delivered corpus;
  scope boundary vs [[summon-restarting]] and the detected-death trigger
  surfaced as operator questions. Adaptive engine not run (non-interactive
  dispatch) — no convergence number claimed; assessment judgement-based.

## Proposal

RULED (operator, 2026-07-25 afternoon — Decision-090): the build IS the
SUPERVISING CONTROLLER, started immediately when [[bus-finishing]] lands:

- OPERATOR RULING (2026-07-26, gardener session): the flow moves to a
  DEDICATED SUPERVISOR subagent. The gardener only asks it to start the
  work; the supervisor decides which agent runs, detects when work is
  closing or closed (bus lifecycle events), and calls the next agent —
  choreography CENTRALISED, agents blind to one another, the flow decidable
  per task. Constraints preserved: operator gates relayed verbatim, never
  absorbed; creator-owns-and-cleans stays structural one level down (the
  supervisor releases what it creates; the gardener releases the supervisor
  and watches for ITS death); supervision collects, never kills
  (Decision-081); writer writes once — the supervisor choreographs, never
  authors. This amends Decision-090's homing clause ("the gardener's own
  groundskeeper" → the groundskeeper fires inside the gardener's supervisor
  subagent) — formal supersession entry recorded on the implementing branch,
  not before (Decision-006 precedent). Settles the controller-home question:
  the supervisor is built ONCE here; [[summon-restarting]] consumes it.
- OPERATOR REFINEMENTS (2026-07-26, same session): the supervisor EXTRACTS
  the information the next agent needs before calling it (the extract builds
  the next agent's context); it SELECTS which agents run based on that data.
  It OWNS the pipeline from the moment the gardener launches it to the
  moment the gardener is notified of the result — so death/timeout
  verification is the supervisor's job: checking on another agent is done by
  ASKING the supervisor. It sleeps waiting for status changes and wakes on a
  3-MINUTE fallback when no event arrives, self-checking that the pipeline
  still works — an operator-ruled bounded exception to the no-timer ban.
  (Reading confirmed by the operator, 2026-07-26.)
- The side agent — real-time decision enforcement: monitors a working
  agent's ACTIVITY, enforces recorded decisions, yes/no at each relevant
  phase, a no forces rework at the moment of deviation — is NAMED Valve 💧
  and is a SEPARATE agent from the supervisor (operator, 2026-07-26): the
  beekeeper routes and never checks, Valve checks and never routes. Valve
  is designed in its own round immediately after this design ([[valve]]).
- The close moves out of the landscaper: the supervisor's groundskeeper
  fires on the landscaper's directed `orchard:agent:lifecycle:stopped`
  (outcome via `orchard:agent:outcome:success|fail`) or on the supervisor's
  own death/timeout verification (above) — and releases what its creator
  scope created — worktree, branch, window — in reverse creation order.
- The landscaper becomes a pure scope: its courier, monitors, sowers and log
  all die inside it before exit (final State + `_closed` + telemetry are its
  LAST acts); it dispatches no closer and touches no window. `.return-window`
  retires — the parent knows its own pane.
- Supervision collects, never kills (Decision-081). The lease/ledger pattern
  is REJECTED — assumes idempotent work, not achievable.
- The four fakes are then re-examined against the new shape; expected: most
  dissolve — close what dissolved with evidence, rescope any residue small.

Sibling work item, same trigger: [[tmux-topology]] — the raw tmux layer made
to work correctly per a WRITTEN spec (operator: "this time I want this
written down").

## Voluntary deferrals (explicit, not blockers)

- ~~Death-detection HOW~~ RULED (operator, 2026-07-26): the supervisor
  checks — it owns the pipeline, sleeps on status events, wakes on a
  3-minute fallback to self-check pipeline health; anyone verifying another
  agent's liveness asks the supervisor.
- Question-broker sub-agent form, `:session:operator` allowlist bypass,
  focus-reclaim-on-closed: the new tmux/operator-interaction component
  (bus-finishing follow-up 2), not this build.
- `sidebar-registry.json` rename (now courier-allowlist-only, name a
  misnomer) and minor sidebar debts (reject-telemetry old layout,
  `progress_pct`, red RGB): bus-finishing follow-ups 3–4, not this build.

## Testing

Per surviving item at rescope time; the dissolution verdicts themselves are
evidence-based (code paths gone, reproduction impossible).

Python changes on this branch are covered: **338 passed, 3 subtests** under
`python3 -m pytest tests -q`. NOTE FOR EVERY FUTURE SESSION: run PYTEST, not
`python3 -m unittest discover`, which collects only 312 and silently omits
bare-function tests. Green was reported three times this session from the wrong
runner, hiding a test broken by this branch's own change.

The CHARTER changes (agents/*.md prose) are NOT exercised by any test. They are
verified by reading, and their first real execution is a live feature close.

#### 3. zombie-revival (gh#30) — **DISSOLVES AS FLOW, SURVIVES AS DIAGNOSTICS**
Not a plain dissolution. The verdict splits by PURPOSE, not by mechanism.

As a FLOW mechanism it is gone, three ways over:
- Delivery to an absent parent is a no-op, not a resurrection: `tools/courier.py:582`
  prints `signal <state> — no parent known, not delivered`, and the fan-out that
  would have sprayed a message at every session is retired.
- Liveness is PASSIVE — `agents/supervisor.md:183`, marker mtime plus lifecycle
  signals. A stale marker with no terminal `stopped` reads as a silent death; nothing
  pokes the corpse to find out.
- Reviving as REPAIR is explicitly forbidden: `agents/supervisor.md:136` — publishing
  to a stopped agent revives its whole session, which is expensive and restores the
  very context that produced the wrong result. Rework spawns a FRESH agent with the
  same instructions plus what went wrong.

The real finding is that revival was the ASSUMED repair path, and it was ruled out
this session on COST grounds. The zombie fear dissolves as a side effect of that
ruling, not because anyone hardened the delivery path against it.

**RETAINED DELIBERATELY (operator, 2026-07-27): revival is a DIAGNOSTIC TOOL.** The
one legitimate reason to wake a dead agent is to learn WHY IT DID WHAT IT DID. That is
useful and is not to be designed away. So the rule is by intent, not capability:
- the FLOW never revives — no automatic redelivery, no retry-by-waking, no
  supervisor-initiated resurrection;
- the OPERATOR may revive deliberately, to interrogate reasoning.

This is the same principle as Decision-081's no-kill rule seen from the other side: an
agent that has been reaped cannot be asked anything. **Collecting rather than killing
is what preserves the evidence that makes diagnostic revival possible**, which is why
"leftovers are reported, never reaped" is load-bearing rather than merely polite.

CONSEQUENCE worth naming: diagnostic revival requires a dead agent's context to still
be REACHABLE. Anything that prunes transcripts, archives or session state on a timer
would quietly destroy this capability while looking like hygiene.

#### 4. sidebar-witnessing (gh#193) — **CODE PATHS GONE; LIVE GATE NOT CLEAN**
The only verdict of the four that does not close. Code evidence is strong, live
evidence is not, and the predecessor deliberately gated this one on live checks
precisely because deleted code paths are not the same as observed behaviour.

CODE EVIDENCE (all verified at branch tip):
- The observed-inbox model is DELETED, not deprecated: `tools/sidebar_model.py` and
  `tools/sidebar_v3.py` no longer exist on disk.
- Nothing reads the courier tree at all — `grep the-works/courier tools/sidebar.py`
  returns nothing. The sidebar reads the orchard event tree directly.
- The ghost-row mechanics are INVERTED. `tools/sidebar.py:177,431,703`: nothing is
  ever excluded or removed by staleness; staleness is a COLOUR, not a removal. The
  symptom class "rows that vanish or linger wrongly" has no mechanism left.

LIVE CHECK 1 — "the sidebar shows activity after the cut": RUN, and it FOUND A REAL
SURVIVING DEFECT. `python3 tools/sidebar.py --dump` against the real runtime returns
ONE repo row (`orchids`) — the worktree fold works live, not only in fixtures — but
TWO rows for the SAME feature.

ATTRIBUTION, settled by fixture rather than guessed (first guess was WRONG and is
recorded here deliberately):
- First hypothesis: a migration artifact of today's branch-keyed slug, since events
  exist in both `kaukea.orchids` and `kaukea.orchids@f-close-family-fakes`.
- Test 1 — same feature id in TWO project dirs → two rows. Consistent with the
  hypothesis, and I nearly stopped here and declared a self-inflicted regression.
- Test 2 — same feature id, two SESSIONS, ONE project dir → **also two rows**.
  So directories are irrelevant. The duplication is PER SESSION and PRE-EXISTING;
  today's slug change neither caused nor worsens it.

- Test 3 — inspected the actual live events. The two rows are two SESSIONS on this
  feature: `7dce8be9` (predecessor) and `0a92186d` (this one). My own session appears
  in both project directories only because the slug changed mid-session today, which
  is a one-off of the migration and not a display issue at all.

**NOT A DEFECT — this is the specified behaviour** (operator, 2026-07-27): the
success/failure of previous TASKS is KEPT until the FEATURE is complete. Two rows for
a feature that has had two tasks is correct and deliberate. `ARCHITECTURE.md` says so
plainly and I read past it: "a task whose agents have all stopped stays on screen as a
single row carrying its final state" — retention is the point, not a leak.

RECORDED AS A PROCESS FAILURE, because it is more useful than the finding was: I
produced THREE successive wrong explanations for one observation — migration artifact,
then self-inflicted regression, then pre-existing defect — each investigated
competently and each wrong, because I was looking for a defect and never established
what the display was SUPPOSED to do. Reading `ARCHITECTURE.md`'s display hierarchy
first would have cost one minute and prevented all three. Live evidence without the
intended behaviour to compare it against produces confident nonsense.

LIVE CHECK 2 — "a real close leaves zero orphan monitors": PARTIAL. This session's
courier release was verified by `pgrep`/`ls`: its own watcher and mailbox gone, the two
other live sessions' watchers untouched. That is one agent's release observed clean,
not a full feature close.

VERDICT: **NOT RULED — I am not competent to close this one, and a fourth guess would
be worse than an honest gap.** The code evidence for dissolution is genuine and stands
(the observed-inbox readers are deleted, nothing reads the courier tree, staleness is
a colour and never a removal). The live gate produced no defect once the intended
behaviour was understood. But I demonstrably did not understand how the sidebar is
meant to work while ruling on it, so my "dissolved" would rest on the same footing as
my three retracted defects.

RETURNED (follow-up 12) for someone who holds the display model: confirm the three
original symptoms against INTENDED behaviour rather than against absence of code, and
finish live check 2 — a full feature close leaving zero orphan monitors. Only a single
courier release was observed clean this session.

## Findings (successor-2, 2026-07-27)

Written against `main` @ 2260f35, branch tip as of this entry. Paths this rests
on: `tools/courier.py`, `tools/sidebar.py`, `tools/orchard_topic.py`,
`agents/*.md`, `hooks/courier-end.sh`.

### The four fakes — VERDICTS

Re-derived against the branch tip, not inherited. The predecessor's proposals in
`architect-session.md` were written against an older SHA and are not repeated on
trust.

#### 1. close-dispatching (gh#258) — **REFRAMED, not fake**
The DUTY question dissolves. Ownership of the close is now single and explicit:
`agents/gardener.md:242` ("You do NOT dispatch the groundskeeper — the feature's
SUPERVISOR does"), `agents/supervisor.md:198` (the supervisor fires it),
`agents/landscaper.md:142` (dispatches no closer). Three charters, one owner, and
the trigger is structural (`lifecycle:stopped` + `outcome`) rather than a duty
someone must remember. `agents/gardener.md:293` homes redispatch-on-detected-death
to the supervisor too.

BUT THE SYMPTOM WAS REAL. The issue was filed as "nobody owns dispatching the
close"; the observable fact behind it was "the close does not fire", and that had a
MECHANICAL cause found this session, in a different layer entirely:
- the courier's only persistent watch was armed on the git-directory mailbox while
  `:session:` traffic lands in the orchard tree, so the close signal woke nothing
  (FIXED this branch);
- `notify_user` is written and policed but read by nobody, so a waiting agent
  surfaces to no one (NOT fixed, returned).

This is why re-homing the duty never made the symptom go away — the issue was filed
against the wrong layer. CLOSE the ownership issue with this evidence; the residual
visibility defect is follow-up 1, not this task.

#### 2. window-closing-owning (gh#215) — **DISSOLVED**, with one real residue
Both halves resolved, and the second was OBSERVED working this session rather than
argued.

The KILL half is dead by ruling: Decision-081 (`docs/decisions.md:1353`) —
"Supervision kills are removed — no agent kills another; tree removal is the close's
last act". This branch carries it consistently: `agents/supervisor.md:35,186,262`,
`agents/groundskeeper.md:91-92`, `agents/gardener.md:301`, `agents/courier.md:335`.
Reaffirmed by the operator today in the strongest terms — "someone was killing it
before and doing real damage" — so this is not merely documented, it is a standing
constraint with a remembered cause.

The SELF-CLOSE half is the live design and was DEMONSTRATED END TO END this session:
this landscaper's courier posted `lifecycle stopping`, stopped its Monitor and
removed its own watcher and mailbox, left the two OTHER live sessions' watchers
(`b7b08d47`, `2eaf05b6`) untouched, then posted `lifecycle stopped`. Verified by
`pgrep` and `ls` afterwards, not taken from the courier's own report. That is the
whole of what the issue asked for — an agent closes itself, and nothing reaches into
what it did not create.

RESIDUE (real, returned as follow-up 5): self-close depends on an agent NOTICING it
should close. Removing the git-directory mailbox removed the structural signal that
used to carry that — a courier's mailbox vanishing WAS its parent's absence. That
detection now rests entirely on `hooks/courier-end.sh` landing, a single point of
failure that fails silently. The ownership question is settled; the TRIGGER for it is
weaker than it was, and must not be answered with a reaper.

**SUPERSEDED IN PART by the operator's placement ruling of 2026-07-27** (staged as a
decision entry). Under it the answer is not "who owns the window closes it" but
"nobody in the flow touches windows at all": a launcher states logical placement in
one of four words — `none`/`sibling`/`child`/`background` — and a PLUGIN SUBAGENT in
its context realises it, waits for `starting`, sleeps, and closes the UI element once
`stopped` has happened. Creation and destruction live in one component, driven by the
two lifecycle events.

That makes the issue's whole framing obsolete rather than merely resolved: an agent
cannot own or close a window because it never learns one exists. It also RETIRES
`tools/landscaper-teardown.sh` as a self-teardown and `.return-window` with it, and
weakens the residue above — the agent no longer needs to notice anything; it announces
`stopped`, and the placement component acts on it.

NOT APPLIED ON THIS BRANCH. `agents/landscaper.md:167` still instructs the self-
teardown, which now contradicts the ruling. Returned as follow-up 11.

### Why the close gate has been dead for days — TWO independent breaks
1. **Delivery.** The courier's only persistent watch was armed on the git-dir
   mailbox; `:session:` traffic lands in the orchard tree. The orchard tree was
   watched ONLY by `_wait_for_orchard_activity()`, whose callers are the
   request/reply waiters — so an unsolicited message woke nothing unless the
   courier already happened to be blocking on a reply. FIXED on this branch.
2. **Visibility.** `notify_user` is written and heavily policed but READ BY
   NOBODY; its only named consumer (`sidebar_model.py`) is retired. The
   waiting-at-gate summons therefore surfaces to no one. NOT FIXED — not mine.

### Other verified defects found en route
- `--operator-origin` was never wired through `orchard_send`, so provenance had
  been a silent no-op on every directed send since the bus landed. FIXED here.
- `hooks/courier-end.sh` sent a bare `--to "$sid"`, rejected by orchard-only
  `send` and swallowed by `|| true` — silently breaking the courier's release
  self-wake. FIXED here, verified end to end.
- `orchard_receive_own()` and `_find_orchard_reply()` share a glob and both
  unlink, so a continuous monitor consumes replies a blocked `request`/`ask` is
  waiting for. Handed to the monitor sower with a required test.

## Result

Result: **done** — merged by operator decision (2026-07-27) with verdict 4 unruled.

OPERATOR RULING at close: "we can't merge without seeing and we cannot see without
merging". The sidebar cannot be judged from inside the branch that changes it, the
remaining sidebar + tmux-extraction work is large, and holding this branch would keep
the transport repairs — including the fix that revives the operator's close gate — out
of main for no gain. Merged deliberately with follow-up 12 outstanding, NOT because the
verdict was reached.

Three of four fakes ruled and closed with evidence (1, 2, 3 above). The fourth is
returned, not resolved. Branch: `f/close-family-fakes`, 345 passed + 3 subtests under
`python3 -m pytest tests -q`.

## Operator follow-ups (RETURNED — not board-edited, not fixed here)

Operator instruction, 2026-07-27: notify_user and the `ask` work are NOT complete;
they were requested but **the tmux part must be EXTRACTED into its own task**.

1. **`notify_user` has no consumer.** Written and heavily policed, read by nobody;
   only named consumer `sidebar_model.py` is retired. The waiting-at-gate summons
   surfaces to no one. INCOMPLETE per the operator.
2. **The `ask` path is dead in practice.** The standalone question broker is built
   (`tests/test_orchard_question_broker.py`, 60 tests) but NOT RUNNING, so
   `courier.py ask` cannot deliver. Live-hit this session: my own ask returned
   "the operator never received the question". INCOMPLETE per the operator.
3. **EXTRACT THE TMUX PART** of 1 and 2 into a separate task (operator ruling).
4. **Outbox is LOCAL, and means coalesce / send-now / batch-interval** (operator).
   Its value: "post only on CHANGE" is prose discipline today and gets ignored;
   coalescing makes it structural. A local outbox is single reader AND single
   writer, so none of the inbox hazards apply. It is also where retry would live —
   `orchard_send` writes straight to the target with no delivery guarantee.
   Priority is next, per operator.
5. **Orphan detection has no structural signal.** Removing the git box removed the
   fact a courier observed (its mailbox vanishing WAS its parent's absence).
   Detection now rests entirely on `hooks/courier-end.sh` landing — a single point
   of failure that fails silently. NOT to be solved with a reaper: an agent cleans
   up after itself, nothing deletes on its behalf (operator: "someone was killing
   it before and doing real damage"). Leftovers are REPORTED, never reaped.
6. **1088 stale `tmp*` project directories** in the live runtime
   (`$XDG_RUNTIME_DIR/orchard/projects/`), each holding a `.marker`, timestamped
   in two clusters 2026-07-26 23:09 → 2026-07-27 01:21. Look like leaked test
   fixtures writing into the REAL runtime dir. NOT touched.
7. **Dead code after the git-box removal**: `tests/support.py::courier_root_of()`
   references a removed layout; `docs/TODO.md.d/orchard-renaming.md:58` still cites
   `courier.py root`.
8. **`agents/courier.md` "On load" still calls `courier.py receive`** before arming
   the Monitor. Harmless (idempotent, delete-on-read) but now redundant with
   `monitor`'s own initial drain.

9. **RENAME `supervisor` — the name is neither orchids nor orchards** (operator,
   2026-07-27). Operator proposal: **beekeeper** 🐝. NOT APPLIED — naming is the
   operator's call and this is a file rename plus every reference. My read: it fits,
   and for reasons beyond vocabulary — a beekeeper tends many hives at once (the
   concurrency correction), the bees do the work so the keeper never makes honey
   (choreographs, never authors), it does not check the honey either (that is
   Valve), and the craft is smoke and calm rather than killing (Decision-081).
   Weak point: our workers are garden-side (sower, landscaper), so "the bees" maps
   onto nobody — cosmetic.
   CONSEQUENCE TO SETTLE WITH IT: `agents/supervisor.md` still states it carries no
   Decision-085 glyph because it is an internal gardener subagent. That is ALREADY
   STALE — this branch established the role is session-bearing and stateful. A named
   role wants a glyph; recommendation is a glyph but NO `step:`, since it routes
   across all five phases rather than occupying one (the courier precedent, and
   `resolve_step` fails open so nothing breaks).

10. **Decisions carry TWO dates — ruled, and last confirmed** (operator ruling,
    2026-07-27). The older an entry, the likelier it is stale; an agent reading one
    with a wide gap asks for confirmation instead of applying it. Staged as a
    decision entry. The FORMAT CANON is `AGENTS.files.md` §Decisions and must be
    updated there — NOT done here, because file formats are the operator's sole
    responsibility. Applying it also implies a backfill question for existing
    entries (do they get a `confirmed` of their original date, or none until
    someone actually checks?), which is the operator's call and affects roughly a
    hundred entries.

11. **Logical placement is four words, realised by a plugin subagent** (operator
    ruling, 2026-07-27, staged as a decision entry). A launcher states only
    `none`/`sibling`/`child`/`background`; a subagent in its context uses whichever
    plugin is installed, waits for `starting`, sleeps, and closes the UI element
    once `stopped` has happened. Same script signature per plugin — ssh by default,
    tmux or Ghostty added. This is the tmux extraction asked for in follow-up 3, and
    the home for `notify_user`/`ask` in follow-ups 1-2, since "show the operator
    something" is the same capability with the same degradation on plain ssh.
    NOT APPLIED. Contradicts `agents/landscaper.md:167` (self-teardown) and retires
    `tools/landscaper-teardown.sh` as a self-teardown plus `.return-window`.

12. **sidebar-witnessing: NOT RULED — needs someone who holds the display model.**
    Code evidence for dissolution is genuine (observed-inbox readers deleted, nothing
    reads the courier tree, staleness is a colour never a removal). The live gate
    produced no defect: multiple rows per feature are RETAINED TASK STATE by design —
    success/failure of previous tasks is kept until the feature completes (operator,
    2026-07-27). I produced three wrong defect explanations for that one observation
    before learning what the display was supposed to do, so my verdict is withheld
    rather than guessed a fourth time. Confirm the three original symptoms against
    INTENDED behaviour, and finish live check 2 (a full feature close leaving zero
    orphan monitors); only one courier release was observed clean this session.

## Decision entries

(Staged UNNUMBERED in the workstream log at
`.git/the-works/close-family-fakes/landscaper-successor-2-a1b9.md`, under
`## Decision entries`, for mechanical numbering at fold.)

## Changelog entry

- **The orchard bus is written down.** `docs/orchard-bus.md` records the address
  forms, the closed subject list, the storage layout and the rules that follow from
  them, each claim tagged as operator-stated design, verified-in-code, or a known
  gap. The messaging design previously existed only as fragments across agent
  charters, decisions and code, so every session re-derived it and several built
  against the wrong half.
- **Git-directory mailboxes are gone; the orchard transport is the only channel.**
  The per-agent mailbox under the shared git common directory could not coexist
  with worktrees — the directory is shared by all of them and a subagent inherits
  its parent's session id, so concurrent instances resolved to one mailbox and
  could delete each other's inbox.
- **One orchard project directory per worktree**, keyed by branch as well as repo,
  so agents working different features no longer wake one another. The sidebar
  folds them back into a single row per repo.
- **A courier is woken only for its own mail, and the wake carries the message.**
  Filtering happens at the watch by path and after parsing by subject, and the
  parsed envelope is handed up rather than a filename to go and fetch.
- **Fixed: the operator's close gate could not be delivered.** A courier's only
  standing watch was armed where `:session:` traffic never lands, so an unsolicited
  message woke nothing unless the courier already happened to be blocking on a
  reply.
- **Fixed: `--operator-origin` was a silent no-op** on every directed send, so
  relayed operator words carried no provenance.
- **Fixed: the session-end self-wake was silently failing**, breaking a courier's
  release detection.
- **Fixed: a running monitor could consume a reply** another caller was blocked on,
  including the operator's own answer to a question.

## Readme delta

None. No user-facing surface, CLI flag, build step or developer instruction
changed; `courier.py`'s new `monitor`/`project-dir` subcommands are internal
agent mechanism, invoked by the courier sidecar and never by a person.

## ARCHITECTURE determination

EDITED. `ARCHITECTURE.md` was updated: the transport section described the
repo-scoped `the-works/courier/<sid>/` inboxes as the transport of record, which
is no longer true — they were removed outright, and a project directory is now
keyed `<owner>.<repo>@<branch>`, one per worktree. That is a change to how
components connect (data flow, wiring), which is a stated trigger.

- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

- None.

## Questions

- Which message classes make up the specified vocabulary — lifecycle signals
  (announce/done/finished/abandoned), activity states, subagent start/done,
  notify-user flags, operator-origin relays — and are any missing or
  superfluous?
- Where does the specification live: the bus agent definition, a channel
  schema per [[fleet-documenting]] (which already envisions channels with
  JSON Schemas), or both — and does this task fold into fleet-documenting or
  precede it as the tightening pass?
- What does "more appropriate" rule out — free-form activity wording, ad-hoc
  labels, duplicate waiting-state broadcasts?

## Findings

- Operator intake (2026-07-24): bus messages need tightening, cleanup and a
  specification of what each message DOES; what each agent actually sends
  diverges from any common shape and must be audited and fixed alongside the
  spec.
- Live example from today's session: the architect's waiting state arrived
  twice in a row as identical `awaiting operator (native prompt)` notify
  broadcasts; activity labels are free-form prose.
- Second live example (successor architect, 2026-07-24 close): its
  `orchid:activity:Closing` broadcast was read by its own bus as a
  session-departure signal — free-form activity wording collides with
  lifecycle vocabulary.
- Operator dictation (2026-07-24 evening, first message of the spec — more
  to come): agents carry (a) a STATUS — one or two plain words for what
  they are doing now (reading, writing, messaging, concluding, thinking…),
  each agent choosing its own word, unlike the Claude UI's invented terms;
  and (b) a STATUS UPDATE — the sentence describing current work, aimed at
  the log/main pane, never at the operator. Only ONE main agent is
  interactive with the operator at a time; agents follow one another.
- Operator dictation, message 2: exactly THREE interrupt classes may break
  his flow visually — SUCCEEDED, FAILED, QUESTION. Everything else is
  already covered by status/status-update and must not interrupt. Concrete
  offender: every tmux window continuously flashes its activity flag
  (possibly his rainbow/fabulous plugin) as if everything were interesting —
  it is not: "I like seeing how the soup is made, but I am here to eat the
  soup."
- Operator dictation, message 3 (the cockpit model): statuses stay as they
  are but gain SUMMARIZED versions on top — "here's what I did", "here's
  what happened". A QUESTION, when triggered, arrives right after a summary
  of WHY it is being asked. Feature progress is legible from the sidebar.
  ULTIMATE GOAL: each agent stays in its own window where the operator
  never goes; the ORCHESTRATOR window synthesizes all statuses in a
  structured way — feature positions at a glance, and incoming questions
  carry an immediate summary sufficient to DECIDE WITHOUT LEAVING THE
  WINDOW. Target capacity: driving five or six connected architects without
  ever visiting them. (Ties directly into [[operator-interacting]] —
  questions/gates/summaries as one typed exchange.) His closing sentence —
  "this is one of the reasons I wanted questioning to go through a
  specific…" — was cut off mid-dictation; completion pending.
- Operator dictation, message 4 (sentence completed): questioning must go
  through a specific path that does NOT use the normal UI tool, precisely
  so the interrupt can be QUEUED — waited until the right moment — instead
  of popping in his face. Live pain during dictation: with everything
  active, flashing windows also DING — four sound notifications in five
  seconds — "by this point I will take any decision just for all this to
  go away" (noted: no design decisions are to be extracted from that state
  beyond killing the noise). Immediate mitigation applied by the
  orchestrator, runtime-only and reversible (lost on tmux server restart):
  monitor-activity/visual-activity off, activity-action none, bell-action
  none, visual-bell off — ALL tmux flash/ding suppressed until the designed
  three-interrupt channel (succeeded/failed/question) exists to replace it.
- Operator dictation, message 5: SUBAGENT rows (the white/black-circle rows
  he requested) DISAPPEAR when done — they have nothing to say and nothing
  to display; only FEATURE rows keep the stays-green-at-top rule. The
  centralized cockpit should eventually convey a sense of PERCENTAGE of
  work done — optional, later, blocked conceptually on EPICS (a grouping of
  smaller features toward a big feature, which the current sidebar/fleet
  cluster de facto is) — boarded as [[epic-grouping]].
- Operator dictation, message 6 (musing, explicitly about to be superseded —
  "however, I think I have a better idea"): perhaps the status word could be
  followed by a discreet emphasized/italic name, purely for his orientation
  in the flow. HELD — no action; awaiting the better idea.
- DELIVERY FAILURE, live (2026-07-24 ~20:2x): the operator's row-split
  clarification, relayed via the bus to the working sidebar-titling
  architect, landed in a DEAD inbox (ac9f36c6, the crash-orphaned builder's
  stale spool). The live architect (PID confirmed running) had NO reachable
  bus registration at delivery time despite its own bus sidecar running — a
  bootstrap/registration gap: an in-production agent the bus can neither
  address nor track. Workaround: the orchestrator relayed the clarification
  directly into the architect's pane (tmux send-keys) with provenance
  stated. Third live exhibit for this task, and corroboration for
  [[sidebar-witnessing]]'s observer gap from the sender's side.
- Operator dictation, message 7 (phase model, checked against the built
  pipeline): features move through phases — his sketch: planning →
  ideation → specification → architecture → testing → release, with
  crash-rebuild as a special case. Orchestrator's faithful mapping given
  back: (1) ideation/intake — boarded with a sidecar stub; (2)
  specification — the bloom round converges the WHAT; (3) sizing &
  dispatch; (4) architecture — architect discovery + frozen plan at the
  gate; (5) build; (6) testing — the pre-agreed gate; (7) release — the
  fold (tag, squash-merge, push); (8) ingest — promotions, mostly
  invisible to him. Crash-resume is a lateral re-entry into whichever
  phase died (successor protocol, proven live today).
- Operator dictation, message 8 (phase list corrected to the OPERATOR-FACING
  view): sizing & dispatch is the orchestrator's concern — none of his
  business; ingest likewise (he cares as the system's designer, not as
  operator — the hovering and file-writing is plumbing). Release INCLUDES
  documentation as a logical grouping. The operator-facing spine is
  therefore SIX phases: ideation → specification → architecture → build →
  testing → release(+docs). Internal plumbing (sizing/dispatch, ingest)
  never surfaces in his flow.
- Operator dictation, message 9 (converging): phases are a SOFT SCALE, each
  containing the previous — ideation and specification adjoin; architecture
  spans the subagents that build; docs are written inside release. His
  candidate spine, "becomes human": IDEATION → SPECIFICATION → ARCHITECTING
  (word to improve) → BUILDING (testing folds in) → RELEASING. Ideation may
  stay permanently for symmetry even when a feature isn't new. Orchestrator
  opinion given: agree on five and on folding testing into building —
  phases are for orientation, the three interrupts carry the summons, so
  "failed" alarms regardless of phase; keep ideation always (it separates
  "just boarded" from "being measured"); proposed word: DESIGNING for the
  architect's discovery+plan span.
- Operator dictation, message 10: the five stand, but "specification" is
  the odd word form out — needs a replacement (orchestrator candidate:
  SCOPING). The phase spine must MAP TO A 100% progress scale as it
  happens. Each phase decomposes into subphases — some invisible
  (internal), some user-visible — and that mapping must be agreed QUICKLY.
  Row anatomy under each feature: line 1 = the current agent's one-word/
  one-line doing-text; line 2, SUBDUED = the name of the actual agent being
  run (the earlier italic-name musing, refined). More dictation coming.
- Operator dictation, message 11 (row block anatomy completed): beneath the
  agent line, SUBAGENT rows come and go — individually meaningless except
  as evidence of motion and COUNT ("five or six queued" is itself the
  information). This collapses the animation problem: while ANYTHING in the
  phase group works, ONE spinner on the group says so; when nothing works —
  waiting-to-start, not-my-turn (yesterday's conversation) — a subdued/
  watch icon, never motion. When a step/phase inside the feature ends, only
  its step line remains, marked COMPLETED or FAILED, and the block moves to
  the next step. (Sentence ran on — likely more coming.)
- Operator dictation, message 12: SCOPING approved — the spine is locked:
  ideation → scoping → designing → building → releasing. Each agent ROLE
  gets its own EMOJI again ("they used to, but were replaced by the wrong
  solution" — revival, choose at build). Window/status-bar title = PROJECT
  and FEATURE (self-corrected from "phase") — consistent with the quick
  pass's repo/name composition. INVARIANT stated to be specific: never
  multiple windows for one feature — within a feature is sequential,
  parallelism is cross-feature; the exception is non-displaying subagents
  running in parallel, which is encouraged. No change to current practice.

## Proposal

(to shape at bloom) One specified bus-message vocabulary — every message
class named, its purpose, payload and consumer defined; every agent's actual
sends audited against it and corrected so the sidebar and orchestrator read
one dialect.

## Testing

To agree when bloomed — expected shape: a session of each role runs and its
bus traffic validates against the specification with no unspecified message.

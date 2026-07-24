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
- Operator dictation, message 13: the PROGRESS BAR is EMBEDDED in the
  feature's name line itself — one line only (name drawn over an advancing
  fill or equivalent). Draft subphase map delivered (five phases, visible
  ticks vs hidden plumbing, spans 10/15/15/45/15 → 100). Plus a general
  working rule, saved to operator memory: ALWAYS reformulate what he said
  in your own words BEFORE starting work on it — that is what makes the
  result acceptable.

## Proposal

AGREED WHAT (operator dictation 2026-07-24, thirteen messages, reformulation
accepted — full record in Findings above). The display-and-messaging grammar:

- **Phase spine**: ideation → scoping → designing → building → releasing.
  A soft scale, each phase containing the last; testing lives inside
  building; documentation inside releasing; sizing/dispatch and ingest are
  orchestrator plumbing and never surface. Maps to a live 100% via the
  agreed subphase map (visible ticks advance the number; hidden work never
  does). Spans as drafted: 10/15/15/45/15, adjustable.
- **Feature row**: ONE line — the feature name drawn over the advancing
  progress fill. Beneath it while live: the current agent's one-word
  status; the running agent's name, subdued; ephemeral subagent rows whose
  COUNT is their only message. Window/status titles carry project +
  feature; one window per feature (parallelism is cross-feature, plus the
  invisible subagent pool).
- **Motion**: exactly one moving thing per feature — a group spinner while
  anyone inside works; a watch icon when waiting-its-turn; finished steps
  freeze to single completed/failed lines; done FEATURES go green, sort to
  top, never leave; done SUBAGENTS vanish. No flashing, no sound.
- **Message classes**: STATUS (one/two plain words, agent-chosen) · STATUS
  UPDATE (log-targeted sentence, never operator-targeted) · exactly three
  interrupts — SUCCEEDED, FAILED, QUESTION. Questions ride the broker path
  (never the native UI popup) so they can QUEUE for the right moment, and
  each arrives prefaced by why it is asked plus a decision-sufficient
  summary, answered from the orchestrator window without moving.
- **Identity**: each agent role carries its own emoji (revival); ONE
  interactive main agent at a time; the orchestrator window is the cockpit
  where all statuses synthesize — target capacity, five-six connected
  architects driven without visiting them.
- **The audit half**: every agent's ACTUAL sends are audited against this
  vocabulary and corrected — the four live exhibits in Findings (duplicate
  waiting notifies, Closing/lifecycle collision, dead-inbox delivery,
  unreachable live agent) define the defect classes to close.

Priority (operator, 2026-07-24): this outranks [[writing-emails]].

MOCK ROUNDS (2026-07-24/25, live in a pane beside the real sidebar):
- R1 verdict: grammar right, "lacks identity". R2: right-aligned %, per-repo
  hue families (orchids violet / signmc teal), model name on a cost/size
  colour ramp (haiku teal → sonnet steel → opus violet → fable gold),
  subagent dots lose their numeric caption, question becomes a dim-amber
  "?1" badge — NEVER red (red = danger, reserved). R3: live row wears its
  status word inline; phases become an indented VERTICAL checklist (filled
  done / hollow not-started / spinner active — one circle family unifies
  features and steps); waiting glyph is the hollow circle, all
  watch/timer glyphs banned; vertical breathing is deliberate. R4: repo
  headers drop the gradient — solid hue block, name CENTERED (centering
  was fine); the motion moves to the LIVE feature line as a KITT-style
  bidirectional sweep across its fill extent — the frame's ONE animated
  element.
- HELD, operator's own markers: (a) he had TWO ideas for the percentage
  and only dictated the first (the sweep) — the second is unspoken; (b)
  after the emoji mapping: REMIND HIM of the last topic, the FOOTER of
  each feature; (c) emoji↔agent mapping requested (roles had emojis once,
  lost to "the wrong solution").
- EMOJI/NAME RULING (operator, round 5): all-orchard naming approved in
  principle ("close enough … I like all of them"). Settled: bloomer 🌸
  stays; housekeeper → GROUNDSKEEPER; bus → COURIER (old-mail family);
  builder → the PLANTING family (planter/sower — not grafter), pick
  pending. Open with alternatives requested: orchestrator (gardener?
  orchardist?) and architect (landscaper concept accepted, word+emoji
  alternatives wanted). VISIBILITY RULE: the roles watched longest get the
  MOST VISIBLE emojis. CLOUD RULE: no per-role cloud variants in user
  surfaces — what users need is WHERE a thing executes: two location
  badges, one local-machine, one cloud, orthogonal to the role emoji, and
  available immediately. Mega-rename boarded as [[orchard-renaming]].
- FOOTER dictation, part 1 (operator, 2026-07-25): each feature block ends
  with a FOOTER whose data must be injectable WITHOUT spending tokens to
  collect (deterministic, locally-emitted sources only). Wanted: (a) the
  feature's lifetime/age displayed against the time actually WORKED on it
  (the git-commit-flavoured stat he's fond of); (b) TOKEN usage per feature
  — granularity open — animating/ticking upward live as work happens, as
  the block's LAST section. Everything else he already has a plugin for —
  do not duplicate. Orchestrator source note: both are already emitted
  locally (bus agent-metadata token denominators; session/commit
  timestamps) — zero-token injection is feasible. Dictation cut mid-
  sentence at "the last two things that…" — continuation pending.
- FOOTER dictation, part 2: also candidates — the BRANCH name with its ⎇
  glyph, the DOLLARS spent, and the TURN count; he asked the orchestrator
  to rank usefulness and propose the display. Orchestrator ranking given:
  tokens and dollars in (one line, tokens tick live, dollars translate
  them); age-vs-worked in (his "amazing" stat); BRANCH dropped from the
  footer (fully derivable — in this fleet the branch IS f/<feature-id>, so
  it restates the feature name for 19 columns of cost); TURNS dropped from
  the cockpit (a telemetry number, not a driving instrument — lives in
  the mined record instead). Footer = two dim guide lines closing the live
  block; done features carry a one-line collapsed footer. Rendered as mock
  round 7 for his visual verdict.
- FOOTER APPROVED (operator, round 7 verdict: "sounds good to me") — age⏱
  vs worked + tokens⚡/dollars, branch and turns out. Note: the footer's ⏱
  coexists with the no-timer rule because that rule governs the
  WAITING-STATE glyph semantics (waiting is not a countdown), not elapsed-
  time stats; flagged, unobjected.
- LIVE-ROW COLOUR RULE (operator, round 8): the live feature line carries
  exactly TWO backgrounds — a uniform DARK shade of the repo hue across
  the whole line, and a VERY LIGHT tint of the hue as the moving band; no
  grey, no near-black cells on a feature line, no fill-extent split (the
  percentage alone carries progress).
- ROUND 9 corrections (operator, live read): (a) the sweep is a LIFT, not
  a band — the base colour raised slightly as the motion passes, title
  always legible (supersedes round 8's "very light" band); (b) the phase
  is spoken ONCE — of his either/or, the orchestrator picked: the feature
  row drops its inline phase word (row = glyph + name + %), the checklist's
  active line is the single place the phase is named, the this-minute word
  lives in the identity line; (c) the identity line "writing ⋮ architect ⋮
  model" is glued with non-breaking spaces around the ⋮, wraps only
  between whole segments, continuation at the SAME indent level; (d) the
  standalone flock line under the model name "doesn't work" — orchestrator
  placement pick, flagged for veto: the dots move inline onto the
  checklist's active phase line ("⠧ building ●●●○○"), the workforce shown
  inside the phase it works.
- ROUND 10 (operator): small-caps phase label opens the sub-block for
  segregation; blank guide lines between segments — vertical breathing is
  mandated; the model name is NEVER alone on a line — truncate it
  (mid-string or entirely) rather than wrap it.
- PHASE APPROVAL (operator, 2026-07-25): "the rest works for me — good to
  go for this phase." ONE RECORDED DEBT, his explicit return-marker: the
  sweep is still not the KITT effect he specifically requested — KITT the
  car's scanner (bright core with a trailing fade sweeping side to side)
  in the existing colour scheme, not a flat lifted block. To be polished
  in a third/fourth pass; DO NOT let this drop — he asked twice that we
  get back to it.
- Design-contract capture pending: once round 10 renders, the approved
  frame (glyphs, exact colours, layout) and the mock renderer are to be
  preserved as the fixed visual contract; mock script currently at
  scratchpad/sidebar-mock.py, to be staged durably with this task.

DESIGN-FIRST RULE (operator, 2026-07-24): the VISUAL is agreed before any
build — a rendered mock the operator adjusts until it is right; the approved
look is then the fixed contract that implementations fit into. Agents never
bend the visual to match what they want to build. Mock round in progress —
the approved frame's exact rendering (glyphs, ANSI codes, layout) is to be
captured here as the design when the operator signs it off.

## Testing

To agree when bloomed — expected shape: a session of each role runs and its
bus traffic validates against the specification with no unspecified message.

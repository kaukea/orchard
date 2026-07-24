# TODO — the orchids board

Slim index; prose in sidecars (`TODO.md.d/<id>.md`). orchids is the fleet's data
package (skills, agents, rule files); the distribution code is the `kauk-sync`
stopgap in serialseb/kauk — it dies when the real kauk CLI ships. Weigh process
items against that.

Badge: `type · status · urgency · readiness · area · gh#`.

## Publication

- `housekeeping · todo · · blocked-on-answers · publication · gh#1` [Pre-publication cleanup & public/private split](TODO.md.d/pre-publication-cleanup.md)

## Process machinery

- `feature · done · · complete · process ·` [Tool split: package manager moved to kauk; orchids data-only](TODO.md.d/tool-split-to-kauk.md)
- `feature · done · · complete/interactive · process · gh#2` [Bus-driven close choreography: retire the finishing hooks](TODO.md.d/hook-choreography.md) ~bus-liveness ~agent-metadata ~tmux-topology
- `feature · todo · nice-to-have · blocked-on-answers · process · gh#3` [Decide the SessionStart self-heal hook](TODO.md.d/session-start-hook.md)
- `housekeeping · done · · complete · process ·` [Registry file set for orchids itself](TODO.md.d/registry-file-set.md)
- `bug · cancelled · nice-to-have · complete · process ·` [~~Self-install: root link entries collide (src == dst)~~](TODO.md.d/self-install-link-collision.md)
- `bug · done · · complete/interactive · process · gh#4` [ARCHITECTURE.md has no Taxonomy table — board lint fails 13/13](TODO.md.d/architecture-taxonomy-missing.md)
- `feature · todo · · blocked-on-answers · process · gh#5` [Cross-repo inbox: agents deliver requirements and knowledge between projects](TODO.md.d/cross-repo-inbox.md) ~role-delivery ~external-blockers
- `feature · todo · · blocked-on-answers · process · gh#6` [Orchestrator resolves external blockers when loading its tasks](TODO.md.d/external-blockers.md) ~cross-repo-inbox
- `housekeeping · todo · nice-to-have · plan-ready · process · gh#7` [Kauk skill: symlink-write guidance is unexecutable under the harness](TODO.md.d/kauk-skill-symlink-write.md)
- `feature · done · · complete/interactive · process ·` [The works: .git/the-works/ transients, dated migrations, write gates, micro-tasks](TODO.md.d/the-works-channel.md) ~kauk-skill-symlink-write
- `feature · done · · complete/interactive · process ·` [Workstream logs: per-session rolling records replace the handover](TODO.md.d/workstream-log.md) ~the-works-channel
- `housekeeping · todo · nice-to-have · queued · process · gh#8` [Decide retention for ingested workstream logs](TODO.md.d/ingested-retention.md) ~workstream-log
- `housekeeping · done · · complete/interactive · process ·` [Configure origin remote; push pending closes](TODO.md.d/origin-remote-missing.md)
- `feature · todo · · blocked-on-answers · process · gh#9` [Hide machinery skills from the slash list (user-invocable pass)](TODO.md.d/skill-slash-visibility.md)
- `feature · todo · · blocked-on-answers · process · gh#10` [Manifest entry attributes copy/ro (upstream kauk)](TODO.md.d/manifest-copy-ro.md) ~github-board-sync
- `feature · todo · · blocked-on-answers · process · gh#11` [Standard tree display+selection for package installs (upstream kauk)](TODO.md.d/package-select-tree.md) ~kauk-skill-symlink-write
- `feature · todo · · plan-ready · process · gh#12` [Sync suggests a reset when the package changed (upstream kauk)](TODO.md.d/sync-suggest-reset.md) ~package-select-tree ~kauk-skill-symlink-write
- `feature · todo · · queued · process · gh#24` [kauk validates role declarations: validate stub now, taxonomy check later (upstream kauk)](TODO.md.d/kauk-validate-roles.md) ~role-dag-frontmatter
- `refactor · todo · · queued · process ·` [Delivery config review: markings out of .ai.toml into AGENTS.d (upstream kauk)](TODO.md.d/delivery-config-review.md) ~manifest-copy-ro ~install-detecting
- `feature · functional · · complete/interactive · · gh#13` [Cross-repo board view: GitHub issues + user-level Project, orchestrator-synced](TODO.md.d/github-board-sync.md) ~cross-repo-inbox ~external-blockers
  - `bug · done · · complete/interactive · process ·` [Sync ingest failing: board-sync's GitHub→board direction exits 1](TODO.md.d/sync-ingest-failing.md) ~github-board-sync ~field-projecting
  - `completion · done · · complete/interactive · process ·` [Field projecting: every sidecar field maps to GitHub or is created there](TODO.md.d/field-projecting.md) ~nested-tasks-projecting ~tags-and-labels
  - `feature · done · · complete/interactive · process ·` [Decision projecting: decisions mirror as their own type, closing on supersession](TODO.md.d/decision-projecting.md) ~field-projecting
  - `completion · todo · · queued · process ·` [Component field declaring: Component missing from board_gh field sets](TODO.md.d/component-field-declaring.md) ~field-projecting
- `housekeeping · todo · nice-to-have · blocked-on-answers · process · gh#14` [Install-id migration to the kaukea org — parked until the org name is final](TODO.md.d/install-id-kaukea.md)
- `feature · todo · idea · queued · process ·` [Epic grouping: features rolled toward a big feature, with cockpit progress](TODO.md.d/epic-grouping.md) ~orchard ~github-board-sync
- `feature · todo · · queued · · gh#25` [Orchard: the fleet workbench — global view, selection, dispatch](TODO.md.d/orchard.md) ~github-board-sync ~cross-repo-inbox
  - `feature · todo · · blocked-on-answers · process · gh#39` [Orchestrator emits the orchard summary file, parseable from outside](TODO.md.d/orchard-summary.md)
  - `feature · todo · · queued · process · gh#40` [Orchard view: consolidate the fleet, show priorities and cross-repo edges](TODO.md.d/orchard-view.md) ⊘orchard-summary
  - `feature · todo · · queued · process · gh#41` [Orchard launch: session per repo, orchestrator told the pick and double-checks](TODO.md.d/orchard-launch.md) ⊘orchard-view
  - `feature · todo · · plan-ready · process · gh#42` [Tmux topology: window per architect, stacked pane per coder, focus returns on close](TODO.md.d/tmux-topology.md) ~hook-choreography ~fleet-sidebar
  - `feature · done · · complete/interactive · · gh#23` [Fleet sidebar: always-visible navigable job states with phase emojis](TODO.md.d/fleet-sidebar.md) ~bus-liveness ~agent-metadata
    - `feature · todo · · blocked-on-answers · process ·` [Cloud event feed: GitHub Actions events land as sidebar files](TODO.md.d/cloud-event-feed.md) ~cloud-architect
    - `bug · done · · complete/interactive · process ·` [Fleet sidebar fixes: correct the defects the first build shipped](TODO.md.d/sidebar-fixes.md)
    - `bug · done · · complete/interactive · process ·` [Sidebar polish: the operator's live-pass list — rows, colors, states, /orchard](TODO.md.d/sidebar-polish.md) ~sidebar-fixes ~message-bus ~orchard
    - `completion · todo · · plan-ready · process ·` [Popup finishing: the operator's round-2 requests, finished and live-proven](TODO.md.d/popup-finishing.md) ~sidebar-polish ~operator-interacting
    - `bug · todo · · queued · process ·` [Sidebar spacing and glyphs: gaps found on the first live pass after sidebar-polish merged](TODO.md.d/sidebar-spacing-and-glyphs.md) ~sidebar-polish
    - `feature · todo · nice-to-have · queued · process ·` [Install detecting: richer orchids-install state beyond .ai.toml presence (upstream kauk)](TODO.md.d/install-detecting.md) ~sidebar-polish ~orchard
    - `bug · todo · · queued · process ·` [Sidebar witnessing: ghost rows persist, silent live agents invisible — the ephemeral-bus observer gap](TODO.md.d/sidebar-witnessing.md) ~sidebar-polish ~bus-singleton ~message-bus
    - `bug · todo · · working/interactive · process ·` [Sidebar titling: the one-go pass — gradients, /name format, truthful icons, 1:1 names, stable titles](TODO.md.d/sidebar-titling.md) ~sidebar-polish ~sidebar-spacing-and-glyphs ~orchestrator-identity
    - `bug · todo · · queued · process ·` [Popup adopting: agents bypass the built choice questions and do-not-interrupt](TODO.md.d/popup-adopting.md) ~popup-finishing ~operator-interacting
  - `bug · done · · complete/interactive · process · gh#34` [Session and feature naming: short, descriptive, visible — sidebar prerequisite](TODO.md.d/session-naming.md)
  - `feature · todo · · working · process · gh#43` [Handover contract: build-ready sidecars, questions front-loaded before launch](TODO.md.d/handover-contract.md) ~architect-delegation ~injection-integrity
  - `feature · done · · complete/interactive · process · gh#44` [Cloud architect: automate the analyzable share of the architect's job](TODO.md.d/cloud-architect.md) ~handover-contract ⊘app-identifying
  - `completion · done · · complete/interactive · process ·` [callabloom: the cloud hops' named app identity](TODO.md.d/app-identifying.md) ~cloud-architect
  - `feature · todo · · blocked-on-answers · process ·` [Branch protection as code: operator approval to merge, callabloom excepted](TODO.md.d/branch-protecting.md) ~app-identifying
  - `feature · todo · · blocked-on-answers · process ·` [Mr. Rabbit: serialized merge ordering owns changelog order, closes the loop](TODO.md.d/merge-ordering.md) ~branch-protecting ~cloud-architect
  - `housekeeping · todo · · queued · process ·` [Merge queue investigating: does GitHub's native queue serve the fleet?](TODO.md.d/merge-queue-investigating.md) ~merge-ordering ~branch-protecting
  - `refactor · todo · · blocked-on-answers · process ·` [Launcher subagent: extract worktree creation and agent launch from the orchestrator](TODO.md.d/launcher-subagent.md) ~merge-ordering
  - `feature · todo · · queued · process ·` [Delta commenting: agents converse in threads — acknowledge, advise, refine](TODO.md.d/delta-commenting.md)
  - `feature · todo · idea · queued · process ·` [Routine NL-trigger: an Anthropic routine dispatches the cloud path](TODO.md.d/routine-triggering.md) ~merge-ordering
  - `feature · todo · · blocked-on-answers · process · gh#45` [Cross-repo bus: live messaging across repository boundaries](TODO.md.d/cross-repo-bus.md) ~message-bus ~cross-repo-inbox
  - `feature · todo · · blocked-on-answers · process · gh#46` [Diagnostic channel for agents, cloud and local — cross-cutting](TODO.md.d/diagnostic-channel.md) ~bus-liveness ~agent-metadata ~fleet-sidebar ~cloud-architect
  - `feature · done · · complete/interactive · process · gh#47` [Bloomer charter: close functional scope, statistical readiness, auto-kick](TODO.md.d/psychometric-discovery.md) ~handover-contract ~retire-groom-vocabulary
  - `feature · todo · · queued · process ·` [Bloom administering: batched question blocks, blind axes](TODO.md.d/bloom-administering.md) ~psychometric-discovery
  - `completion · todo · · queued · process ·` [Bloomer repointing: groomer verdict, pipeline repoints, orchestrator adopts the pane](TODO.md.d/bloomer-repointing.md) ~psychometric-discovery ~bloom-administering
  - `bug · todo · · queued · process ·` [Bloom subset posterior: multi-select dimensions converge instead of exhausting](TODO.md.d/bloom-subset-posterior.md) ~psychometric-discovery ~bloom-administering
- `bug · done · · complete/interactive · process ·` [Agents leave sub-agents and sessions unclosed: the flow cannot finish](TODO.md.d/agent-closing.md) ~message-bus ~hook-choreography ~zombie-revival
- `bug · todo · nice-to-have · plan-ready · process ·` [Skills cite decision numbers that mean something else in decisions.md](TODO.md.d/decision-collision-skills.md)
- `housekeeping · todo · nice-to-have · blocked-on-answers · process · gh#26` [Rename the TODO vocabulary to task list](TODO.md.d/todo-to-task-list.md)
- `housekeeping · done · · complete/interactive · process · gh#27` [Retire the ripen word family: rename the skill, the agent, and the verb](TODO.md.d/retire-groom-vocabulary.md) ~todo-to-task-list
- `refactor · todo · · blocked-on-answers · process ·` [Orchard renaming: every role wears an orchard name, its emoji, and a location badge](TODO.md.d/orchard-renaming.md) ~retire-groom-vocabulary ~bus-message-specifying ~bloomer-repointing
- `feature · todo · critical · blocked-on-answers · process · gh#28` [Injection integrity: make instructions arrive intact, not summarised](TODO.md.d/injection-integrity.md) ⊘readme-changelog-ownership ~session-start-hook
- `feature · cancelled · · complete · process · gh#29` [~~Sidecar liveness: prove an agent is still listening after load~~](TODO.md.d/bus-liveness.md) ~message-bus
- `feature · todo · · blocked-on-answers · process · gh#30` [Zombie delivery: scripts revive dead sessions before handing them messages](TODO.md.d/zombie-revival.md) ~bus-liveness ~message-bus
- `bug · done · · complete/interactive · process · gh#48` [Nested tasks projecting: board_gh push skips orchard children](TODO.md.d/nested-tasks-projecting.md) ~github-board-sync
- `feature · todo · · blocked-on-answers · process · gh#49` [Tags and labels: one vocabulary, board and GitHub, emojis included](TODO.md.d/tags-and-labels.md) ~github-board-sync ~nested-tasks-projecting
- `housekeeping · todo · · blocked-on-answers · process · gh#50` [Linking references: repo-doc mentions become document+line links](TODO.md.d/linking-references.md)
- `feature · done · · complete/interactive · process ·` [Agent metadata: model, effort and token denominators on the bus](TODO.md.d/agent-metadata.md) ~message-bus
- `feature · done · · complete · process ·` [Review model + effort per agent role; make effort frontmatter-pinnable like model](TODO.md.d/role-model-effort.md) ~agent-metadata ~role-dag-frontmatter
- `bug · cancelled · · complete · process ·` [~~Distribution is a hand-typed index: derive it from the tree, and fail loudly meanwhile~~](TODO.md.d/manifest-by-convention.md) ~role-dag-frontmatter
- `feature · functional · · complete/interactive · process · gh#31` [Move README and CHANGELOG to the orchestrator](TODO.md.d/readme-changelog-ownership.md) ~injection-integrity
- `feature · todo · · queued · process · gh#32` [Deviance detection: surface drift when it happens, not weeks later](TODO.md.d/deviance-detection.md) ⊘injection-integrity
- `feature · functional · · complete/interactive · ·` [Rules tuning: exit interviews feed statistical prompt optimization, A/B tested](TODO.md.d/rules-tuning.md) ~deviance-detection ~diagnostic-channel ~psychometric-discovery
  - `feature · done · · complete/interactive · process ·` [Telemetry collecting: deviations and exit interviews to git notes](TODO.md.d/telemetry-collecting.md)
  - `feature · todo · · blocked-on-answers · process ·` [Digest identity: the telemetry routine publishes as callabloom, not the operator](TODO.md.d/digest-identity.md) ~telemetry-collecting ~app-identifying ~branch-protecting
  - `feature · todo · · blocked-on-answers · process ·` [Digest formatting: emoji-keyed bullets, impact subtitles, links](TODO.md.d/digest-formatting.md) ~telemetry-collecting ~digest-identity
  - `feature · functional · · queued · process · gh#51` [Telemetry mining: batch analysis of notes and transcripts](TODO.md.d/telemetry-mining.md) ⊘telemetry-collecting
  - `feature · todo · · queued · process · gh#52` [Prompt optimizing: rule changes proposed from deviation evidence](TODO.md.d/prompt-optimizing.md) ⊘telemetry-mining
  - `feature · todo · idea · queued · process · gh#53` [Rules abtesting: variants measured statistically, reverted on regression](TODO.md.d/rules-abtesting.md) ⊘prompt-optimizing
- `bug · todo · · blocked-on-answers · process · gh#33` [Hooks are an unowned pool in one shared file: no per-repo surface, no provenance](TODO.md.d/hook-composition.md) ~manifest-by-convention
- `bug · cancelled · · complete · process ·` [~~Architect skips its delegation contract: builds without dispatching builders~~](TODO.md.d/architect-delegation.md) ~handover-contract
- `feature · done · · complete/interactive · process ·` [Message bus: repo-scoped agent-to-agent messaging via a bus sidecar](TODO.md.d/message-bus.md) ~hook-choreography ~cross-repo-inbox
- `refactor · todo · · working · process ·` [Bus message specifying: tighten the vocabulary, fix what each agent sends](TODO.md.d/bus-message-specifying.md) ~message-bus ~fleet-documenting ~sidebar-witnessing ~sidebar-titling ~orchard-renaming
- `bug · todo · critical · plan-ready · process ·` [Bus close actually cleans up: wake the bus to close, never kill its monitor](TODO.md.d/bus-close-cleanup.md) ~agent-closing ~bus-singleton ~window-closing-owning ~message-bus ~bus-message-specifying
- `bug · todo · critical · plan-ready · process ·` [Bus singleton: exactly one bus sidecar per agent, as designed](TODO.md.d/bus-singleton.md) ~message-bus ~sidebar-polish ~agent-closing
- `feature · todo · nice-to-have · queued · process ·` [Bus recycling: a deep bus warns its host and hands over to a fresh one](TODO.md.d/bus-recycling.md) ~bus-singleton ~message-bus
- `housekeeping · todo · idea · queued · process ·` [Fleet documenting: agent wiki pages; channels with JSON Schemas](TODO.md.d/fleet-documenting.md) ~message-bus ~operator-interacting ~digest-identity
- `bug · todo · critical · plan-ready · process ·` [Window closing owning: agents close themselves; a listener kills at five](TODO.md.d/window-closing-owning.md) ~sidebar-polish ~bus-singleton ~agent-closing
- `bug · todo · · queued · process ·` [Focus returning: a finish always selects the orchestrator window, the view follows only in-session](TODO.md.d/focus-returning.md) ~tmux-topology ~window-closing-owning
- `bug · todo · · queued · process ·` [Orchestrator identity: one per repo, single instance, session named after the project](TODO.md.d/orchestrator-identity.md) ~session-naming ~sidebar-titling
- `feature · todo · critical · plan-ready · process ·` [Intake enforcing: typed requests in, board writes denied](TODO.md.d/intake-enforcing.md) ~message-bus ~bus-singleton ~fleet-documenting
- `feature · todo · · blocked-on-answers · process ·` [Operator interacting: questions, gates and summaries as one typed exchange](TODO.md.d/operator-interacting.md) ~message-bus ~sidebar-polish ~hook-choreography
- `feature · todo · critical · working · process ·` [Capture now: transcripts and logs preserved before the ledger exists](TODO.md.d/capture-now.md)
- `feature · todo · · working · process ·` [Corpus indexing: inventory-first index of all fleet history](TODO.md.d/corpus-indexing.md) ~capture-now
- `bug · done · · complete · process ·` [Bloomer forensics: why the built shape diverged from its charter](TODO.md.d/bloomer-forensics.md) ~injection-integrity ~psychometric-discovery
- `feature · todo · · blocked-on-answers · process ·` [Step recording: one authored record, scripted projections](TODO.md.d/step-recording.md) ~handover-contract
- `feature · todo · nice-to-have · queued · process ·` [Keyword configuring: the gate-phrase table becomes configuration](TODO.md.d/keyword-configuring.md) ~operator-interacting
- `feature · todo · idea · queued · process · gh#15` [Writing emails — scope to be defined by the operator](TODO.md.d/writing-emails.md)
- `feature · todo · · queued · process ·` [Notify channel: fleet→operator email notifications, wanted, scope pending](TODO.md.d/notify-channel.md) ~writing-emails ~operator-interacting

## Role delivery

- `feature · todo · · blocked-on-answers · · gh#16` [Role-based delivery of skills and agents](TODO.md.d/role-delivery.md) ~dynamic-skill-delivery
  - `feature · done · · complete/interactive · sync ·` [Declare the role DAG in skill and agent frontmatter](TODO.md.d/role-dag-frontmatter.md)
  - `feature · todo · · plan-ready · sync · gh#54` [Make agents first-class, with skill dependencies](TODO.md.d/agents-first-class.md) ⊘role-dag-frontmatter
  - `refactor · todo · · blocked-on-answers · process · gh#55` [Rename and split skills to fit the role DAG](TODO.md.d/skill-renames-and-splits.md)
  - `refactor · todo · · blocked-on-answers · process · gh#56` [Terseness and conflicting-advice pass over all skills](TODO.md.d/skill-terseness-pass.md) ⊘role-dag-frontmatter ⊘skill-renames-and-splits

## Skills

- `feature · todo · · blocked-on-answers · skills · gh#17` [Web account signup: create account, store password + OTP in Bitwarden](TODO.md.d/web-account-signup-skill.md) ~role-delivery
- `feature · todo · · working · skills ·` [Operator voice: bilingual style, rhythm and vocabulary for anything under his name](TODO.md.d/operator-voice.md) ~writing-emails ~corpus-indexing

## Future (dot.ai features, design only)

- `feature · todo · idea · queued · sync · gh#18` [Dynamic skill delivery per role](TODO.md.d/dynamic-skill-delivery.md)
- `feature · todo · idea · queued · sync · gh#19` [Multi-source namespacing](TODO.md.d/multi-source-namespacing.md)
- `feature · todo · idea · blocked-on-answers · sync · gh#20` [Agents: external dependencies beyond in-package skills](TODO.md.d/agent-external-deps.md) ~agents-first-class ~multi-source-namespacing

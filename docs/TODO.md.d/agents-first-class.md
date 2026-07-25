- created: 2026-07-17
- created_by: opus-4.8

## Blockers
- ~~Depends on `role-dag-frontmatter` settling the `roles:` key + path syntax
  (Proposal step 1 only).~~ Resolved — syntax ruled, Decision-005. Ordering stands
  (⊘ edge): `role-dag-frontmatter` amends the keystone contract in `authoring-skills`
  first; this task conforms to it. The dependency-list contract was ruled separately
  (`requirements:`, Decision-004).

## Questions
- None open — the 2026-07-17 rulings (Findings, Decision-004) closed the last two.

## Findings
Operator rulings, 2026-07-17 — these close what were the three open questions here:
- **The dependency list lives in the agent's OWN frontmatter.** A list of skills shipped
  inside the package. Consistent with Decision-002: authors declare, because they know.
- **External dependencies are deferred**, deliberately — a dependency could one day be
  outside the package (another source's skill, a system tool). Not now; filed as
  `agent-external-deps`. Do not design for it here, only avoid precluding it.
- **The package layout gains an `agents/` folder, symmetric with `skills/`**, linked
  into place from its own location exactly as skills are. Agents are not a skill
  variant; they are a peer artifact with a peer folder.
- **An agent may require MULTIPLE skills that ship with it, and that changes how
  choosing skills works** — this is the consequence that drives the install flow, see
  below.

Operator rulings, 2026-07-17 (Decision-004) — close the two questions above:
- **Agents depend on other agents, and declare it.** The real graph's edges
  (gardener → landscaper/groundskeeper/bloomer; landscaper → sower) become
  declarations; an undeclared edge deploys a broken agent. On page 1, an agent
  required by a chosen agent is greyed out — visible, selected, not deselectable —
  exactly the page-2 skill pattern.
- **The declaration is a `requirements:` frontmatter map with two sub-lists**, kinds
  explicit, no cross-folder uniqueness rule needed:

  ```yaml
  requirements:
    agents: [sower]
    skills: [workflow, workflow-complete, handover]
  ```

  Ruled directly, so the dependency contract no longer rides on
  `role-dag-frontmatter` (which still owns `roles:`). External deps stay deferred
  (`agent-external-deps`); the map form takes a third sub-list later without
  disturbing these two.

Background (unchanged):
- Agents are `link` lines today — `link agents/architect.md .claude/agents/architect.md`
  — which the manifest header documents as "everyone gets it". All 5 agents install
  unconditionally into every repo, with no role and no opt-out. Skills at least have a
  (dead) role field; agents have nothing.
- Agent frontmatter carries only `name`, `description`, `model`. No roles, no deps.
- Real dependency edges exist and cannot currently be stated: the workflow needs the
  bloomer; the landscaper needs `workflow` + `workflow-complete` + `handover`; the
  groundskeeper needs `workflow-complete` + `readme-sync`.

## Proposal
1. Declare roles on all 5 agents using the contract from `role-dag-frontmatter`.
2. Declare each agent's `requirements:` map (`agents:` + `skills:`) in its own
   frontmatter.
3. Keep the `link` lines working until kauk ships the reader, so nothing regresses.

**Two-page install selection (operator, 2026-07-17)** — the flow, which orchids
specifies and kauk implements:
- **Page 1: choose agents** — an agent required by a chosen agent is greyed out here,
  same rule as page 2 applies to skills (Decision-004).
- **Page 2: choose skills** — the skills required by the agents chosen on page 1 appear
  **greyed out**: visible, already selected, not deselectable.

Greyed-out rather than hidden is the point. The operator sees exactly what their agent
choice pulled in and why it is not theirs to uncheck — the requirement is legible
instead of silently applied. A hidden pre-selection would leave them wondering later why
a skill they never picked is in their repo.

This is also why agents come first: an agent is the thing an operator actually wants,
and its skills follow from it. It dissolves the "what if a required skill was excluded?"
question — the flow makes it unaskable rather than answering it.

The `agent` manifest type, the `agents/` folder handling, the dependency resolution and
the two-page picker are **kauk's work, on kauk's board** — `agent-deployment` (`cli` /
`cli-core`), filed 2026-07-17. State intent here; do not re-specify the engine.

## Testing
Declaration lint: every agent declares ≥1 role and a resolvable `requirements:` map —
every `skills:` id names a real skill and every `agents:` id a real agent in the
package, no self-reference, agent graph acyclic. End-to-end (page 1 → page 2 → exactly
the right set laid) is kauk-side and cannot run here; report it untested rather than
implied.

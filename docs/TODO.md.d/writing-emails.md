- created: 2026-07-18
- created_by: operator
- created_during: f/workstream-log

## Blockers
- ~~Scope undefined — stub captured at the operator's request ("add a TODO for
  writing emails", 2026-07-18, in lieu of a next-day reminder). The operator
  defines intent before blooming.~~ Resolved 2026-07-24: scope measured with the
  operator over a full bloom round (v1 engine); see Findings and Proposal.

## Questions
- ~~What is this? A skill for agents drafting/writing emails (Gmail connector can
  create drafts, not send), actual emails the operator needs written, or email
  as a fleet notification channel?~~ Answered 2026-07-24: a reusable email-writing
  SKILL for agents — measured three ways with consistent answers. Correspondence
  was not ruled out as a later use of the skill, but this task owes no finished
  emails; the notification channel and connector wiring are explicitly out.

## Findings
- **Bloom measurement round, 2026-07-24 (bloomer v1, engine-driven).**
  Convergence: overall SE 0.461 → band **lower** (thresholds: very-high ≤ 0.20,
  medium-high ≤ 0.35). Per dimension: deliverable SE 0.309 (converged, 3 items,
  top: skill) · standing SE 0.324 (converged, 1 item, top: durable) · send-model
  SE 0.259 (converged, 3 items, top: approval-gated) · surface SE 0.522
  (EXHAUSTED at 6 items, top: thunderbird) · email-domain SE 0.888 (EXHAUSTED at
  6 items, top: personal). No person-fit (misfit) flags anywhere.
- **The two exhaustions are structural, not disagreement**: both are multi-select
  dimensions whose true state is a stable subset of hypotheses; the v1
  ordinal-index entropy SE proxy cannot fall below a floor for subset answers
  (email-domain plateaued 0.901→0.888 over four consistent rounds). The operator
  confirmed both dimensions' composed rules verbatim in final confirmation
  items. Calibration input for the psychometric-discovery build.
- One mid-round tension (scope: "any email" vs "personal + secure@ only") was
  surfaced as an explicit consistency check and resolved with a rule, not a
  list: any human-audience email is in scope; machine notifications are not.
- **Launch sizing (engine): l → claude-fable-5, effort high.**
- **Uncalibrated-items caveat**: all 2PL item parameters (discrimination,
  difficulty) in this round are LLM-assessed, not corpus-fitted; the convergence
  number, band, and sizing inherit that limitation (v1, per operator ruling).

## Proposal
A durable **email-writing skill** (SKILL.md in this package) that agents load
whenever composing email for a human reader. Standing capability, maintained
like the rest of the package.

**Scope (rule, not list):** every email an agent writes for a human reader —
personal correspondence (seb@serialseb.com), security-disclosure mail (secure@),
and any future identity or context automatically. Machine-formatted /
purely-technical notification mail is out of scope.

**Send model — approval-gated everywhere:** an agent may send only after the
operator approves that specific email. No exceptions for trivial one-liners; no
carve-out making secure@ drafts-only — the same gate holds across all in-scope
mail. Never autonomous send.

**Surfaces and routing:**
- The skill knows four vehicles: thunderbird-secure MCP (local drafts +
  approval-gated send), the claude.ai Gmail connector (cloud drafts only),
  prose handed over in-session, and a local `.eml` file.
- Thunderbird first when present.
- Gmail connector is allowed for ordinary mail only.
- **Sensitive mail (secure@ and anything similarly sensitive) must never touch
  the cloud before the final send** — local Thunderbird, prose, or local `.eml`
  only.
- Prose or `.eml` when no mail tool is available; the skill still governs the
  text.
- Surface choice is scenario/location/feature dependent — the skill encodes the
  selection rules above rather than a fixed surface.

**Standing constraints folded in:** plain-text email by default, never HTML
(existing operator rule).

**Out of scope for this task:** a fleet→operator email notification channel;
connector/MCP integration work; producing specific finished correspondence.

### Explicit voluntary deferrals (Decision-027)
- **Sensitivity classification boundary** — which non-secure@ mail counts as
  "very sensitive" is left to agent judgement with a when-in-doubt-treat-as-
  sensitive default; a sharper definition is deferred to the architect's plan.
- **Voice/tone/style content** of the skill (beyond plain-text) — unmeasured
  this round; deferred to the architect's plan phase with the operator.
- **Engine deferral candidates** `surface` and `email-domain` — stopped by
  exhaustion, not convergence; substance operator-confirmed but uncertified by
  the v1 proxy. Re-examine at plan review.

## Testing
To be agreed with the operator at build time. Candidate method staged for the
architect: draft one ordinary email via thunderbird-secure and one via the Gmail
connector; exercise the sensitive path with a local-only vehicle and verify the
no-cloud rule holds; confirm the per-email approval gate is enforced before any
send; verify plain-text output.

## Decision entries
Staged for orchestrator promotion to docs/decisions.md (operator rulings,
2026-07-24, measured during the writing-emails bloom round):
- `#email #skills` — Email-writing skill scope is a RULE, not a list: any email
  an agent writes for a human reader is governed; machine-formatted technical
  notifications are not.
- `#email #security` — Agent email sending is approval-gated per email,
  everywhere: no autonomous send, no trivial-mail exception, and no
  drafts-only carve-out for secure@.
- `#email #security #cloud` — Sensitive email (secure@ and similar) never
  touches a cloud surface before final send; drafting stays on local vehicles
  (thunderbird-secure MCP, in-session prose, local `.eml`). The Gmail connector
  is restricted to ordinary mail.

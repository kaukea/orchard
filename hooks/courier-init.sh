#!/usr/bin/env bash
# SessionStart hook — put every session in this repository on the message courier.
#
# A hook rather than a prompt instruction on purpose: code does not drift, models
# do, and AGENTS.md / CLAUDE.md get bypassed regularly. This applies to every
# agent in every flow, not only the ones that happen to read their briefing.
#
# Two jobs, and only the first is enforceable from a shell:
#   1. create this session's inbox (structural — it exists whatever the model does);
#   2. instruct the session to load its courier and announce itself (a model action; a
#      hook cannot spawn a subagent, so this step is prompted, not enforced).
#
# The announcement is what makes step 2 verifiable: an agent that never announces
# is visibly absent to every peer, so a skipped courier is detectable rather than a
# silently deaf agent. Note this is detection, NOT a capability gate — the session
# id is an environment variable and nothing here can withhold it.
set -eu

root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
for candidate in "$root/.claude/tools/courier.py" "$root/tools/courier.py" "$root/.claude/tools/bus.py" "$root/tools/bus.py"; do
  [ -f "$candidate" ] && courier="$candidate" && break
done
[ -n "${courier:-}" ] || exit 0

# Structural half: the inbox exists even if the model ignores everything below.
python3 "$courier" init >/dev/null 2>&1 || exit 0

cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"MESSAGING: you can exchange messages with the other agents in this repository. Load your courier sidecar now — spawn a subagent with subagent_type \"courier\", description \"messaging\", and the prompt \"You are my courier. Announce me and stay listening.\" Do this BEFORE starting work: it announces you to your peers, and until it runs you are invisible to them and will silently miss anything broadcast to you. Ask your courier in plain language to send things; arriving messages appear on their own."}}
JSON

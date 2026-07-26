#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash) — an agent must be structurally unable to
# post on the transport without having gone through its courier subagent
# (operator ruling: "I don't want a MUST but CANNOT here").
#
# Env vars cannot carry this rule: a courier subagent inherits its parent's
# environment wholesale, so CLAUDE_CODE_AGENT reads as the PARENT's type
# inside the courier too (measured). agent_type on this hook's stdin JSON is
# harness-supplied per tool call instead, so an agent cannot spoof it by
# prefixing its command. That is what makes a hook the only viable gate.
#
# FAILS CLOSED on purpose: only agent_type exactly "courier" is let through.
# Everything else is denied, including a missing or unrecognised agent_type —
# the value the harness sends for the main/top-level agent is undocumented,
# so this never trusts it; an undocumented value is just one more thing that
# is not "courier" and is denied the same as any other.
#
# The command match below is anchored at a shell command boundary (start of
# line, or after ; && || & |) rather than a bare substring search: a plain
# substring match also fires on `grep -rn "courier.py signal" agents/*.md`,
# which mentions the surface but invokes nothing, and that false positive
# would cost whoever maintains this hook — the exact people who need to grep
# for these strings — a confusing debugging session. A shell command line is
# not fully regex-parseable, so where a construct is genuinely ambiguous this
# still resolves to DENY: a direct script invocation with no interpreter
# (`courier.py send`, relying on a shebang) counts as an invocation, and any
# env-assignment prefix (`FOO=bar courier.py send`) counts too, even though
# neither is verified to actually execute anything.
#
# Beyond the boundary anchor, this also has to see through the shell's own
# hiding places: a quoted env-assignment value, a `bash -c`/`sh -c`/`zsh -c`
# or `eval` payload, a `python3 -c` import of the transport module, and
# `$(...)`/backtick command substitution. Each of those is unwrapped and the
# same anchor check is re-run on the inner text, a few levels deep, because a
# regex over command text cannot parse a shell — it can only widen the net.
# This is NOT airtight and must never be represented as such: it stops
# accidental and casual bypass, and a deliberate one is still possible and
# will look visibly deliberate (e.g. writing the courier call to a script
# file on disk and executing that file — no command-text matcher, this one
# included, can see inside a file it was never shown). Where a construct
# cannot be confidently classified, this still resolves to DENY; it never
# grows an allowlist or override flag to compensate.
set -eu

input="$(cat)"

command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || printf '')"

sq="'"
dq='"'

boundary='(^|;|&&|\|\||&|\|)[[:space:]]*'
env_value="($sq[^$sq]*$sq|$dq[^$dq]*$dq|[^[:space:]]*)"
env_prefix="([A-Za-z_][A-Za-z0-9_]*=$env_value[[:space:]]+)*"
interpreter='(python3?[[:space:]]+)?'
path_prefix='([A-Za-z0-9_./-]*/)?'
target='(orchard_topic\.py[[:space:]]+post|courier\.py[[:space:]]+(send|signal|ask|announce))\b'
invocation="$boundary$env_prefix$interpreter$path_prefix$target"

import_pattern='(import[[:space:]]+(courier|orchard_topic)\b|from[[:space:]]+(courier|orchard_topic)[[:space:]]+import\b)'

has_invocation() {
  printf '%s' "$1" | grep -Eq "$invocation"
}

has_transport_import() {
  printf '%s' "$1" | grep -Eq "$import_pattern"
}

# Payloads a shell/interpreter -c flag can carry, single- or double-quoted.
shell_c_payloads() {
  printf '%s' "$1" | sed -nE "s/.*(bash|sh|zsh)[[:space:]]+-c[[:space:]]+'([^']*)'.*/\\2/p"
  printf '%s' "$1" | sed -nE 's/.*(bash|sh|zsh)[[:space:]]+-c[[:space:]]+"([^"]*)".*/\2/p'
}

eval_payloads() {
  printf '%s' "$1" | sed -nE "s/.*eval[[:space:]]+'([^']*)'.*/\\1/p"
  printf '%s' "$1" | sed -nE 's/.*eval[[:space:]]+"([^"]*)".*/\1/p'
}

python_c_payloads() {
  printf '%s' "$1" | sed -nE "s/.*python3?[[:space:]]+-c[[:space:]]+'([^']*)'.*/\\1/p"
  printf '%s' "$1" | sed -nE 's/.*python3?[[:space:]]+-c[[:space:]]+"([^"]*)".*/\1/p'
}

subst_payloads() {
  printf '%s' "$1" | sed -nE 's/.*\$\(([^()]*)\).*/\1/p'
  printf '%s' "$1" | sed -nE 's/.*`([^`]*)`.*/\1/p'
}

# Recursively examine command text for a transport invocation, unwrapping the
# handful of ways a shell can hide one from a flat pattern match. Depth is
# capped so a pathological command cannot recurse forever; three levels
# covers every known bypass plus one level of nesting between them (e.g.
# `bash -c 'eval "python3 tools/courier.py send ..."'`).
is_denied_construct() {
  local text="$1" depth="$2" payload

  if has_invocation "$text"; then
    return 0
  fi

  while IFS= read -r payload; do
    if [ -n "$payload" ] && has_transport_import "$payload"; then
      return 0
    fi
  done <<PAYLOADS
$(python_c_payloads "$text")
PAYLOADS

  if [ "$depth" -ge 3 ]; then
    return 1
  fi

  while IFS= read -r payload; do
    if [ -n "$payload" ] && is_denied_construct "$payload" $((depth + 1)); then
      return 0
    fi
  done <<PAYLOADS
$(shell_c_payloads "$text"; eval_payloads "$text"; subst_payloads "$text"; python_c_payloads "$text")
PAYLOADS

  return 1
}

if ! is_denied_construct "$command" 0; then
  exit 0
fi

agent_type="$(printf '%s' "$input" | jq -r '.agent_type // empty' 2>/dev/null || printf '')"

if [ "$agent_type" = "courier" ]; then
  exit 0
fi

printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Only the courier subagent may post on the transport. Do not call courier.py or orchard_topic.py yourself — ask your courier, in plain language, to send/signal/ask/announce this for you."}}'
exit 0

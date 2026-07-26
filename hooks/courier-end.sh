#!/usr/bin/env bash
# SessionEnd hook — wake this session's courier for its OWN controlled shutdown.
#
# The courier owns its close end-to-end (Decisions 041/046/081): only it stops
# its Monitor, verifies the watcher is gone, tears down the shared mailbox, and
# exits. This hook must never do any of that FOR it — departing or tearing the
# mailbox down here would race a live Monitor and orphan it mid-watch, which is
# exactly the "killed externally" shape the courier's own charter forbids.
#
# So this hook performs the SAME self-message wake a normal mid-session release
# uses: it drops a message into the mailbox the courier's Monitor is already
# watching. If the courier is still listening, this wakes it and it runs its
# own release sequence (depart, then teardown, then exit). If it has already
# released (mailbox gone, or nobody home), the send fails harmlessly — there is
# nothing left to wake, and this hook leaves it exactly as found rather than
# forcing cleanup itself.
set -eu

root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
for candidate in "$root/.claude/tools/courier.py" "$root/tools/courier.py"; do
  [ -f "$candidate" ] && courier="$candidate" && break
done
[ -n "${courier:-}" ] || exit 0

sid="${CLAUDE_CODE_SESSION_ID:-}"
[ -n "$sid" ] || exit 0

python3 "$courier" send --from "$sid" --to "$sid" --body "release" >/dev/null 2>&1 || true
exit 0

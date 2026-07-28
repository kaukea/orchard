- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# Close permission blocking: the harness classifier can strangle a close mid-merge

## Proposal

During the sidebar-teamwork salvage close (2026-07-28), the Claude Code auto-mode
permission classifier blocked every git write — staging, checkout, merge, push,
worktree removal — for the groundskeeper AND for the gardener, from the moment a
conflicted squash existed on the close branch. The operator's explicit, repeated
verbal authorization could not reach the harness: there is no prompt in that mode,
the settings file is (correctly) protected from self-granting, and wrapping the
command in an allowlisted lane is content-inspected. The close stalled one staging
command from completion until the operator changed the session's permission mode.

Make the close machinery immune to this: the fleet's close must either run with
the permissions it needs from the start, or fail fast with a one-line operator
action instead of a multi-round negotiation.

## Questions

1. **Allowlist or mode?** A standing `Bash(git *)`-class allow rule in the project
   settings (operator-pasted once), versus documenting that closes require a
   non-auto permission mode, versus scoping rules to the exact close command set
   (checkout/merge/rm/worktree/branch/push).
2. **Who carries the rule?** settings.json is shipped by this package; a rule there
   reaches every consuming repo. settings.local.json stays per-machine. The close
   runs in both.
3. **Detection.** Should the groundskeeper probe a no-op git write at dispatch time
   and stop BEFORE starting a close it cannot finish, rather than mid-merge?

## Findings

- The block began exactly when the DU-conflicted merge state appeared and then
  covered all git writes for the rest of the session, including previously-working
  commits.
- The operator's authorization channel in auto mode is only: a settings allow rule
  (which the agent cannot write for itself) or leaving the mode. Both are operator
  keystrokes; neither was documented anywhere in the close machinery.
- Cost today: four blocked attempts across two agents, three operator round-trips,
  a close held open across them.

## Testing

Reproduce a conflicted close in a scratch state under auto mode and observe the
close either complete or stop at dispatch with the documented one-line fix.

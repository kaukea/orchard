# supervisor → arborist: the per-feature pipeline role renamed (Decision-140)

The role Decision-090 introduced as "supervisor" is ruled ARBORIST 🌲
(operator, 2026-08-09). The agent definition moved from
`agents/supervisor.md` to `agents/arborist.md`; charters and the sidebar
glyph table now say arborist. Consuming repos that link or copy the agent
set carry a dangling `supervisor.md` until converted.

## Detect → convert

```sh
root="$(git rev-parse --show-toplevel)"
a="$root/.claude/agents"
# Symlink install: retarget if a supervisor link exists
if [ -L "$a/supervisor.md" ]; then
  rm "$a/supervisor.md"
  [ -e "$a/arborist.md" ] || ln -s ../../agents/arborist.md "$a/arborist.md"
fi
# Copy install: rename if a real file exists and no arborist yet
if [ -f "$a/supervisor.md" ] && [ ! -L "$a/supervisor.md" ] && [ ! -e "$a/arborist.md" ]; then
  mv -n "$a/supervisor.md" "$a/arborist.md"
fi
```

Judgement step: if repo-local docs or scripts spawn `--agent supervisor` or
`subagent_type: "supervisor"`, repoint them to `arborist` — grep
`supervisor` and convert only role references (leave unrelated uses, e.g.
thread/process supervisors, alone).

## Verify

- `[ -e .claude/agents/arborist.md ]` and no `.claude/agents/supervisor.md`
- `grep -L` no remaining `--agent supervisor` launches in repo-local tooling

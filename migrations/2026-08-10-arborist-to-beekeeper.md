# arborist → beekeeper: same-day reversal of Decision-140 (Decision-141); groomer retired

The per-feature pipeline role is ruled BEEKEEPER 🐝 (operator, 2026-08-10),
reversing the same-day Decision-140 "arborist" naming — that name is freed
for a separate technical-HOW-designer role. `agents/arborist.md` moved to
`agents/beekeeper.md`; `agents/groomer.md` is DELETED, its prep-only
responsibilities folded into `bloomer` (pass mode).

## Detect → convert

```sh
root="$(git rev-parse --show-toplevel)"
a="$root/.claude/agents"
if [ -L "$a/arborist.md" ]; then
  rm "$a/arborist.md"
  [ -e "$a/beekeeper.md" ] || ln -s ../../agents/beekeeper.md "$a/beekeeper.md"
fi
if [ -f "$a/arborist.md" ] && [ ! -L "$a/arborist.md" ] && [ ! -e "$a/beekeeper.md" ]; then
  mv -n "$a/arborist.md" "$a/beekeeper.md"
fi
[ -L "$a/groomer.md" ] && rm "$a/groomer.md"
[ -f "$a/groomer.md" ] && [ ! -L "$a/groomer.md" ] && rm "$a/groomer.md"
```

Judgement step: repoint `--agent arborist` / `subagent_type: "arborist"` launches to
`beekeeper`, and drop any `--agent groomer` / `subagent_type: "groomer"` in favor of
`bloomer`. Grep `arborist`/`groomer` and convert only role references.

## Verify

```sh
[ -e "$root/.claude/agents/beekeeper.md" ] && [ ! -e "$root/.claude/agents/arborist.md" ] \
  && [ ! -e "$root/.claude/agents/groomer.md" ] && echo OK
```

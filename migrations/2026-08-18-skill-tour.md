# The skill tour: categories arrive; enforcing-rules and writing-prose rename

Every artifact now declares `categories:` (the `roles:` key is retired; readers
fall back while consumers converge) with the ruled tree: `process/orchard`
(the renamed workflow node), `authoring` (new), `development`, `general` as the
catch-all. Two skills rename: `read-agents` → `enforcing-rules`, `writing` →
`writing-prose`. Agents declare `categories:` and `dependencies-skills:`.

## Detect → convert

```sh
set -eu
root=$(git rev-parse --show-toplevel)
for pair in "read-agents enforcing-rules" "writing writing-prose"; do
  old=${pair% *}; new=${pair#* }
  l="$root/.claude/skills/$old"
  if [ -L "$l" ] && [ ! -e "$l" ]; then
    rm "$l"
    echo "removed dangling $old link (renamed to $new; next sync lays it)"
  fi
done
exit 0
```

## Verify

- After a sync, `.claude/skills/enforcing-rules` and `.claude/skills/writing-prose`
  resolve; no `read-agents` or `writing` link remains.
- Selecting `process/orchard` in a consumer lays the workflow corpus and its
  closure; `general` carries only the catch-all.

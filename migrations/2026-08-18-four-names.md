# Four skills say what they do: writing-commits, diagnosing-issues, organising-work, continuing-work

The grandfathered one-word names take their replacements (kauk Decision-048's
two-part rule, names ruled by the operator 2026-08-18): `git` →
`writing-commits`, `diagnostics` → `diagnosing-issues`, `workflow` →
`organising-work`, `handover` → `continuing-work`. `git-workflow` and
`workflow-complete` keep their names.

## Detect → convert

```sh
set -eu
root=$(git rev-parse --show-toplevel)
for pair in "git writing-commits" "diagnostics diagnosing-issues" "workflow organising-work" "handover continuing-work"; do
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

- After a sync, the four new links resolve and no old-named link remains.

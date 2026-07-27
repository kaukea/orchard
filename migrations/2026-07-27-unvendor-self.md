# 2026-07-27 — orchids stops installing itself; `.claude/**` links point at this repo

This repository is the SOURCE of the orchids package. Since `5fee5a7` it also listed
itself as a kauk SOURCE, so `kauk sync` cloned it into
`.ai/repositories/serialseb/orchids/` and laid 51 absolute symlinks under `.claude/`
pointing into that clone — agents, skills, hooks, `settings.json` and every tool.

The consequence is that agents executed the clone, not the repository. The clone sat at
`2fbc3cc` while `main` was at `d0b27dd`, so the running code was several commits stale
and the gap spanned a whole transport rewrite: the clone still described per-agent
mailboxes under the git-common-dir, which `main` had already replaced with flat files
under `$XDG_RUNTIME_DIR/orchard/`. Editing `tools/` changed nothing about what ran until
someone happened to sync. Because the links were ABSOLUTE, every worktree resolved into
the same stale clone as well, so a feature branch could not run its own code either.

Decision-112 recorded one symptom of this — a feedback surface showing `main`'s renderer
to an operator judging a branch — and attributed it to one symlink in
`tools/sidebar-mount.sh`. The cause was general: it was the whole `.claude/` tree.

A source repository consuming a vendored clone of its own output is circular. It is
removed rather than pinned or refreshed: no sync cadence makes a repo's own code a
downstream dependency of itself.

`serialseb/kauk` remains a source and its `.claude/skills/kauk` link is untouched — that
one is a genuine external package.

## Detect → convert

```sh
# 1. Repoint any tracked symlink that still resolves into this repo's own vendored
#    clone at the repo's real file, using a RELATIVE link so worktrees resolve locally.
prefix_suffix=".ai/repositories/serialseb/orchids/"
root="$(git rev-parse --show-toplevel)"
[ -n "$root" ] || exit 0
cd "$root" || exit 0
git ls-files | while IFS= read -r f; do
  [ -L "$f" ] || continue
  t="$(readlink "$f")"
  case "$t" in
    *"$prefix_suffix"*) rel="${t##*$prefix_suffix}" ;;
    *) continue ;;
  esac
  [ -n "$rel" ] && [ -e "$rel" ] || continue
  newlink="$(realpath --relative-to="$root/$(dirname "$f")" "$root/$rel")"
  rm "$f" && ln -s "$newlink" "$f"
done

# 2. Drop the self-source from the kauk manifest so a later sync cannot re-vendor it.
if [ -f .ai.toml ] && grep -q '^\[sources\."serialseb/orchids"\]' .ai.toml; then
  awk '
    /^\[sources\."serialseb\/orchids"\]$/ { skip=1; next }
    skip && /^\[/ { skip=0 }
    !skip { print }
  ' .ai.toml > .ai.toml.tmp && mv .ai.toml.tmp .ai.toml
fi

# 3. The clone itself is gitignored and may simply be deleted; nothing reads it now.
rm -rf .ai/repositories/serialseb/orchids
true
```

## Consequence to be aware of

Unvendoring makes the repository's real state the running state, which is the point —
but it also EXPOSES a regression that the stale clone was masking. The clone's
`courier.identity_of()` returned `task_id` and `task_name`; `main`'s does not. Decision-108
("messaging carries which task an agent is on") was implemented, then lost in the
transport rewrite, and live events carried `identity.task` only because old code was
producing them. After this migration that field disappears from the bus until it is
restored in `tools/courier.py`. Consumers must fall back to the feature when it is absent.

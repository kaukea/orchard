# The migration watermark becomes one file per package

A clone installs several packages, each carrying its own `migrations/`. A single
`the-works/migrated` file holding one basename cannot track them: whichever package
advanced it last hides every other package's pending work, and a pure consumer — which
has no repo-root `migrations/` of its own — was never told anything at all.

The watermark is now a directory keyed exactly like everything else, by owner and repo:
`the-works/migrated/<owner>/<repo>` holds that package's last applied migration basename.
No file = everything pending for that package.

## Detect → convert

```sh
set -eu
root=$(git rev-parse --show-toplevel)
gcd=$(git rev-parse --git-common-dir)
case "$gcd" in /*) ;; *) gcd="$root/$gcd" ;; esac
wm="$gcd/the-works/migrated"

# Only a bare-file watermark needs converting. A directory is already converted.
[ -f "$wm" ] || { echo "watermark already per-package (or absent) — nothing to do"; exit 0; }

name=$(cat "$wm")
[ -n "$name" ] || { rm -f "$wm"; mkdir -p "$wm"; echo "empty watermark discarded"; exit 0; }

# Which package does that basename belong to? The one whose migrations/ contains it.
owner_repo=""
for d in "$root/migrations" "$root"/.ai/repositories/*/*/migrations; do
  [ -f "$d/$name.md" ] || continue
  pkg=${d%/migrations}
  if [ "$pkg" = "$root" ]; then
    url=$(git -C "$root" remote get-url origin 2>/dev/null || true)
    url=${url%.git}; url=${url%/}
    [ -n "$url" ] || continue
    owner_repo="$(basename "$(dirname "$url")")/$(basename "$url")"
  else
    owner_repo="$(basename "$(dirname "$pkg")")/$(basename "$pkg")"
  fi
  break
done

rm -f "$wm"
mkdir -p "$wm"
if [ -n "$owner_repo" ]; then
  mkdir -p "$wm/$(dirname "$owner_repo")"
  printf '%s\n' "$name" > "$wm/$owner_repo"
  echo "watermark $name attributed to $owner_repo"
else
  echo "watermark $name matches no installed package — discarded, all migrations pending"
fi
```

Discarding an unattributable watermark is safe: every migration step is guarded by
observable state, so re-applying one already applied is a no-op.

## Verify

- `the-works/migrated` is a directory, not a file.
- Each installed package that has ever been migrated has one file under it at
  `<owner>/<repo>` containing a single basename.
- The session's pending notice now lists packages separately, and a package whose
  watermark is current no longer appears.

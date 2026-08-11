#!/usr/bin/env bash
# Announce unapplied migrations, per package.
#
# Every installed package carries its own migrations/, and the consuming clone
# keeps one watermark per package at .git/the-works/migrated/<owner>/<repo>.
# Absent watermark = everything pending for that package.
set -u

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$root" ] || exit 0
gcd=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
case "$gcd" in /*) ;; *) gcd="$root/$gcd" ;; esac
wmdir="$gcd/the-works/migrated"

# owner/repo from a remote URL or path — last two components, .git stripped.
ident_from_url() {
  local u=${1%.git}
  u=${u%/}
  local repo=${u##*/} rest=${u%/*}
  local owner=${rest##*/}
  [ -n "$owner" ] && [ -n "$repo" ] && [ "$owner" != "$repo" ] && printf '%s/%s' "$owner" "$repo"
}

report=""

# $1 = owner/repo   $2 = that package's migrations directory
collect() {
  local id=$1 dir=$2 wm="" latest="" pending="" b
  [ -n "$id" ] && [ -d "$dir" ] || return 0
  [ -f "$wmdir/$id" ] && wm=$(cat "$wmdir/$id" 2>/dev/null)

  for f in "$dir"/*.md; do
    [ -e "$f" ] || continue
    b=${f##*/}; b=${b%.md}
    [ "$b" \> "$latest" ] && latest=$b
    [ "$b" \> "$wm" ] && pending="$pending $b"
  done

  [ -n "$pending" ] || return 0
  report="$report\n- $id (watermark: ${wm:-none}):$pending"
}

# The repository's own migrations, keyed by its own identity.
collect "$(ident_from_url "$(git -C "$root" remote get-url origin 2>/dev/null)")" "$root/migrations"

# Every installed package's migrations, keyed by where it is vendored.
for d in "$root"/.ai/repositories/*/*/migrations; do
  [ -d "$d" ] || continue
  pkg=${d%/migrations}
  collect "$(basename "$(dirname "$pkg")")/$(basename "$pkg")" "$d"
done

[ -n "$report" ] || exit 0

printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"Migrations are pending, per package:%s\\n\\nFor each package listed, read the named migrations from that package'"'"'s migrations/ directory (the repo root for its own, .ai/repositories/<owner>/<repo>/migrations/ otherwise), merge them, apply the net effect - every step guarded by observable state - then write the highest applied basename to .git/the-works/migrated/<owner>/<repo>. Packages are independent: finish one before starting the next. See AGENTS.files.md Migrations section."}}' "$report"
exit 0

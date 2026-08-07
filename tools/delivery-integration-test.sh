#!/usr/bin/env bash
# Delivery integration test — proves a brand-new project pulling in orchids
# gets the right files in the right position via the conventional kauk path.
#
# What it does, end to end, all in a throwaway directory:
#   1. Snapshots this repository's committed HEAD as the package origin
#      (uncommitted noise never ships, so the test judges what a consumer
#      would actually receive).
#   2. Snapshots the kauk repository's committed HEAD (KAUK_DIR, default
#      ~/src/serialseb/kauk) the same way.
#   3. Creates a fresh consumer project and runs the real `kauk install`.
#   4. Verifies every manifest entry landed: each skill and link resolves at
#      its destination, the AGENTS.md template was substituted, the CLAUDE.md
#      prefix is present, and no dangling symlink exists under .claude.
#   5. Verifies the committed manifest.conf matches a regeneration from the
#      tree (the anti-silent-drift gate).
#   6. Runs `kauk sync` a second time and re-verifies (idempotence).
#
# Exit 0 = all green. Any failure prints FAIL with the reason and exits 1.
set -euo pipefail

say()  { printf '%s\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KAUK_DIR="${KAUK_DIR:-$HOME/src/serialseb/kauk}"
[ -d "$KAUK_DIR/.git" ] || fail "kauk repository not found at $KAUK_DIR (set KAUK_DIR)"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

snapshot() { # snapshot <src-repo> <dst> — committed HEAD only, branch named main
  git init --quiet "$2"
  git -C "$2" fetch --quiet "$1" HEAD
  git -C "$2" checkout --quiet -B main FETCH_HEAD
}

say "== snapshot package under test ($(git -C "$SRC" rev-parse --short HEAD))"
pkg="$work/orchids-origin"
snapshot "$SRC" "$pkg"
[ -f "$pkg/manifest.conf" ] || fail "manifest.conf is not committed at the package root"

say "== snapshot kauk ($(git -C "$KAUK_DIR" rev-parse --short HEAD))"
kauk="$work/kauk"
snapshot "$KAUK_DIR" "$kauk"
KAUK_BIN="$kauk/bin/kauk"
[ -x "$KAUK_BIN" ] || fail "kauk stopgap not executable at $KAUK_BIN"

say "== create fresh consumer project"
consumer="$work/fresh-project"
git init --quiet "$consumer"
git -C "$consumer" -c user.email=t@t -c user.name=t commit --quiet --allow-empty -m init

say "== kauk install serialseb/orchids"
(cd "$consumer" && "$KAUK_BIN" install serialseb/orchids "$pkg")

clone="$consumer/.ai/repositories/serialseb/orchids"

manifest_entries() { grep -Ev '^[[:space:]]*(#|$)' "$clone/manifest.conf"; }

verify() {
  local checked=0 t a b _rest target
  while read -r t a b _rest; do
    case "$t" in
      skill)
        target="$consumer/.claude/skills/$a"
        [ -L "$target" ] || fail "skill $a: no symlink at .claude/skills/$a"
        [ -f "$target/SKILL.md" ] || fail "skill $a: SKILL.md unreachable through the link"
        checked=$((checked+1)) ;;
      link)
        [ -L "$consumer/$b" ] || fail "link $b: missing"
        [ -e "$consumer/$b" ] || fail "link $b: dangling (target $a absent in package)"
        checked=$((checked+1)) ;;
      template)
        [ -f "$consumer/$b" ] || fail "template $b: not created"
        checked=$((checked+1)) ;;
      prefix)
        [ -f "$consumer/$b" ] || fail "prefix target $b: missing"
        grep -qF "$(head -1 "$clone/$a")" "$consumer/$b" || fail "prefix $b: marker absent"
        checked=$((checked+1)) ;;
    esac
  done < <(manifest_entries)
  [ "$checked" -gt 0 ] || fail "manifest produced zero verifiable entries"

  grep -q "fresh-project" "$consumer/AGENTS.md" || fail "AGENTS.md template: <project-name> not substituted"

  local dangling
  dangling="$(find "$consumer/.claude" -type l ! -exec test -e {} \; -print)"
  [ -z "$dangling" ] || fail "dangling links under consumer .claude:$(printf '\n%s' "$dangling")"

  say "   verified $checked manifest entries, no dangling links"
}

say "== verify layout after install"
verify

say "== verify manifest matches a regeneration from the tree"
python3 "$clone/tools/manifest_gen.py" > "$work/manifest.regen"
diff -u "$clone/manifest.conf" "$work/manifest.regen" \
  || fail "committed manifest.conf drifted from the tree — regenerate with tools/manifest_gen.py"

say "== verify every tracked skill dir is indexed"
for d in "$clone"/skills/*/; do
  n="$(basename "$d")"
  grep -q "^skill $n " "$clone/manifest.conf" || fail "skill $n exists in tree but not in manifest"
done

say "== kauk sync (idempotence)"
(cd "$consumer" && "$KAUK_BIN" sync)

say "== verify layout after sync"
verify

say "PASS: fresh project receives the package correctly"

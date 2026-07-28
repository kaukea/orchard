#!/usr/bin/env bash
# capture-snapshot.sh — incremental preservation of mortal fleet data (ledger v0 spool).
# Idempotent; safe to run at every orchestrator boot. Ledger proper replaces this later.
set -euo pipefail

DEST="$(git -C "$(dirname "$0")/../.." rev-parse --git-common-dir)/the-works/_capture"
HOST="$(hostname -s)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DEST/$HOST"

# 1. Claude session transcripts (all projects, all repos) — the most mortal corpus.
if [ -d "$HOME/.claude/projects" ]; then
  rsync -a --exclude '*.tmp' "$HOME/.claude/projects/" "$DEST/$HOST/claude-projects/"
fi

# 2. Every repo's uncommittable the-works channel (workstream logs, MOOD) under ~/src.
find "$HOME/src" -maxdepth 4 -type d -name "the-works" -path "*/.git/*" 2>/dev/null |
while IFS= read -r works; do
  repo="$(basename "$(dirname "$(dirname "$works")")")"
  [ "$repo" = "orchids" ] && continue   # our own the-works already lives here
  mkdir -p "$DEST/$HOST/the-works/$repo"
  rsync -a --exclude '_capture' "$works/" "$DEST/$HOST/the-works/$repo/"
done

# 3. Append a manifest line: when, what, how much (the spool's own audit trail).
COUNT="$(find "$DEST/$HOST" -type f | wc -l)"
SIZE="$(du -sh "$DEST/$HOST" | cut -f1)"
printf '%s snapshot files=%s size=%s\n' "$STAMP" "$COUNT" "$SIZE" >> "$DEST/manifest.log"
printf 'capture-snapshot: %s files, %s\n' "$COUNT" "$SIZE"

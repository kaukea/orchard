#!/usr/bin/env python3
"""Canonical human name for a feature id — the single helper every
title-setting call site reads, so the sidebar/tmux window title is never the
program name ("claude"), a bare id, or an inconsistently-grammared guess.

Priority (docs/TODO.md.d/sidebar-polish.md item 11, "GRAMMAR — RESOLVED"):
  1. The board's authored short title — `[Short title](TODO.md.d/<id>.md)`
     in docs/TODO.md (AGENTS.files.md §TODO board format). Authored AT THE
     MOMENT the ledger entry is written, so this is read verbatim, never
     grammar-converted.
  2. The sidecar's own first `# ...` H1 heading (docs/TODO.md.d/<id>.md),
     used only when the board entry is missing or fails to parse.
  3. Mechanical `id.replace("-", " ")` — the pre-intake fallback, for a
     brand-new feature with no board entry or sidecar content yet.

No grammar-conversion code is built here (that was explicitly rejected by
the resolution above): steps 1 and 2 read an already-authored human name;
step 3 is a literal transliteration, not grammar.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess

# Mirrors board_lint.py's parse_board() regex (AGENTS.files.md §TODO) — same
# shape, narrowed to "does this line name THIS id" rather than parsing every
# task on the board.
_TITLE_RE = re.compile(
    r'^\s*-\s*`[^`]*`\s*\[(.*?)\]\(TODO\.md\.d/([a-z0-9-]+)\.md\)'
)
_H1_RE = re.compile(r'^#\s+(.+?)\s*$')


def _repo_root(start: str | None = None) -> str | None:
    """git toplevel for `start` (or cwd) — the same resolution courier.py's
    identity_of() uses, so a caller that already has that value should pass
    it in via `root=` instead of paying for a second subprocess call."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True, check=True,
        )
        path = out.stdout.strip()
        return path or None
    except Exception:
        return None


def _strip_strike(title: str) -> str:
    """A cancelled task's board title is struck (`~~text~~`, AGENTS.files.md
    §TODO status=cancelled) — the human name is the text underneath."""
    if title.startswith("~~") and title.endswith("~~") and len(title) >= 4:
        return title[2:-2]
    return title


def _board_title(root: str, feature_id: str) -> str | None:
    board = os.path.join(root, "docs", "TODO.md")
    if not os.path.isfile(board):
        return None
    try:
        with open(board, encoding="utf-8") as fh:
            for line in fh:
                m = _TITLE_RE.match(line)
                if m and m.group(2) == feature_id:
                    title = m.group(1).strip()
                    return _strip_strike(title) if title else None
    except OSError:
        return None
    return None


def _sidecar_h1(root: str, feature_id: str) -> str | None:
    sidecar = os.path.join(root, "docs", "TODO.md.d", f"{feature_id}.md")
    if not os.path.isfile(sidecar):
        return None
    try:
        with open(sidecar, encoding="utf-8") as fh:
            for line in fh:
                m = _H1_RE.match(line)
                if m:
                    heading = m.group(1).strip()
                    return heading or None
    except OSError:
        return None
    return None


def feature_name(feature_id: str | None, root: str | None = None) -> str | None:
    """The canonical human name for `feature_id`.

    `root` is the repo/worktree root to read docs/TODO.md and its sidecars
    from; resolved via `git rev-parse --show-toplevel` (cwd) if omitted.
    Returns None only when `feature_id` itself is falsy — the caller's own
    concern (e.g. show the repo name dimmed pre-announce), never this
    helper's.
    """
    if not feature_id:
        return None
    root = root or _repo_root()
    if root:
        name = _board_title(root, feature_id) or _sidecar_h1(root, feature_id)
        if name:
            return name
    return feature_id.replace("-", " ")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--id", required=True, help="feature id (board/sidecar basename)")
    p.add_argument("--root", default=None, help="repo root (default: git toplevel of cwd)")
    args = p.parse_args()
    print(feature_name(args.id, root=args.root) or "")


if __name__ == "__main__":
    main()

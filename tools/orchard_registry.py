#!/usr/bin/env python3
"""Orchard registry — the persisted list of repos the fleet sidebar shows, and
which of them the operator has asked to hide (docs/TODO.md.d/sidebar-polish.md
item 7).

Design (this module's HOW, greenfield — `/orchard add <path>` is REVERTED):
installing orchids in a repo makes it appear automatically ("installation IS
registration") — `.ai.toml` presence is the install signal (unchanged from the
sidebar-polish item-7 ruling). There is no clean kauk-install hook to write the
registry from in THIS checkout (the real `kauk init`/`install` verbs live in
the sibling `serialseb/kauk` package, not here), so this module is the hook
point instead: `register_repo()` is the one call whatever bootstraps a new
orchids repo (a future kauk step, or a manual call) should make, and
`registered_repos()` self-heals on every read — no separate "uninstall" verb
is needed, a repo whose `.ai.toml` disappears just drops out on the next scan.

Registry file: ~/.config/orchids/sidebar-registry.json

    {
      "repos": ["/home/user/src/a", "/home/user/src/b"],
      "hidden": ["/home/user/src/b"]
    }

`repos` is every registered path (self-healed against `.ai.toml` presence);
`hidden` is the operator's persistent hide list (sidebar-polish item 7b) —
always a subset of `repos`, self-healed the same way so an uninstalled repo
never lingers in either list. Hiding/showing is by REPO PATH; the sidebar/
skill layer resolves the operator's displayed name to a path (see
`repo_named()`) before calling into this module.

Public API: register_repo, registered_repos, hidden_repos, visible_repos,
hide_repo, show_repo, repo_named.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REGISTRY_PATH = Path.home() / ".config" / "orchids" / "sidebar-registry.json"

_EMPTY = {"repos": [], "hidden": []}


def _has_ai_toml(path: str) -> bool:
    return (Path(path) / ".ai.toml").is_file()


def _resolve_path(registry_path: Path | None) -> Path:
    # lazy default -- resolved at CALL time, not at def time, so tests (and
    # sidebar_model, which calls these without passing registry_path) can
    # redirect every default-taking caller by patching the module attribute
    # `orchard_registry.REGISTRY_PATH` rather than needing every call site to
    # thread the path through explicitly.
    return registry_path if registry_path is not None else REGISTRY_PATH


def _load(registry_path: Path | None = None) -> dict:
    registry_path = _resolve_path(registry_path)
    try:
        text = registry_path.read_text(encoding="utf-8")
    except OSError:
        return dict(_EMPTY)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return dict(_EMPTY)
    if not isinstance(data, dict):
        return dict(_EMPTY)
    repos = data.get("repos")
    hidden = data.get("hidden")
    return {
        "repos": list(repos) if isinstance(repos, list) else [],
        "hidden": list(hidden) if isinstance(hidden, list) else [],
    }


def _save(data: dict, registry_path: Path | None = None) -> None:
    """Write atomically (same idiom as tools/courier.py's deliver()) so a reader
    never observes a half-written registry."""
    registry_path = _resolve_path(registry_path)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = registry_path.parent / f".{registry_path.name}.partial"
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, registry_path)


def _heal(registry_path: Path | None = None) -> dict:
    """Load, drop any repo whose `.ai.toml` no longer exists (self-healing —
    an uninstalled/deleted repo falls out on its own, no explicit unregister
    verb needed), prune `hidden` to match, persist if anything changed."""
    registry_path = _resolve_path(registry_path)
    data = _load(registry_path)
    healed_repos = [r for r in data["repos"] if _has_ai_toml(r)]
    healed_hidden = [r for r in data["hidden"] if r in healed_repos]
    if healed_repos != data["repos"] or healed_hidden != data["hidden"]:
        data = {"repos": healed_repos, "hidden": healed_hidden}
        _save(data, registry_path)
    return data


def register_repo(path: str, registry_path: Path | None = None) -> bool:
    """Register `path` if it has `.ai.toml` and isn't already registered.
    Returns True iff the registry changed. The "installing IS registration"
    hook point — call this the moment `.ai.toml` presence is detected."""
    if not _has_ai_toml(path):
        return False
    registry_path = _resolve_path(registry_path)
    data = _heal(registry_path)
    if path in data["repos"]:
        return False
    data["repos"].append(path)
    _save(data, registry_path)
    return True


def registered_repos(registry_path: Path | None = None) -> list[str]:
    """Every registered repo, self-healed against current `.ai.toml` presence."""
    return list(_heal(registry_path)["repos"])


def hidden_repos(registry_path: Path | None = None) -> list[str]:
    """The operator's persistent hide list, self-healed the same way."""
    return list(_heal(registry_path)["hidden"])


def visible_repos(registry_path: Path | None = None) -> list[str]:
    """Registered repos minus hidden ones — what the sidebar should show."""
    data = _heal(registry_path)
    hidden = set(data["hidden"])
    return [r for r in data["repos"] if r not in hidden]


def hide_repo(path: str, registry_path: Path | None = None) -> bool:
    """Persist `path` into the hidden list. Returns True iff it changed
    (path must already be registered; hiding an unregistered path is a no-op)."""
    registry_path = _resolve_path(registry_path)
    data = _heal(registry_path)
    if path not in data["repos"] or path in data["hidden"]:
        return False
    data["hidden"].append(path)
    _save(data, registry_path)
    return True


def show_repo(path: str, registry_path: Path | None = None) -> bool:
    """Remove `path` from the hidden list. Returns True iff it changed."""
    registry_path = _resolve_path(registry_path)
    data = _heal(registry_path)
    if path not in data["hidden"]:
        return False
    data["hidden"] = [r for r in data["hidden"] if r != path]
    _save(data, registry_path)
    return True


def repo_named(name: str, candidates: list[str]) -> str | None:
    """Resolve an operator-given displayed name (or a bare path) to one of
    `candidates` — exact path match first, else the last path component
    (the same `Path(p).name` the sidebar renders as the repo's display name).
    None if no candidate matches, or more than one shares that display name
    (ambiguous — the caller should fall back to the numbered-list prompt)."""
    if name in candidates:
        return name
    matches = [c for c in candidates if Path(c).name == name]
    return matches[0] if len(matches) == 1 else None


# --------------------------------------------------------------------------
# CLI — used by the `orchard` skill so the direct forms don't need bespoke
# scripting; conversational hide/show is driven by the skill's instructions
# calling `list` then `hide <path>`/`show <path>` with an operator-picked path.
# --------------------------------------------------------------------------

def _cli(argv: list[str]) -> int:
    if not argv:
        print("usage: orchard_registry.py list|hide <name-or-path>|show <name-or-path>",
              file=sys.stderr)
        return 2

    cmd, *rest = argv

    if cmd == "list":
        repos = registered_repos()
        hidden = set(hidden_repos())
        if not repos:
            print("(no repos registered)")
            return 0
        for i, r in enumerate(repos, start=1):
            flag = " [hidden]" if r in hidden else ""
            print(f"{i}. {Path(r).name}{flag}  ({r})")
        return 0

    if cmd in ("hide", "show") and rest:
        target = rest[0]
        pool = registered_repos()
        path = repo_named(target, pool)
        if path is None:
            print(f"orchard: no unambiguous registered repo matches {target!r}",
                  file=sys.stderr)
            return 1
        changed = hide_repo(path) if cmd == "hide" else show_repo(path)
        verb = "hidden" if cmd == "hide" else "shown"
        print(f"{Path(path).name}: {verb}" if changed else f"{Path(path).name}: already {verb}")
        return 0

    print("usage: orchard_registry.py list|hide <name-or-path>|show <name-or-path>",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))

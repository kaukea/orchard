#!/usr/bin/env python3
"""Cross-repo bus reader/aggregator for the fleet sidebar.

READ-ONLY observer over the on-disk bus (see tools/bus.py, message.schema.json):

    <git-common-dir>/the-works/bus/<session-id>/<datetime>.json

one JSON message per file. This module never deletes, moves, or otherwise
mutates a bus file — messages are owned by their recipients (bus.py's
`receive` drains them on the way up); the sidebar only looks.

ATTRIBUTION: the folder a message physically sits in is its RECIPIENT's inbox,
not its origin — bus.py's fan_out/broadcast delivers a copy into every OTHER
session's folder, never the sender's own (`peers = [... d.name != sender]`).
So every message is attributed to its envelope `from` field, never to the
folder it was found in: a repo's bus is scanned in full (every session
folder), and each parsed message is routed to state[from].

EPHEMERALITY: a message file disappears once its recipient's bus sidecar
drains it (`receive` unlinks on read), often within moments. A sender's
last-known activity/lifecycle/subagent-set must therefore be remembered
across scans, not just re-derived from whatever happens to be on disk right
now — see _BusAggregator, which accumulates per-sender state keyed by
envelope `from`, deduplicated by envelope `id`, applied in `ts` order
(last-write-wins per field). `build_model()` is a single-scan convenience
wrapper around a fresh, throwaway aggregator; `watch()` keeps one aggregator
alive for the life of the watch so accumulation survives across scans.

Repo list resolution (env ORCHIDS_SIDEBAR_REPOS -> file path, else
~/.config/orchids/sidebar-repos; one repo path per line, '#' comments and
blank lines ignored; falls back to the current repo alone).

Public API: build_model(), iter_bus_roots(), watch(on_change, ...).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_REPOLIST = Path.home() / ".config" / "orchids" / "sidebar-repos"

# Sidecar sessions surface as agent_type "bus"; their subagent label is
# conventionally "messaging" — never shown as a fleet subagent row (they get
# their own single collapsed "bus row" instead — see _pick_bus()).
BUS_AGENT_TYPE = "bus"
BUS_LABEL = "messaging"

# Six-state status vocabulary (final, settled — sidebar-polish item 9,
# revised). Every status below is STATIC: no glyph may ever change
# frame-to-frame. "working"/"done"/"failed" fall straight out of the
# lifecycle table; "waiting" (component vs operator variant) and
# "awaiting_agent" (blocked on a peer) need the extra blocked_on/notify_user
# logic in _status_for() below, so they are deliberately NOT in this table.
LIFECYCLE_TO_STATUS = {
    "started": "working",
    "building": "working",
    "testing": "working",
    "finished": "done",
    "abandoned": "failed",
    # "done" (the pre-terminal "built, awaiting THAT IS ALL" lifecycle state)
    # and "blocked" are handled by _status_for()'s precedence rules, not this
    # table — both need more than a 1:1 lifecycle->status mapping.
}

# A `blocked` lifecycle signal's body may carry a `blocked_on` tag
# distinguishing what it's blocked ON — bus.py's signal command didn't carry
# this distinction before this change (checked: LIFECYCLE_STATES only ever
# had a bare "blocked", no qualifier), so this is the minimal tag added to
# make the waiting/awaiting_agent split possible. Absent (older senders,
# senders that didn't pass --blocked-on) defaults to BLOCKED_ON_COMPONENT —
# the safer assumption, since a peer-agent block should be opted into
# explicitly.
BLOCKED_ON_COMPONENT = "component"
BLOCKED_ON_AGENT = "agent"

# A "bare session-UUID row" — no announced name, only the raw session id —
# is never operator-facing (sidebar-polish item 2 / this round's item 3b).
_SESSION_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _is_bare_uuid(text: str | None) -> bool:
    return bool(text) and bool(_SESSION_UUID_RE.match(text))


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------

@dataclass
class Subagent:
    label: str


@dataclass
class Bus:
    """One collapsed bus-sidecar row for a live parent agent (repo's
    orchestrator or a feature's architect) — sidebar-polish item 5. At most
    one per parent, rendered at the top of that parent's row group."""
    label: str = BUS_LABEL


@dataclass
class Feature:
    feature_id: str
    name: str
    activity: str
    status: str
    waiting_on_operator: bool
    subagents: list[Subagent] = field(default_factory=list)
    bus: Bus | None = None


@dataclass
class Repo:
    path: str
    name: str
    activity: str
    status: str
    waiting_on_operator: bool
    paused: bool = False
    features: list[Feature] = field(default_factory=list)
    bus: Bus | None = None


@dataclass
class Fleet:
    repos: list[Repo] = field(default_factory=list)


# --------------------------------------------------------------------------
# Repo list resolution
# --------------------------------------------------------------------------

def _git(*args: str, cwd: str | None = None) -> str:
    try:
        done = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True, cwd=cwd,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return done.stdout.strip()


def _current_repo() -> str | None:
    common = _git("rev-parse", "--git-common-dir")
    if not common:
        return None
    # git-common-dir is typically "<repo>/.git" (or the bare-repo dir itself);
    # the repo path is its parent unless it IS the toplevel already.
    common_path = Path(common).resolve()
    if common_path.name == ".git":
        return str(common_path.parent)
    return str(common_path)


def _read_repolist(path: Path) -> list[str]:
    repos: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return repos
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        repos.append(line)
    return repos


def resolve_repos(repolist: list[str] | None = None) -> list[str]:
    """Resolve the list of repo paths the sidebar aggregates over."""
    if repolist:
        return list(repolist)

    env_path = os.environ.get("ORCHIDS_SIDEBAR_REPOS", "").strip()
    candidate = Path(env_path) if env_path else DEFAULT_REPOLIST
    repos = _read_repolist(candidate)
    if repos:
        return repos

    current = _current_repo()
    return [current] if current else []


def _bus_root_for(repo_path: str) -> Path | None:
    """<git-common-dir>/the-works/bus for one repo path, or None if not a repo."""
    common = _git("rev-parse", "--git-common-dir", cwd=repo_path)
    if not common:
        return None
    common_dir = Path(common)
    if not common_dir.is_absolute():
        common_dir = Path(repo_path) / common_dir
    return common_dir.resolve() / "the-works" / "bus"


def iter_bus_roots(repolist: list[str] | None = None) -> list[Path]:
    """The bus root (<git-common-dir>/the-works/bus) for each resolved repo."""
    roots = []
    for repo_path in resolve_repos(repolist):
        root = _bus_root_for(repo_path)
        if root is not None:
            roots.append(root)
    return roots


# --------------------------------------------------------------------------
# Bus reading (read-only) — per-sender state, accumulated across scans
# --------------------------------------------------------------------------

@dataclass
class _SessionState:
    session_id: str
    agent_type: str | None = None
    worktree: str | None = None
    feature_id: str | None = None
    name: str | None = None
    parent_session: str | None = None
    activity: str = ""
    lifecycle_state: str | None = None
    blocked_on: str | None = None  # BLOCKED_ON_COMPONENT / BLOCKED_ON_AGENT
    active_subagents: set = field(default_factory=set)
    last_notify_user: bool = False  # notify_user flag of the latest message seen


def _apply_message(state: _SessionState, msg: dict) -> None:
    body = msg.get("body")

    if isinstance(body, dict) and set(body) >= {
        "session_id", "agent_type", "worktree", "feature_id", "name", "parent_session",
    }:
        # identity/announce push (identity_of() shape)
        state.agent_type = body.get("agent_type")
        state.worktree = body.get("worktree")
        state.feature_id = body.get("feature_id")
        state.name = body.get("name")
        state.parent_session = body.get("parent_session")

    elif isinstance(body, dict) and body.get("kind") == "lifecycle":
        state.lifecycle_state = body.get("state")
        state.blocked_on = body.get("blocked_on")

    elif isinstance(body, str):
        if body.startswith("orchid:activity:"):
            # text after the 2nd colon; may itself contain colons/spaces
            state.activity = body.split(":", 2)[2]
            # only an activity broadcast may set or clear the waiting flash —
            # identity/announce/lifecycle messages must leave it untouched, or
            # a later re-announce/lifecycle signal would silently clear a
            # still-open "waiting on operator" flash (last-write-wins per
            # field, applied in ts order).
            state.last_notify_user = msg.get("notify_user") is True
        elif body.startswith("orchid:subagent:start:"):
            label = body[len("orchid:subagent:start:"):]
            if not (state.agent_type == BUS_AGENT_TYPE or label == BUS_LABEL):
                state.active_subagents.add(label)
        elif body.startswith("orchid:subagent:done:"):
            label = body[len("orchid:subagent:done:"):]
            state.active_subagents.discard(label)


# a finished/abandoned session is resolved — it must never keep flashing a
# stale "waiting on operator" hourglass. last_notify_user (set by the last
# activity broadcast) is otherwise only cleared by a NEW activity broadcast,
# which a closing session does not always emit before it signals terminal.
_TERMINAL_LIFECYCLE = {"finished", "abandoned"}

# the pre-terminal lifecycle "done" (built/tested, awaiting the operator's
# THAT IS ALL — see agents/architect.md) is, by definition, an operator-wait:
# treated as the waiting status with the operator (❓) variant forced on.
_AWAITING_OPERATOR_LIFECYCLE = "done"


def _waiting_on_operator_of(state: _SessionState) -> bool:
    """Within the "waiting" status, is this specifically a wait on the
    OPERATOR (❓ variant) rather than an external component (⌚)? Only
    meaningful when _status_for() returns "waiting"."""
    if state.lifecycle_state in _TERMINAL_LIFECYCLE:
        return False
    return state.last_notify_user or state.lifecycle_state == _AWAITING_OPERATOR_LIFECYCLE


def _status_for(state: _SessionState) -> str:
    if state.lifecycle_state in _TERMINAL_LIFECYCLE:
        return LIFECYCLE_TO_STATUS.get(state.lifecycle_state, "idle")
    if state.lifecycle_state == "blocked":
        return "awaiting_agent" if state.blocked_on == BLOCKED_ON_AGENT else "waiting"
    if state.last_notify_user or state.lifecycle_state == _AWAITING_OPERATOR_LIFECYCLE:
        return "waiting"
    if state.active_subagents or state.lifecycle_state in (
        "started", "building", "testing",
    ):
        return "working"
    return "idle"


class _BusAggregator:
    """Accumulates per-sender state for one repo's bus across repeated scans.

    Keyed by envelope `from` (the originating session), NOT by which folder a
    message happened to be found in — a broadcast from A sitting in B's inbox
    still updates A's state. Deduplicated by envelope `id`, applied in `ts`
    order so last-write-wins-per-sender holds even when new messages arrive
    across several scans out of file-system enumeration order.

    State, once applied, is never forgotten even after the message that
    produced it is deleted from disk by its recipient's `receive` — this is
    what lets the sidebar survive the bus's ephemerality. A sender seen with
    activity/lifecycle traffic but no identity (announce) message yet simply
    has agent_type=None and is not placed into any Repo/Feature row until an
    identity message for it does arrive in a later scan; it never crashes,
    it is just not renderable yet.

    ROOT-CAUSE STALE-ROW EVICTION (sidebar-polish item 2/3): a sender's state
    used to survive forever, even past its own terminal lifecycle signal
    (only the waiting flag got cleared, per _TERMINAL_LIFECYCLE) — this is
    why a long-closed feature ("app-identifying") kept rendering as a
    permanent stale row. Once a sender's lifecycle reaches a terminal signal
    (finished/abandoned), its state is shown for exactly one more scan (so a
    "done"/"failed" row is still visible right after the signal — no
    documented grace window exists beyond that, so one scan is the deliberate
    minimum), then evicted in full on the NEXT scan, before that scan's own
    row assembly — never lingering indefinitely.
    """

    def __init__(self) -> None:
        self.states: dict[str, _SessionState] = {}
        self._seen_ids: set[str] = set()
        self._pending_eviction: set[str] = set()

    def scan(self, bus_root: Path) -> None:
        # evict senders whose terminal signal was already observed on a
        # PREVIOUS scan — one full scan's grace to show "done"/"failed"
        for sender in self._pending_eviction:
            self.states.pop(sender, None)
        self._pending_eviction.clear()

        if not bus_root.is_dir():
            return

        new_messages = []
        current_ids: set[str] = set()
        for session_dir in bus_root.iterdir():
            if not session_dir.is_dir():
                continue
            for f in session_dir.glob("*.json"):
                if f.name.startswith("."):
                    continue  # bus.py's atomic-write .partial temp files
                try:
                    msg = json.loads(f.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue  # tolerate malformed JSON — skip, never crash
                msg_id = msg.get("id")
                sender = msg.get("from")
                if not msg_id or not sender:
                    continue
                current_ids.add(msg_id)
                if msg_id in self._seen_ids:
                    continue
                new_messages.append(msg)

        # chronological per envelope ts, so per-sender field overwrites land
        # in the right order regardless of which folder/scan surfaced them
        new_messages.sort(key=lambda m: m.get("ts") or "")
        for msg in new_messages:
            sender = msg["from"]
            state = self.states.setdefault(sender, _SessionState(session_id=sender))
            _apply_message(state, msg)

        # bound to messages still on disk this scan — the underlying files
        # are ephemeral (deleted by their recipient's receive), so anything
        # not seen this scan can never recur and its id is safe to drop
        self._seen_ids = current_ids

        # anyone now resolved gets exactly one more scan's visibility, then
        # eviction at the top of the NEXT scan (see class docstring)
        for sender, state in self.states.items():
            if state.lifecycle_state in _TERMINAL_LIFECYCLE:
                self._pending_eviction.add(sender)

    def repo(self, repo_path: str) -> Repo:
        return _assemble_repo(repo_path, self.states)


# --------------------------------------------------------------------------
# Assembly: per-sender states -> Fleet
# --------------------------------------------------------------------------

def _pick_bus(sessions: dict[str, _SessionState], parent_session_id: str) -> Bus | None:
    """The single collapsed bus row for a live parent (sidebar-polish item 5).

    Per-agent bus is a singleton BY DESIGN (Decision-051); multiplicity
    beyond one is a known, separately-root-caused defect (bus-singleton
    task). This function only owns the DISPLAY-side guarantee: never render
    more than one row, picked deterministically (lowest session_id) so
    repeated scans don't flicker between duplicates.
    """
    candidates = sorted(
        s.session_id for s in sessions.values()
        if s.agent_type == BUS_AGENT_TYPE and s.parent_session == parent_session_id
    )
    return Bus() if candidates else None


def _assemble_repo(repo_path: str, sessions: dict[str, _SessionState]) -> Repo:
    name = Path(repo_path).name
    repo = Repo(path=repo_path, name=name, activity="", status="idle",
                waiting_on_operator=False)

    orchestrator = next(
        (s for s in sessions.values() if s.agent_type == "orchestrator"), None,
    )
    if orchestrator is not None:
        repo.activity = orchestrator.activity
        repo.status = _status_for(orchestrator)
        repo.waiting_on_operator = _waiting_on_operator_of(orchestrator)
        repo.bus = _pick_bus(sessions, orchestrator.session_id)

    architects = [s for s in sessions.values() if s.agent_type == "architect"]
    for arch in architects:
        # bare session-UUID row: an architect that never announced a name OR
        # a feature_id has nothing operator-facing to show — never render it
        # (sidebar-polish item 2 / this round's item 3b).
        if not arch.name and not arch.feature_id and _is_bare_uuid(arch.session_id):
            continue

        feature_id = arch.feature_id or arch.session_id
        feature_name = arch.name or (feature_id.replace("-", " ") if feature_id else feature_id)
        feature = Feature(
            feature_id=feature_id,
            name=feature_name,
            activity=arch.activity,
            status=_status_for(arch),
            waiting_on_operator=_waiting_on_operator_of(arch),
            bus=_pick_bus(sessions, arch.session_id),
        )
        # subagents surfaced directly by the architect's own orchid:subagent traffic
        for label in sorted(arch.active_subagents):
            feature.subagents.append(Subagent(label=label))
        # plus any other (non-bus-sidecar) session whose parent_session points
        # at this architect (EVERY architect, not just the first — sidebar-
        # polish item 3), surfaced by name
        for s in sessions.values():
            if s is arch or s.parent_session != arch.session_id:
                continue
            if s.agent_type == BUS_AGENT_TYPE:
                continue
            if not s.name and _is_bare_uuid(s.session_id):
                continue  # bare session-UUID row: never operator-facing
            feature.subagents.append(Subagent(label=s.name or s.session_id))
        repo.features.append(feature)

    return repo


def build_model(repolist: list[str] | None = None) -> Fleet:
    """One snapshot of the fleet: scan every resolved repo's bus in full,
    attribute messages by `from`, dedup by `id`, assemble the tree.

    A fresh, throwaway aggregator per call — no state survives between calls
    (that persistence is what `watch()` is for).
    """
    fleet = Fleet()
    for repo_path in resolve_repos(repolist):
        bus_root = _bus_root_for(repo_path)
        if bus_root is None:
            continue
        aggregator = _BusAggregator()
        aggregator.scan(bus_root)
        fleet.repos.append(aggregator.repo(repo_path))
    return fleet


# --------------------------------------------------------------------------
# Watch (event-driven; falls back to polling)
# --------------------------------------------------------------------------

def watch(on_change, repolist: list[str] | None = None) -> None:
    """Call on_change(fleet) whenever a repo's bus changes.

    One `_BusAggregator` per repo is kept alive for the life of the watch, so
    accumulated per-sender state survives a recipient draining (deleting) its
    copy of a message between scans. On each event: rescan every repo's bus
    root, merge unseen messages into the accumulated state, rebuild the
    Fleet, and call on_change(fleet).

    Prefers `inotifywait -m -r` across every resolved bus root that already
    exists on disk; falls back to a 2s re-scan when inotifywait is
    unavailable or no bus root exists yet. Resilient to bus roots that do not
    exist yet — scanning a missing root is a no-op, never a crash.
    """
    repos = resolve_repos(repolist)
    roots = {repo_path: _bus_root_for(repo_path) for repo_path in repos}
    aggregators = {repo_path: _BusAggregator() for repo_path in repos}

    def rescan_and_notify() -> None:
        fleet = Fleet()
        for repo_path in repos:
            root = roots[repo_path]
            if root is not None:
                aggregators[repo_path].scan(root)
            fleet.repos.append(aggregators[repo_path].repo(repo_path))
        on_change(fleet)

    existing = [r for r in roots.values() if r is not None and r.is_dir()]

    if shutil.which("inotifywait") and existing:
        cmd = [
            "inotifywait", "-m", "-r",
            "-e", "create", "-e", "moved_to", "-e", "modify", "-e", "delete",
            "--format", "%f",
            *[str(r) for r in existing],
        ]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        try:
            rescan_and_notify()  # initial snapshot before the first event
            for _ in proc.stdout:
                rescan_and_notify()
        finally:
            proc.terminate()
        return

    # Fallback: polling re-scan every 2 seconds.
    while True:
        rescan_and_notify()
        time.sleep(2)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _print_tree(fleet: Fleet) -> None:
    if not fleet.repos:
        print("(no repos resolved)")
        return
    for repo in fleet.repos:
        print(f"{repo.name}  [{repo.status}] {repo.activity}".rstrip())
        for feature in repo.features:
            print(f"  {feature.name}  [{feature.status}] {feature.activity}".rstrip())
            for sub in feature.subagents:
                print(f"    - {sub.label}")


if __name__ == "__main__":
    _print_tree(build_model())

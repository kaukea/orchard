#!/usr/bin/env python3
"""Cross-repo bus reader/aggregator for the fleet sidebar.

READ-ONLY observer over the on-disk bus (see tools/bus.py, message.schema.json).
Parses WIRE GRAMMAR v1: orchid:status (+ deprecated orchid:activity fallback),
orchid:update, orchid:phase, orchid:subagent:queue/start/done,
orchid:interrupt:question, lifecycle JSON, notify_user.

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

Repo list resolution (sidebar-polish item 7a, "dynamic appearance" — see
resolve_repos()): primary discovery is the orchard registry
(tools/orchard_registry.py, ~/.config/orchids/sidebar-registry.json) —
installing orchids in a repo (`.ai.toml` presence) IS registration, no
hand-kept list required day to day. ORCHIDS_SIDEBAR_REPOS survives as an
explicit, optional override for manual/debug use: when set, it names a
repolist file (one repo path per line, '#' comments and blank lines ignored)
read verbatim, registry and hiding bypassed. Falls back to the current repo
alone if the registry resolves nothing.

Public API: build_model(), iter_bus_roots(), watch(on_change, ...),
resolve_repos().
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feature_name import feature_name as _feature_name  # noqa: E402
import orchard_registry  # noqa: E402

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
class Question:
    """One still-open ask, surfaced on a row's `open_questions` (WIRE GRAMMAR
    v1, bus-message-specifying B3). Cleared by a matching reply or by the
    asker's next status-clearing signal — see _clear_open_questions()."""
    question_id: str
    subject: str


@dataclass
class Feature:
    feature_id: str
    name: str
    activity: str
    status: str
    waiting_on_operator: bool
    subagents: list[Subagent] = field(default_factory=list)
    bus: Bus | None = None
    status_word: str = ""
    update_text: str = ""
    phase: str | None = None
    phase_tick: tuple[int, int] | None = None
    progress_pct: int | None = None
    subagents_running: int = 0
    subagents_queued: int = 0
    open_questions: list[Question] = field(default_factory=list)
    question_count: int = 0
    first_question_subject: str | None = None
    interrupt: str = "none"


@dataclass
class Repo:
    path: str
    name: str
    activity: str
    status: str
    waiting_on_operator: bool
    paused: bool = False
    # True when the repo has at least one live session (an orchestrator session
    # or any feature). A repo with no live session is not rendered (the sidebar's
    # flatten() skips it). Defaults True so hand-built Repo() test fixtures render
    # as before unless a test opts out; _assemble_repo() sets the real value.
    has_session: bool = True
    features: list[Feature] = field(default_factory=list)
    bus: Bus | None = None
    status_word: str = ""
    update_text: str = ""
    phase: str | None = None
    phase_tick: tuple[int, int] | None = None
    progress_pct: int | None = None
    subagents_running: int = 0
    subagents_queued: int = 0
    open_questions: list[Question] = field(default_factory=list)
    question_count: int = 0
    first_question_subject: str | None = None
    interrupt: str = "none"


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
    """Resolve the list of repo paths the sidebar aggregates over.

    Primary discovery (sidebar-polish item 7a): the orchard registry —
    installing orchids in a repo (`.ai.toml` presence) IS registration, no
    hand-kept list required. The current repo self-registers here if it has
    `.ai.toml` and isn't registered yet — this checkout has no other
    kauk-install hook to call `orchard_registry.register_repo()` from, so
    resolution time doubles as the registration point. Hidden repos
    (item 7b) are excluded via `visible_repos()`.

    ORCHIDS_SIDEBAR_REPOS survives as an explicit, optional override for
    manual/debug use (architect HOW decision): when set, it names a
    repolist file read verbatim — registry and hiding are bypassed entirely,
    same file format as before (one repo path per line, '#'/blank ignored).
    """
    if repolist:
        return list(repolist)

    env_path = os.environ.get("ORCHIDS_SIDEBAR_REPOS", "").strip()
    if env_path:
        return _read_repolist(Path(env_path))

    current = _current_repo()
    if current and orchard_registry._has_ai_toml(current):
        orchard_registry.register_repo(current)

    # checked separately from visible_repos(): a registry with entries, ALL
    # of them hidden, must resolve to [] (hiding must actually hide) -- the
    # bare-current-repo fallback below is only for a genuinely EMPTY
    # registry (fresh install, nothing registered yet), never as a way
    # around an explicit hide.
    if orchard_registry.registered_repos():
        return orchard_registry.visible_repos()

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
    status_word: str = ""
    update_text: str = ""
    phase: str | None = None
    phase_tick: tuple[int, int] | None = None
    lifecycle_state: str | None = None
    blocked_on: str | None = None  # BLOCKED_ON_COMPONENT / BLOCKED_ON_AGENT
    # notify_user carried on the CURRENT lifecycle signal itself — kept apart
    # from last_notify_user (which only an activity/status broadcast may set
    # or clear, see _apply_status_word) so a blocked+notify interrupt read
    # doesn't depend on the sticky flash flag.
    blocked_notify: bool = False
    active_subagents: set = field(default_factory=set)  # running
    subagents_queued: set = field(default_factory=set)
    open_questions: dict = field(default_factory=dict)  # question_id -> subject
    last_notify_user: bool = False  # notify_user flag of the latest message seen
    last_signature: tuple | None = None  # (body, notify_user) of the previous message


# WIRE GRAMMAR v1 body prefixes (bus-message-specifying B3).
_STATUS_PREFIX = "orchid:status:"
_ACTIVITY_PREFIX = "orchid:activity:"  # deprecated fallback, one transition release
_UPDATE_PREFIX = "orchid:update:"
_PHASE_PREFIX = "orchid:phase:"
_QUESTION_PREFIX = "orchid:interrupt:question:"
_SUBAGENT_QUEUE_PREFIX = "orchid:subagent:queue:"
_SUBAGENT_START_PREFIX = "orchid:subagent:start:"
_SUBAGENT_DONE_PREFIX = "orchid:subagent:done:"

# progress_pct phase table (bus-message-specifying B3 task item 3): base %
# a phase starts at, and the % span it covers before the next phase begins.
_PHASE_BASES = {
    "ideation": 0, "scoping": 10, "designing": 25, "building": 40, "releasing": 85,
}
_PHASE_SPANS = {
    "ideation": 10, "scoping": 15, "designing": 15, "building": 45, "releasing": 15,
}


def _clear_open_questions(state: _SessionState) -> None:
    state.open_questions.clear()


def _apply_status_word(state: _SessionState, msg: dict, text: str) -> None:
    state.status_word = text
    # only a status/activity broadcast may set or clear the waiting flash —
    # identity/announce/lifecycle messages must leave it untouched, or a
    # later re-announce/lifecycle signal would silently clear a still-open
    # "waiting on operator" flash (last-write-wins per field, ts order).
    state.last_notify_user = msg.get("notify_user") is True
    _clear_open_questions(state)


def _apply_update_text(state: _SessionState, msg: dict, text: str) -> None:
    # update never derives status and never notifies — no other field touched
    state.update_text = text


def _parse_phase(remainder: str) -> tuple[str | None, tuple[int, int] | None]:
    phase, _, tick_text = remainder.partition(":")
    if phase not in _PHASE_BASES:
        return None, None
    if not tick_text:
        return phase, None
    k_text, sep, n_text = tick_text.partition("/")
    if not sep:
        return None, None
    try:
        k, n = int(k_text), int(n_text)
    except ValueError:
        return None, None
    if k < 0 or n <= 0:
        return None, None
    return phase, (k, n)


def _apply_phase(state: _SessionState, msg: dict, remainder: str) -> None:
    phase, tick = _parse_phase(remainder)
    if phase is None:
        return  # invalid phase string — defensive, bus.py validates at send
    state.phase = phase
    state.phase_tick = tick


def _apply_question(state: _SessionState, msg: dict, subject: str) -> None:
    question_id = msg.get("question_id")
    if question_id:
        state.open_questions[question_id] = subject
    state.last_notify_user = msg.get("notify_user") is True


def _is_bus_subagent(state: _SessionState, label: str) -> bool:
    return state.agent_type == BUS_AGENT_TYPE or label == BUS_LABEL


def _apply_subagent_queue(state: _SessionState, msg: dict, label: str) -> None:
    if not _is_bus_subagent(state, label):
        state.subagents_queued.add(label)


def _apply_subagent_start(state: _SessionState, msg: dict, label: str) -> None:
    state.subagents_queued.discard(label)
    if not _is_bus_subagent(state, label):
        state.active_subagents.add(label)


def _apply_subagent_done(state: _SessionState, msg: dict, label: str) -> None:
    state.subagents_queued.discard(label)
    state.active_subagents.discard(label)


# Tried in order against a string body; the first matching prefix's handler
# runs with the text after that prefix. Composition over an elif chain, so a
# new WIRE GRAMMAR verb is one more row, not a deeper branch.
_STRING_BODY_HANDLERS = [
    (_STATUS_PREFIX, _apply_status_word),
    (_ACTIVITY_PREFIX, _apply_status_word),  # deprecated fallback — same field
    (_UPDATE_PREFIX, _apply_update_text),
    (_PHASE_PREFIX, _apply_phase),
    (_QUESTION_PREFIX, _apply_question),
    (_SUBAGENT_QUEUE_PREFIX, _apply_subagent_queue),
    (_SUBAGENT_START_PREFIX, _apply_subagent_start),
    (_SUBAGENT_DONE_PREFIX, _apply_subagent_done),
]


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
        state.blocked_notify = msg.get("notify_user") is True
        if state.lifecycle_state in _TERMINAL_LIFECYCLE:
            _clear_open_questions(state)

    elif isinstance(body, str):
        for prefix, handler in _STRING_BODY_HANDLERS:
            if body.startswith(prefix):
                handler(state, msg, body[len(prefix):])
                break


def _is_repeat_of_previous(state: _SessionState, msg: dict) -> bool:
    """Dedup rule (bus-message-specifying B3 item 7): a message identical in
    body+notify_user to the SENDER's previous one changes nothing and
    re-raises no notify — kills the duplicate-summons defect where a resent
    ask could reopen a question already answered."""
    signature = (msg.get("body"), msg.get("notify_user") is True)
    is_repeat = signature == state.last_signature
    state.last_signature = signature
    return is_repeat


def _clear_replied_question(states: dict, msg: dict) -> None:
    """A reply's `from` is the ANSWERER, not the asker — the open question it
    resolves lives on whichever sender's state still holds that question_id,
    found by matching envelope in_reply_to, independent of the normal
    per-sender attribution the rest of _apply_message uses."""
    in_reply_to = msg.get("in_reply_to")
    if not in_reply_to:
        return
    for state in states.values():
        if in_reply_to in state.open_questions:
            del state.open_questions[in_reply_to]
            return


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


def _progress_pct_for(state: _SessionState) -> int | None:
    if state.lifecycle_state == "finished":
        return 100
    if state.phase is None:
        return None
    base = _PHASE_BASES[state.phase]
    if state.phase_tick is None:
        return base
    span = _PHASE_SPANS[state.phase]
    k, n = state.phase_tick
    return base + (span * k) // n


def _interrupt_for(state: _SessionState) -> str:
    """The renderer's badge signal, derived from state already tracked for
    other purposes (bus-message-specifying B3 item 6) — additional to, never
    a replacement for, the working/waiting/idle status derivation above."""
    if state.open_questions:
        return "question"
    if state.lifecycle_state in ("done", "finished"):
        return "succeeded"
    if state.lifecycle_state == "abandoned":
        return "failed"
    if state.lifecycle_state == "blocked" and state.blocked_notify:
        return "failed"
    return "none"


def _apply_row_extension(row, state: _SessionState) -> None:
    """Copy the WIRE GRAMMAR v1 fields from an aggregated sender state onto a
    public Feature or Repo row — both dataclasses share this exact field set,
    so one function serves either (duck-typed on purpose, see _assemble_repo)."""
    row.status_word = state.status_word
    row.update_text = state.update_text
    row.phase = state.phase
    row.phase_tick = state.phase_tick
    row.progress_pct = _progress_pct_for(state)
    row.subagents_running = len(state.active_subagents)
    row.subagents_queued = len(state.subagents_queued)
    row.open_questions = [
        Question(question_id=qid, subject=subject)
        for qid, subject in state.open_questions.items()
    ]
    row.question_count = len(state.open_questions)
    row.first_question_subject = next(iter(state.open_questions.values()), None)
    row.interrupt = _interrupt_for(state)


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
    permanent stale row. Once a sender's lifecycle reaches a terminal signal,
    eviction now depends on WHICH terminal state it reached (operator
    decision, 2026-07-24, sidebar-titling item 7): a `finished` (done) sender
    is retained deliberately for the life of the current sidebar's view — a
    done feature's row never leaves — it keeps rendering (green, "done") and
    is never scheduled for eviction. An `abandoned` sender keeps the prior
    one-scan-grace behaviour: shown for exactly one more scan (so a "failed"
    row is still visible right after the signal), then evicted in full on the
    NEXT scan, before that scan's own row assembly — never lingering
    indefinitely.
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
            if _is_repeat_of_previous(state, msg):
                continue
            _clear_replied_question(self.states, msg)
            _apply_message(state, msg)

        # bound to messages still on disk this scan — the underlying files
        # are ephemeral (deleted by their recipient's receive), so anything
        # not seen this scan can never recur and its id is safe to drop
        self._seen_ids = current_ids

        # only "abandoned" senders get exactly one more scan's visibility
        # then eviction at the top of the NEXT scan; "finished" (done)
        # senders are retained deliberately and never scheduled for eviction
        # (see class docstring)
        for sender, state in self.states.items():
            if state.lifecycle_state == "abandoned":
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
        repo.activity = orchestrator.status_word
        repo.status = _status_for(orchestrator)
        repo.waiting_on_operator = _waiting_on_operator_of(orchestrator)
        repo.bus = _pick_bus(sessions, orchestrator.session_id)
        _apply_row_extension(repo, orchestrator)

    architects = [s for s in sessions.values() if s.agent_type == "architect"]
    for arch in architects:
        # bare session-UUID row: an architect that never announced a name OR
        # a feature_id has nothing operator-facing to show — never render it
        # (sidebar-polish item 2 / this round's item 3b).
        if not arch.name and not arch.feature_id and _is_bare_uuid(arch.session_id):
            continue

        feature_id = arch.feature_id or arch.session_id
        # arch.name is whatever the architect announced (already ledger-derived
        # via bus.py's identity_of() in the normal case) — an explicit runtime
        # override wins; otherwise re-derive from the board/sidecar directly
        # (sidebar-polish item 11) rather than falling back to the mechanical
        # id-with-spaces form.
        feature_name = arch.name or (
            _feature_name(feature_id, root=repo_path) if feature_id else feature_id
        )
        feature = Feature(
            feature_id=feature_id,
            name=feature_name,
            activity=arch.status_word,
            status=_status_for(arch),
            waiting_on_operator=_waiting_on_operator_of(arch),
            bus=_pick_bus(sessions, arch.session_id),
        )
        _apply_row_extension(feature, arch)
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

    # a repo with no orchestrator session AND no features has nothing live to
    # show — the renderer's flatten() reads this flag and skips the repo
    # entirely (item 3, "empty projects don't render").
    repo.has_session = orchestrator is not None or bool(repo.features)

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

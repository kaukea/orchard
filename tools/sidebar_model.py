"""The sidebar's MODEL layer — data classes, event folding, registry
reading, and tree assembly. `tools/sidebar.py` imports from here and owns
everything downstream: the pure-text Row/render pipeline and the curses
draw layer. This module never imports curses and never formats a string
for a screen.

THE RULED TREE (operator, 2026-07-27 — `docs/TODO.md.d/sidebar-teamwork.md`
section "The tree, as ruled by the operator 2026-07-27" is the
specification this module is built against; see also Decision-105 through
Decision-110, Decision-099, Decision-101, and `docs/courier-wire.md` §4
(a subagent inherits its parent's session id)):

  - **project** — the repository; `<owner>.<repo>` and any `@<branch>`
    worktree variant of it are ONE project, folded together
    (`_repo_identity`/`_group_project_dirs`). The watched set of projects
    comes from the STATIC REGISTRY (`load_watched_repo_names`), never from
    walking the whole runtime tree — which at last count carried 1091
    leaked `tmp*` project directories alongside the real ones.
  - **feature** — metadata carried on an event's `identity.feature`/
    `identity.feature_name`. NEVER manufactured from a session. Holds a
    LIST of tasks.
  - **task** — from `identity.task`/`identity.task_name`.
  - **the five stages** (`PHASES`) belong to the TASK and are derived
    CLIENT-SIDE from each live agent's own role (`resolve_step`,
    `load_role_step_map`) — nothing on the wire names a step, and an
    unmapped role still renders, without a step (fails open).
  - **agent** — identified by the TRIPLE `(session_id, parent, agent_name)`,
    never by session id alone: an in-session subagent with its own identity
    inherits its parent's session id VERBATIM, so two different agents can
    share one session id and must not fold into one record
    (`_fold_agent_records`). A step holds a LIST of agents (Decision-105).
  - **the activity line** is a POSITION in a stage, not an entity — it is
    simply whichever agent's record currently occupies that stage.
  - **subagents** come from delegation events, keyed `(parent_session_id,
    subagent_name)`. No session, no identity, no model, no status text —
    only scheduled/doing/done (Decision-109).
  - **the courier is NOT an agent and never earns a row of its own**
    (`COURIER_AGENT_NAME`) — but it is not discarded either. Per
    Decision-018, the courier answers identity/status requests off its
    PARENT's transcript, sharing the parent's session id, precisely so the
    parent is never woken to answer itself; a courier-labelled event is
    therefore the session-bearing agent's OWN liveness signal, folded into
    that agent's record (never creating a second one, never overwriting its
    identity — operator correction, 2026-07-27; see `_fold_agent_records`).
    A session with no qualifying agent identity at all earns no row.
  - **status is transient activity.** An agent with no live `orchard:agent:
    status` post is idle, never an empty string — `NO_LIVE_ACTIVITY` is
    what `Agent.activity` carries instead, so nothing downstream ever has
    to special-case "".

KNOWN PRODUCER DEFECTS, worked around here rather than fixed (out of this
module's scope): `orchard:agent:status` events arrive with `repo: null,
project: null` (attribution here never depends on those fields); clearing a
session is meant to mint a new session id and currently keeps the old one
(an acknowledged exception, not designed around — the triple-keyed fold
simply treats whatever identity actually rides each event as authoritative,
so a session reused this way lands as two distinct agent records rather
than one corrupting the other).

Read straight off the per-session event layout orchard_topic.py writes:
`$XDG_RUNTIME_DIR/orchard/projects/<repo>.<project>/<sessionid>.<ts>.json`,
one file per event. `build_model()`/`watch()` are this module's own.

STDLIB ONLY.
"""
from __future__ import annotations

import functools
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sidebar_text import _format_dollars, _format_running_time, _format_token_count  # noqa: E402

# --------------------------------------------------------------------------
# Canonical vocabulary
# --------------------------------------------------------------------------

# Canonical five-phase order (bus-message-specifying B3's phase vocabulary).
PHASES = ("ideation", "scoping", "designing", "building", "releasing")

# Stage spans (spec §1 / bus-message-specifying.md:209, ruled): the five
# PHASES do NOT weigh an equal fifths each — ideation/scoping/designing/
# building/releasing weigh 10/15/15/45/15 -> 100%. The client-side progress
# surface that already exists (`sidebar_rows._task_progress_glyph`)
# reweights its computation against this rather than counting done steps
# 1-for-1 (M2).
PHASE_WEIGHTS: dict[str, int] = dict(zip(PHASES, (10, 15, 15, 45, 15)))

# Separates the repo half of an orchard project slug from its branch half:
# `<owner>.<repo>@<branch>`. Must match courier.py's BRANCH_SEPARATOR, and is
# duplicated rather than imported because this tool stays stdlib-only.
BRANCH_SEPARATOR = "@"

# A task's terminal states (Decision-058: done and failed never share a
# glyph or a colour-pair with each other, nor with a still-working task).
TERMINAL_TASK_STATUSES = {"done", "failed"}

# The exact `orchard:agent:status` freetext words that map onto Decision-
# 058's two wait states — ruled 2026-07-29 ("Questioning is not waiting: the
# two wait words", docs/TODO.md.d/bus-addressing.md §Decision entries): a
# status word of `questioning` means an answer this agent asked for is
# outstanding (the operator's own done-gate included) and reads as
# Decision-058's "waiting" state — its ORIGINAL glyph slot, unchanged; a
# status word of `waiting` means this agent is waiting on another AGENT and
# reads as the separate "awaiting_agent" state, previously unreachable (no
# producer word had been ruled for it). Both are exact, case-sensitive
# matches — the wire defines these as specific status WORDS, not a
# case-folded pattern, and no other spelling is ruled.
_QUESTIONING_ACTIVITY = "questioning"
_WAITING_ACTIVITY = "waiting"

# A session with no event inside this window, and no terminal outcome,
# renders "stale" (gray) rather than "working"/"idle" — it is NOT dropped
# from the model (retention ruling, 2026-07-25, revised same day: nothing
# ever leaves the sidebar due to staleness; only a session restart, which
# clears the tmpfs projects tree, resets what is shown). See `_status_for`.
ACTIVE_WINDOW_SECONDS = 60 * 60

# schedule/begin/end -> the subagent's own three-state vocabulary (operator
# ruling, 2026-07-26: a subagent renders as a label plus exactly one of
# scheduled/doing/done — "done" is a real, visible state now, not a vanish;
# a subagent only disappears once its owning TASK folds).
_DELEGATION_STATE = {"schedule": "scheduled", "begin": "doing", "end": "done"}
_DELEGATION_SUBJECTS = (
    "orchard:agent:delegation:schedule",
    "orchard:agent:delegation:begin",
    "orchard:agent:delegation:end",
)

# The courier rides its parent's session id verbatim (it is an in-session
# sidecar, not its own agent) and should not be posting identity-bearing
# events at all — that producer defect is upstream and out of scope here.
# What IS this module's job: never let one of its posts stand in for the
# agent whose session it shares (operator ruling, 2026-07-27: "the courier
# is not an agent... filter it out of the display entirely").
COURIER_AGENT_NAME = "courier"

# `Agent.activity` when no live `orchard:agent:status` post exists for that
# agent's record — never "", so the identity line's quote-wrapped rendering
# ("<activity>") downstream never wraps nothing (operator ruling,
# 2026-07-27: "status is transient activity... it must never reach the
# renderer as ''").
NO_LIVE_ACTIVITY = "no activity"

_SESSION_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _is_bare_uuid(text: str | None) -> bool:
    return bool(text) and bool(_SESSION_UUID_RE.match(text))


# --------------------------------------------------------------------------
# Data classes
# --------------------------------------------------------------------------

@dataclass
class Subagent:
    """A delegation's own row — no model, no status text, no identity of
    its own (Decision-109): a label plus exactly one of scheduled/doing/
    done, sourced from `orchard:agent:delegation:schedule/begin/end`.
    Live-only, and folds away only once its owning TASK folds — never
    persisted to a feature marker."""
    label: str
    state: str = "doing"


@dataclass
class Agent:
    """One agent sitting on a step of a task — the identity line ("<doing>
    ⋮ <role> ⋮ <model>"). Identified by the TRIPLE `(session_id, parent,
    agent_name)`, never by `session_id` alone (see module docstring):
    `parent` is carried here mainly for traceability, since two agents
    sharing one session id are already disambiguated by the fold itself.
    `step` is derived client-side from `role` via the role->step map
    (`resolve_step`); None when the role is missing or unmapped — the
    agent still renders, just without a step (`Task.unstepped_agents`,
    fails open, operator ruling 2026-07-26).

    `context_tokens`/`spend` ride straight off the status snapshot
    (`docs/courier-wire.md` §2b, `orchard_topic.py`'s `_status()`) — raw
    pass-through, no derived dollar figure or in/out split computed here
    (that reading of `spend`'s nested token classes is the renderer's job
    in a later step). `context_tokens` is USAGE/occupancy
    (`courier.status_of()`'s own `occupancy` count — "an agent watching
    context occupancy, its own death condition"), never "remaining":
    turning it into a remaining-of-budget figure would need a per-model
    context-window-size table the wire does not carry, so none is
    invented (M2, spec §3). `effort` now rides too (courier-wire.md §2b,
    `CLAUDE_EFFORT` when a launcher sets it) — raw pass-through, same as
    `model`; None when the status snapshot carries no `effort` at all, no
    value invented. `started_ts`/`updated_ts` are this agent's own
    earliest/latest event timestamps (`rec["_first_ts"]`/`rec["_seen_ts"]`)
    — the raw material `Task` aggregates into its own running time (see
    `_agent_timestamp_bounds`) and the repo footer aggregates into its own
    age/worked figures (see `_repo_time_and_tokens`)."""
    session_id: str
    role: str | None
    model: str | None
    activity: str
    status: str
    parent: str | None = None
    step: str | None = None
    subagents: list[Subagent] = field(default_factory=list)
    context_tokens: int | None = None
    spend: dict | None = None
    effort: str | None = None
    started_ts: float | None = None
    updated_ts: float | None = None


@dataclass
class Step:
    """One of the five canonical `PHASES` for a task, positioned done/
    active/todo relative to the task's own active step (`phase_states`).
    `agents` is populated only for the active step — a done/todo step folds
    to a plain line (operator ruling, 2026-07-26)."""
    name: str
    state: str  # "done" | "active" | "todo"
    agents: list[Agent] = field(default_factory=list)


@dataclass
class Task:
    """A TASK is terminal (`status` in `TERMINAL_TASK_STATUSES`) or open —
    never reopened once terminal; new work is a new task (operator ruling,
    2026-07-26). `steps` is empty when no live agent's role maps to a step;
    `unstepped_agents` holds any live agent whose role is missing or
    unmapped.

    `started_ts`/`updated_ts` are the earliest/latest event timestamp
    across every live agent on this task (`_agent_timestamp_bounds`) — None
    for a marker-only task, since the marker schema records no start time
    (an honest gap, not a guess). `running_seconds` is the deterministic,
    script-computed running time spec §3 rules for the task row
    (`_task_running_seconds`, computed once at `build_model()` time against
    its own `now`, never recomputed from a live wall clock inside the
    renderer — see `sidebar_rows._task_metrics_text`): for a still-open
    task, `now - started_ts`; for a terminal one, frozen at
    `updated_ts - started_ts`. None whenever `started_ts` is None.

    `context_tokens` (M2) is the CONTEXT-occupancy figure the task row's
    own metrics text surfaces (`sidebar_rows._task_metrics_text`) — the
    most-recently-updated live agent's own `Agent.context_tokens` among
    this task's agents (`_task_context_tokens`), an implementer's reading
    of "which agent represents a multi-agent task's context", not itself a
    ruling. None whenever no agent on this task carries a context figure
    (a marker-only task, or a live one whose agents' status snapshots
    never carried `context_tokens`)."""
    task_id: str
    name: str
    status: str
    steps: list[Step] = field(default_factory=list)
    unstepped_agents: list[Agent] = field(default_factory=list)
    started_ts: float | None = None
    updated_ts: float | None = None
    running_seconds: float | None = None
    context_tokens: int | None = None


@dataclass
class Feature:
    """A FEATURE holds a list of open (or recently-completed) tasks — NOT
    terminal and NOT idempotent: a new task revives a fully-collapsed
    feature, and its completed sibling tasks come back alongside it
    (operator ruling, 2026-07-26). `status` is the aggregate of `tasks`
    (see `_combine_status`). Exists in metadata only — never a session,
    never an agent, never derived from either."""
    feature_id: str
    name: str
    status: str
    tasks: list[Task] = field(default_factory=list)


@dataclass
class Repo:
    name: str
    activity: str
    status: str
    waiting_on_operator: bool
    paused: bool = False
    # True when the repo has at least one live session (a gardener session
    # or any feature). A repo with no live session is skipped by flatten().
    has_session: bool = True
    features: list[Feature] = field(default_factory=list)
    status_word: str = ""
    # role/model come straight off the gardener session's identity/status
    # snapshot.
    role: str | None = None
    model: str | None = None
    # age/worked/tokens (M2) feed `sidebar_render_text.footer_lines`/
    # `done_footer_line` — spec §3's `age⏱ vs worked + tokens⚡/dollars`
    # footer grammar — computed deterministically from this repo's own
    # agent records by `_repo_time_and_tokens` (event timestamps for age/
    # worked, the status snapshot's `tokens_in`/`tokens_out` for tokens).
    # Already-formatted human text, same convention `running_seconds`'s own
    # renderer-side formatting uses.
    age: str | None = None
    worked: str | None = None
    tokens: str | None = None
    # `dollars` rides `orchard_topic.py`'s `_status()`, which now promotes
    # `estimates.cost_usd` (courier.py's own price-table estimate,
    # `estimates_for()`) out to a first-class `dollars` field the same way
    # `tokens_in`/`tokens_out` were promoted — summed the same way tokens
    # are, by `_repo_time_and_tokens`. None whenever no agent record on this
    # repo carries a `dollars` figure (an unrecognised model, or no status
    # snapshot at all) — never invented.
    dollars: str | None = None


@dataclass
class Fleet:
    repos: list[Repo] = field(default_factory=list)


# --------------------------------------------------------------------------
# Static registry — which projects to fold at all
# --------------------------------------------------------------------------

def _default_registry_path() -> Path:
    return Path.home() / ".config" / "orchids" / "sidebar-registry.json"


def _registry_repo_names(entries: object) -> set[str]:
    """Basenames of every path/name in one registry list (`repos` or
    `hidden`). Comparing basenames — not full paths — is what lets this
    stay a pure string match against `_repo_display_name()`'s own owner-
    and branch-stripped output, with no git call needed to learn a
    registered repo's real orchard slug."""
    if not isinstance(entries, list):
        return set()
    return {Path(str(e)).name for e in entries if e}


def load_watched_repo_names(registry_path: Path | None = None) -> set[str] | None:
    """The repo DISPLAY names `build_model()` should fold — the static
    registry's `repos` list (a list of repo paths) minus its `hidden` list
    (operator ruling, 2026-07-27: "the project list comes from the
    registry"; DO NOT scan the whole runtime tree, which at last count
    carried 1091 leaked `tmp*` project directories alongside the real
    ones).

    None (fail open — fold every project directory found, matching
    build_model()'s pre-registry default) when the registry is missing,
    unreadable, or carries no `repos` list: an absent or misconfigured
    registry degrades to "show everything", never to a blank board.

    Not called by `build_model()` itself — a production entry point
    (`sidebar.py`'s `_run_dump`/`_paint_once`/`_watch_thread`) computes this
    once per scan and passes it through as `watched_names`, keeping
    `build_model()` a plain, registry-agnostic primitive that tests can
    drive without touching `~/.config`."""
    registry_path = registry_path or _default_registry_path()
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    watched = _registry_repo_names(registry.get("repos"))
    if not watched:
        return None
    return watched - _registry_repo_names(registry.get("hidden"))


# --------------------------------------------------------------------------
# Project directory discovery
# --------------------------------------------------------------------------

def projects_root() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        return Path("/nonexistent")  # build_model()/watch() just see nothing
    return Path(runtime) / "orchard" / "projects"


def _repo_display_name(slug: str) -> str:
    """`<owner>.<repo>@<branch>` (courier.py's project_slug() format) -> `<repo>`
    — the bare name sidebar_nav's gardener-window match expects.

    Two components are stripped, each optional:
    * the `@<branch>` suffix, present since the orchard project directory became
      one-per-worktree; the match is on the repo, which every worktree shares.
    * the `<owner>.` prefix, absent when there was no git remote at post time.
    """
    repo = slug.partition(BRANCH_SEPARATOR)[0]
    _owner, sep, name = repo.partition(".")
    return name if sep else repo


def _repo_identity(slug: str) -> str:
    """`<owner>.<repo>@<branch>` -> `<owner>.<repo>` — what makes two project
    directories the SAME repo.

    Grouping keys off this and never off the display name. Two unrelated
    repos can share a bare name under different owners (`kaukea.orchids` and
    `someoneelse.orchids`); folding those together would merge one repo's
    features into another's row. The owner is dropped for DISPLAY only, where
    a collision is merely confusing rather than wrong.
    """
    return slug.partition(BRANCH_SEPARATOR)[0]


def _group_project_dirs(root: Path) -> list[tuple[str, list[Path]]]:
    """Every project directory under `root`, grouped by repo identity — one
    group per repo, spanning however many worktree directories
    (`<owner>.<repo>@<branch>`) that repo currently has. Groups and the
    directories within each group are both in sorted order, so the result
    is deterministic."""
    groups: dict[str, list[Path]] = {}
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        groups.setdefault(_repo_identity(d.name), []).append(d)
    return sorted(groups.items())


# --------------------------------------------------------------------------
# Event folding
# --------------------------------------------------------------------------

def _latest(rec: dict, key: str, ts: float) -> bool:
    """True (and records ts) when this event is the newest of its kind for a session."""
    if ts < rec.get(key, -1.0):
        return False
    rec[key] = ts
    return True


def _iter_project_events(project_dir: Path):
    """(session_id, envelope, file_mtime) for every event file directly
    under `project_dir` — the single place that reads and parses them, so
    the session-level fold (`_fold_sessions`, used for repo-header lookup)
    and the agent-triple fold (`_fold_agent_records`, used for the feature/
    task tree) apply the identical per-event merge logic (`_apply_event`)
    to the identical event stream, never drifting from each other on what
    counts as a valid file."""
    for f in project_dir.iterdir():
        if f.name.startswith(".") or not f.name.endswith(".json") or not f.is_file():
            continue
        try:
            env = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        sid = env.get("from", "").removeprefix(":session:")
        if not sid:
            continue
        yield sid, env, f.stat().st_mtime


def _apply_event(rec: dict, env: dict, ts: float, *, trust_snapshot: bool = True) -> None:
    """Merge one event envelope into `rec` — latest-of-each-kind wins per
    kind (`_latest`), independent of file iteration order. Shared by both
    the session-level and the agent-triple fold (see `_iter_project_events`).

    `trust_snapshot=False` applies every OTHER field this event carries
    (activity, lifecycle state, outcome, delegation) while leaving `rec`'s
    own `identity`/`status` untouched — the courier's own identity/status
    snapshot describes ITS OWN resolution context (Decision-018: it answers
    off its parent's transcript so the parent is never woken), not a
    trustworthy stand-in for the agent it is reporting on behalf of. See
    `_fold_agent_records`/`_fold_sessions`, the two callers that decide
    when an event's own identity is untrustworthy this way.

    `_first_ts` tracks the EARLIEST event ts seen for this record,
    unconditionally (unlike every other field here, which is gated on
    "latest of its kind wins") — the running-time seam (`Task.started_ts`,
    `_agent_timestamp_bounds`) needs the record's own start, independent of
    file iteration order or which kind of event happened to arrive first."""
    rec["_seen_ts"] = max(rec.get("_seen_ts", 0.0), ts)
    rec["_first_ts"] = min(rec.get("_first_ts", ts), ts)
    if trust_snapshot and _latest(rec, "_snap", ts):
        rec["identity"] = env.get("identity", rec.get("identity", {}))
        rec["status"] = env.get("status", rec.get("status", {}))
    subject = env.get("subject", "")
    if subject.startswith("orchard:agent:lifecycle:") and _latest(rec, "_life", ts):
        rec["state"] = subject.rsplit(":", 1)[-1]
    elif subject == "orchard:agent:status" and _latest(rec, "_stat", ts):
        rec["activity"] = env.get("body", "")
    elif subject.startswith("orchard:agent:outcome:") and _latest(rec, "_out", ts):
        rec["outcome"] = subject.rsplit(":", 1)[-1]
    elif subject.startswith("orchard:task:outcome:") and _latest(rec, "_task", ts):
        rec["task_outcome"] = subject.rsplit(":", 1)[-1]
    elif subject in _DELEGATION_SUBJECTS:
        # EXACT subject match — the subagent id is no longer derived from
        # the subject tail (there is none any more): it rides the body.
        action = subject.removeprefix("orchard:agent:delegation:")
        sub = (env.get("body") or {}).get("subagent")
        state = _DELEGATION_STATE.get(action)
        if sub and state and _latest(rec, f"_sub_{sub}", ts):
            rec["subs"][sub] = state


def _fold_sessions(project_dir: Path) -> dict[str, dict]:
    """Fold one project's event files into one record PER SESSION ID —
    used only for repo-HEADER lookup (`_root_session_id`/`_apply_common`),
    never for the feature/task tree (see `_fold_agent_records`): the header
    is always exactly one session, and a resumed root session's own
    identity block is legitimately empty, which the tree's per-agent fold
    would otherwise (correctly) filter out as "no agent".

    A courier-labelled event (`identity.agent == COURIER_AGENT_NAME`) still
    updates this session's activity/lifecycle/outcome — it is the courier
    reporting on its parent's behalf (Decision-018), not a second session —
    but never becomes the session's own identity/status snapshot (operator
    correction, 2026-07-27: that overwrite is what silently blanked a live
    agent's own identity in an earlier build of this fold)."""
    found: dict[str, dict] = {}
    for sid, env, ts in _iter_project_events(project_dir):
        rec = found.setdefault(sid, {"sid": sid, "subs": {}})
        identity = env.get("identity") or {}
        _apply_event(rec, env, ts, trust_snapshot=identity.get("agent") != COURIER_AGENT_NAME)
    return found


def _merge_sessions(dirs: list[Path]) -> dict[str, dict]:
    """`_fold_sessions()` for each directory, merged into one session map.
    Session ids are unique per session, so this is a plain union — except
    on the (unexpected) case of the same session id appearing in two
    directories, where the record with the more recent `_seen_ts` wins
    rather than whichever directory was folded last."""
    merged: dict[str, dict] = {}
    for d in dirs:
        for sid, rec in _fold_sessions(d).items():
            current = merged.get(sid)
            if current is None or rec["_seen_ts"] >= current["_seen_ts"]:
                merged[sid] = rec
    return merged


AgentKey = tuple  # (session_id: str, parent: str | None, agent_name: str | None)


def _named_agent_keys(sid: str, events: list[tuple[dict, float]]) -> set[AgentKey]:
    """Every distinct `(session_id, parent, agent_name)` triple this
    session's own events announce, EXCLUDING the courier — the set of
    "session-bearing agents" a courier-labelled event under the same
    session id might be reporting on behalf of (see `_fold_agent_records`)."""
    return {
        (sid, identity.get("parent"), identity.get("agent"))
        for env, _ts in events
        for identity in [env.get("identity") or {}]
        if identity.get("agent") and identity.get("agent") != COURIER_AGENT_NAME
    }


def _fold_agent_records(project_dir: Path) -> dict[AgentKey, dict]:
    """Fold one project's event files into one record PER AGENT TRIPLE
    `(session_id, identity.parent, identity.agent)` — never per session id
    alone, since a session id is shared VERBATIM by an in-session subagent
    that has its own identity.

    The courier is the one deliberate exception (Decision-018: it answers
    identity/status off its PARENT's transcript, sharing the parent's
    session id, precisely so the parent is never woken to answer itself).
    A courier-labelled event is therefore never its own agent record: its
    non-identity payload (activity, lifecycle, outcome, delegation) is
    folded into the ONE session-bearing agent sharing that session id
    (operator correction, 2026-07-27 — "there is ONE agent... the
    courier's posts carry its status. Do not create two agents. Do not
    drop the courier's posts."), with `trust_snapshot=False` so it can
    never overwrite that agent's own identity/status (the mechanism behind
    an earlier build's "the landscaper's identity and its whole task
    vanished" regression). A session with zero or several session-bearing
    agents of its own has no unambiguous target to attribute a courier
    event to — such an event is dropped rather than guessed at."""
    events_by_session: dict[str, list[tuple[dict, float]]] = {}
    for sid, env, ts in _iter_project_events(project_dir):
        events_by_session.setdefault(sid, []).append((env, ts))

    found: dict[AgentKey, dict] = {}
    for sid, events in events_by_session.items():
        named_keys = _named_agent_keys(sid, events)
        sole_named_key = next(iter(named_keys)) if len(named_keys) == 1 else None
        for env, ts in events:
            identity = env.get("identity") or {}
            is_courier = identity.get("agent") == COURIER_AGENT_NAME
            if is_courier:
                if sole_named_key is None:
                    continue
                key = sole_named_key
            else:
                key = (sid, identity.get("parent"), identity.get("agent"))
            rec = found.setdefault(key, {"sid": sid, "subs": {}})
            _apply_event(rec, env, ts, trust_snapshot=not is_courier)
    return found


def _merge_agent_records(dirs: list[Path]) -> dict[AgentKey, dict]:
    """`_fold_agent_records()` for each directory, merged the same way
    `_merge_sessions()` merges its session map — newer `_seen_ts` wins on a
    (rare, unexpected) key collision across worktree directories."""
    merged: dict[AgentKey, dict] = {}
    for d in dirs:
        for key, rec in _fold_agent_records(d).items():
            current = merged.get(key)
            if current is None or rec["_seen_ts"] >= current["_seen_ts"]:
                merged[key] = rec
    return merged


# --------------------------------------------------------------------------
# Feature-node markers — the durable task node (Decision-099)
# --------------------------------------------------------------------------

_MARKER_ARCHIVE_DIR = "_archived"
# A task entry's own persisted terminal state maps onto the same outcome
# vocabulary `_status_for` already understands.
_MARKER_STATE_OUTCOME = {"done": "success", "failed": "fail"}
# A task entry's own persisted "working" state maps onto the same lifecycle
# vocabulary `_status_for`'s working/idle split already understands (any of
# starting/started/stopping reads "working" there). This is what makes
# "working" reachable for a marker-only task at all (bug fix, 2026-07-26:
# this mapping was previously absent, so a marker-only record could never
# enter that branch — a task whose events had aged out of the tree but
# whose marker said "working" rendered idle/stale/done/failed, never
# "working", however fresh its marker).
_MARKER_STATE_LIFECYCLE = {"working": "started"}


def _parse_iso_ts(text: str | None) -> float:
    """ISO-8601 UTC (courier.py's `datetime.now(timezone.utc).isoformat()`
    shape) -> epoch seconds; 0.0 — maximally stale, never a crash — on
    anything unparsable or missing."""
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0


def _iter_feature_markers(project_dir: Path):
    """Yield (feature_id, marker) for every on-disk feature-node marker
    (`<feature-id>.marker`) a project directory holds — the structural
    source a TASK row survives on even once the archiver has removed its
    event files (retention ruling, 2026-07-26: a finished task persists
    until restart). `_archived/` is never scanned; a legacy zero-byte
    `<session-id>.marker` heartbeat (courier.py's mailbox touch) has no
    JSON to parse and is skipped. A marker's actual per-task data lives in
    its `tasks` list (see `_marker_task_rec`) — this function only
    discovers and parses the file; any legacy `sessions` key a marker still
    happens to carry is never read."""
    for f in project_dir.iterdir():
        if f.name == _MARKER_ARCHIVE_DIR or not f.is_file():
            continue
        if not f.name.endswith(".marker") or f.stat().st_size == 0:
            continue
        try:
            marker = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        yield f.name.removesuffix(".marker"), marker


def _marker_task_rec(task: dict) -> dict:
    """A synthetic `_status_for` input for one of a marker's `tasks[]`
    entries, standing in for a task with no live agent at all. Its own
    persisted `state` supplies either a terminal outcome (done/failed) or
    the lifecycle signal that makes `_status_for`'s working/idle split
    reachable ("working" -> "started", the same value a live "started"
    lifecycle event carries); any other state, or none at all, leaves
    `_status_for` to fall through to its own staleness/idle default.

    `_status_for` runs its staleness check BEFORE the lifecycle check, so
    a marker declaring "working" whose own `updated` has aged past
    ACTIVE_WINDOW_SECONDS still reads "stale" — staleness is a colour, not
    a removal, and a marker's word for its own liveness does not override
    "not heard from in a while" (Decision-094). `done`/`failed` remain
    terminal and are never demoted by staleness, per `_status_for` itself.

    This stays deliberately narrow: it feeds only `_status_for`'s existing
    lifecycle/outcome vocabulary. Nothing agent- or subagent-shaped ever
    comes out of a marker-only record — role, model, activity and all
    subagent rows stay live-only (operator ruling, 2026-07-26)."""
    rec = {"subs": {}, "_seen_ts": _parse_iso_ts(task.get("updated"))}
    state = task.get("state")
    outcome = _MARKER_STATE_OUTCOME.get(state)
    if outcome:
        rec["outcome"] = outcome
    else:
        lifecycle = _MARKER_STATE_LIFECYCLE.get(state)
        if lifecycle:
            rec["state"] = lifecycle
    return rec


def _marker_task_id(task: dict) -> str | None:
    """The task's own id from a marker `tasks[]` entry — schema 2's `task`
    key, falling back to schema 1's `feature` key (today's on-disk shape,
    where one feature maps to exactly one task and the entry names it via
    the marker's own top-level feature id instead — DATA CONTRACT, 2026-
    07-26). An entry with NEITHER key is a rejected earlier shape (e.g. a
    bare delegation label); it yields None and is skipped outright, never
    guessed at."""
    return task.get("task") or task.get("feature")


# --------------------------------------------------------------------------
# Status derivation
# --------------------------------------------------------------------------

def _status_for(rec: dict, now: float) -> str:
    """working/done/failed/idle/waiting/awaiting_agent/stale, derived from
    the lifecycle+outcome+status signals this grammar actually carries,
    plus `now` for the staleness check. Both wait states are now reachable
    (M2 remap, ruled 2026-07-29 — "Questioning is not waiting: the two wait
    words", docs/TODO.md.d/bus-addressing.md §Decision entries):

    - `questioning` -> Decision-058's own "waiting" glyph state (its
      ORIGINAL slot — an answer this agent asked for is outstanding, the
      operator's own done-gate included).
    - `waiting` -> Decision-058's "awaiting_agent" state, previously
      unreachable (no producer word had been ruled for it) — this agent is
      waiting on another AGENT, not on an answer.

    Both are read off this record's own latest `orchard:agent:status` post
    body (`rec["activity"]`, `_apply_event`) — an ordinary STATUS post, the
    same channel "building tree" or any other one-word activity already
    rides, not a new subject or verb. Checked AFTER the terminal-outcome
    and staleness gates (an agent in either wait state that then finishes,
    or goes quiet past ACTIVE_WINDOW_SECONDS, is done/failed/stale like any
    other — Decision-094: staleness is a colour, not a removal, and it
    overrides a stuck activity word the same way it already overrides a
    stuck "starting" lifecycle state) but BEFORE the working/idle split,
    since either wait state is itself more specific than the generic
    "working" a live lifecycle state alone would otherwise read as.

    A terminal outcome (done/failed) always wins — it is never demoted to
    stale, no matter how old (retention ruling, 2026-07-25 revision: a
    finished task is a permanent green/red one-liner). Absent a terminal
    outcome, a session with no event inside ACTIVE_WINDOW_SECONDS reads
    stale (gray) rather than working/idle/waiting/awaiting_agent — checked
    before every other live-status read, since staleness overrides even a
    stuck "starting" lifecycle state (or a stuck wait activity word) that
    never followed up.

    A live record (one folded from real traffic, always carrying its own
    "sid") with no surviving lifecycle event still reads "working" once it
    is not stale — recent traffic of any kind is itself proof of life, so a
    "started" lifecycle event aging out of the archiver's retention must
    not silently demote a still-posting session to idle (bug fix, 2026-07-
    26: the live-record counterpart of the marker-only "working" fix
    above; see `_marker_task_rec`). An explicit "stopped" lifecycle event
    is a real signal rather than an absence and still reads idle. A
    synthetic marker-only record (no "sid") never had live traffic to
    infer from, so it is unaffected and keeps falling through to idle
    absent an explicit state — and never carries an `activity` either, so
    it can never read either wait state (live-only, same footing as
    role/model)."""
    if rec.get("outcome") == "fail" or rec.get("task_outcome") == "failed":
        return "failed"
    if rec.get("outcome") == "success" or rec.get("task_outcome") == "completed":
        return "done"
    if now - rec.get("_seen_ts", 0.0) >= ACTIVE_WINDOW_SECONDS:
        return "stale"
    if rec.get("activity") == _QUESTIONING_ACTIVITY:
        return "waiting"
    if rec.get("activity") == _WAITING_ACTIVITY:
        return "awaiting_agent"
    state = rec.get("state")
    if state in ("starting", "started", "stopping"):
        return "working"
    if state is None and "sid" in rec:
        return "working"
    return "idle"


def _row_label(rec: dict) -> str | None:
    """The identity name/feature to show, or None if there is nothing
    operator-facing on the identity itself (a bare session-UUID with no
    announced name or feature). Callers always fall back to the session id
    on a None here (operator ruling, 2026-07-26: a session with events
    ALWAYS renders something — missing identity degrades the label, never
    drops the row; see `_assemble_repo`)."""
    identity = rec.get("identity") or {}
    label = identity.get("name") or identity.get("feature")
    if label:
        return label
    return None if _is_bare_uuid(rec["sid"]) else rec["sid"]


def _apply_common(repo: Repo, rec: dict, now: float) -> None:
    """Copy the header record's own fields onto the repo header."""
    identity = rec.get("identity") or {}
    status = rec.get("status") or {}
    repo.activity = rec.get("activity", "")
    repo.status_word = repo.activity
    repo.status = _status_for(rec, now)
    repo.waiting_on_operator = False  # no source in this grammar
    repo.role = identity.get("agent")
    repo.model = status.get("model")


def _live_subagents(subs: dict[str, str]) -> list[Subagent]:
    """One Subagent row per delegation this record still remembers —
    sourced purely from its own live traffic (`subs`, from `orchard:agent:
    delegation:schedule|begin|end`), sorted by label. All three states
    render (rule 6, 2026-07-26): "done" is not a vanish, only the owning
    task's own fold removes the row. Nothing is ever unioned in from a
    feature marker — a subagent is live-only."""
    return sorted(
        (Subagent(label=label, state=state) for label, state in subs.items()),
        key=lambda sub: sub.label,
    )


# --------------------------------------------------------------------------
# Role -> step
# --------------------------------------------------------------------------

# role -> step, read from each charter's `step:` frontmatter key. A
# concurrent branch is adding these keys one charter at a time, so the
# loader must work whether or not any given one has it yet (operator
# ruling, 2026-07-26): a charter with no frontmatter, no `name`, no `step`,
# or a `step` outside `PHASES` simply contributes nothing to the map.
_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def load_role_step_map(agents_dir: Path | None = None) -> dict[str, str]:
    """role -> one of `PHASES`, from every `agents/*.md` charter's `step:`
    frontmatter key. Never raises on a missing `agents/` directory or an
    unreadable file — an empty map just means every agent renders without
    a step (fails open, see `resolve_step`)."""
    agents_dir = agents_dir or _AGENTS_DIR
    role_step_map: dict[str, str] = {}
    if not agents_dir.is_dir():
        return role_step_map
    for charter in sorted(agents_dir.glob("*.md")):
        try:
            fields = _parse_frontmatter(charter.read_text(encoding="utf-8"))
        except OSError:
            continue
        name, step = fields.get("name"), fields.get("step")
        if name and step in PHASES:
            role_step_map[name] = step
    return role_step_map


@functools.lru_cache(maxsize=1)
def _default_role_step_map() -> dict[str, str]:
    return load_role_step_map()


def resolve_step(role: str | None, rec: dict, role_step_map: dict[str, str]) -> str | None:
    """The step an agent is on. An explicit `phase` on the record always
    wins were one ever posted (none of today's event grammar carries one,
    but a future addition lands here without a rewrite — operator ruling,
    2026-07-26: the map is a FALLBACK, not the source of truth); otherwise
    the role->step map, keyed by the agent's own announced role. Fails
    open: a missing or unmapped role resolves to None, never a guess."""
    explicit = rec.get("phase")
    if explicit in PHASES:
        return explicit
    return role_step_map.get(role) if role else None


def phase_states(active_phase: str | None) -> list[tuple[str, str]]:
    """[(phase_word, state)] for every `PHASES` entry, state in
    {done, active, todo}, given the current active phase name (an unknown or
    absent phase renders every entry as `todo` — nothing claimed done or
    active without a signal)."""
    if active_phase not in PHASES:
        return [(p, "todo") for p in PHASES]
    active_index = PHASES.index(active_phase)
    return [
        (p, "done" if i < active_index else "active" if i == active_index else "todo")
        for i, p in enumerate(PHASES)
    ]


# --------------------------------------------------------------------------
# Agent / task / feature assembly
# --------------------------------------------------------------------------

def _agent_from_rec(sid: str, rec: dict, now: float, role_step_map: dict[str, str]) -> Agent:
    identity = rec.get("identity") or {}
    status = rec.get("status") or {}
    role = identity.get("agent")
    return Agent(
        session_id=sid, role=role, model=status.get("model"),
        activity=rec.get("activity") or NO_LIVE_ACTIVITY,
        status=_status_for(rec, now),
        parent=identity.get("parent"),
        step=resolve_step(role, rec, role_step_map),
        subagents=_live_subagents(rec.get("subs", {})),
        context_tokens=status.get("context_tokens"),
        spend=status.get("spend"),
        effort=status.get("effort"),
        started_ts=rec.get("_first_ts"),
        updated_ts=rec.get("_seen_ts"),
    )


def _task_active_step(agents: list[Agent]) -> str | None:
    """The task's current step: the furthest-along `PHASES` entry among its
    mapped agents. Purely positional — nothing on the bus remembers which
    step a task passed through earlier, so a done step's own agent is never
    reconstructed, only its position (see `_build_task_steps`)."""
    indices = [PHASES.index(agent.step) for agent in agents if agent.step in PHASES]
    return PHASES[max(indices)] if indices else None


def _build_task_steps(agents: list[Agent], active_step: str | None) -> list[Step]:
    """All five `PHASES` positions, always, once a task has an active step
    (operator ruling, 2026-07-26: steps must not flash in and out as a
    session's staleness flips) — done/todo ones are plain lines; only the
    active one carries the agents actually on it."""
    if active_step is None:
        return []
    return [
        Step(name=name, state=state,
             agents=[a for a in agents if a.step == name] if state == "active" else [])
        for name, state in phase_states(active_step)
    ]


_STATUS_PRECEDENCE = ("failed", "working", "waiting", "awaiting_agent", "stale", "idle")


def _combine_status(statuses: list[str]) -> str:
    """A parent's own status, aggregated from its children's (a feature
    from its tasks, a task from its live agents): the status most needing
    attention wins (failed > working > waiting > awaiting_agent > stale >
    idle — M2's two wait states both slotted between working and stale: a
    gated agent needs less attention than one still actively working, but
    more than a merely stale/idle one; `waiting` (questioning, an
    outstanding answer) ranks fractionally above `awaiting_agent` (waiting
    on a peer) since an unanswered question is the more attention-worthy of
    the two, a tie-break the ruling itself does not settle further);
    "done" only once EVERY child is done (operator ruling, 2026-07-26: a
    feature/task is complete only when everything inside it is)."""
    if not statuses:
        return "idle"
    for candidate in _STATUS_PRECEDENCE:
        if candidate in statuses:
            return candidate
    return "done"


def _agent_timestamp_bounds(agents: list[Agent]) -> tuple[float | None, float | None]:
    """(earliest `started_ts`, latest `updated_ts`) across a task's own live
    agents — the raw material `_task_running_seconds` turns into a running
    time. `None` for either half whenever no agent carries it (never
    reachable in practice once `_apply_event` has run, but a live agent
    could in principle carry an unset field, e.g. one built by a test)."""
    starts = [a.started_ts for a in agents if a.started_ts is not None]
    updates = [a.updated_ts for a in agents if a.updated_ts is not None]
    return (min(starts) if starts else None, max(updates) if updates else None)


def _task_running_seconds(
    status: str, started_ts: float | None, updated_ts: float | None, now: float,
) -> float | None:
    """The task row's own RUNNING TIME (spec §3: "calculations are
    performed by deterministic script code... elapsed aggregates derive
    from event timestamps" — computed here, at `build_model()` time,
    against its own `now`, so the same Fleet always renders the same text
    regardless of when it happens to be drawn — never recomputed from a
    live wall clock inside the renderer).

    None when `started_ts` is unknown (a marker-only task has no start time
    to read — an honest gap, not a guess). A still-open task's running time
    is `now - started_ts`, ticking forward every time the model rebuilds. A
    terminal task's (Decision-058's `done`/`failed`) freezes at
    `updated_ts - started_ts` — its own last event marks when it stopped,
    matching the retention ruling that a finished task's stats do not keep
    advancing after it is done."""
    if started_ts is None:
        return None
    if status in TERMINAL_TASK_STATUSES:
        return (updated_ts - started_ts) if updated_ts is not None else None
    return max(now - started_ts, 0.0)


def _task_context_tokens(agents: list[Agent]) -> int | None:
    """The task row's own CONTEXT figure (M2, spec §3's "context remaining"
    ruled metric — rendered as USAGE, see `Task.context_tokens`'s own
    docstring for why): the most-recently-updated live agent's own
    `context_tokens` among this task's agents — an implementer's reading
    of "which agent represents a multi-agent task's context", mirroring
    how `sidebar_model`'s own "activity line" concept already picks
    "whichever agent runs there now" for a task's live position, rather
    than a new rule invented for this figure alone. None when no agent on
    this task carries a `context_tokens` figure at all (no source, never a
    guess)."""
    candidates = [a for a in agents if a.context_tokens is not None and a.updated_ts is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda a: a.updated_ts).context_tokens


def _finalize_task(
    task_id: str, name: str, agents: list[Agent], marker_status: str | None, now: float,
) -> Task:
    if not agents:
        return Task(task_id=task_id, name=name, status=marker_status or "idle")
    mapped = [a for a in agents if a.step is not None]
    unmapped = [a for a in agents if a.step is None]
    status = _combine_status([a.status for a in agents])
    started_ts, updated_ts = _agent_timestamp_bounds(agents)
    return Task(
        task_id=task_id, name=name, status=status,
        steps=_build_task_steps(mapped, _task_active_step(mapped)),
        unstepped_agents=unmapped,
        started_ts=started_ts, updated_ts=updated_ts,
        running_seconds=_task_running_seconds(status, started_ts, updated_ts, now),
        context_tokens=_task_context_tokens(agents),
    )


class _TaskBuilder:
    def __init__(self, name: str) -> None:
        self.name = name
        self.agents: list[Agent] = []
        self.marker_status: str | None = None


class _FeatureBuilder:
    def __init__(self, name: str | None) -> None:
        self.name = name
        self.tasks: dict[str, _TaskBuilder] = {}

    def task(self, task_id: str, name: str) -> _TaskBuilder:
        builder = self.tasks.setdefault(task_id, _TaskBuilder(name))
        if not builder.name:
            builder.name = name
        return builder


def _finalize_feature(feature_id: str, builder: _FeatureBuilder, now: float) -> Feature:
    tasks = [
        _finalize_task(task_id, task_builder.name or task_id, task_builder.agents,
                        task_builder.marker_status, now)
        for task_id, task_builder in builder.tasks.items()
    ]
    return Feature(feature_id=feature_id, name=builder.name or feature_id,
                    status=_combine_status([t.status for t in tasks]), tasks=tasks)


def _root_session_id(sess: dict[str, dict]) -> str | None:
    """The root of the parent chain: a session that appears as some OTHER
    session's `identity.parent`, but names no parent of its own.

    A resumed root session (the gardener, notably — `claude --resume` with
    no `--agent`) loses its own role permanently: CLAUDE_CODE_AGENT is only
    set for subagent contexts, so its identity block comes out empty and it
    cannot name itself. Its CHILDREN still name it, though — every identity
    block already carries the spawning session's id as `parent` — so the
    root is derived from them instead (operator ruling, 2026-07-26: a
    UI-side inference over data already on the bus, not a new wire field —
    "it is a UI concern, not a bus concern").

    An intermediate parent (a landscaper is the parent of its own sowers)
    is never mistaken for the root: only the session with NO parent of its
    own qualifies, however many sessions it is itself the parent of.

    Operates over the SESSION-level fold (`sess`), not the agent-triple
    one: this is a fallback path for a session with no identifiable agent
    at all, which the triple fold would (correctly) treat as "no agent"."""
    parent_ids = {(sess[sid].get("identity") or {}).get("parent") for sid in sess}
    parent_ids.discard(None)
    roots = sorted(
        sid for sid in sess
        if sid in parent_ids and not (sess[sid].get("identity") or {}).get("parent")
    )
    return roots[0] if roots else None


def _gardener_key(agent_records: dict[AgentKey, dict]) -> AgentKey | None:
    """The agent-triple key whose announced role is explicitly "gardener",
    or None. Preferred over the session-level `_root_session_id` fallback
    whenever it exists: it is immune to a courier (or any other identity)
    sharing that same session id and happening to post the temporally-
    latest event, which would otherwise corrupt a session-level "latest
    snapshot" merge (see `_fold_sessions`'s docstring)."""
    return next(
        (key for key in sorted(agent_records, key=_agent_key_sort)
         if key[2] == "gardener"),
        None,
    )


def _agent_key_sort(key: AgentKey) -> tuple[str, str, str]:
    sid, parent, agent_name = key
    return sid, parent or "", agent_name or ""


_FEATURE_TASK_ID_RE = re.compile(r"^f/([^/]+)/([^/]+)$")


def _split_feature_task_id(task_id: str) -> tuple[str, str] | None:
    """(feature segment, task segment) when `task_id` has the `f/<feature>/
    <task>` shape a task identifier carries going forward (operator,
    2026-07-28: "we make the feature name the prefix of the task name
    moving forward, so f/sidebar/themes"); None for anything else —
    including today's own branch, a single segment (`f/sidebar-teamwork`)
    — DEGRADE HONESTLY, never invent a split that isn't there."""
    match = _FEATURE_TASK_ID_RE.match(task_id)
    return (match.group(1), match.group(2)) if match else None


def _identity_task_keys(
    identity: dict, label: str | None, sid: str,
) -> tuple[str, str | None, str, str]:
    """(feature_id, feature_name, task_id, task_name) from an agent's
    identity block. `feature`/`task` themselves still fall back to the
    announced label, then the bare session id (a session with events
    always lands somewhere, operator ruling 2026-07-26) — those are
    internal KEYS, not displayed names, so a session/label standing in for
    a missing one is not an invented name.

    `feature_name` is NEVER a borrowed label/session id any more (operator
    ruling, 2026-07-28, correcting a prior report that no feature-level
    name existed at all: `identity.feature_name` is the authored human
    name and already rides the wire — the renderer previously discarded it
    and fell through to a borrowed label instead, which is why the wrong
    text showed). Precedence: the explicit `feature_name` (or its `name`
    alias, kept for a reader on the older shape) wins outright; failing
    that, the middle segment of a `task_id` with the `f/<feature>/<task>`
    shape; failing THAT, None — nothing invented, left for the caller
    (`_finalize_feature`) to fall back to the bare `feature_id`, its own
    existing honest degradation.

    `task_name` follows the same shape-derived option (the LAST segment)
    ahead of the old blind reuse of `feature_name`, falling back to
    `task_id` itself only if truly nothing else is available (Task.name is
    never None)."""
    feature_id = identity.get("feature") or label or sid
    task_id = identity.get("task") or feature_id
    split = _split_feature_task_id(task_id)
    feature_name = (
        identity.get("feature_name") or identity.get("name")
        or (split[0] if split else None)
    )
    task_name = identity.get("task_name") or (split[1] if split else None) or feature_name or task_id
    return feature_id, feature_name, task_id, task_name


def _merged_interval_seconds(intervals: list[tuple[float, float]]) -> float:
    """Total seconds covered by the UNION of `intervals` (each an agent
    record's own `[_first_ts, _seen_ts]` span) — overlapping/concurrent
    agent spans count ONCE, not twice, so two agents working the SAME
    stretch of wall-clock time never double the repo's own "worked" total.
    Pure interval-union arithmetic over already-known timestamps, no wall
    clock read of its own."""
    if not intervals:
        return 0.0
    ordered = sorted(intervals)
    total = 0.0
    cur_start, cur_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= cur_end:
            cur_end = max(cur_end, end)
        else:
            total += cur_end - cur_start
            cur_start, cur_end = start, end
    total += cur_end - cur_start
    return total


def _repo_time_and_tokens(
    agent_records: dict[AgentKey, dict], now: float,
) -> tuple[str | None, str | None, str | None, str | None]:
    """(age, worked, tokens, dollars) for the repo footer (M2, spec §3's
    `age⏱ vs worked + tokens⚡/dollars` grammar, `sidebar_render_text.
    footer_lines`/`done_footer_line`) — all four deterministic,
    script-computed from this repo's own agent records at `build_model()`
    time against its own `now`, never a live wall clock read inside a
    renderer (spec §3: "never through an agent's context").

    AGE is the wall-clock span since this repo's OWN earliest event, across
    every agent (`now - min(_first_ts)`) — "how long has anything been
    happening here at all".

    WORKED is the UNION of every agent record's own `[_first_ts, _seen_ts]`
    span (`_merged_interval_seconds`) — the total wall-clock time during
    which AT LEAST ONE agent was actually posting, excluding any stretch
    before the first agent ever started or between two agents where
    nothing was live. This is an implementer's reading of "time actually
    worked" (spec §3 names the STAT — "the feature's lifetime/age
    displayed against the time actually worked on it" — not this exact
    aggregation): the model carries no finer-grained activity timeline
    than each agent's own first/last-seen timestamps to derive it from, so
    AGE and WORKED can differ only by the gaps those timestamps expose
    (idle stretches before/between agents), never by anything finer.

    TOKENS is the sum of each agent's own latest known `tokens_in` +
    `tokens_out` (already-accumulated running totals per session, promoted
    to first-class status fields per courier-wire.md §2b), formatted via
    `_format_token_count`. None whenever no agent record carries a
    timestamp/token figure at all (an empty repo).

    DOLLARS is the sum of each agent's own latest known `dollars` (promoted
    out of `courier.estimates_for()`'s `cost_usd` by `orchard_topic.py`'s
    `_status()`, same footing as tokens above), formatted via
    `_format_dollars`. None whenever no agent record on this repo carries a
    `dollars` figure — an unrecognised model, or no status snapshot at all —
    never invented, matching TOKENS' own "no data means no field" rule."""
    intervals: list[tuple[float, float]] = []
    earliest: float | None = None
    total_tokens = 0
    have_tokens = False
    total_dollars = 0.0
    have_dollars = False
    for rec in agent_records.values():
        first_ts, seen_ts = rec.get("_first_ts"), rec.get("_seen_ts")
        if first_ts is not None and seen_ts is not None:
            intervals.append((first_ts, seen_ts))
            earliest = first_ts if earliest is None else min(earliest, first_ts)
        status = rec.get("status") or {}
        tokens_in, tokens_out = status.get("tokens_in"), status.get("tokens_out")
        if tokens_in is not None or tokens_out is not None:
            total_tokens += (tokens_in or 0) + (tokens_out or 0)
            have_tokens = True
        dollars = status.get("dollars")
        if dollars is not None:
            total_dollars += dollars
            have_dollars = True
    age = _format_running_time(max(now - earliest, 0.0)) if earliest is not None else None
    worked = _format_running_time(_merged_interval_seconds(intervals)) if intervals else None
    tokens = _format_token_count(total_tokens) if have_tokens else None
    dollars = _format_dollars(total_dollars) if have_dollars else None
    return age, worked, tokens, dollars


def _merged_feature_markers(project_dirs: list[Path]):
    """(feature_id, marker) pairs across EVERY `@branch` variant directory
    of one repo group. Sessions and agent records already merge across the
    variants (`_merge_sessions`/`_merge_agent_records`); feature markers
    must too, or a feature whose marker lives in any directory but the
    group's first is invisible (live-fired 2026-07-29: the observability
    feature's own fresh marker sat unread in its worktree's directory while
    markers were only ever read from the group's first variant, and the
    sidebar showed "no activity" over a working feature). The same feature
    written by several variants resolves to the newest top-level `updated`
    — one file per (project, feature) is the ruled granularity
    (Decision-099), and the variants are ONE project on the board."""
    best: dict[str, dict] = {}
    for project_dir in project_dirs:
        for feature_id, marker in _iter_feature_markers(project_dir):
            held = best.get(feature_id)
            if held is None or (marker.get("updated") or "") > (held.get("updated") or ""):
                best[feature_id] = marker
    return best.items()


def _assemble_repo(
    dir_name: str, project_dirs: list[Path], sess: dict[str, dict],
    agent_records: dict[AgentKey, dict], now: float, role_step_map: dict[str, str],
) -> Repo:
    repo = Repo(name=_repo_display_name(dir_name), activity="", status="idle",
                waiting_on_operator=False)

    # Prefer an EXPLICIT "gardener" identity, found among the agent-triple
    # records (immune to courier/session-id collision); fall back to the
    # root of the parent chain (`_root_session_id`, session-level) for a
    # resumed root session that can no longer name itself. Either way, this
    # one session supplies the repo header and is excluded from the
    # feature/task loop below, so it never also draws a duplicate row for
    # itself.
    gardener_key = _gardener_key(agent_records)
    if gardener_key is not None:
        header_sid = gardener_key[0]
        _apply_common(repo, agent_records[gardener_key], now)
    else:
        header_sid = _root_session_id(sess)
        if header_sid is not None:
            _apply_common(repo, sess[header_sid], now)

    features: dict[str, _FeatureBuilder] = {}
    live_task_keys: set[tuple[str, str]] = set()

    for key in sorted(agent_records, key=_agent_key_sort):
        sid, _parent, agent_name = key
        # The header session is excluded entirely — it already supplied the
        # repo header above. A record with no agent name at all (identity-
        # less traffic — a courier event with no session-bearing agent to
        # attribute to is already dropped by `_fold_agent_records` itself,
        # never reaching here as its own key) earns no row: a session with
        # no qualifying agent does not belong on the board (operator
        # ruling, 2026-07-27). Every other agent earns a row: missing
        # feature/task, an unknown/unmapped role — none of these drop it
        # (Decision-101).
        if sid == header_sid or not agent_name:
            continue
        rec = agent_records[key]
        identity = rec.get("identity") or {}
        feature_id, feature_name, task_id, task_name = _identity_task_keys(
            identity, _row_label(rec), sid,
        )
        builder = features.setdefault(feature_id, _FeatureBuilder(feature_name))
        if not builder.name:
            builder.name = feature_name
        task_builder = builder.task(task_id, task_name)
        task_builder.agents.append(_agent_from_rec(sid, rec, now, role_step_map))
        live_task_keys.add((feature_id, task_id))

    # A task with no live agent at all still renders — as a single row
    # carrying whatever its marker persisted, nothing beneath it (operator
    # ruling, 2026-07-26: the task is the one thing that doesn't
    # disappear). Skipped when a live session already supplied this exact
    # task's row above, so an in-progress task never doubles up.
    for feature_id, marker in _merged_feature_markers(project_dirs):
        builder = None
        for task in marker.get("tasks") or []:
            task_id = _marker_task_id(task)
            if not task_id or (feature_id, task_id) in live_task_keys:
                continue
            if builder is None:
                builder = features.setdefault(feature_id, _FeatureBuilder(marker.get("name")))
            task_name = task.get("name") or task_id
            # Schema 1 markers (still on disk) carry no top-level feature
            # `name` at all — today one feature maps to exactly one task,
            # so the degenerate case falls back to that sole task's own
            # name (DATA CONTRACT, 2026-07-26).
            if not builder.name:
                builder.name = task_name
            task_builder = builder.task(task_id, task_name)
            task_builder.marker_status = _status_for(_marker_task_rec(task), now)

    repo.features = [_finalize_feature(fid, b, now) for fid, b in features.items()]
    repo.has_session = header_sid is not None or bool(repo.features)
    repo.age, repo.worked, repo.tokens, repo.dollars = _repo_time_and_tokens(agent_records, now)
    return repo


def build_model(
    root: Path | None = None, now: float | None = None,
    role_step_map: dict[str, str] | None = None,
    watched_names: set[str] | None = None,
) -> Fleet:
    """One snapshot of the fleet: every WATCHED project directory is
    folded and assembled into one Repo — nothing is ever excluded by
    staleness (retention ruling, 2026-07-25 revision: a row leaves the
    sidebar only when the process restarts and the tmpfs projects tree
    clears with it). ACTIVE_WINDOW_SECONDS still matters — it is what
    `_status_for` compares `now` against to decide whether an
    unfinished session reads "stale" (gray) rather than "working"/"idle" —
    but it no longer removes anything from this snapshot.

    `now`, when given, stands in for the wall-clock read normally taken at
    call time — a seam for tests that need the staleness check pinned to a
    fixed instant relative to a captured fixture's own `updated` timestamp,
    rather than the real clock racing that fixture's age. Production call
    sites never pass it, so the default (`time.time()` at call time) is
    unchanged.

    `role_step_map`, when given, overrides the role->step map read from the
    real `agents/*.md` charters (`_default_role_step_map()`) — a seam for
    tests that don't want to depend on this repo's own agents/ directory.

    `watched_names`, when given, is the set of repo DISPLAY names to fold
    (`load_watched_repo_names()`) — every other project directory is
    skipped before any of its event/marker files are even opened. None
    (the default) folds every project directory found: the pre-registry
    behaviour, which is what this function's own tests exercise; a
    production entry point is what supplies the real registry's set (see
    `sidebar_model.py`'s module docstring)."""
    root = root or projects_root()
    fleet = Fleet()
    if not root.is_dir():
        return fleet
    now = time.time() if now is None else now
    role_step_map = _default_role_step_map() if role_step_map is None else role_step_map
    for identity, dirs in _group_project_dirs(root):
        display_name = _repo_display_name(identity)
        if watched_names is not None and display_name not in watched_names:
            continue
        fleet.repos.append(_assemble_repo(
            display_name, dirs, _merge_sessions(dirs), _merge_agent_records(dirs),
            now, role_step_map,
        ))
    return fleet


_WATCH_RESTART_BACKOFF_SECONDS = 1.0


def watch(on_change, root: Path | None = None, watched_names: set[str] | None = None) -> None:
    """Call on_change(fleet) whenever the projects root changes. Never
    returns while the process lives.

    Prefers `inotifywait -m -r` on the root, supervised for the whole
    lifetime of the call: a dying inotifywait child is reaped and, as long
    as the binary is installed, restarted — with a short backoff if it
    keeps exiting immediately, so a crash loop never busy-spins. While the
    root doesn't exist (or inotifywait isn't installed at all) this falls
    back to a 2s re-scan, matching the retired sidebar_model.watch()
    shape; a root that later reappears is picked back up by inotifywait on
    the next iteration. build_model() on a missing root is just an empty
    Fleet, never a crash.

    `watched_names` is threaded straight through to each `build_model()`
    call — see its own docstring; `None` (the default) folds every project
    directory found."""
    root = root or projects_root()
    has_inotifywait = shutil.which("inotifywait") is not None

    def rescan_and_notify() -> None:
        on_change(build_model(root, watched_names=watched_names))

    def run_inotify_until_exit() -> None:
        cmd = [
            "inotifywait", "-m", "-r",
            "-e", "create", "-e", "moved_to", "-e", "modify", "-e", "delete",
            "--format", "%f", str(root),
        ]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        try:
            for _ in proc.stdout:
                rescan_and_notify()
        finally:
            proc.terminate()
            proc.wait()

    while True:
        rescan_and_notify()
        if has_inotifywait and root.is_dir():
            started_at = time.monotonic()
            run_inotify_until_exit()
            if time.monotonic() - started_at < _WATCH_RESTART_BACKOFF_SECONDS:
                time.sleep(_WATCH_RESTART_BACKOFF_SECONDS)
        else:
            time.sleep(2)

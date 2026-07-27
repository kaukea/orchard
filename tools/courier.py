#!/usr/bin/env python3
"""Repo-scoped agent message courier.

The envelope lives here and nowhere else. Agents never construct or parse a
message: the courier sidecar shells out to this script on both send and receive, so
the format cannot drift across prompts and cannot be got wrong by an agent
following prose.

Transport: flat files + marker heartbeats under $XDG_RUNTIME_DIR/orchard/ (see
the "orchard transport" section below), addressed by :session:<id> or
:topic:<name>. This is the ONLY transport — the git-common-dir per-agent
mailbox this replaced could not coexist with worktrees (--git-common-dir is
shared by every worktree of a repo, and a subagent inherits its parent's
CLAUDE_CODE_SESSION_ID, so concurrent worktrees resolved to the same box and
could delete each other's inbox) and was removed outright (operator ruling,
2026-07-27).

Messages are ephemeral and deleted on consumption, so receiving is "take what is
there", with no bookkeeping. There is NO delivery guarantee: a sender expects no
answer and decides for itself whether to retry, abandon, or error.

Identity is the session id, read from the environment. It is not derived from
location: two sessions can share a directory, and a subagent inherits its
parent's environment verbatim — which is deliberate, since a courier sidecar must
resolve to its PARENT's mailbox.

Usage:
  courier.py whoami                                this session's id
  courier.py init                                  ensure this session's orchard
                                                project directory exists; print it
                                                (also SessionStart's structural
                                                guarantee — hooks/courier-init.sh)
  courier.py teardown                              no-op (nothing owned to remove)
  courier.py project-dir                           print this session's orchard
                                                project directory (what a courier's
                                                Monitor watches, agents/courier.md)
  courier.py send --to :session:<id>|:topic:<name>|operator --subject S
             [--body X] [--notify-user] [--target-project SLUG]
             [--in-reply-to ID]                    `:session:operator` is a
                                                RESERVED, dot-free target: always
                                                the SENDER's own project
                                                (projects/<repo>.<project>/
                                                operator.<ts>.json), no allowlist
                                                needed
  courier.py broadcast                             RETIRED — errors, pointing at
                                                orchard_topic.py post (telemetry) or
                                                send/request (directed). Fan-out is
                                                the token leak; nothing fans out any
                                                more (see below: announce/depart/
                                                signal/ask all lost their fallback).
  courier.py receive                               drain this session's orchard
                                                mailbox: JSON array, oldest first,
                                                delete-on-read
  courier.py monitor [--poll-interval N]           long-running: one inotifywait
                                                watcher per mailbox source, filtered
                                                at the watch to what could possibly
                                                be this session's own (falls back to
                                                polling every N seconds — default
                                                2.0 — when inotifywait is missing);
                                                on each arrival, drains and prints
                                                every message that is actually its
                                                own as JSON Lines, flushed
                                                immediately; never exits on its own
                                                (agents/courier.md arms this as the
                                                Monitor)
  courier.py request --to :session:<id> --subject S [--body X]
             [--target-project SLUG]               send, then block for the
                                                matching reply; prints its body
  courier.py reply --to :session:<id> --in-reply-to ID --subject S
             [--body X] [--target-project SLUG]
  courier.py identity                              immutable facts about this session
  courier.py status                                mutable state: occupancy and spend
  courier.py announce                              no-op (identity rides every
                                                orchard_topic.py event instead)
  courier.py depart                                no-op (nothing reads it)
  courier.py signal --state S [--to ID]            lifecycle push, directed at the
                                                parent ONLY (--to, else
                                                ORCHID_PARENT_SESSION; cross-repo via
                                                ORCHID_PARENT_PROJECT, allowlist-
                                                gated same as any cross-project
                                                :session: send) — delivered over the
                                                orchard transport. No parent known
                                                means not delivered; never broadcast.
  courier.py ask --question Q --option A --option B [...] [--multi]
             [--title T] [--summary S]
                                                a directed orchard request to the
                                                reserved :session:operator mailbox
                                                (never a broadcast); the standalone
                                                question-broker drains it and
                                                replies :session:<asker> with
                                                orchard:operator:message:response,
                                                matched via in_reply_to exactly like
                                                request/reply. Blocks until answered,
                                                then prints ONE JSON object to stdout
                                                and exits.

                                                This is a THREE-WAY outcome (four-way with
                                                --multi) — the caller MUST branch on which key
                                                is present, never assume a single shape:
                                                  {"index": N, "option": "..."}
                                                      single-select (default): this option chosen
                                                  {"indices": [...], "options": [...]}
                                                      --multi: this set chosen, Enter-confirmed
                                                  {"continue": true}
                                                      operator pressed Escape — this means "keep
                                                      discussing before deciding", NOT declined
                                                      or cancelled; treat as pause-and-keep-talking
                                                  {"gate": "MAKE IT SO" | "THAT IS ALL"}
                                                      operator typed one of the two always-
                                                      available gate phrases, bypassing the
                                                      specific question entirely

                                                --multi: digits TOGGLE membership instead of
                                                committing instantly; Enter confirms. Default
                                                (no --multi) is unchanged: instant-on-digit.
                                                --title/--summary: optional short framing shown
                                                prominently above the question in the popup.
  courier.py validate [PATH]                       audit recorded traffic against
                                                WIRE GRAMMAR v1; PATH is an
                                                orchard-root directory read
                                                recursively, else envelopes
                                                come JSON-lines from stdin;
                                                prints one line per violation/
                                                warning + a summary count,
                                                exit 1 if any violation
"""
import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, NamedTuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feature_name import feature_name as _feature_name  # noqa: E402

try:
    from orchard_compact import maybe_compact
except ImportError:  # orchard_compact ships in a parallel step; degrade to a no-op
    def maybe_compact(dir_path):  # noqa: ANN001, ANN201
        return None

# Standard request bodies the sidecar answers itself, without waking its parent:
# a message whose body is one of these is a pull for that information. Closed set,
# handled deterministically so it costs no tokens in the parent or the sidecar.
FIXED = ("identity", "status")

TOKEN_CLASSES = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)

# Model card — context window (tokens) and USD-per-million-token rates, cached from
# the Claude API reference of 2026-06-24 (MODEL_CARD_DATE below travels on status so
# a consumer can judge staleness). The schema principle: report what is AVAILABLE
# (raw counts, model id) and what we can ESTIMATE (occupancy, cost) — an unknown
# model yields nulls, never guesses. Cache reads bill ~0.1x base input; cache
# writes ~1.25x (the 5-minute default TTL — 1-hour writes bill 2x, which this
# estimate cannot see, so cost is a floor, marked estimate).
MODEL_CARD_DATE = "2026-06-24"
MODEL_CARD = {
    "claude-fable-5": {"window": 1_000_000, "in": 10.0, "out": 50.0},
    "claude-mythos-5": {"window": 1_000_000, "in": 10.0, "out": 50.0},
    "claude-opus-4-8": {"window": 1_000_000, "in": 5.0, "out": 25.0},
    "claude-opus-4-7": {"window": 1_000_000, "in": 5.0, "out": 25.0},
    "claude-opus-4-6": {"window": 1_000_000, "in": 5.0, "out": 25.0},
    "claude-sonnet-5": {"window": 1_000_000, "in": 3.0, "out": 15.0},
    "claude-sonnet-4-6": {"window": 1_000_000, "in": 3.0, "out": 15.0},
    "claude-haiku-4-5": {"window": 200_000, "in": 1.0, "out": 5.0},
}


def card_for(model: str | None) -> dict | None:
    """Longest-prefix match so dated variants (claude-haiku-4-5-20251001) resolve."""
    if not model:
        return None
    hits = [k for k in MODEL_CARD if model.startswith(k)]
    return MODEL_CARD[max(hits, key=len)] if hits else None


def estimates_for(model: str | None, spend: dict, occupancy: int) -> dict:
    """Derived figures, clearly second-class to the raw counts they come from.

    Empty rather than null (operator, 2026-07-21): an unknown model yields an
    EMPTY dict — absence means "cannot estimate"; no field ever carries null.
    """
    card = card_for(model)
    if card is None:
        return {}
    per_m = 1_000_000
    cost = (
        spend["input_tokens"] * card["in"]
        + spend["output_tokens"] * card["out"]
        + spend["cache_read_input_tokens"] * card["in"] * 0.1
        + spend["cache_creation_input_tokens"] * card["in"] * 1.25
    ) / per_m
    return {
        "window": card["window"],
        "occupancy": round(occupancy / card["window"], 3),
        "cost_usd": round(cost, 4),
        "rates_cached": MODEL_CARD_DATE,
    }

LIFECYCLE_STATES = ("started", "building", "testing", "done", "finished", "blocked", "abandoned")

# What a "blocked" signal is blocked ON — the sidebar (sidebar_model.py) needs
# this to tell "waiting on an external component" (⌚) apart from "waiting on
# a peer agent" (🪷); absent (older callers, or any state other than
# "blocked") the sidebar defaults to "component".
BLOCKED_ON_STATES = ("component", "agent")

# WIRE GRAMMAR v1 (docs/TODO.md.d/bus-message-specifying.md): the closed set of
# orchid:* body classes a hand-sent send/broadcast may use. orchid:interrupt:*
# is deliberately absent — courier.py ask is its only emitter.
NOTIFY_FORBIDDEN_ORCHID_CLASSES = ("status", "update", "phase", "subagent")
SIGNAL_NOTIFY_STATES = ("done", "blocked", "abandoned")

ORCHID_STATUS_DENYLIST = frozenset({
    "started", "building", "testing", "done", "finished", "blocked",
    "abandoned", "closing", "releasing", "departing", "announcing",
})
ORCHID_PHASES = ("ideation", "scoping", "designing", "building", "releasing")
_STATUS_WORD_RE = re.compile(r"[a-z]+(-[a-z]+)*")


def _validate_status_body(rest: str) -> str | None:
    words = rest.split()
    if not words or len(words) > 2:
        return "orchid:status:<word> takes 1 or 2 lowercase words"
    for word in words:
        if not _STATUS_WORD_RE.fullmatch(word):
            return f"orchid:status word {word!r} must be lowercase letters/hyphens only"
        if word in ORCHID_STATUS_DENYLIST:
            return f"orchid:status word {word!r} collides with a lifecycle state"
    return None


def _validate_update_body(rest: str) -> str | None:
    return None if rest.strip() else "orchid:update:<sentence> needs non-empty text"


def _validate_phase_tick(tick: str) -> str | None:
    k, sep, n = tick.partition("/")
    if not sep or not k.isdigit() or not n.isdigit():
        return "orchid:phase tick must be k/n positive integers"
    if int(k) <= 0 or int(n) <= 0 or int(k) > int(n):
        return "orchid:phase tick must satisfy 1 <= k <= n"
    return None


def _validate_phase_body(rest: str) -> str | None:
    parts = rest.split(":")
    if len(parts) not in (1, 2):
        return "orchid:phase:<phase>[:<k>/<n>] malformed"
    phase = parts[0]
    if phase not in ORCHID_PHASES:
        return f"orchid:phase {phase!r} not one of {'/'.join(ORCHID_PHASES)}"
    return _validate_phase_tick(parts[1]) if len(parts) == 2 else None


def _validate_subagent_body(rest: str) -> str | None:
    action, sep, label = rest.partition(":")
    if not sep:
        return "orchid:subagent:(queue|start|done):<label> malformed"
    if action not in ("queue", "start", "done"):
        return f"orchid:subagent action {action!r} must be queue, start, or done"
    return None if label else "orchid:subagent label must be non-empty"


ORCHID_BODY_VALIDATORS = {
    "status": _validate_status_body,
    "update": _validate_update_body,
    "phase": _validate_phase_body,
    "subagent": _validate_subagent_body,
}
ORCHID_ALLOWED_CLASSES_TEXT = "status, update, phase, subagent, interrupt:question (ask-only)"


def _orchid_body_error(body: str) -> str | None:
    cls, _, rest = body[len("orchid:"):].partition(":")
    if cls == "interrupt":
        return "orchid:interrupt:* may only be emitted by courier.py ask, never send/broadcast"
    validator = ORCHID_BODY_VALIDATORS.get(cls)
    if validator is None:
        return f"unknown orchid:* class {cls!r}"
    return validator(rest)


def _orchid_class(body: str) -> str:
    return body[len("orchid:"):].partition(":")[0]


def enforce_orchid_grammar(args) -> None:
    body = getattr(args, "body", None)
    if not body or not body.startswith("orchid:"):
        return
    reason = _orchid_body_error(body)
    if reason:
        args.parser.error(f"courier: {reason} — allowed orchid:* classes: {ORCHID_ALLOWED_CLASSES_TEXT}")
    cls = _orchid_class(body)
    if cls in NOTIFY_FORBIDDEN_ORCHID_CLASSES and getattr(args, "notify_user", False):
        args.parser.error(f"courier: --notify-user is not legal on orchid:{cls}:* bodies")


def git(*args: str) -> str:
    """Run a git command, returning '' rather than raising outside a repo."""
    try:
        done = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return done.stdout.strip()


def whoami() -> str:
    """This session's id, straight from the environment.

    Every session has one and can read its own. A subagent inherits its parent's,
    which is what lets a courier sidecar find its parent's mailbox without being told.
    """
    session = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    if not session:
        sys.exit("courier: CLAUDE_CODE_SESSION_ID is unset — not inside an agent session")
    return session


def stamp() -> str:
    # sortable and readable; ':' avoided so the name is portable
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S.%f")


def transcript() -> Path | None:
    """This session's transcript, located by session id across project folders."""
    projects = Path.home() / ".claude" / "projects"
    matches = sorted(projects.glob(f"*/{whoami()}.jsonl"))
    return matches[-1] if matches else None


def usage_entries(path: Path):
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = entry.get("message") or {}
        usage = message.get("usage")
        if isinstance(usage, dict):
            yield usage, message.get("model")


def identity_of() -> dict:
    """Immutable facts, fixed for this session's whole life.

    Model and effort are deliberately absent: they can change mid-session, so they
    are not identity, and pinning them here would bake in a value that goes stale.
    """
    top = git("rev-parse", "--show-toplevel")
    worktree = Path(top).name if top else None
    linked = "/worktrees/" in git("rev-parse", "--git-dir")
    feature_id = worktree if linked else None
    return {
        "session_id": whoami(),
        "agent_type": os.environ.get("CLAUDE_CODE_AGENT") or None,
        "worktree": worktree,
        "feature_id": feature_id,
        # Ledger-derived human name (tools/feature_name.py, sidebar-polish item 11):
        # board short-title, else sidecar H1, else mechanical hyphen->space, so
        # every consumer reads one already-authored field instead of re-deriving
        # (Decision-032).
        "name": _feature_name(feature_id, root=top) if feature_id else None,
        "parent_session": os.environ.get("ORCHID_PARENT_SESSION") or None,
    }


def status_of() -> dict:
    """Mutable state, read off the transcript — the parent is never consulted.

    Two consumers with near-identical payloads: an agent watching context
    occupancy (its own death condition) and an operator watching spend. Token
    classes stay broken out because they bill at different rates, so a single
    total cannot produce cost.

    Raw counts only. Expressing occupancy against a window, or classes as money,
    needs the model — which now travels alongside the counts as the denominator
    source. `effort` is best-effort: filled from the environment when a reliable
    source exists, else None.
    """
    path = transcript()
    if path is None:
        return {"session_id": whoami(), "state": "unknown", "reason": "no transcript"}

    spend = dict.fromkeys(TOKEN_CLASSES, 0)
    latest = None
    model = None
    for usage, entry_model in usage_entries(path):
        latest = usage
        if entry_model:
            model = entry_model
        for field in TOKEN_CLASSES:
            spend[field] += usage.get(field, 0) or 0

    occupancy = sum((latest or {}).get(f, 0) or 0 for f in TOKEN_CLASSES
                    if f != "output_tokens")
    # no reliable reasoning-effort env var is exposed to the CLI today
    effort = os.environ.get("CLAUDE_CODE_REASONING_EFFORT") or None
    status = {
        "session_id": whoami(),
        "state": "live",
        "context_tokens": occupancy,
        "spend": spend,
        "model": model,
        "effort": effort,
        # AVAILABLE above; ESTIMATED below — empty when the model is unknown,
        # never guesses and never null (operator schema ruling, 2026-07-21).
        "estimates": estimates_for(model, spend, occupancy),
    }
    # Empty rather than null, matching the envelope convention: a field with
    # nothing to say is absent.
    return {k: v for k, v in status.items() if v is not None and v != {}}


def make_envelope(sender: str, to: str, *, body=None, notify_user=False,
                  operator_origin=False, in_reply_to=None) -> dict:
    """Build a message envelope carrying only the fields that mean something.

    id/ts/from/to are always present. `to` is a recipient id or `*` (everyone).
    Everything else appears only when set: no in_reply_to unless it answers a
    request, no notify_user unless the user should see it, no operator_origin
    unless the message originates from the operator, no body when there is
    none. A request is not tagged — its id is its identifier, and a standard
    request is recognised by its body (see the fixed identifiers).
    """
    env = {
        "id": uuid.uuid4().hex[:12],
        "ts": datetime.now(timezone.utc).isoformat(),
        "from": sender,
        "to": to,
    }
    if notify_user:
        env["notify_user"] = True
    if operator_origin:
        env["operator_origin"] = True
    if in_reply_to is not None:
        env["in_reply_to"] = in_reply_to
    if body is not None:
        env["body"] = body
    return env


def cmd_send(args) -> None:
    enforce_orchid_grammar(args)
    if not is_orchard_address(args.to):
        sys.exit(
            f"courier: send --to {args.to!r} is not an orchard address — the "
            "legacy per-agent mailbox is gone; use :session:<id> or "
            ":topic:<name>"
        )
    env = orchard_send(args)
    print(env["id"])


def cmd_broadcast(args) -> None:
    """Retired: this used to fan a copy into every OTHER agent's inbox — the
    token leak the courier is being redesigned to kill. status/phase/subagent
    are 1->many TELEMETRY, which belongs on a topic (orchard_topic.py post),
    never on the courier. There is no fan-out replacement command: a
    directed `send`/`request` is the only way left to reach a specific peer.
    """
    sys.exit(
        "courier: broadcast is retired — it fanned a copy into every inbox. "
        "For status/phase/subagent telemetry, use `orchard_topic.py post` "
        "instead. For a directed message, use `send --to <id>` or "
        "`send --to :session:<id>`."
    )


def cmd_receive(args) -> None:
    print(json.dumps(orchard_receive_own(), indent=2))


def cmd_monitor(args) -> None:
    """Long-running: watches THIS session's mailbox sources, filtered at the
    watch to what could possibly be its own, and on each arrival drains and
    prints every message that is actually its own — one JSON object per
    line, flushed immediately. Reuses each source's own read (for the
    project-directory mailbox, orchard_receive_own()) so delete-on-
    consumption semantics are unchanged and there is no second parsing
    path. Never exits on its own — this is what agents/courier.md arms as
    the Monitor."""
    sources = _monitor_sources()
    _drain_all(sources)
    if shutil.which("inotifywait"):
        _monitor_inotify(sources)
    else:
        _monitor_poll(sources, args.poll_interval)


def _ensure_project_dir() -> Path:
    dir_path = project_dir(project_slug())
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def cmd_init(args) -> None:
    """Structural half of SessionStart (hooks/courier-init.sh): ensure this
    session's orchard project directory exists, so a courier's Monitor
    always has something to watch even before anyone has announced or sent
    anything. The legacy per-agent mailbox this used to create and claim
    ownership of (Decision-095/096) is gone — orchard messages are flat
    files under a shared project directory, so there is nothing left here
    for one courier to own against another.
    """
    print(_ensure_project_dir())


def cmd_teardown(args) -> None:
    """Dead: the legacy per-agent mailbox this used to remove is gone —
    orchard messages are flat, delete-on-read files under a directory
    shared by every session in the project, with nothing owned by one
    courier to tear down. Kept as a documented no-op so an existing
    caller's `teardown` at release does not start erroring."""
    print("teardown: no-op — no owned mailbox to remove")


def cmd_project_dir(args) -> None:
    """This session's orchard project directory — what a courier's Monitor
    watches (agents/courier.md) and what `receive` drains."""
    print(_ensure_project_dir())


def cmd_announce(args) -> None:
    """No longer fans identity into every peer's inbox: the same identity
    snapshot now rides every orchard_topic.py event (its `identity` field,
    see tools/orchard_topic.py._attach_snapshot), so a separate broadcast is
    dead weight — the fan-out this replaced was the token leak. Kept as a
    documented no-op so an existing caller's `announce` at session start
    does not start erroring."""
    print(f"announce: identity no longer fanned out — it rides every "
          f"orchard_topic.py event for {whoami()} instead")


def cmd_depart(args) -> None:
    """Dead: nothing reads a depart broadcast. Kept as a documented no-op
    (rather than removed outright) so an existing caller's `depart` at
    session end does not start erroring."""
    print("depart: no-op — no consumer reads this signal")


def cmd_signal(args) -> None:
    """A lifecycle signal is a push: it carries the data itself, not a
    request for it. Directed at the parent alone, over the orchard transport
    — so a parent living in a different repo (ORCHID_PARENT_PROJECT) can
    receive it too, cross-project allowlist gating applying exactly as it
    does for any other cross-project :session: send. There is no broadcast
    fallback any more: a signal with no known parent (no --to, no
    ORCHID_PARENT_SESSION) is simply not delivered — the fan-out this
    replaced was the token leak. You signal for yourself, always — the
    envelope `from` is the caller's own session, never someone else's.
    """
    if args.notify_user and args.state not in SIGNAL_NOTIFY_STATES:
        args.parser.error(
            f"courier: --notify-user is only legal with --state {'|'.join(SIGNAL_NOTIFY_STATES)}"
        )
    feature = args.feature or identity_of()["feature_id"]
    body = {"kind": "lifecycle", "state": args.state, "feature_id": feature}
    if args.state == "blocked" and args.blocked_on:
        body["blocked_on"] = args.blocked_on

    to = args.to or os.environ.get("ORCHID_PARENT_SESSION") or None
    if not to:
        print(f"signal {args.state} — no parent known, not delivered")
        return

    parent_project = os.environ.get("ORCHID_PARENT_PROJECT") or project_slug()
    ns = argparse.Namespace(
        to=f":session:{to}", subject="orchard:agent:message:content",
        body=json.dumps(body), target_project=parent_project,
        in_reply_to=None, notify_user=args.notify_user,
    )
    env = orchard_send(ns)
    print(f"signal {args.state} -> :session:{to} ({env['id']})")


def _question_envelope(sender: str, to: str, question_id: str, question: str,
                        options: list[str], *, title: str | None = None,
                        summary: str | None = None, multi: bool = False) -> dict:
    """The legacy fan-out envelope `courier.py ask` used to put in every
    peer's inbox (sidebar-polish item 12c; title/summary/multi added round
    2, item 12g; body switched to WIRE GRAMMAR v1's orchid:interrupt:question
    in the bus-message-specifying feature). `cmd_ask` no longer calls this —
    it now sends one directed orchard request to `:session:operator` instead
    of fanning out — but the shape stays, still covered by unit tests and
    available for reuse.

    `body` is `orchid:interrupt:question:<subject>` with `notify_user=True`
    — the one interrupt class `ask` alone may emit (send/broadcast reject a
    hand-sent orchid:interrupt:* outright). question_id/question/options are
    additional envelope-level fields a plain interrupt broadcast never
    carries; sidebar_model.py only reads `body`/`notify_user` and ignores
    them, so this is the SAME message doing double duty, not two messages.
    A reply is matched purely on the existing `in_reply_to` field (see
    _match_answer) — no new field is needed on the answer side.

    title/summary/multi follow the envelope's existing convention: present
    only when set, so a plain single-select ask (the unchanged default) adds
    no new fields to the wire format at all.

    The subject is `title` when one was given, else the raw question text —
    the same choice logic as before the wire-grammar change, minus the
    trailing ellipsis: the orchid:interrupt:question prefix now carries the
    meaning the prose used to.
    """
    subject = title or question
    body = f"orchid:interrupt:question:{subject}"
    env = make_envelope(sender, to, body=body, notify_user=True)
    env["question_id"] = question_id
    env["question"] = question
    env["options"] = options
    if title:
        env["title"] = title
    if summary:
        env["summary"] = summary
    if multi:
        env["multi"] = True
    return env


def _match_answer(box: Path, question_id: str) -> str | None:
    """Non-destructively scan `box` for a reply to `question_id`. Legacy
    (paired with _question_envelope, no longer called by cmd_ask — see
    there); kept for reuse and its own unit-test coverage.

    Only the ONE matching file is consumed (deleted) — every other message
    sitting in this inbox belongs to this session for some other reason and
    is left untouched, exactly like courier.py's own receive() leaves anything
    it does not drain. Returns the reply's `body` (whatever cmd_ask's caller
    put there) or None if no reply has arrived yet.
    """
    if not box.is_dir():
        return None
    for f in sorted(box.glob("*.json")):
        if f.name.startswith("."):
            continue  # atomic-write .partial temp files
        try:
            env = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if env.get("in_reply_to") == question_id:
            f.unlink(missing_ok=True)
            return env.get("body")
    return None


def _await_answer(box: Path, question_id: str, poll_interval: float) -> str:
    """Block until _match_answer finds a reply. No timeout: `ask` is a
    blocking primitive by design (the trial's live round trip needs exactly
    this); the broker script owns all of the deferral/keypress policy, not
    this wait loop (sidebar-polish item 12f)."""
    while True:
        answer = _match_answer(box, question_id)
        if answer is not None:
            return answer
        time.sleep(poll_interval)


def cmd_ask(args) -> None:
    """Directed to the reserved per-repo operator mailbox (`:session:operator`,
    same-project always — no allowlist needed) rather than broadcast to every
    peer: the old fan-out was the token leak. The standalone question-broker
    drains `orchard:agent:message:request` envelopes there and replies
    `:session:<asker>` with `orchard:operator:message:response`, matched via
    the same in_reply_to mechanism `request`/`reply` already use — the
    envelope's own `id` is the identifier the reply answers, no separate
    protocol. `question_id` also rides the body for the broker/popup's own
    bookkeeping, but is not itself what matching keys on.
    """
    if len(args.option) < 2:
        sys.exit("courier: ask requires at least two --option values")
    me = whoami()
    question_id = uuid.uuid4().hex[:12]
    body = {"question_id": question_id, "question": args.question, "options": args.option}
    if args.title:
        body["title"] = args.title
    if args.summary:
        body["summary"] = args.summary
    if args.multi:
        body["multi"] = True

    ns = argparse.Namespace(
        to=":session:operator", subject="orchard:agent:message:request",
        body=json.dumps(body), target_project=None, in_reply_to=None,
        notify_user=False,
    )
    sent = orchard_send(ns)
    print(f"courier: asked the operator; question {question_id}; waiting for an answer",
          file=sys.stderr)

    dir_path = project_dir(project_slug())
    reply = _await_orchard_reply_forever(dir_path, me, sent["id"], args.poll_interval)
    reply_body = reply.get("body")
    print(json.dumps(reply_body) if isinstance(reply_body, (dict, list))
          else ("" if reply_body is None else reply_body))


def _orchid_interrupt_violation(body: str, env: dict) -> str | None:
    """orchid:interrupt:* is illegal everywhere except as the well-formed
    question shape `courier.py ask` itself emits (_question_envelope): unlike
    enforce_orchid_grammar (which bans interrupt outright for hand-sent
    send/broadcast), recorded traffic legitimately contains these, so
    validate checks the shape instead of rejecting the class."""
    rest = body[len("orchid:interrupt:"):]
    subclass, sep, subject = rest.partition(":")
    if subclass != "question" or not sep or not subject:
        return "orchid:interrupt:* must be orchid:interrupt:question:<subject>"
    if not env.get("question_id"):
        return "orchid:interrupt:question message missing question_id"
    return None


def _orchid_traffic_violation(env: dict, body: str) -> str | None:
    cls = _orchid_class(body)
    if cls == "interrupt":
        return _orchid_interrupt_violation(body, env)
    validator = ORCHID_BODY_VALIDATORS.get(cls)
    if validator is None:
        return f"unknown orchid:* class {cls!r}"
    rest = body[len("orchid:"):].partition(":")[2]
    reason = validator(rest)
    if reason:
        return reason
    if cls in NOTIFY_FORBIDDEN_ORCHID_CLASSES and env.get("notify_user"):
        return f"--notify-user is not legal on orchid:{cls}:* bodies"
    return None


def _lifecycle_traffic_violation(env: dict, body: dict) -> str | None:
    state = body.get("state")
    if state not in LIFECYCLE_STATES:
        return f"lifecycle state {state!r} not one of {LIFECYCLE_STATES}"
    if env.get("notify_user") and state not in SIGNAL_NOTIFY_STATES:
        return f"notify_user is not legal on lifecycle state {state!r}"
    return None


def _free_prose_traffic_flag(env: dict) -> tuple[str, str] | None:
    """Free prose (no wire-grammar class, no fixed request, no reply) is only
    legal directed — a broadcast is, at best, legal peer prose flagged for
    the operator's send-path redesign (WARNING), and at worst an unspecified
    summons (VIOLATION) when it carries notify_user: nothing outside
    ask/lifecycle may summon the operator."""
    if env.get("to") != "*":
        return None
    if env.get("notify_user"):
        return "violation", "free-prose broadcast carries notify_user — only ask/lifecycle may summon"
    return "warning", "undirected free-prose broadcast (legal peer prose; send-path redesign candidate)"


def _classify_traffic(env: dict) -> tuple[str, str] | None:
    """None means the envelope is fine. Otherwise (severity, reason), where
    severity is "violation" or "warning". Checked in the order WIRE GRAMMAR v1
    defines the traffic: orchid:* classes, lifecycle pushes, identity/depart
    pushes, fixed requests and replies, then whatever free prose remains."""
    if not isinstance(env, dict):
        return "violation", "envelope is not a JSON object"
    body = env.get("body")
    if isinstance(body, str) and body.startswith("orchid:"):
        reason = _orchid_traffic_violation(env, body)
        return ("violation", reason) if reason else None
    if isinstance(body, dict) and body.get("kind") == "lifecycle":
        reason = _lifecycle_traffic_violation(env, body)
        return ("violation", reason) if reason else None
    if isinstance(body, dict) and "session_id" in body:
        return None
    if isinstance(body, str) and body in FIXED:
        return None
    if env.get("in_reply_to"):
        return None
    return _free_prose_traffic_flag(env)


def _path_envelope_sources(root: Path):
    for f in sorted(root.rglob("*.json")):
        if not f.name.startswith("."):
            yield str(f.relative_to(root)), f.read_text(encoding="utf-8")


def _stdin_envelope_sources():
    for lineno, line in enumerate(sys.stdin, start=1):
        line = line.strip()
        if line:
            yield f"<stdin>:{lineno}", line


def _report(label: str, severity: str, frm: str, reason: str) -> None:
    print(f"{severity.upper()} {label} from={frm}: {reason}")


def cmd_validate(args) -> None:
    """Audit recorded courier traffic against WIRE GRAMMAR v1 (the feature's
    agreed test method: a role's traffic must validate with no unspecified
    message). PATH is an orchard-root directory, read recursively; with no
    PATH, envelopes come JSON-lines from stdin."""
    if args.path:
        root = Path(args.path)
        if not root.is_dir():
            sys.exit(f"courier: validate — no such path {args.path!r}")
        sources = _path_envelope_sources(root)
    else:
        sources = _stdin_envelope_sources()

    total = violations = warnings = 0
    for label, text in sources:
        total += 1
        try:
            env = json.loads(text)
        except json.JSONDecodeError as exc:
            violations += 1
            _report(label, "violation", "?", f"malformed JSON ({exc})")
            continue
        outcome = _classify_traffic(env)
        if outcome is None:
            continue
        severity, reason = outcome
        _report(label, severity, env.get("from", "?"), reason)
        if severity == "violation":
            violations += 1
        else:
            warnings += 1

    print(f"{violations} violation(s), {warnings} warning(s) across {total} envelope(s)")
    sys.exit(1 if violations else 0)


# ---------------------------------------------------------------------------
# orchard transport: flat files + marker heartbeats under
# $XDG_RUNTIME_DIR/orchard/{projects/<repo>.<project>,topics/<name>}/, addressed
# by ":session:<id>" / ":topic:<name>". THE transport — the legacy
# git-common-dir per-agent mailbox this replaced could not coexist with
# worktrees (--git-common-dir is shared by every worktree of a repo, and a
# subagent inherits its parent's CLAUDE_CODE_SESSION_ID, so concurrent
# worktrees resolved to the same box and could delete each other's inbox)
# and was removed outright (operator ruling, 2026-07-27).
# ---------------------------------------------------------------------------

ORCHARD_ADDRESS_RE = re.compile(r"^:(session|topic):(.+)$")
ORCHARD_REGISTRY_PATH = Path.home() / ".config" / "orchids" / "sidebar-registry.json"
ORCHARD_REQUEST_TIMEOUT_S = 30.0
ORCHARD_POLL_INTERVAL_S = 0.5
MONITOR_POLL_INTERVAL_S = 2.0

# The orchard subject list is CLOSED and NOT extensible (operator ruling):
# validation is EXACT MEMBERSHIP against this frozenset — no regex, no
# startswith, no prefix/split matching, no derivation of any kind. A subject
# is known or it is not; if not, reject. Variable data (a subagent id, a
# topic name, ...) never rides the subject — it goes in the body.
ORCHARD_VALID_SUBJECTS = frozenset({
    "orchard:agent:status",
    "orchard:agent:outcome:success",
    "orchard:agent:outcome:fail",
    "orchard:agent:lifecycle:starting",
    "orchard:agent:lifecycle:started",
    "orchard:agent:lifecycle:stopping",
    "orchard:agent:lifecycle:stopped",
    "orchard:agent:delegation:schedule",
    "orchard:agent:delegation:begin",
    "orchard:agent:delegation:end",
    "orchard:bus:subscribe",
    "orchard:bus:unsubscribe",
    "orchard:operator:message:todo",
    "orchard:operator:message:instructions",
    "orchard:operator:message:request",
    "orchard:operator:message:response",
    "orchard:operator:message:content",
    "orchard:agent:message:request",
    "orchard:agent:message:response",
    "orchard:agent:message:content",
    "orchard:task:outcome:completed",
    "orchard:task:outcome:failed",
})

# orchard:task:outcome:* is gardener-only: a task is fully complete only when
# the GARDENER says so. Enforced here too (not just in orchard_topic.py's
# do_post) now that these two subjects are members of the valid set and so
# pass courier.py's own subject check on a hand-sent send/request/reply.
ORCHARD_GARDENER_ONLY_SUBJECTS = frozenset({
    "orchard:task:outcome:completed",
    "orchard:task:outcome:failed",
})


def is_orchard_address(addr: str | None) -> bool:
    return bool(addr) and (addr.startswith(":session:") or addr.startswith(":topic:"))


def parse_orchard_address(addr: str) -> tuple[str, str]:
    match = ORCHARD_ADDRESS_RE.match(addr or "")
    if not match or not match.group(2):
        sys.exit(f"courier: malformed orchard address {addr!r} — expected "
                  ":session:<id> or :topic:<name>")
    return match.group(1), match.group(2)


def _check_path_component(value: str, label: str, *, dot_free: bool = False) -> None:
    if not value or "/" in value or value in (".", ".."):
        sys.exit(f"courier: invalid {label} {value!r}")
    if dot_free and "." in value:
        sys.exit(f"courier: invalid {label} {value!r} — must be dot-free")


def orchard_root() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        sys.exit("courier: XDG_RUNTIME_DIR is unset — no orchard root")
    return Path(runtime) / "orchard"


def project_dir(slug: str) -> Path:
    return orchard_root() / "projects" / slug


def topic_dir(name: str) -> Path:
    return orchard_root() / "topics" / name


_REMOTE_OWNER_REPO_RE = re.compile(r"[:/](?P<owner>[^/:]+)/(?P<repo>[^/]+?)(?:\.git)?/?$")


def _owner_repo_slug(remote_url: str) -> str | None:
    match = _REMOTE_OWNER_REPO_RE.search(remote_url)
    return f"{match.group('owner')}.{match.group('repo')}" if match else None


BRANCH_SEPARATOR = "@"


def _sanitise_branch(branch: str) -> str:
    """A branch name as a single safe path component: `f/close-family-fakes` ->
    `f-close-family-fakes`. Slashes are what force this, but anything outside
    the safe set is folded the same way so no branch name can escape a
    directory or smuggle a separator."""
    return re.sub(r"[^A-Za-z0-9._-]", "-", branch).strip("-") or "detached"


def current_branch() -> str:
    """This WORKTREE's branch, sanitised. A detached HEAD has no branch name,
    so its short SHA stands in — still unique per worktree, which is the only
    property being relied on."""
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch and branch != "HEAD":
        return _sanitise_branch(branch)
    return _sanitise_branch(git("rev-parse", "--short", "HEAD") or "detached")


def project_slug() -> str:
    """`<owner>.<repo>@<branch>` — one orchard project directory PER WORKTREE.

    The repo half prefers the origin remote's owner/repo (stable across clones
    and forks) and falls back to the repo-root directory basename.

    The branch half is what keeps parallel worktrees apart. `--git-common-dir`
    deliberately folds every worktree of a repo to one path, so a slug built
    from it alone is IDENTICAL in every worktree — and worktrees exist precisely
    so several jobs run at once. Without the branch, concurrent features share
    one project directory and their traffic and feature markers pile together
    (operator ruling, 2026-07-27).

    The separator is `@`, not a dot, so the `<owner>.<repo>` shape stays
    splittable on its first dot for display.
    """
    common = git("rev-parse", "--git-common-dir")
    if not common:
        sys.exit("courier: not inside a git repository — no project slug")
    repo_root = Path(common).resolve().parent
    remote = git("remote", "get-url", "origin")
    repo = (_owner_repo_slug(remote) if remote else None) or repo_root.name
    return f"{repo}{BRANCH_SEPARATOR}{current_branch()}"


def _stamp_filename(sid: str) -> str:
    return f"{sid}.{stamp()}.json"


def orchard_deliver(dir_path: Path, sid: str, envelope: dict) -> Path:
    """Atomically write the message, touch/create the marker heartbeat, bump
    the parent dir's mtime (nested writes don't bubble automatically), then
    give the compaction pass a chance to run."""
    dir_path.mkdir(parents=True, exist_ok=True)
    final = dir_path / _stamp_filename(sid)
    tmp = dir_path / f".{final.name}.partial"
    tmp.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    os.replace(tmp, final)
    (dir_path / f"{sid}.marker").touch(exist_ok=True)
    os.utime(dir_path, None)
    maybe_compact(dir_path)
    return final


def make_orchard_envelope(sender: str, to: str, subject: str, *, body=None,
                           in_reply_to=None, repo=None, project=None,
                           notify_user=False, operator_origin=False) -> dict:
    env = {
        "id": uuid.uuid4().hex[:12],
        "ts": datetime.now(timezone.utc).isoformat(),
        "from": sender,
        "to": to,
        "subject": subject,
    }
    if in_reply_to is not None:
        env["in_reply_to"] = in_reply_to
    if repo is not None:
        env["repo"] = repo
    if project is not None:
        env["project"] = project
    if notify_user:
        env["notify_user"] = True
    if operator_origin:
        env["operator_origin"] = True
    if body is not None:
        env["body"] = body
    return env


def _orchard_subject_error(subject: str) -> str | None:
    """EXACT membership only — the orchard subject list is closed and not
    extensible. No startswith, no regex, no split-based derivation: a
    subject is a member of ORCHARD_VALID_SUBJECTS or it is rejected."""
    if subject in ORCHARD_VALID_SUBJECTS:
        return None
    return (f"unknown orchard subject {subject!r} — not in the closed set of "
            f"{len(ORCHARD_VALID_SUBJECTS)} valid subjects")


def _orchard_gardener_only_error(subject: str) -> str | None:
    """orchard:task:outcome:* may only be sent by the gardener — a task is
    fully complete only when the gardener says so."""
    if subject not in ORCHARD_GARDENER_ONLY_SUBJECTS:
        return None
    if identity_of().get("agent_type") == "gardener":
        return None
    return f"{subject!r} may only be sent by the gardener"


def _load_envelope_schema() -> dict:
    path = Path(__file__).resolve().parent / "message.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_violation(env: dict, schema: dict) -> str | None:
    missing = set(schema.get("required", [])) - env.keys()
    if missing:
        return f"envelope missing required field(s): {sorted(missing)}"
    if schema.get("additionalProperties") is False:
        extra = env.keys() - set(schema.get("properties", {}).keys())
        if extra:
            return f"envelope has unknown field(s): {sorted(extra)}"
    return None


def _registry_slugs(path: Path) -> set[str]:
    """Tolerate several reasonable shapes: a bare JSON array of slugs, a dict
    with a `slugs`/`allowed`/`projects` list, or a dict used as a set (truthy
    values keyed by slug). A missing or unparseable file yields no slugs."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if isinstance(data, list):
        return {str(s) for s in data}
    if isinstance(data, dict):
        for key in ("slugs", "allowed", "projects"):
            value = data.get(key)
            if isinstance(value, list):
                return {str(s) for s in value}
        return {k for k, v in data.items() if v}
    return set()


def _authorize_cross_project(target_project: str) -> None:
    if target_project not in _registry_slugs(ORCHARD_REGISTRY_PATH):
        sys.exit(
            f"courier: cross-project send to {target_project!r} denied — not in "
            f"the registry allowlist ({ORCHARD_REGISTRY_PATH})"
        )


def _parse_orchard_body(raw: str | None):
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def orchard_send(args) -> dict:
    """Shared by the `send`, `request`, and `reply` commands: build, validate,
    and deliver one orchard envelope; return it so `request` can capture its
    id to wait on."""
    sender = whoami()
    _check_path_component(sender, "sender session id", dot_free=True)
    subject = getattr(args, "subject", None)
    if not subject:
        sys.exit("courier: orchard send requires --subject")
    reason = _orchard_subject_error(subject)
    if reason:
        sys.exit(f"courier: {reason} — allowed subjects: "
                 f"{', '.join(sorted(ORCHARD_VALID_SUBJECTS))}")
    reason = _orchard_gardener_only_error(subject)
    if reason:
        sys.exit(f"courier: {reason}")

    kind, value = parse_orchard_address(args.to)
    repo = project_slug()
    body = _parse_orchard_body(getattr(args, "body", None))
    from_addr = f":session:{sender}"

    if kind == "session":
        _check_path_component(value, "target session id", dot_free=True)
        target_project = getattr(args, "target_project", None) or repo
        _check_path_component(target_project, "target project slug")
        if target_project != repo:
            _authorize_cross_project(target_project)
        dir_path = project_dir(target_project)
        file_sid = value
        project_field = target_project
    else:
        _check_path_component(value, "topic name")
        dir_path = topic_dir(value)
        file_sid = sender
        project_field = None

    env = make_orchard_envelope(
        from_addr, args.to, subject, body=body,
        in_reply_to=getattr(args, "in_reply_to", None),
        repo=repo, project=project_field,
        notify_user=bool(getattr(args, "notify_user", False)),
        operator_origin=bool(getattr(args, "operator_origin", False)),
    )
    violation = _schema_violation(env, _load_envelope_schema())
    if violation:
        sys.exit(f"courier: {violation}")
    orchard_deliver(dir_path, file_sid, env)
    return env


def orchard_receive_own(*, skip_replies: bool = False) -> list[dict]:
    """This session's personal-mailbox messages, delete-on-read. Skipped
    (returns []) when XDG_RUNTIME_DIR is unset, so a plain `receive` in an
    environment with no orchard root keeps working exactly as before.

    `skip_replies` leaves an envelope carrying `in_reply_to` untouched —
    neither returned nor deleted — instead of consuming it. `_find_orchard_reply`
    and `_match_answer` glob this SAME directory for exactly such an
    envelope while a `request`/`ask` caller blocks on it; a continuously
    running reader (`monitor`) that drained indiscriminately would race
    that waiter and could delete the one reply it is owed before it looks —
    including the operator's own answer to `ask`. Plain one-shot `receive`
    keeps the old, indiscriminate default (`skip_replies=False`): it has no
    waiter of its own to race against attention that already moved to
    consume its output the same turn.
    """
    if not os.environ.get("XDG_RUNTIME_DIR"):
        return []
    sid = whoami()
    dir_path = project_dir(project_slug())
    out = []
    if not dir_path.is_dir():
        return out
    for f in sorted(dir_path.glob(f"{sid}.*.json")):
        if f.name.startswith("."):
            continue
        try:
            env = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            out.append({"type": "malformed", "file": f.name, "error": str(exc)})
            continue
        if skip_replies and env.get("in_reply_to"):
            continue
        out.append(env)
        f.unlink(missing_ok=True)
    return out


class MonitorSource(NamedTuple):
    """One watchable mailbox, filtered in two stages that must never be
    confused:

    WATCH-STAGE selectivity (`directory`, `path_filter`) happens at the
    kernel, via `inotifywait --include` matching a file's full path — cheap,
    but limited to what a filename can say. This is what direct addressing
    (`:session:<id>`) uses: the recipient id IS the filename prefix, so
    filtering by path is exact and sufficient — every message that reaches
    this stage already belongs to this session.

    PARSE-STAGE selectivity (`subject_filter`) happens after `read()` has
    parsed an envelope, because a subject lives INSIDE the file, not in its
    path — no filename pattern can express it. Direct mail leaves this
    empty (everything addressed to this session is its own, by
    definition); a topic subscription — not implemented here, only shaped
    for — would use a non-empty set, since subscribing yields everything
    published on the topic and the subject is what narrows it to what this
    session actually asked for. Empty means "no narrowing: pass whatever
    reached parsing."

    `read()` is the one place an envelope is built and consumed
    (`orchard_receive_own` for the mailbox source below) — never
    reinvented per source.
    """
    directory: Path
    path_filter: str
    subject_filter: frozenset[str]
    read: Callable[[], list[dict]]


def _own_mailbox_path_filter(sid: str) -> str:
    """Cuts the obvious noise in the project directory: a sibling session's
    message files, and this session's own `<sid>.marker` heartbeat.
    `inotifywait --include` matches the FULL PATH, not the bare filename, so
    the pattern is unanchored at the start; verified empirically to fire for
    `<sid>.<ts>.json` and not for `<sid>.marker`, `<other-sid>.<ts>.json`, or
    `<other-sid>.marker`."""
    return rf"/{re.escape(sid)}\..*\.json$"


def _own_mailbox_source() -> MonitorSource:
    """Direct mail: addressed to this session by id, so watch-stage
    filtering is exact and there is nothing left for parse-stage filtering
    to narrow. `skip_replies=True` (orchard_receive_own, above) is load-
    bearing here, not cosmetic: `monitor` runs continuously, so without it
    it would race a blocked `request`/`ask` waiter for the one reply file
    that answers it — including the operator's own answer — and could
    delete it first, leaving that caller hanging forever."""
    sid = whoami()
    return MonitorSource(
        _ensure_project_dir(), _own_mailbox_path_filter(sid), frozenset(),
        lambda: orchard_receive_own(skip_replies=True),
    )


def _monitor_sources() -> list[MonitorSource]:
    """Today: just this session's own project-directory mailbox. A
    subscribed topic folder (`orchard/topics/<name>/<sessionid>/`) is a
    second entry in this list, not a reason to change this function's
    shape, `MonitorSource`, or the watch loop below."""
    return [_own_mailbox_source()]


def _passes_subject_filter(env: dict, subject_filter: frozenset[str]) -> bool:
    return not subject_filter or env.get("subject") in subject_filter


def _drain_and_print(source: MonitorSource) -> None:
    for env in source.read():
        if _passes_subject_filter(env, source.subject_filter):
            print(json.dumps(env), flush=True)


def _drain_all(sources: list[MonitorSource]) -> None:
    for source in sources:
        _drain_and_print(source)


def _spawn_inotifywait(source: MonitorSource) -> subprocess.Popen:
    command = [
        "inotifywait", "-m", "-e", "create", "-e", "moved_to",
        "--include", source.path_filter, "--format", "%f", str(source.directory),
    ]
    return subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1,
    )


def _inotify_watch_is_armed(pid: int) -> bool:
    """True once `pid`'s inotify fd shows an established watch descriptor
    (a `wd:` line in its fdinfo) — the kernel is now watching, so any file
    created from this instant on is guaranteed to raise an event. Before
    this, a file this process's watch was meant to see can slip past
    unnoticed and un-eventful."""
    try:
        fds = list(Path(f"/proc/{pid}/fd").iterdir())
    except OSError:
        return False
    for fd in fds:
        try:
            if "inotify" not in os.readlink(fd):
                continue
            if "wd:" in Path(f"/proc/{pid}/fdinfo/{fd.name}").read_text():
                return True
        except OSError:
            continue
    return False


def _await_inotify_armed(process: subprocess.Popen, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and process.poll() is None:
        if _inotify_watch_is_armed(process.pid):
            return
        time.sleep(0.005)


def _watch_source_forever(source: MonitorSource, sources: list[MonitorSource],
                           processes: list[subprocess.Popen]) -> None:
    while True:
        process = _spawn_inotifywait(source)
        processes.append(process)
        _await_inotify_armed(process)
        # Closes the startup race: a file created between spawning this
        # watcher and its watch actually going live raises no kernel event
        # (the watch was not yet armed to see it) and would otherwise sit
        # forever unless some UNRELATED later event happened to trigger a
        # drain. This catch-up drain is unconditional and state-based, so
        # it picks up exactly such a file regardless of when it landed.
        _drain_all(sources)
        for _line in process.stdout:
            _drain_all(sources)
        process.wait()


def _kill_children(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass


def _monitor_inotify(sources: list[MonitorSource]) -> None:
    """ONE `inotifywait` watcher PER SOURCE, each with its own exact
    `--include` filter — `--include` is a single global regex per
    invocation, so a source with a different directory and pattern (a
    subscribed topic folder, one day) cannot share a process with this one
    without widening the filter and letting noise back in. Every watcher
    feeds the same drain: whichever one fires, every source's mailbox is
    drained (the existing wholesale-drain rule), so which source fired is
    never load-bearing.

    On SIGTERM — how the courier's Monitor teardown ends this process —
    every watcher this instance spawned is killed before exit, so nothing
    is ever left behind for the charter to have to hunt down process by
    process."""
    processes: list[subprocess.Popen] = []
    signal.signal(signal.SIGTERM, lambda *_args: sys.exit(0))
    try:
        threads = [
            threading.Thread(target=_watch_source_forever, args=(source, sources, processes), daemon=True)
            for source in sources
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        _kill_children(processes)


def _monitor_poll(sources: list[MonitorSource], poll_interval: float) -> None:
    while True:
        time.sleep(poll_interval)
        _drain_all(sources)


def _find_orchard_reply(dir_path: Path, sid: str, request_id: str) -> dict | None:
    if not dir_path.is_dir():
        return None
    for f in sorted(dir_path.glob(f"{sid}.*.json")):
        if f.name.startswith("."):
            continue
        try:
            env = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if env.get("in_reply_to") == request_id:
            f.unlink(missing_ok=True)
            return env
    return None


def _wait_for_orchard_activity(dir_path: Path, budget: float) -> None:
    if shutil.which("inotifywait"):
        try:
            subprocess.run(
                ["inotifywait", "-q", "-t", str(max(1, int(round(budget)))),
                 "-e", "create", "-e", "moved_to", str(dir_path)],
                capture_output=True, text=True, timeout=budget + 5,
            )
            return
        except (subprocess.TimeoutExpired, OSError):
            return
    time.sleep(min(ORCHARD_POLL_INTERVAL_S, budget))


def _await_orchard_reply(dir_path: Path, sid: str, request_id: str, timeout: float) -> dict | None:
    """Bounded wait for exactly the one reply this request is owed — one
    waiter per request, never a broadcast fan-out like the old `ask`."""
    dir_path.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        reply = _find_orchard_reply(dir_path, sid, request_id)
        if reply is not None:
            return reply
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        _wait_for_orchard_activity(dir_path, remaining)


def _await_orchard_reply_forever(dir_path: Path, sid: str, request_id: str,
                                  poll_interval: float) -> dict:
    """Unbounded twin of _await_orchard_reply: `ask` blocks until answered,
    by design (the operator may be away; there is no timeout to give up on)."""
    dir_path.mkdir(parents=True, exist_ok=True)
    while True:
        reply = _find_orchard_reply(dir_path, sid, request_id)
        if reply is not None:
            return reply
        _wait_for_orchard_activity(dir_path, poll_interval)


def cmd_request(args) -> None:
    kind, _value = parse_orchard_address(args.to)
    if kind != "session":
        sys.exit("courier: request --to must be :session:<id>")
    sent = orchard_send(args)
    dir_path = project_dir(project_slug())
    reply = _await_orchard_reply(dir_path, whoami(), sent["id"], ORCHARD_REQUEST_TIMEOUT_S)
    if reply is None:
        sys.exit(f"courier: request timed out after {ORCHARD_REQUEST_TIMEOUT_S:.0f}s "
                 f"waiting for a reply to {sent['id']}")
    body = reply.get("body")
    print(json.dumps(body) if isinstance(body, (dict, list)) else ("" if body is None else body))


def cmd_reply(args) -> None:
    kind, _value = parse_orchard_address(args.to)
    if kind != "session":
        sys.exit("courier: reply --to must be :session:<id>")
    orchard_send(args)


def main() -> None:
    p = argparse.ArgumentParser(description="repo-scoped agent message courier")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("whoami").set_defaults(func=lambda a: print(whoami()))
    sub.add_parser("init").set_defaults(func=cmd_init)
    sub.add_parser("teardown").set_defaults(func=cmd_teardown)
    sub.add_parser("receive").set_defaults(func=cmd_receive)
    s = sub.add_parser("monitor")
    s.add_argument("--poll-interval", dest="poll_interval", type=float, default=MONITOR_POLL_INTERVAL_S,
                   help="seconds between drains when inotifywait is unavailable "
                        f"(default {MONITOR_POLL_INTERVAL_S})")
    s.set_defaults(func=cmd_monitor)
    sub.add_parser("project-dir").set_defaults(func=cmd_project_dir)
    sub.add_parser("announce").set_defaults(func=cmd_announce)
    sub.add_parser("depart").set_defaults(func=cmd_depart)
    sub.add_parser("identity").set_defaults(
        func=lambda a: print(json.dumps(identity_of(), indent=2)))
    sub.add_parser("status").set_defaults(
        func=lambda a: print(json.dumps(status_of(), indent=2)))

    def msg_args(s):
        # --from is accepted but IGNORED — orchard always derives the sender
        # from whoami() (orchard_send). Kept only so an existing caller that
        # still passes it (e.g. hooks/courier-end.sh's self-wake send) does
        # not start hitting an argparse "unrecognized arguments" error.
        s.add_argument("--from", dest="sender", required=False, default=None)
        s.add_argument("--body")
        s.add_argument("--notify-user", dest="notify_user", action="store_true",
                       help="the sending agent intends this for the user to see")
        s.add_argument("--operator-origin", dest="operator_origin", action="store_true",
                       help="the message originates from the operator")
        return s

    s = msg_args(sub.add_parser("send"))
    s.add_argument("--to", required=True, help=":session:<id> or :topic:<name>")
    s.add_argument("--in-reply-to", dest="in_reply_to")
    s.add_argument("--subject", help="orchard wire-grammar subject; required")
    s.add_argument("--target-project", dest="target_project",
                    help="cross-project slug for a :session: send outside the "
                         "sender's own project")
    s.set_defaults(func=cmd_send, parser=s)

    s = msg_args(sub.add_parser("broadcast"))
    s.set_defaults(func=cmd_broadcast, to=None, in_reply_to=None, parser=s)

    s = sub.add_parser("request")
    s.add_argument("--to", required=True, help=":session:<id>")
    s.add_argument("--subject", required=True)
    s.add_argument("--body")
    s.add_argument("--target-project", dest="target_project")
    s.set_defaults(func=cmd_request, parser=s, in_reply_to=None)

    s = sub.add_parser("reply")
    s.add_argument("--to", required=True, help=":session:<id>")
    s.add_argument("--in-reply-to", dest="in_reply_to", required=True)
    s.add_argument("--subject", required=True)
    s.add_argument("--body")
    s.add_argument("--target-project", dest="target_project")
    s.set_defaults(func=cmd_reply, parser=s)

    s = sub.add_parser("signal")
    s.add_argument("--state", required=True, choices=LIFECYCLE_STATES)
    s.add_argument("--feature")
    s.add_argument("--to")
    s.add_argument("--blocked-on", dest="blocked_on", choices=BLOCKED_ON_STATES,
                   help="only meaningful with --state blocked: what the block is "
                        "on (component, the default sidebar assumption, or agent, "
                        "a peer awaited)")
    s.add_argument("--notify-user", dest="notify_user", action="store_true",
                   help="the sending agent intends this for the user to see")
    s.set_defaults(func=cmd_signal, parser=s)

    s = sub.add_parser("ask")
    s.add_argument("--question", required=True)
    s.add_argument("--option", dest="option", action="append", required=True,
                   help="an answer choice, numbered by the order given; repeat "
                        "for each option (at least two required)")
    s.add_argument("--multi", action="store_true",
                   help="multi-select: digits TOGGLE membership instead of "
                        "committing instantly, Enter confirms the current "
                        "selection; answer becomes "
                        '{"indices": [...], "options": [...]}. Default '
                        "(unset) is single-select, unchanged: instant-on-digit, "
                        '{"index": N, "option": "..."}')
    s.add_argument("--title", help="short title shown prominently above the "
                                    "question in the popup (optional)")
    s.add_argument("--summary", help="short summary of what the decision is "
                                      "about, shown below the title (optional)")
    s.add_argument("--poll-interval", dest="poll_interval", type=float, default=1.0,
                   help="seconds between checks for the answer while blocked "
                        "(default 1.0) — polling cadence only, not a timeout: "
                        "ask never gives up on its own")
    s.set_defaults(func=cmd_ask)

    s = sub.add_parser("validate")
    s.add_argument("path", nargs="?", default=None,
                    help="orchard-root directory to audit recursively; omit to "
                         "read JSON-lines envelopes from stdin")
    s.set_defaults(func=cmd_validate)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

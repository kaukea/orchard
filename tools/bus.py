#!/usr/bin/env python3
"""Repo-scoped agent message bus.

The envelope lives here and nowhere else. Agents never construct or parse a
message: the bus sidecar shells out to this script on both send and receive, so
the format cannot drift across prompts and cannot be got wrong by an agent
following prose.

Layout (uncommittable, git-common-dir, so every worktree of the repo shares it):

    <git-common-dir>/the-works/bus/<session-id>/<datetime>.json

The set of folders IS the registry — an agent exists for messaging purposes iff
its folder does. A SessionEnd hook removes it, so sending to an agent that has
finished fails immediately rather than writing into a folder nobody watches.

Messages are ephemeral and deleted on consumption, so receiving is "take what is
there", with no bookkeeping. There is NO delivery guarantee: a sender expects no
answer and decides for itself whether to retry, abandon, or error.

Identity is the session id, read from the environment. It is not derived from
location: two sessions can share a directory, and a subagent inherits its
parent's environment verbatim — which is deliberate, since a bus sidecar must
resolve to its PARENT's inbox.

Usage:
  bus.py whoami                                this session's id
  bus.py init [id]                             create an inbox
  bus.py teardown [id]                         remove it (session end)
  bus.py list                                  registry: one agent id per line
  bus.py send --from A --to B [--body X] [--notify-user] [--in-reply-to ID]
  bus.py broadcast --from A [--body X] [--notify-user]
  bus.py receive [id]                          drain: JSON array, oldest first
  bus.py identity                              immutable facts about this session
  bus.py status                                mutable state: occupancy and spend
  bus.py announce [--exit-grace-seconds N]     broadcast identity (session start);
                                                N = seconds this agent needs to
                                                finish + exit once it starts
                                                leaving (default 10)
  bus.py depart                                broadcast departure (session end)
  bus.py signal --state S [--to ID]            lifecycle push (to parent, else broadcast)
  bus.py signal --state S --on-behalf-of ID     same, but `from` is ID, not the caller —
                                                orchestrator-only, for signaling a
                                                killed agent's own terminal state
  bus.py root                                  print the bus root
"""
import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

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


def git(*args: str) -> str:
    """Run a git command, returning '' rather than raising outside a repo."""
    try:
        done = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return done.stdout.strip()


def bus_root() -> Path:
    common = git("rev-parse", "--git-common-dir")
    if not common:
        sys.exit("bus: not inside a git repository — no bus root")
    return Path(common).resolve() / "the-works" / "bus"


def whoami() -> str:
    """This session's id, straight from the environment.

    Every session has one and can read its own. A subagent inherits its parent's,
    which is what lets a bus sidecar find its parent's inbox without being told.
    """
    session = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    if not session:
        sys.exit("bus: CLAUDE_CODE_SESSION_ID is unset — not inside an agent session")
    return session


def inbox(agent_id: str) -> Path:
    if not agent_id or "/" in agent_id or agent_id.startswith("."):
        sys.exit(f"bus: invalid agent id {agent_id!r}")
    return bus_root() / agent_id


def stamp() -> str:
    # sortable and readable; ':' avoided so the name is portable
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S.%f")


def deliver(target: Path, envelope: dict) -> None:
    """Write atomically: a watcher must never observe a half-written message."""
    target.mkdir(parents=True, exist_ok=True)
    final = target / f"{stamp()}.json"
    tmp = target / f".{final.name}.partial"
    tmp.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    os.replace(tmp, final)          # atomic; fires the watcher's moved_to


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


DEFAULT_EXIT_GRACE_SECONDS = 10


def identity_of(exit_grace_seconds: int = DEFAULT_EXIT_GRACE_SECONDS) -> dict:
    """Immutable facts, fixed for this session's whole life.

    Model and effort are deliberately absent: they can change mid-session, so they
    are not identity, and pinning them here would bake in a value that goes stale.

    `exit_grace_seconds` is the one exception to "immutable" in spirit rather than
    mechanism: an agent declares it once, at announce time, as how long it needs
    to send its two closing messages and exit after it starts finishing — the
    orchestrator's lifecycle contract (docs/TODO.md.d/sidebar-polish.md item 2)
    grants this instead of the default 10s before killing the process.
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
        # Human name = feature id with '-' → spaces; derived once here so the sidebar
        # and any bash consumer read one field instead of re-deriving (Decision-032).
        "name": feature_id.replace("-", " ") if feature_id else None,
        "parent_session": os.environ.get("ORCHID_PARENT_SESSION") or None,
        "exit_grace_seconds": exit_grace_seconds,
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


def envelope_of(args, to: str) -> dict:
    return make_envelope(
        args.sender, to,
        body=getattr(args, "body", None),
        notify_user=bool(getattr(args, "notify_user", False)),
        operator_origin=bool(getattr(args, "operator_origin", False)),
        in_reply_to=getattr(args, "in_reply_to", None),
    )


def fan_out(sender: str, envelope_for) -> int:
    root = bus_root()
    if not root.is_dir():
        return 0
    peers = [d for d in sorted(root.iterdir()) if d.is_dir() and d.name != sender]
    for peer in peers:
        deliver(peer, envelope_for(peer.name))
    return len(peers)


def cmd_send(args) -> None:
    target = inbox(args.to)
    if not target.is_dir():
        sys.exit(f"bus: no such agent {args.to!r} (no inbox) — it has finished or never started")
    deliver(target, envelope_of(args, args.to))


def cmd_broadcast(args) -> None:
    if not bus_root().is_dir():
        sys.exit("bus: no bus root — nothing to broadcast to")
    # every copy is addressed to `*`, though each lands in a specific peer's folder
    reached = fan_out(args.sender, lambda name: envelope_of(args, "*"))
    print(f"broadcast to {reached} agent(s)")


def cmd_receive(args) -> None:
    box = inbox(args.agent_id)
    out = []
    if box.is_dir():
        for f in sorted(box.glob("*.json")):        # lexical == chronological
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError) as exc:
                # left on disk deliberately: a malformed envelope is evidence, and
                # deleting it would destroy the only copy of the thing to debug
                out.append({"type": "malformed", "file": f.name, "error": str(exc)})
                continue
            f.unlink(missing_ok=True)               # ephemeral: consumed is gone
    print(json.dumps(out, indent=2))


def cmd_init(args) -> None:
    box = inbox(args.agent_id)
    box.mkdir(parents=True, exist_ok=True)
    print(box)


def cmd_teardown(args) -> None:
    box = inbox(args.agent_id)
    if box.is_dir():
        for f in box.iterdir():
            f.unlink(missing_ok=True)
        box.rmdir()
    print(f"removed {box}")


def cmd_list(args) -> None:
    root = bus_root()
    if root.is_dir():
        for d in sorted(root.iterdir()):
            if d.is_dir():
                print(d.name)


def announcement(body: dict, sender: str):
    # a push, not a request: broadcast (to `*`) carrying the data itself, so a
    # receiving sidecar records it. No id-tag — the body IS the payload.
    def build(to: str) -> dict:
        return make_envelope(sender, "*", body=body)
    return build


def cmd_announce(args) -> None:
    me = whoami()
    inbox(me).mkdir(parents=True, exist_ok=True)
    reached = fan_out(me, announcement(identity_of(args.exit_grace_seconds), me))
    print(f"announced to {reached} agent(s)")


def cmd_depart(args) -> None:
    me = whoami()
    reached = fan_out(me, announcement({"session_id": me}, me))
    print(f"departure sent to {reached} agent(s)")


def cmd_signal(args) -> None:
    """A lifecycle signal is a push, like announce/depart: it carries the data
    itself, not a request for it. Directed at the parent when its inbox is
    known and live, so only the conductor acts on it; broadcast otherwise, so
    the signal is not silently lost.

    `--on-behalf-of` is the one exception to "you signal for yourself": the
    orchestrator's exit-grace enforcement (docs/TODO.md.d/sidebar-polish.md
    item 2) kills an agent that overran its declared grace period, and the
    killed process can no longer send its own terminal signal — the
    orchestrator sends it FOR it, `from` set to the killed session's id, so
    the sidebar's evict-on-observed-terminal-signal logic still fires on that
    agent's own row (attribution there is strictly by envelope `from`).
    """
    sender = args.on_behalf_of or whoami()
    feature = args.feature or identity_of()["feature_id"]
    body = {"kind": "lifecycle", "state": args.state, "feature_id": feature}
    if args.state == "blocked" and args.blocked_on:
        body["blocked_on"] = args.blocked_on
    to = args.to or os.environ.get("ORCHID_PARENT_SESSION") or None
    if to and inbox(to).is_dir():
        deliver(inbox(to), make_envelope(sender, to, body=body, notify_user=args.notify_user))
        print(f"signal {args.state} -> {to}")
        return
    reached = fan_out(sender, lambda name: make_envelope(sender, "*", body=body,
                                                          notify_user=args.notify_user))
    print(f"signal {args.state} broadcast to {reached} agent(s)")


def main() -> None:
    p = argparse.ArgumentParser(description="repo-scoped agent message bus")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, fn in (("init", cmd_init), ("teardown", cmd_teardown),
                     ("receive", cmd_receive)):
        s = sub.add_parser(name)
        s.add_argument("agent_id", nargs="?", default=None)
        s.set_defaults(func=fn)

    sub.add_parser("whoami").set_defaults(func=lambda a: print(whoami()))
    sub.add_parser("list").set_defaults(func=cmd_list)
    sub.add_parser("root").set_defaults(func=lambda a: print(bus_root()))
    s = sub.add_parser("announce")
    s.add_argument("--exit-grace-seconds", dest="exit_grace_seconds", type=int,
                   default=DEFAULT_EXIT_GRACE_SECONDS,
                   help="seconds this agent needs, after it starts finishing, to "
                        "send its two closing messages and exit before the "
                        "orchestrator kills it (default 10)")
    s.set_defaults(func=cmd_announce)
    sub.add_parser("depart").set_defaults(func=cmd_depart)
    sub.add_parser("identity").set_defaults(
        func=lambda a: print(json.dumps(identity_of(), indent=2)))
    sub.add_parser("status").set_defaults(
        func=lambda a: print(json.dumps(status_of(), indent=2)))

    def msg_args(s):
        s.add_argument("--from", dest="sender", required=True)
        s.add_argument("--body")
        s.add_argument("--notify-user", dest="notify_user", action="store_true",
                       help="the sending agent intends this for the user to see")
        s.add_argument("--operator-origin", dest="operator_origin", action="store_true",
                       help="the message originates from the operator")
        return s

    s = msg_args(sub.add_parser("send"))
    s.add_argument("--to", required=True)
    s.add_argument("--in-reply-to", dest="in_reply_to")
    s.set_defaults(func=cmd_send)

    s = msg_args(sub.add_parser("broadcast"))
    s.set_defaults(func=cmd_broadcast, to=None, in_reply_to=None)

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
    s.add_argument("--on-behalf-of", dest="on_behalf_of", metavar="SESSION_ID",
                   help="signal as this session id instead of the caller — the "
                        "orchestrator's escape hatch to broadcast an `abandoned` "
                        "terminal signal for an agent it just killed after its "
                        "exit-grace period ran out, so the sidebar still evicts it")
    s.set_defaults(func=cmd_signal)

    args = p.parse_args()
    if getattr(args, "agent_id", "sentinel") is None:
        args.agent_id = whoami()
    args.func(args)


if __name__ == "__main__":
    main()

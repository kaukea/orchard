#!/usr/bin/env python3
"""The courier's boxes — scenario inbox-outbox of the courier rebuild.

One logical OUTBOX where a sender puts every outgoing message, one logical
INBOX that is the sole receiving surface, UDP semantics throughout: a message
is deleted the moment it is received. Boxes are common filtered places, never
per-agent folders. Strict envelope both ways; the delivery dispatch
(tools/dispatch.py) is the only mover. Specification: docs/courier-wire.md
§2c; tests: docs/testing/01-inbox-outbox.md.
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


SUBJECTS = frozenset((
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
    "orchard:agent:message:request",
    "orchard:agent:message:response",
    "orchard:agent:message:content",
    "orchard:bus:subscribe",
    "orchard:bus:unsubscribe",
    "orchard:operator:message:todo",
    "orchard:operator:message:instructions",
    "orchard:operator:message:request",
    "orchard:operator:message:response",
    "orchard:operator:message:content",
    "orchard:task:outcome:completed",
    "orchard:task:outcome:failed",
))

SESSION_ADDRESS = re.compile(r"^:session:([A-Za-z0-9_-]+)$")
REQUIRED_FIELDS = ("from", "to", "subject")
OPTIONAL_FIELDS = ("body",)
TMP_PREFIX = ".tmp-"


class EnvelopeError(ValueError):
    """An envelope that deviates from the wire. Rejected, never coerced."""


def boxes_root(env: dict) -> Path:
    runtime = env.get("XDG_RUNTIME_DIR")
    if not runtime:
        raise EnvelopeError("XDG_RUNTIME_DIR is unset — the boxes have no home")
    return Path(runtime) / "orchard" / "boxes"


def outbox_dir(env: dict) -> Path:
    return boxes_root(env) / "outbox"


def inbox_dir(env: dict) -> Path:
    return boxes_root(env) / "inbox"


def quarantine_dir(env: dict) -> Path:
    return boxes_root(env) / "quarantine"


def session_id_of(address: str) -> str:
    match = SESSION_ADDRESS.match(address)
    if not match:
        raise EnvelopeError(f"not a :session: address: {address!r}")
    return match.group(1)


def validate_envelope(envelope: object) -> dict:
    if not isinstance(envelope, dict):
        raise EnvelopeError("envelope is not an object")
    for field in REQUIRED_FIELDS:
        if field not in envelope:
            raise EnvelopeError(f"missing required field: {field}")
    allowed = set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    extras = set(envelope) - allowed
    if extras:
        raise EnvelopeError(f"unknown fields: {sorted(extras)}")
    session_id_of(envelope["from"])
    session_id_of(envelope["to"])
    if envelope["subject"] not in SUBJECTS:
        raise EnvelopeError(f"unknown subject: {envelope['subject']!r}")
    if "body" in envelope and not isinstance(envelope["body"], str):
        raise EnvelopeError("body is not a string")
    return envelope


def make_envelope(sender_sid: str, to: str, subject: str, body: str | None = None) -> dict:
    envelope = {"from": f":session:{sender_sid}", "to": to, "subject": subject}
    if body is not None:
        envelope["body"] = body
    return validate_envelope(envelope)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%f")


def message_name(sid: str) -> str:
    return f"{sid}.{_timestamp()}.{uuid.uuid4().hex[:8]}.json"


def write_atomic(directory: Path, name: str, envelope: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    tmp = directory / f"{TMP_PREFIX}{name}"
    tmp.write_text(json.dumps(envelope, sort_keys=True))
    final = directory / name
    tmp.rename(final)
    return final


def put_outbox(envelope: dict, env: dict) -> Path:
    validate_envelope(envelope)
    sender = session_id_of(envelope["from"])
    return write_atomic(outbox_dir(env), message_name(sender), envelope)


def receive(sid: str, env: dict) -> list[dict]:
    inbox = inbox_dir(env)
    if not inbox.is_dir():
        return []
    received = []
    for path in sorted(inbox.glob(f"{sid}.*.json")):
        received.append(json.loads(path.read_text()))
        path.unlink()
    return received


def main(argv: list[str], env: dict) -> int:
    parser = argparse.ArgumentParser(prog="boxes.py")
    commands = parser.add_subparsers(dest="command", required=True)
    send = commands.add_parser("send")
    send.add_argument("--from-sid", required=True)
    send.add_argument("--to", required=True)
    send.add_argument("--subject", required=True)
    send.add_argument("--body", help="literal body; '-' reads the body from stdin")
    drain = commands.add_parser("receive")
    drain.add_argument("--sid", required=True)
    args = parser.parse_args(argv)

    if args.command == "send":
        body = sys.stdin.read() if args.body == "-" else args.body
        try:
            path = put_outbox(
                make_envelope(args.from_sid, args.to, args.subject, body), env,
            )
        except EnvelopeError as error:
            print(f"boxes: rejected: {error}", file=sys.stderr)
            return 1
        print(path)
        return 0
    print(json.dumps(receive(args.sid, env)))
    return 0


if __name__ == "__main__":  # pragma: no cover — exercised by the seam test
    import os
    sys.exit(main(sys.argv[1:], dict(os.environ)))

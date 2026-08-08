#!/usr/bin/env python3
"""The delivery dispatch — the component that moves messages between boxes.

Drains the common outbox oldest-first: a valid envelope is atomically renamed
into the inbox under the RECIPIENT's key (the move is both the delivery and
the outbox deletion); anything unreadable or off-schema is moved verbatim to
quarantine — its presence means something bypassed the sanctioned path.
One-to-one only in this scenario. Specification: docs/courier-wire.md §2c.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from boxes import (  # noqa: E402
    EnvelopeError,
    TMP_PREFIX,
    inbox_dir,
    outbox_dir,
    quarantine_dir,
    session_id_of,
    validate_envelope,
)


def _quarantine(path: Path, env: dict) -> None:
    quarantine = quarantine_dir(env)
    quarantine.mkdir(parents=True, exist_ok=True)
    path.rename(quarantine / path.name)


def _deliver(path: Path, envelope: dict, env: dict) -> None:
    recipient = session_id_of(envelope["to"])
    inbox = inbox_dir(env)
    inbox.mkdir(parents=True, exist_ok=True)
    remainder = path.name.split(".", 1)[1]
    path.rename(inbox / f"{recipient}.{remainder}")


def dispatch_once(env: dict) -> dict:
    stats = {"delivered": 0, "quarantined": 0}
    outbox = outbox_dir(env)
    if not outbox.is_dir():
        return stats
    for path in sorted(outbox.glob("*.json")):
        if path.name.startswith(TMP_PREFIX):
            continue
        try:
            envelope = validate_envelope(json.loads(path.read_text()))
        except (json.JSONDecodeError, EnvelopeError):
            _quarantine(path, env)
            stats["quarantined"] += 1
            continue
        _deliver(path, envelope, env)
        stats["delivered"] += 1
    return stats


def main(argv: list[str], env: dict) -> int:
    if argv != ["once"]:
        print("dispatch: the only command is: once", file=sys.stderr)
        return 2
    print(json.dumps(dispatch_once(env)))
    return 0


if __name__ == "__main__":  # pragma: no cover — exercised by the seam test
    import os
    sys.exit(main(sys.argv[1:], dict(os.environ)))

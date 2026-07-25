#!/usr/bin/env python3
"""Archive-and-sweep old telemetry out of the live orchard message tree.

Message files live under directories like
`$XDG_RUNTIME_DIR/orchard/projects/<repo>.<project>/` and
`$XDG_RUNTIME_DIR/orchard/topics/<name>/`, named `<sessionid>.<ts>.json` where
`ts` is the courier/topic `stamp()` format (`%Y-%m-%dT%H-%M-%S.%f`, UTC).
`<sessionid>.marker` files live alongside them and are never touched here.

That tree is tmpfs (`$XDG_RUNTIME_DIR`) — nothing there survives a reboot, and
telemetry the operator keeps around for another project must not live only
there. `maybe_compact()` is meant to be called by a courier after each
message write: cheap on the hot path (a single sentinel-file mtime check),
and only when that sentinel is stale does it sweep the directory, moving any
message older than `COMPACT_AGE_SECONDS` into a persistent zip archive under
`$XDG_CACHE_HOME/orchard/archives/` (falling back to `~/.cache/...`) and
removing it from the live directory. Nothing is ever destroyed — only moved
from tmpfs into the persistent archive.
"""

from __future__ import annotations

import os
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Overridable via env (trivial, so exposed) — otherwise these constants stand.
COMPACT_AGE_SECONDS = int(os.environ.get("ORCHARD_COMPACT_AGE_SECONDS", 7200))
COMPACT_CHECK_INTERVAL = int(os.environ.get("ORCHARD_COMPACT_CHECK_INTERVAL", 600))

SENTINEL_NAME = ".compacted"
TS_FORMAT = "%Y-%m-%dT%H-%M-%S.%f"


def _parse_ts(filename: str) -> datetime | None:
    """Pull the ts out of `<sessionid>.<ts>.json`; None on anything odd.

    The sessionid is dot-free, so the ts is everything after the first '.'
    up to the trailing '.json'. Never raises — an unparseable name is simply
    skipped by the caller.
    """
    if not filename.endswith(".json"):
        return None
    stem = filename[: -len(".json")]
    session_id, sep, ts_str = stem.partition(".")
    if not sep:
        return None
    try:
        return datetime.strptime(ts_str, TS_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _archive_root() -> Path:
    cache_home = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache_home) if cache_home else Path.home() / ".cache"
    return base / "orchard" / "archives"


def _sanitize_dir(dir_path: Path) -> str:
    """A source directory's resolved path, flattened into one path-safe token."""
    resolved = str(dir_path.resolve()).strip("/")
    return resolved.replace("/", "__") or "root"


def _archive_zip_path(dir_path: Path) -> Path:
    """One zip per source-dir per UTC day, so a whole day's sweeps append
    into a single archive instead of proliferating."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return _archive_root() / f"{_sanitize_dir(dir_path)}.{day}.zip"


def _arcname(dir_path: Path, message: Path) -> str:
    """Path inside the zip that keeps the message's origin dir + filename."""
    return f"{_sanitize_dir(dir_path)}/{message.name}"


def _stale_messages(dir_path: Path, cutoff: datetime) -> list[Path]:
    stale = []
    for f in sorted(dir_path.glob("*.json")):
        if f.name.startswith("."):
            continue  # in-progress atomic-write temp files
        ts = _parse_ts(f.name)
        if ts is None or ts >= cutoff:
            continue
        stale.append(f)
    return stale


def _archive_and_remove(dir_path: Path, stale: list[Path]) -> None:
    zip_path = _archive_zip_path(dir_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as zf:
        existing = set(zf.namelist())
        for message in stale:
            try:
                data = message.read_bytes()
            except OSError:
                continue  # vanished mid-sweep — nothing to archive or remove
            arcname = _arcname(dir_path, message)
            if arcname not in existing:
                zf.writestr(arcname, data)
            try:
                message.unlink(missing_ok=True)
            except OSError:
                pass


def compact_now(dir_path: Path | str) -> None:
    """Run the sweep unconditionally (bypasses the cheap gate; for tests and
    direct invocation). Any `*.json` message older than COMPACT_AGE_SECONDS
    is moved into the persistent zip archive and removed from `dir_path`;
    `.marker` and `.compacted` files are never touched."""
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        return
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=COMPACT_AGE_SECONDS)
    stale = _stale_messages(dir_path, cutoff)
    if stale:
        _archive_and_remove(dir_path, stale)


def _recently_checked(sentinel: Path) -> bool:
    try:
        age = time.time() - sentinel.stat().st_mtime
    except OSError:
        return False
    return age < COMPACT_CHECK_INTERVAL


def _touch_sentinel(dir_path: Path, sentinel: Path) -> None:
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        sentinel.touch()
    except OSError:
        pass


def maybe_compact(dir_path: Path | str) -> None:
    """Cheap-gated entry point — call after each message write.

    Checks `<dir_path>/.compacted`'s mtime; if younger than
    COMPACT_CHECK_INTERVAL, returns immediately without scanning the
    directory. Otherwise runs the sweep (compact_now) and touches the
    sentinel so the next COMPACT_CHECK_INTERVAL seconds are free.
    """
    dir_path = Path(dir_path)
    sentinel = dir_path / SENTINEL_NAME
    if _recently_checked(sentinel):
        return
    compact_now(dir_path)
    _touch_sentinel(dir_path, sentinel)

#!/usr/bin/env python3
"""Fleet event SIMULATOR — writes a realistic, deterministic multi-project
orchard event tree into an ISOLATED runtime directory, so `tools/sidebar.py`
can be developed and judged against a populated fleet instead of sparse live
data.

The on-disk shape matches `tools/orchard_topic.py`'s sanctioned writer
exactly (see its `build_envelope()`/`_attach_snapshot()`): one JSON file per
event at `<root>/<repo>.<project>[@<branch>]/<session-id>.<timestamp>.json`,
carrying `from`/`to`/`subject`/optional `body`/optional `identity`/optional
`status` — no `id`, no `ts` (those belong to the courier-transport envelope
shape, not the topic-post one; `tests/fixtures/event_topic_post_status.json`
and `event_identity_new_shape_live.json` are the captured ground truth this
mirrors). This script never imports or calls `tools/courier.py` or
`tools/orchard_topic.py` — it only reads them for the format — so it never
touches the real orchard transport, a real session id, or `XDG_RUNTIME_DIR`.

SAFETY: this script refuses outright to write into the live tree
($XDG_RUNTIME_DIR/orchard) — see `_refuse_live_tree()`. It always requires an
explicit target root argument.

Modes:
  --once TARGET   write the static scenario once and exit (the fixture the
                  tests use).
  --loop TARGET   write the static scenario, then keep mutating a handful of
                  live agents (status text, subagent progress) at --interval
                  seconds so motion can be watched in a running sidebar.
                  Ctrl-C exits.

--base-ts (ISO-8601, e.g. 2026-07-27T09:00:00+00:00) anchors the scenario's
relative timestamps and the staleness cutoff. It is read once in `main()`
(never at import) and defaults to the current time if omitted, which is
convenient for eyeballing a freshly generated tree in a live sidebar but NOT
reproducible byte-for-byte across runs — a caller that wants a stable fixture
(e.g. a test) must pass --base-ts explicitly.

Usage:
    tools/sidebar_sim.py --once /tmp/sim-orchard/projects --base-ts 2026-07-27T09:00:00+00:00
    tools/sidebar_sim.py --loop /tmp/sim-orchard/projects
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

TS_FORMAT = "%Y-%m-%dT%H-%M-%S.%f"  # matches courier.py's stamp()
TOPIC_FAMILY = "repository"  # matches orchard_topic.py's TOPIC_FAMILY

# Mirrors tools/sidebar.py's ACTIVE_WINDOW_SECONDS (1h) without importing it —
# this tool stays standalone, like courier.py/orchard_topic.py stay
# stdlib-only. A stale agent's file mtime is pushed comfortably past this.
ACTIVE_WINDOW_SECONDS = 60 * 60
STALE_OFFSET_SECONDS = ACTIVE_WINDOW_SECONDS * 3

DEFAULT_INTERVAL_SECONDS = 4.0


def _die(msg: str) -> None:
    sys.exit(f"sidebar_sim: {msg}")


# ---------------------------------------------------------------------------
# Envelope construction — mirrors orchard_topic.py's build_envelope() +
# _attach_snapshot() exactly, without calling into that module.
# ---------------------------------------------------------------------------


def identity(agent: str, *, feature: str | None = None, feature_name: str | None = None,
             task: str | None = None, task_name: str | None = None,
             parent: str | None = None) -> dict:
    """Matches orchard_topic.py's `_identity()` output shape: only fields
    that are set appear; `name` rides as a plain alias of `feature_name`."""
    out: dict = {"agent": agent}
    if feature:
        out["feature"] = feature
    if feature_name:
        out["feature_name"] = feature_name
        out["name"] = feature_name
    if task:
        out["task"] = task
    if task_name:
        out["task_name"] = task_name
    if parent:
        out["parent"] = parent
    return out


def status(model: str, seed: int) -> dict:
    """Matches orchard_topic.py's `_status()` output shape. `seed` varies
    the numbers deterministically per agent — no randomness."""
    return {
        "model": model,
        "context_tokens": 18_000 + seed * 733,
        "spend": {
            "input_tokens": 200 + seed * 3,
            "output_tokens": 4_000 + seed * 251,
            "cache_read_input_tokens": 80_000 + seed * 4_111,
            "cache_creation_input_tokens": 2_000 + seed * 97,
        },
    }


def envelope(sid: str, bare_repo: str, subject: str, *, body=None,
             identity_block: dict | None = None, status_block: dict | None = None) -> dict:
    env = {
        "from": f":session:{sid}",
        "to": f":topic:{TOPIC_FAMILY}/{bare_repo}",
        "subject": subject,
    }
    if body is not None:
        env["body"] = body
    if identity_block:
        env["identity"] = identity_block
    if status_block:
        env["status"] = status_block
    return env


def _sid(label: str) -> str:
    """A deterministic, UUID-shaped session id derived from a label — no
    randomness, stable across runs (courier.py session ids are always
    dot-free UUIDs; a bare-UUID session with no announced name/feature is
    exactly what `_is_bare_uuid()`/`_row_label()` in sidebar.py special-cases,
    so keeping the real shape matters)."""
    h = hashlib.sha1(label.encode("utf-8")).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


class Emitter:
    """Writes one event per call, advancing a one-second tick each time so
    every filename (and, absent `stale=True`, every file mtime) is strictly
    increasing and collision-free — deterministic ordering with no clock
    reads and no randomness. `tools/sidebar.py`'s `_fold_sessions()` keys
    staleness/"latest wins" off the file's actual mtime (not any field
    inside the JSON), so the mtime is what has to carry the story."""

    def __init__(self, root: Path, base_dt: datetime) -> None:
        self.root = root
        self.base_dt = base_dt
        self._tick = 0

    def _next_dt(self) -> datetime:
        dt = self.base_dt + timedelta(seconds=self._tick)
        self._tick += 1
        return dt

    def post(self, dirname: str, bare_repo: str, sid: str, subject: str, *,
              body=None, identity_block: dict | None = None,
              status_block: dict | None = None, stale: bool = False,
              at: datetime | None = None) -> Path:
        dt = at or self._next_dt()
        env = envelope(sid, bare_repo, subject, body=body,
                       identity_block=identity_block, status_block=status_block)
        dir_path = self.root / dirname
        dir_path.mkdir(parents=True, exist_ok=True)
        path = dir_path / f"{sid}.{dt.strftime(TS_FORMAT)}.json"
        path.write_text(json.dumps(env, indent=2) + "\n", encoding="utf-8")
        mtime = (self.base_dt - timedelta(seconds=STALE_OFFSET_SECONDS)).timestamp() if stale \
            else dt.timestamp()
        os.utime(path, (mtime, mtime))
        return path


# ---------------------------------------------------------------------------
# Safety gate
# ---------------------------------------------------------------------------


def _refuse_live_tree(target: Path) -> None:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        return  # nothing to compare against; caller's target stands as given
    live_root = (Path(runtime) / "orchard").resolve()
    resolved = target.resolve()
    if resolved == live_root or live_root in resolved.parents:
        _die(f"refusing to write into the live orchard tree ({live_root}) — "
             "pass an isolated target root outside it. The live tree already "
             "carries 1091 leaked tmp* dirs from tests; this script will not "
             "add to that.")


# ---------------------------------------------------------------------------
# Scenario identifiers — shared between the static --once write and the
# --loop mutations, so the two never drift out of step with each other.
#
#   PROJECT A "orchids"  — kaukea.orchids (bare, legacy) + kaukea.orchids@f-
#                          sidebar-teamwork (current worktree): the SAME repo
#                          across two directories, exercising the renderer's
#                          project-folding (_repo_identity partitions on the
#                          FIRST "@", so both fold to "kaukea.orchids").
#   PROJECT B "throwy"   — kaukea.throwy@main: a second, unrelated repo.
#   PROJECT C "widgets"  — acme.widgets@f-onboarding-flow: a third repo,
#                          different owner.
# ---------------------------------------------------------------------------

DIR_A_LEGACY = "kaukea.orchids"
DIR_A_BRANCH = "kaukea.orchids@f-sidebar-teamwork"
REPO_A = "orchids"

DIR_B = "kaukea.throwy@main"
REPO_B = "throwy"

DIR_C = "acme.widgets@f-onboarding-flow"
REPO_C = "widgets"

GARDENER_SID = _sid("orchids-gardener")
LANDSCAPER_SID = _sid("orchids-landscaper-render-model")
SOWER1_SID = _sid("orchids-sower-renderer-refactor-1")
SOWER2_SID = _sid("orchids-sower-renderer-refactor-2")
QUIET_SID = _sid("orchids-landscaper-noop")
DOCS_SID = _sid("orchids-sower-docs")
FAIL_SID = _sid("orchids-sower-flaky")
STALE_SID = _sid("orchids-groundskeeper-stale")
GROOMER_A_SID = _sid("orchids-groomer-close-family-fakes")
BLOOMER_A_SID = _sid("orchids-bloomer-close-family-fakes")

LANDS_B1_SID = _sid("throwy-landscaper-cert-rotation")
SOWER_B1_SID = _sid("throwy-sower-escrow-doc")
GROOMER_B1_SID = _sid("throwy-groomer-vault-migration")
BLOOMER_B1_SID = _sid("throwy-bloomer-vault-migration")

GROOMER_C1_SID = _sid("widgets-groomer-wireframe")
LANDS_C1_SID = _sid("widgets-landscaper-onboarding-screens")
BLOOMER_C1_SID = _sid("widgets-bloomer-telemetry")
GK_C1_SID = _sid("widgets-groundskeeper-telemetry")

MODEL_A = "claude-opus-5"
MODEL_B = "claude-sonnet-5"
MODEL_C = "claude-fable-5"

FEATURE_TEAMWORK = "sidebar-teamwork"
FEATURE_TEAMWORK_NAME = "Sidebar teamwork: render model, renderer refactor, and its rough edges"
FEATURE_CLOSE_FAMILY = "close-family-fakes"
FEATURE_CLOSE_FAMILY_NAME = "Close family fakes"

FEATURE_CERT = "hardware-cert-rotation"
FEATURE_CERT_NAME = "Hardware cert rotation"
FEATURE_VAULT = "sops-vault-migration"
FEATURE_VAULT_NAME = "SOPS vault migration"

FEATURE_ONBOARDING = "onboarding-flow-redesign"
FEATURE_ONBOARDING_NAME = "Onboarding flow redesign"
FEATURE_TELEMETRY = "widget-telemetry-events"
FEATURE_TELEMETRY_NAME = "Widget telemetry events"


def _identity_a_render_model() -> dict:
    return identity(
        "landscaper", feature=FEATURE_TEAMWORK, feature_name=FEATURE_TEAMWORK_NAME,
        task="sidebar-teamwork-render-model", task_name="Render model layer",
        parent=GARDENER_SID,
    )


def _identity_a_courier_under_landscaper() -> dict:
    """The SAME session id as `_identity_a_render_model()` — a courier
    sidecar's session id is its parent's, verbatim (courier.py's module
    docstring: "a subagent inherits its parent's environment verbatim").
    Two distinct logical agents, one wire session id — the rare-but-real
    case the renderer must not silently fold into one."""
    return identity("courier", parent=GARDENER_SID)


def build_static_scenario(root: Path, base_dt: datetime) -> Emitter:
    em = Emitter(root, base_dt)

    # --- Project A: "orchids" ------------------------------------------------
    # Repo header: the gardener, in the LEGACY (no-branch) directory — the
    # renderer must fold this together with the branch-suffixed directory
    # below into one "orchids" repo row.
    gardener_identity = identity("gardener")
    gardener_status = status(MODEL_C, seed=1)
    em.post(DIR_A_LEGACY, REPO_A, GARDENER_SID, "orchard:agent:status",
            body="folding board", identity_block=gardener_identity, status_block=gardener_status)

    # Task "render-model": landscaper, building. Also posts a SECOND, distinct
    # agent (its courier sidecar) under the exact same session id — the
    # "two agents share one session id" case.
    land_identity = _identity_a_render_model()
    land_status = status(MODEL_A, seed=2)
    em.post(DIR_A_BRANCH, REPO_A, LANDSCAPER_SID, "orchard:agent:lifecycle:started",
            identity_block=land_identity, status_block=land_status)
    em.post(DIR_A_BRANCH, REPO_A, LANDSCAPER_SID, "orchard:agent:status",
            body="reviewing plan", identity_block=land_identity, status_block=land_status)
    courier_identity = _identity_a_courier_under_landscaper()
    courier_status = status(MODEL_A, seed=3)
    em.post(DIR_A_BRANCH, REPO_A, LANDSCAPER_SID, "orchard:agent:status",
            body="watching inbox", identity_block=courier_identity, status_block=courier_status)

    # Task "renderer-refactor": TWO agents on the same task/step (rare but
    # real — the renderer must not assume a single agent per step), each
    # with its own delegated subagents in different delegation states.
    refactor_task = "sidebar-teamwork-renderer-refactor"
    refactor_task_name = "Renderer refactor"
    sower1_identity = identity(
        "sower", feature=FEATURE_TEAMWORK, feature_name=FEATURE_TEAMWORK_NAME,
        task=refactor_task, task_name=refactor_task_name, parent=LANDSCAPER_SID,
    )
    sower1_status = status(MODEL_A, seed=4)
    em.post(DIR_A_BRANCH, REPO_A, SOWER1_SID, "orchard:agent:lifecycle:started",
            identity_block=sower1_identity, status_block=sower1_status)
    em.post(DIR_A_BRANCH, REPO_A, SOWER1_SID, "orchard:agent:status",
            body="extracting model", identity_block=sower1_identity, status_block=sower1_status)
    em.post(DIR_A_BRANCH, REPO_A, SOWER1_SID, "orchard:agent:delegation:schedule",
            body={"subagent": "grep-scan"}, identity_block=sower1_identity, status_block=sower1_status)
    em.post(DIR_A_BRANCH, REPO_A, SOWER1_SID, "orchard:agent:delegation:begin",
            body={"subagent": "grep-scan"}, identity_block=sower1_identity, status_block=sower1_status)
    em.post(DIR_A_BRANCH, REPO_A, SOWER1_SID, "orchard:agent:delegation:end",
            body={"subagent": "grep-scan"}, identity_block=sower1_identity, status_block=sower1_status)

    sower2_identity = identity(
        "sower", feature=FEATURE_TEAMWORK, feature_name=FEATURE_TEAMWORK_NAME,
        task=refactor_task, task_name=refactor_task_name, parent=LANDSCAPER_SID,
    )
    sower2_status = status(MODEL_A, seed=5)
    em.post(DIR_A_BRANCH, REPO_A, SOWER2_SID, "orchard:agent:lifecycle:started",
            identity_block=sower2_identity, status_block=sower2_status)
    em.post(DIR_A_BRANCH, REPO_A, SOWER2_SID, "orchard:agent:status",
            body="writing tests", identity_block=sower2_identity, status_block=sower2_status)
    # "docs-audit" — scheduled only (still queued).
    em.post(DIR_A_BRANCH, REPO_A, SOWER2_SID, "orchard:agent:delegation:schedule",
            body={"subagent": "docs-audit"}, identity_block=sower2_identity, status_block=sower2_status)
    # "test-runner" — scheduled then begun (in progress).
    em.post(DIR_A_BRANCH, REPO_A, SOWER2_SID, "orchard:agent:delegation:schedule",
            body={"subagent": "test-runner"}, identity_block=sower2_identity, status_block=sower2_status)
    em.post(DIR_A_BRANCH, REPO_A, SOWER2_SID, "orchard:agent:delegation:begin",
            body={"subagent": "test-runner"}, identity_block=sower2_identity, status_block=sower2_status)

    # Task "noop": an agent with NO status event at all — absence of status
    # means idle/doing nothing; the renderer currently renders this as
    # literal empty quotes.
    quiet_identity = identity(
        "landscaper", feature=FEATURE_TEAMWORK, feature_name=FEATURE_TEAMWORK_NAME,
        task="sidebar-teamwork-noop", task_name="Idle placeholder task", parent=GARDENER_SID,
    )
    quiet_status = status(MODEL_A, seed=6)
    em.post(DIR_A_BRANCH, REPO_A, QUIET_SID, "orchard:agent:lifecycle:started",
            identity_block=quiet_identity, status_block=quiet_status)

    # Task "docs": terminal success.
    docs_identity = identity(
        "sower", feature=FEATURE_TEAMWORK, feature_name=FEATURE_TEAMWORK_NAME,
        task="sidebar-teamwork-docs", task_name="Write docs", parent=LANDSCAPER_SID,
    )
    docs_status = status(MODEL_A, seed=7)
    em.post(DIR_A_BRANCH, REPO_A, DOCS_SID, "orchard:agent:status",
            body="polishing", identity_block=docs_identity, status_block=docs_status)
    em.post(DIR_A_BRANCH, REPO_A, DOCS_SID, "orchard:agent:outcome:success",
            identity_block=docs_identity, status_block=docs_status)

    # Task "flaky": terminal failure.
    fail_identity = identity(
        "sower", feature=FEATURE_TEAMWORK, feature_name=FEATURE_TEAMWORK_NAME,
        task="sidebar-teamwork-flaky", task_name="Flaky test fix", parent=LANDSCAPER_SID,
    )
    fail_status = status(MODEL_A, seed=8)
    em.post(DIR_A_BRANCH, REPO_A, FAIL_SID, "orchard:agent:status",
            body="debugging", identity_block=fail_identity, status_block=fail_status)
    em.post(DIR_A_BRANCH, REPO_A, FAIL_SID, "orchard:agent:outcome:fail",
            identity_block=fail_identity, status_block=fail_status)

    # Task "stale": last event well outside the liveness window (mtime
    # forced back, not just an old envelope field — the renderer keys
    # staleness off the file's real mtime).
    stale_identity = identity(
        "groundskeeper", feature=FEATURE_TEAMWORK, feature_name=FEATURE_TEAMWORK_NAME,
        task="sidebar-teamwork-stale", task_name="Stale liveness check", parent=GARDENER_SID,
    )
    stale_status = status(MODEL_C, seed=9)
    em.post(DIR_A_BRANCH, REPO_A, STALE_SID, "orchard:agent:status",
            body="sweeping", identity_block=stale_identity, status_block=stale_status, stale=True)

    # Feature "close-family-fakes": scoping + designing stages.
    groomer_a_identity = identity(
        "groomer", feature=FEATURE_CLOSE_FAMILY, feature_name=FEATURE_CLOSE_FAMILY_NAME,
        task="close-family-fakes-spec", task_name="Spec the fake-closing rules", parent=GARDENER_SID,
    )
    groomer_a_status = status(MODEL_B, seed=10)
    em.post(DIR_A_BRANCH, REPO_A, GROOMER_A_SID, "orchard:agent:status",
            body="drafting spec", identity_block=groomer_a_identity, status_block=groomer_a_status)

    bloomer_a_identity = identity(
        "bloomer", feature=FEATURE_CLOSE_FAMILY, feature_name=FEATURE_CLOSE_FAMILY_NAME,
        task="close-family-fakes-bloom", task_name="Bloom intake", parent=GARDENER_SID,
    )
    bloomer_a_status = status(MODEL_C, seed=11)
    em.post(DIR_A_BRANCH, REPO_A, BLOOMER_A_SID, "orchard:agent:status",
            body="asking questions", identity_block=bloomer_a_identity, status_block=bloomer_a_status)

    # --- Project B: "throwy" -------------------------------------------------
    # No gardener/root session here on purpose — no `parent` fields either,
    # so no session accidentally qualifies as the parent-chain root
    # (`_root_session_id`); the repo is populated purely by its features.
    lands_b1_identity = identity(
        "landscaper", feature=FEATURE_CERT, feature_name=FEATURE_CERT_NAME,
        task="rotate-nitrokey-cert", task_name="Rotate Nitrokey cert",
    )
    lands_b1_status = status(MODEL_B, seed=12)
    em.post(DIR_B, REPO_B, LANDS_B1_SID, "orchard:agent:status",
            body="rotating cert", identity_block=lands_b1_identity, status_block=lands_b1_status)

    sower_b1_identity = identity(
        "sower", feature=FEATURE_CERT, feature_name=FEATURE_CERT_NAME,
        task="update-escrow-doc", task_name="Update escrow doc",
    )
    sower_b1_status = status(MODEL_B, seed=13)
    em.post(DIR_B, REPO_B, SOWER_B1_SID, "orchard:agent:status",
            body="updating doc", identity_block=sower_b1_identity, status_block=sower_b1_status)

    groomer_b1_identity = identity(
        "groomer", feature=FEATURE_VAULT, feature_name=FEATURE_VAULT_NAME,
        task="migrate-secrets", task_name="Migrate secrets",
    )
    groomer_b1_status = status(MODEL_B, seed=14)
    em.post(DIR_B, REPO_B, GROOMER_B1_SID, "orchard:agent:status",
            body="auditing secrets", identity_block=groomer_b1_identity, status_block=groomer_b1_status)

    bloomer_b1_identity = identity(
        "bloomer", feature=FEATURE_VAULT, feature_name=FEATURE_VAULT_NAME,
        task="verify-migration", task_name="Verify migration",
    )
    bloomer_b1_status = status(MODEL_C, seed=15)
    em.post(DIR_B, REPO_B, BLOOMER_B1_SID, "orchard:agent:status",
            body="confirming scope", identity_block=bloomer_b1_identity, status_block=bloomer_b1_status)

    # --- Project C: "widgets" -------------------------------------------------
    groomer_c1_identity = identity(
        "groomer", feature=FEATURE_ONBOARDING, feature_name=FEATURE_ONBOARDING_NAME,
        task="wireframe-review", task_name="Wireframe review",
    )
    groomer_c1_status = status(MODEL_B, seed=16)
    em.post(DIR_C, REPO_C, GROOMER_C1_SID, "orchard:agent:status",
            body="reviewing wireframes", identity_block=groomer_c1_identity, status_block=groomer_c1_status)

    lands_c1_identity = identity(
        "landscaper", feature=FEATURE_ONBOARDING, feature_name=FEATURE_ONBOARDING_NAME,
        task="build-onboarding-screens", task_name="Build onboarding screens",
    )
    lands_c1_status = status(MODEL_B, seed=17)
    em.post(DIR_C, REPO_C, LANDS_C1_SID, "orchard:agent:status",
            body="scaffolding screens", identity_block=lands_c1_identity, status_block=lands_c1_status)
    em.post(DIR_C, REPO_C, LANDS_C1_SID, "orchard:agent:delegation:schedule",
            body={"subagent": "screen-scaffold"}, identity_block=lands_c1_identity, status_block=lands_c1_status)
    em.post(DIR_C, REPO_C, LANDS_C1_SID, "orchard:agent:delegation:begin",
            body={"subagent": "screen-scaffold"}, identity_block=lands_c1_identity, status_block=lands_c1_status)

    bloomer_c1_identity = identity(
        "bloomer", feature=FEATURE_TELEMETRY, feature_name=FEATURE_TELEMETRY_NAME,
        task="spec-telemetry-events", task_name="Spec telemetry events",
    )
    bloomer_c1_status = status(MODEL_C, seed=18)
    em.post(DIR_C, REPO_C, BLOOMER_C1_SID, "orchard:agent:status",
            body="measuring intake", identity_block=bloomer_c1_identity, status_block=bloomer_c1_status)

    gk_c1_identity = identity(
        "groundskeeper", feature=FEATURE_TELEMETRY, feature_name=FEATURE_TELEMETRY_NAME,
        task="close-telemetry-events", task_name="Close telemetry events",
    )
    gk_c1_status = status(MODEL_C, seed=19)
    em.post(DIR_C, REPO_C, GK_C1_SID, "orchard:agent:status",
            body="tagging release", identity_block=gk_c1_identity, status_block=gk_c1_status)
    em.post(DIR_C, REPO_C, GK_C1_SID, "orchard:agent:outcome:success",
            identity_block=gk_c1_identity, status_block=gk_c1_status)

    return em


# ---------------------------------------------------------------------------
# --loop: keeps a handful of live agents visibly moving. Reuses the exact
# identity/status blocks the static scenario built (recomputed here rather
# than threaded through Emitter, since each mutation needs a fresh `status`
# snapshot and a real wall-clock timestamp, not the static scenario's
# relative ticks) so a loop run never drifts out of sync with the fixture
# `--once` produces. The stale agent (STALE_SID) is deliberately never
# touched here — it must stay stale for the whole run.
# ---------------------------------------------------------------------------


def _loop_step(root: Path, cycle: int) -> None:
    now = datetime.now(timezone.utc)
    em = Emitter(root, now)
    seed = 20 + cycle

    # 1. sower1 status text alternates.
    sower1_identity = identity(
        "sower", feature=FEATURE_TEAMWORK, feature_name=FEATURE_TEAMWORK_NAME,
        task="sidebar-teamwork-renderer-refactor", task_name="Renderer refactor",
        parent=LANDSCAPER_SID,
    )
    text = "extracting model" if cycle % 2 == 0 else "folding cases"
    em.post(DIR_A_BRANCH, REPO_A, SOWER1_SID, "orchard:agent:status", body=text,
            identity_block=sower1_identity, status_block=status(MODEL_A, seed), at=now)

    # 2. sower2's "docs-audit" subagent advances scheduled -> begin -> end,
    #    then is rescheduled, so its dot keeps moving through all three
    #    delegation states over time.
    sower2_identity = identity(
        "sower", feature=FEATURE_TEAMWORK, feature_name=FEATURE_TEAMWORK_NAME,
        task="sidebar-teamwork-renderer-refactor", task_name="Renderer refactor",
        parent=LANDSCAPER_SID,
    )
    stage = cycle % 3
    action = ("schedule", "begin", "end")[stage]
    em.post(DIR_A_BRANCH, REPO_A, SOWER2_SID, f"orchard:agent:delegation:{action}",
            body={"subagent": "docs-audit"}, identity_block=sower2_identity,
            status_block=status(MODEL_A, seed + 1), at=now)

    # 3. the gardener's status text alternates, so the repo header itself
    #    visibly ticks over.
    gardener_text = "folding board" if cycle % 2 == 0 else "watching fleet"
    em.post(DIR_A_LEGACY, REPO_A, GARDENER_SID, "orchard:agent:status", body=gardener_text,
            identity_block=identity("gardener"), status_block=status(MODEL_C, seed + 2), at=now)

    # 4. project C's onboarding-screens subagent advances the same way.
    lands_c1_identity = identity(
        "landscaper", feature=FEATURE_ONBOARDING, feature_name=FEATURE_ONBOARDING_NAME,
        task="build-onboarding-screens", task_name="Build onboarding screens",
    )
    stage_c = cycle % 3
    action_c = ("schedule", "begin", "end")[stage_c]
    em.post(DIR_C, REPO_C, LANDS_C1_SID, f"orchard:agent:delegation:{action_c}",
            body={"subagent": "screen-scaffold"}, identity_block=lands_c1_identity,
            status_block=status(MODEL_B, seed + 3), at=now)


def run_loop(root: Path, base_dt: datetime, interval: float) -> None:
    build_static_scenario(root, base_dt)
    print(f"sidebar_sim: static baseline written to {root}; looping every {interval}s "
          "(Ctrl-C to stop)", file=sys.stderr)
    cycle = 0
    try:
        while True:
            time.sleep(interval)
            cycle += 1
            _loop_step(root, cycle)
    except KeyboardInterrupt:
        print("sidebar_sim: stopped", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_base_ts(text: str) -> datetime:
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        _die(f"--base-ts {text!r} is not a valid ISO-8601 timestamp")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", type=Path, help="isolated target root directory to write into")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="write the static scenario and exit")
    mode.add_argument("--loop", action="store_true",
                       help="write the static scenario, then keep mutating it until Ctrl-C")
    parser.add_argument("--base-ts", default=None,
                         help="ISO-8601 instant anchoring the scenario (default: current time)")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_SECONDS,
                         help=f"--loop only: seconds between mutation ticks (default {DEFAULT_INTERVAL_SECONDS})")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    target: Path = args.target
    _refuse_live_tree(target)
    base_dt = _parse_base_ts(args.base_ts) if args.base_ts else datetime.now(timezone.utc)
    target.mkdir(parents=True, exist_ok=True)

    if args.once:
        build_static_scenario(target, base_dt)
        print(f"sidebar_sim: wrote static scenario to {target} (base {base_dt.isoformat()})")
    else:
        run_loop(target, base_dt, args.interval)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Before/after token-cost harness for courier changes (Decision "The token A/B
measures the whole path with a static scenario and static prompts").

The ruled method (operator, 2026-07-29, plan-gate Q3): a STATIC scenario with
STATIC PROMPTS, run once per checkout, collecting three kinds of telemetry in
one comparison — the messaging layer's own event snapshots, Claude's own
reported usage, and wall-clock timings — so a single number catches
improvements in the script, in agent behaviour, and in the courier agent
together. Less precise than isolating one layer; preferred for exactly that
reason (it reflects real usage). The continuous alerting version of this is a
separate task; this script runs ONE honest comparison, on demand.

What it does:

  run       Drive the fixed SCENARIO against one checkout's courier agent via
            headless `claude -p --agent courier`, resuming the same session
            turn to turn (mirrors how a courier is actually used: loaded once,
            asked for several things, released). Writes one JSON result file
            and prints a human summary.

  compare   Read two `run` result files (before, after) and print the numbers
            side by side. No verdict, no threshold — the numbers are the
            deliverable.

Isolation: each `run` gets its OWN temporary $XDG_RUNTIME_DIR, so the
courier's real orchard writes (markers, events, the name registry) never touch
this machine's live orchard runtime — a harness run must not appear on
anyone's actual sidebar. The directory is removed when the run finishes.

Usage:
  token-ab.py run --checkout /path/to/checkout --label before --out before.json
  token-ab.py run --checkout /path/to/checkout --label after  --out after.json
  token-ab.py compare before.json after.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# The scenario is byte-identical across runs — this is what makes the two
# runs comparable at all. It walks the courier lifecycle an agent session
# actually exercises: on-load, a delegation it watched happen, its own status
# changing, and its own close. Deliberately plain-language and verb-agnostic
# — the whole point is letting each checkout's own charter and scripts pick
# whatever mechanism they actually have, rather than scripting the tool calls
# ourselves and measuring nothing but the script.
SCENARIO: list[str] = [
    "Your parent session has just started and loaded you as its courier. "
    "Complete your on-load procedure now, then reply with one short line "
    "confirming you are listening.",

    "Your parent is about to dispatch a sub-agent named 'sower-a' to build "
    "one step. Record its dispatch, then record that it began work, then "
    "record that it finished successfully — all three, in order, the way "
    "you normally would for your parent. Reply with one short line when "
    "done.",

    "Your parent's own status has changed: it is now testing its changes. "
    "Let the project know the way you normally would, then reply with one "
    "short line confirming it is sent.",

    "Your parent is finished and is releasing you now. Complete your "
    "release procedure, then reply with one short line confirming you are "
    "releasing.",
]

CLAUDE_TIMEOUT_S = 180
MAX_BUDGET_PER_STEP_USD = "0.50"

USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def _run_claude_step(checkout: Path, xdg_runtime_dir: Path, prompt: str,
                      resume_session: str | None) -> dict:
    """Run one scenario prompt as a real headless courier turn and return the
    parsed `--output-format json` result, plus our own wall-clock bracket.
    `checkout` is both the subprocess cwd and what selects the checkout's own
    agents/courier.md and tools/courier.py — nothing here is hardcoded to a
    version."""
    cmd = [
        "claude", "-p",
        "--agent", "courier",
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
        "--max-budget-usd", MAX_BUDGET_PER_STEP_USD,
    ]
    if resume_session:
        cmd += ["--resume", resume_session]
    cmd.append(prompt)

    env = {"XDG_RUNTIME_DIR": str(xdg_runtime_dir)}
    import os
    env = {**os.environ, **env}

    started = time.monotonic()
    started_wall = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run(
            cmd, cwd=checkout, env=env, capture_output=True, text=True,
            timeout=CLAUDE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return {
            "prompt": prompt, "started_wall": started_wall,
            "wall_clock_s": time.monotonic() - started, "ok": False,
            "error": f"timed out after {CLAUDE_TIMEOUT_S}s",
        }
    wall_clock_s = time.monotonic() - started

    if proc.returncode != 0:
        return {
            "prompt": prompt, "started_wall": started_wall,
            "wall_clock_s": wall_clock_s, "ok": False,
            "error": f"exit {proc.returncode}: {proc.stderr.strip()[:500]}",
        }
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {
            "prompt": prompt, "started_wall": started_wall,
            "wall_clock_s": wall_clock_s, "ok": False,
            "error": f"non-JSON output ({exc}): {proc.stdout.strip()[:500]}",
        }

    usage = payload.get("usage") or {}
    return {
        "prompt": prompt,
        "started_wall": started_wall,
        "wall_clock_s": wall_clock_s,
        "ok": not payload.get("is_error", False),
        "session_id": payload.get("session_id"),
        "resumed_from": resume_session,
        "duration_ms": payload.get("duration_ms"),
        "duration_api_ms": payload.get("duration_api_ms"),
        "num_turns": payload.get("num_turns"),
        "total_cost_usd": payload.get("total_cost_usd"),
        "usage": {k: usage.get(k) for k in USAGE_KEYS},
        "result_text": payload.get("result"),
        "stop_reason": payload.get("stop_reason"),
    }


def _run_scenario(checkout: Path, xdg_runtime_dir: Path) -> list[dict]:
    steps: list[dict] = []
    resume_session = None
    for prompt in SCENARIO:
        step = _run_claude_step(checkout, xdg_runtime_dir, prompt, resume_session)
        steps.append(step)
        if not step.get("ok"):
            break  # a broken step invalidates resuming further turns on it
        resume_session = step.get("session_id") or resume_session
    return steps


def _charter_word_count(checkout: Path) -> int | None:
    charter = checkout / "agents" / "courier.md"
    if not charter.exists():
        return None
    return len(charter.read_text().split())


def _git(checkout: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=checkout, capture_output=True, text=True)
    return out.stdout.strip()


def _scan_messaging_layer(xdg_runtime_dir: Path) -> dict:
    """Everything the courier's own transport wrote during the run, read as
    an outside observer would — no coupling to courier.py's internals beyond
    the on-disk shapes it already documents (marker vs `<sid>.<ts>.json`
    event files; `identity`/`status` snapshots riding an event when
    attached)."""
    orchard = xdg_runtime_dir / "orchard"
    if not orchard.exists():
        return {"present": False}

    all_files = [p for p in orchard.rglob("*") if p.is_file()]
    markers = [p for p in all_files if p.suffix == ".marker"]
    events = [p for p in all_files if p.name.count(".") >= 2 and p.suffix == ".json"
              and p not in markers]
    other = [p for p in all_files if p not in markers and p not in events]

    subjects: dict[str, int] = {}
    tokens_in_seen = []
    tokens_out_seen = []
    dollars_seen = []
    snapshot_events = 0
    for p in events:
        try:
            body = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        subject = body.get("subject")
        if subject:
            subjects[subject] = subjects.get(subject, 0) + 1
        status = body.get("status") or {}
        if status:
            snapshot_events += 1
            if status.get("tokens_in") is not None:
                tokens_in_seen.append(status["tokens_in"])
            if status.get("tokens_out") is not None:
                tokens_out_seen.append(status["tokens_out"])
            if status.get("dollars") is not None:
                dollars_seen.append(status["dollars"])

    return {
        "present": True,
        "files_total": len(all_files),
        "marker_files": len(markers),
        "event_files": len(events),
        "other_files": len(other),
        "event_subjects": subjects,
        "events_carrying_snapshot": snapshot_events,
        "snapshot_tokens_in_last": tokens_in_seen[-1] if tokens_in_seen else None,
        "snapshot_tokens_out_last": tokens_out_seen[-1] if tokens_out_seen else None,
        "snapshot_dollars_last": dollars_seen[-1] if dollars_seen else None,
    }


def cmd_run(args: argparse.Namespace) -> None:
    checkout = Path(args.checkout).resolve()
    if not checkout.is_dir():
        sys.exit(f"token-ab: no such checkout directory: {checkout}")

    xdg_runtime_dir = Path(tempfile.mkdtemp(prefix="token-ab-xdg-"))
    try:
        steps = _run_scenario(checkout, xdg_runtime_dir)
        messaging = _scan_messaging_layer(xdg_runtime_dir)
    finally:
        shutil.rmtree(xdg_runtime_dir, ignore_errors=True)

    ok_steps = [s for s in steps if s.get("ok")]
    totals = {
        "steps_run": len(steps),
        "steps_ok": len(ok_steps),
        "wall_clock_s": sum(s["wall_clock_s"] for s in steps),
        "total_cost_usd": sum(s.get("total_cost_usd") or 0 for s in ok_steps),
    }
    for key in USAGE_KEYS:
        totals[key] = sum((s.get("usage") or {}).get(key) or 0 for s in ok_steps)

    result = {
        "label": args.label,
        "checkout": str(checkout),
        "commit": _git(checkout, "rev-parse", "HEAD"),
        "branch_or_ref": _git(checkout, "rev-parse", "--abbrev-ref", "HEAD"),
        "charter_word_count": _charter_word_count(checkout),
        "scenario": SCENARIO,
        "steps": steps,
        "totals": totals,
        "messaging_layer": messaging,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "degraded": len(ok_steps) < len(SCENARIO),
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(result, indent=2) + "\n")

    print(f"token-ab run: {args.label} @ {result['commit'][:12]} "
          f"({result['charter_word_count']} charter words)")
    if result["degraded"]:
        print(f"  DEGRADED — only {len(ok_steps)}/{len(SCENARIO)} scenario steps "
              f"completed; Claude-side numbers below this point are partial. "
              f"First failure: {steps[len(ok_steps)].get('error') if len(ok_steps) < len(steps) else 'unknown'}")
    print(f"  wall clock:  {totals['wall_clock_s']:.1f}s over {totals['steps_run']} step(s)")
    print(f"  claude cost: ${totals['total_cost_usd']:.4f}")
    print(f"  claude tokens in/out: {totals['input_tokens']}/{totals['output_tokens']} "
          f"(cache read {totals['cache_read_input_tokens']}, "
          f"cache create {totals['cache_creation_input_tokens']})")
    if messaging.get("present"):
        print(f"  messaging files: {messaging['files_total']} total "
              f"({messaging['event_files']} events, {messaging['marker_files']} markers)")
    else:
        print("  messaging files: none observed (isolated orchard runtime was never touched)")
    print(f"  wrote {out_path}")


def _pct_delta(before: float, after: float) -> str:
    if before == 0:
        return "n/a" if after == 0 else "+inf"
    return f"{(after - before) / before * 100:+.1f}%"


def cmd_compare(args: argparse.Namespace) -> None:
    before = json.loads(Path(args.before).read_text())
    after = json.loads(Path(args.after).read_text())

    print(f"BEFORE: {before['label']} @ {before['commit'][:12]}  "
          f"({before['charter_word_count']} charter words)")
    print(f"AFTER:  {after['label']} @ {after['commit'][:12]}  "
          f"({after['charter_word_count']} charter words)")
    print()

    rows = [
        ("charter words", before["charter_word_count"], after["charter_word_count"]),
        ("steps completed", before["totals"]["steps_ok"], after["totals"]["steps_ok"]),
        ("wall clock (s)", before["totals"]["wall_clock_s"], after["totals"]["wall_clock_s"]),
        ("claude cost (USD)", before["totals"]["total_cost_usd"], after["totals"]["total_cost_usd"]),
        ("input tokens", before["totals"]["input_tokens"], after["totals"]["input_tokens"]),
        ("output tokens", before["totals"]["output_tokens"], after["totals"]["output_tokens"]),
        ("cache read tokens", before["totals"]["cache_read_input_tokens"],
         after["totals"]["cache_read_input_tokens"]),
        ("cache create tokens", before["totals"]["cache_creation_input_tokens"],
         after["totals"]["cache_creation_input_tokens"]),
        ("messaging files total",
         before["messaging_layer"].get("files_total", 0),
         after["messaging_layer"].get("files_total", 0)),
        ("messaging event files (wakes)",
         before["messaging_layer"].get("event_files", 0),
         after["messaging_layer"].get("event_files", 0)),
    ]

    print(f"{'metric':30} {'before':>14} {'after':>14} {'delta':>10}")
    for name, b, a in rows:
        b_s = f"{b:.4f}" if isinstance(b, float) else str(b)
        a_s = f"{a:.4f}" if isinstance(a, float) else str(a)
        print(f"{name:30} {b_s:>14} {a_s:>14} {_pct_delta(b, a):>10}")

    print()
    print("per-step (before):")
    for i, s in enumerate(before["steps"]):
        u = s.get("usage") or {}
        print(f"  [{i}] ok={s.get('ok')} wall={s['wall_clock_s']:.1f}s "
              f"cost=${s.get('total_cost_usd') or 0:.4f} "
              f"in={u.get('input_tokens')} out={u.get('output_tokens')} "
              f"cache_read={u.get('cache_read_input_tokens')}")
    print("per-step (after):")
    for i, s in enumerate(after["steps"]):
        u = s.get("usage") or {}
        print(f"  [{i}] ok={s.get('ok')} wall={s['wall_clock_s']:.1f}s "
              f"cost=${s.get('total_cost_usd') or 0:.4f} "
              f"in={u.get('input_tokens')} out={u.get('output_tokens')} "
              f"cache_read={u.get('cache_read_input_tokens')}")

    if before.get("degraded") or after.get("degraded"):
        print()
        print("CAVEAT: at least one side is DEGRADED (not every scenario step "
              "completed) — totals above are partial on that side, not a full "
              "scenario comparison.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="run the static scenario against one checkout")
    p_run.add_argument("--checkout", required=True)
    p_run.add_argument("--label", required=True, choices=["before", "after"])
    p_run.add_argument("--out", required=True)
    p_run.set_defaults(func=cmd_run)

    p_cmp = sub.add_parser("compare", help="print before/after numbers side by side")
    p_cmp.add_argument("before")
    p_cmp.add_argument("after")
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

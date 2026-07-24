#!/usr/bin/env python3
"""Statistical engine behind the "bloomer" intake-measurement agent.

The bloomer turns a 2-3 sentence feature spec into a converged scope by
adaptive questioning. The LLM (agent) owns phrasing and parsing of questions
and answers; THIS SCRIPT owns question selection and stopping. It is a pure
statistical engine with no model calls of its own — stdlib only.

MODEL
-----
The latent variable is the intended feature. The agent decomposes it into
DIMENSIONS (scope aspects); each dimension carries 2-6 discrete candidate
HYPOTHESES. The engine holds one discrete posterior distribution per
dimension over that dimension's hypotheses, updated after every answer.

SELECTION (next)
-----------------
For each eligible dimension (see FUNNEL below), the engine scores:

    score = EIG(dimension) * fisher_info(dimension)

- EIG (expected information gain) is approximated by the dimension's current
  Shannon entropy in bits: H = -sum(p * log2(p)) over its posterior. This is
  the theoretical ceiling on how much a single well-chosen question could
  still teach the engine about that dimension, and is used as a ranking
  proxy rather than a probe-specific exact computation.
- fisher_info composes an IRT (2PL) layer on top: each dimension carries
  "last_item_params" {a, b} — the discrimination/difficulty the agent most
  recently asserted for an item on that dimension (a=1.0, b=0.0 by default
  before any item has been answered). A dimension's "ability" position theta
  is proxied by its NORMALIZED entropy (H / log2(hypothesis_count), in
  [0, 1]) — a fully-resolved dimension sits near theta=0, a maximally
  uncertain one near theta=1. Fisher information at that position is the
  standard 2PL form:
      P(theta) = 1 / (1 + exp(-a * (theta - b)))
      I(theta) = a^2 * P(theta) * (1 - P(theta))

Operator ruling: IRT/Fisher weighting is included despite the item
parameters being LLM-ASSUMED, not calibrated against real respondents.
Every `report` therefore carries "uncalibrated_items": true unconditionally,
and this is a first-calibration approximation, not a validated model.

The dimension with the highest score is probed next. Ties break on fewer
items already asked, then on dimension id, for determinism.

FUNNEL
------
Dimensions carry level "broad" or "narrow". While ANY broad dimension is
still active (not stopped), only broad dimensions are eligible for
selection — narrow dimensions are not probed until every broad dimension has
stopped (converged or exhausted).

ITEM FORM
---------
- multi_select dimension -> always "multi", probing every hypothesis at
  once (respondent selects the subset that applies).
- otherwise, rank hypotheses by current posterior mass. If the top two are
  within FORCED_CHOICE_GAP of each other -> "forced-choice", naming both.
  Otherwise -> "single", naming only the current top (MAP) hypothesis.

ANSWER UPDATE
-------------
The probe is scored as a 2PL item measuring the latent "this specific
hypothesis is the true one" (theta=1) versus "it is not" (theta=0):

    p_true  = P(theta=1; a, b)   # prob. of an endorsement if h really is true
    p_false = P(theta=0; a, b)   # prob. of an endorsement if h is not true (noise)

Exactly one hypothesis j is ever true, so the response is scored once per
CANDIDATE j (a categorical-latent likelihood): for every hypothesis h that
was probed, j's own membership uses p_true/(1-p_true), every OTHER probed
hypothesis (necessarily false whenever j is the true one) uses
p_false/(1-p_false). Hypotheses outside the probe contribute no factor.
j's unnormalized posterior weight is prior(j) times that product; the
dimension's posterior is the renormalized weights. This lets a "no" on the
current top hypothesis lift the rest even though they were never probed
directly.

STOPPING / STANDARD ERROR
--------------------------
Per-dimension standard error is the posterior std of the hypothesis INDEX
(hypotheses are 0..n-1 in declaration order), i.e. treat "which hypothesis"
as an ordinal-coded random variable under the current posterior:
    mean = sum(i * p_i)
    var  = sum(p_i * (i - mean)^2)
    SE   = sqrt(var)
This is a positional proxy for concentration, not a normalized metric
(unbounded comparability across dimensions with different hypothesis
counts is a known first-calibration limitation). A dimension stops once its
SE drops below SE_THRESHOLD ("converged") or its item count reaches
MAX_ITEMS_PER_DIMENSION ("exhausted"). The engine stops globally once every
dimension has stopped; the reported reason is "exhausted" if any dimension
stopped that way, else "converged".

PERSON-FIT (misfit)
--------------------
An lz-like statistic: for each probed hypothesis h, the MARGINAL expected
probability of the observed endorsement under the PRIOR (before this
update) is
    p_expect(h) = prior(h) * p_true + (1 - prior(h)) * p_false
The average log-likelihood of the observed response across the probed
hypotheses is compared to MISFIT_LOGLIK_THRESHOLD; falling below it flags
the dimension as misfitting — i.e. the answer was surprising given
everything believed so far, a candidate contradiction the agent must
surface to the respondent as a consistency check. The flag is sticky (not
auto-cleared) once set.

BANDS / LAUNCH SIZING (report)
-------------------------------
Band is "very-high" when overall SE (mean of per-dimension SE) is at or
below BAND_VERY_HIGH_SE AND there are zero misfit flags anywhere; "medium
-high" when overall SE is at or below BAND_MEDIUM_HIGH_SE; else "lower".
These thresholds are first-calibration values, not derived from data.

Launch sizing folds dimension count, residual uncertainty (overall SE) and
deferral count (dimensions stopped by exhaustion rather than convergence)
into one score:
    size_score = dimension_count + overall_se * 10 + deferral_count * 3
mapped to s / m / l against LAUNCH_SIZE_S_MAX / LAUNCH_SIZE_M_MAX (first-
calibration constants below). Each size maps to a model/effort tier that
MIRRORS the current per-role table (docs/decisions.md Decision-018,
Decision-019, as of 2026-07-20):
    s -> claude-sonnet-5 / high    (the builder tier: a small, short-lived
                                     build handled inline)
    m -> claude-opus-4-8 / xhigh   (the architect's pegged default)
    l -> claude-fable-5 / high     (the top of the architect's complexity
                                     scaling, "the hardest long-horizon
                                     builds")
This mapping is descriptive guidance for the operator/orchestrator, not an
authority over the live per-role table — if that table changes, update
MODEL_TIER to match.

PRIORS (stub)
-------------
`init --priors <json-file>` is optional; absent, every dimension starts
uniform over its hypotheses. When given, the file must be a JSON object
{dimension_id: {hypothesis_id: weight}}; weights are non-negative numbers,
renormalized per dimension (a dimension/hypothesis absent from the file
falls back to uniform). v1 accepts and validates this shape only — nothing
more. The intended FUTURE feed (not built here) is corpus-derived priors,
mined from the operator's own agentic-work corpus: every repo under
~/src/serialseb and ~/src/SafeKeepIt.

CLI
---
See --help on each subcommand. All state lives in a JSON file at --state;
all I/O is JSON on stdout; invalid input exits non-zero with a message on
stderr.
"""
import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

SE_THRESHOLD = 0.35
MAX_ITEMS_PER_DIMENSION = 6
FORCED_CHOICE_GAP = 0.15

BAND_VERY_HIGH_SE = 0.20
BAND_MEDIUM_HIGH_SE = 0.35

MISFIT_LOGLIK_THRESHOLD = math.log(0.2)  # ~= -1.609, per-item average

LAUNCH_SIZE_S_MAX = 6.0
LAUNCH_SIZE_M_MAX = 12.0

MODEL_TIER = {
    "s": {"model": "claude-sonnet-5", "effort": "high"},
    "m": {"model": "claude-opus-4-8", "effort": "xhigh"},
    "l": {"model": "claude-fable-5", "effort": "high"},
}


def read_json_arg(path_str: str):
    if path_str == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def load_state(path: Path) -> dict:
    if not path.is_file():
        sys.exit(f"bloom_engine: no state file at {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"bloom_engine: state file corrupt: {exc}")


def save_state(path: Path, state: dict) -> None:
    """Write atomically so a reader never observes a half-written state file."""
    tmp = path.with_name(path.name + ".partial")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def validate_dimensions(raw) -> list:
    if not isinstance(raw, list) or not raw:
        raise ValueError("dimensions must be a non-empty JSON array")
    seen_ids = set()
    for d in raw:
        if not isinstance(d, dict):
            raise ValueError(f"dimension entry must be an object: {d!r}")
        for key in ("id", "question_topic", "level", "multi_select", "hypotheses"):
            if key not in d:
                raise ValueError(f"dimension missing required field {key!r}: {d!r}")
        if d["id"] in seen_ids:
            raise ValueError(f"duplicate dimension id {d['id']!r}")
        seen_ids.add(d["id"])
        if d["level"] not in ("broad", "narrow"):
            raise ValueError(f"dimension {d['id']!r} level must be 'broad' or 'narrow'")
        if not isinstance(d["multi_select"], bool):
            raise ValueError(f"dimension {d['id']!r} multi_select must be boolean")
        hyps = d["hypotheses"]
        if not isinstance(hyps, list) or not (2 <= len(hyps) <= 6):
            raise ValueError(f"dimension {d['id']!r} must carry 2-6 hypotheses")
        hyp_ids = set()
        for h in hyps:
            if not isinstance(h, dict) or "id" not in h or "label" not in h:
                raise ValueError(f"dimension {d['id']!r} hypothesis missing id/label: {h!r}")
            if h["id"] in hyp_ids:
                raise ValueError(f"dimension {d['id']!r} duplicate hypothesis id {h['id']!r}")
            hyp_ids.add(h["id"])
    return raw


def validate_priors(dims: list, priors_raw) -> dict:
    if not isinstance(priors_raw, dict):
        raise ValueError("priors must be a JSON object of {dimension_id: {hypothesis_id: weight}}")
    by_dim = {d["id"]: [h["id"] for h in d["hypotheses"]] for d in dims}
    for dim_id, weights in priors_raw.items():
        if dim_id not in by_dim:
            raise ValueError(f"priors reference unknown dimension {dim_id!r}")
        if not isinstance(weights, dict):
            raise ValueError(f"priors for dimension {dim_id!r} must be an object")
        for hyp_id, w in weights.items():
            if hyp_id not in by_dim[dim_id]:
                raise ValueError(f"priors for {dim_id!r} reference unknown hypothesis {hyp_id!r}")
            if not isinstance(w, (int, float)) or isinstance(w, bool) or w < 0:
                raise ValueError(f"priors weight for {dim_id!r}/{hyp_id!r} must be a non-negative number")
    return priors_raw


def build_state(dims: list, priors: dict | None = None) -> dict:
    dimensions = {}
    for d in dims:
        hyp_ids = [h["id"] for h in d["hypotheses"]]
        labels = {h["id"]: h["label"] for h in d["hypotheses"]}
        weights = None
        if priors and d["id"] in priors:
            given = priors[d["id"]]
            candidate = {hid: float(given.get(hid, 0.0)) for hid in hyp_ids}
            if sum(candidate.values()) > 0:
                weights = candidate
        if weights is None:
            weights = {hid: 1.0 for hid in hyp_ids}
        total = sum(weights.values())
        posterior = {hid: w / total for hid, w in weights.items()}
        dimensions[d["id"]] = {
            "question_topic": d["question_topic"],
            "level": d["level"],
            "multi_select": d["multi_select"],
            "hypothesis_ids": hyp_ids,
            "labels": labels,
            "posterior": posterior,
            "history": [],
            "item_count": 0,
            "last_item_params": {"a": 1.0, "b": 0.0},
            "stopped": False,
            "stop_reason": None,
            "misfit": False,
            "misfit_flags": [],
        }
    return {
        "created": datetime.now(timezone.utc).isoformat(),
        "priors_used": bool(priors),
        "dimensions": dimensions,
    }


def entropy_bits(dist: dict) -> float:
    return -sum(p * math.log2(p) for p in dist.values() if p > 0)


def index_se(dim: dict) -> float:
    """SE formula: sqrt of the posterior variance of the ordinal hypothesis
    index. See module docstring "STOPPING / STANDARD ERROR"."""
    ids = dim["hypothesis_ids"]
    post = dim["posterior"]
    n = len(ids)
    if n <= 1:
        return 0.0
    mean = sum(i * post[ids[i]] for i in range(n))
    var = sum(post[ids[i]] * (i - mean) ** 2 for i in range(n))
    return math.sqrt(var)


def normalized_entropy(dim: dict) -> float:
    n = len(dim["hypothesis_ids"])
    if n <= 1:
        return 0.0
    max_h = math.log2(n)
    return entropy_bits(dim["posterior"]) / max_h if max_h > 0 else 0.0


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def p2pl(a: float, b: float, theta: float) -> float:
    return sigmoid(a * (theta - b))


def fisher_info(a: float, b: float, theta: float) -> float:
    p = p2pl(a, b, theta)
    return (a ** 2) * p * (1 - p)


def update_stop_status(dim: dict) -> float:
    """Recompute (idempotently) whether `dim` has stopped; returns its SE."""
    se = index_se(dim)
    if not dim["stopped"]:
        if se < SE_THRESHOLD:
            dim["stopped"] = True
            dim["stop_reason"] = "converged"
        elif dim["item_count"] >= MAX_ITEMS_PER_DIMENSION:
            dim["stopped"] = True
            dim["stop_reason"] = "exhausted"
    return se


def select_next(state: dict) -> dict:
    dims = state["dimensions"]
    for dim in dims.values():
        update_stop_status(dim)

    active = {did: d for did, d in dims.items() if not d["stopped"]}
    if not active:
        reasons = {d["stop_reason"] for d in dims.values()}
        reason = "exhausted" if "exhausted" in reasons else "converged"
        return {"stop": True, "reason": reason}

    broad_active = {did: d for did, d in active.items() if d["level"] == "broad"}
    eligible = broad_active if broad_active else active

    scored = []
    for did, d in eligible.items():
        eig = entropy_bits(d["posterior"])
        theta = normalized_entropy(d)
        params = d["last_item_params"]
        fi = fisher_info(params["a"], params["b"], theta)
        scored.append((eig * fi, d["item_count"], did, eig, fi))
    scored.sort(key=lambda t: (-t[0], t[1], t[2]))
    _, _, chosen_id, eig, fi = scored[0]

    dim = dims[chosen_id]
    ids = dim["hypothesis_ids"]
    ranked = sorted(ids, key=lambda hid: -dim["posterior"][hid])

    if dim["multi_select"]:
        item_form = "multi"
        probe = list(ids)
    elif len(ranked) >= 2 and (dim["posterior"][ranked[0]] - dim["posterior"][ranked[1]]) <= FORCED_CHOICE_GAP:
        item_form = "forced-choice"
        probe = ranked[:2]
    else:
        item_form = "single"
        probe = ranked[:1]

    return {
        "stop": False,
        "dimension": chosen_id,
        "item_form": item_form,
        "probe_hypotheses": probe,
        "funnel_level": dim["level"],
        "rationale": {"eig": round(eig, 6), "fisher_info": round(fi, 6)},
    }


def validate_item(state: dict, item: dict):
    if not isinstance(item, dict):
        raise ValueError("item must be a JSON object")
    for key in ("dimension", "probe_hypotheses", "response", "item_params"):
        if key not in item:
            raise ValueError(f"item missing required field {key!r}")
    did = item["dimension"]
    if did not in state["dimensions"]:
        raise ValueError(f"unknown dimension {did!r}")
    dim = state["dimensions"][did]
    probe = item["probe_hypotheses"]
    if not isinstance(probe, list) or not probe:
        raise ValueError("probe_hypotheses must be a non-empty list")
    for hid in probe:
        if hid not in dim["hypothesis_ids"]:
            raise ValueError(f"probe_hypotheses references unknown hypothesis {hid!r} for dimension {did!r}")
    response = item["response"]
    if not isinstance(response, list):
        raise ValueError("response must be a list")
    for hid in response:
        if hid not in probe:
            raise ValueError(f"response id {hid!r} was not among probe_hypotheses")
    params = item["item_params"]
    if not isinstance(params, dict) or "a" not in params or "b" not in params:
        raise ValueError("item_params must carry 'a' and 'b'")
    a, b = params["a"], params["b"]
    if not isinstance(a, (int, float)) or isinstance(a, bool) or a <= 0:
        raise ValueError("item_params.a (discrimination) must be a positive number")
    if not isinstance(b, (int, float)) or isinstance(b, bool):
        raise ValueError("item_params.b (difficulty) must be a number")
    return did, dim, probe, response, float(a), float(b)


def apply_answer(state: dict, item: dict) -> dict:
    did, dim, probe, response, a, b = validate_item(state, item)
    prior = dict(dim["posterior"])
    p_true = p2pl(a, b, 1.0)
    p_false = p2pl(a, b, 0.0)
    eps = 1e-9

    ll = 0.0
    for hid in probe:
        pr = prior[hid]
        endorsed = hid in response
        p_expect = min(max(pr * p_true + (1 - pr) * p_false, eps), 1 - eps)
        ll += math.log(p_expect) if endorsed else math.log(1 - p_expect)

    # Categorical-latent likelihood: exactly one hypothesis j is true, so the
    # observed response over `probe` is scored once PER CANDIDATE j — j's own
    # probed membership uses p_true/(1-p_true), every OTHER probed hypothesis
    # (which is false whenever j is true) uses p_false/(1-p_false). This is
    # what lets a "no" on the current top hypothesis lift hypotheses it was
    # never directly asked about.
    weights = {}
    for j in dim["hypothesis_ids"]:
        likelihood = 1.0
        for hid in probe:
            endorsed = hid in response
            if hid == j:
                likelihood *= p_true if endorsed else (1 - p_true)
            else:
                likelihood *= p_false if endorsed else (1 - p_false)
        weights[j] = prior[j] * likelihood

    total = sum(weights.values())
    if total <= 0:
        weights = {hid: 1.0 for hid in dim["hypothesis_ids"]}
        total = float(len(weights))
    dim["posterior"] = {hid: w / total for hid, w in weights.items()}

    avg_ll = ll / len(probe)
    misfit_now = avg_ll < MISFIT_LOGLIK_THRESHOLD

    dim["history"].append({
        "probe_hypotheses": probe,
        "response": response,
        "item_params": {"a": a, "b": b},
        "avg_ll": round(avg_ll, 6),
        "misfit": misfit_now,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    dim["last_item_params"] = {"a": a, "b": b}
    dim["item_count"] += 1
    if misfit_now:
        dim["misfit"] = True
        dim["misfit_flags"].append({
            "dimension": did,
            "item_index": dim["item_count"],
            "avg_ll": round(avg_ll, 6),
            "probe_hypotheses": probe,
            "response": response,
        })

    se = update_stop_status(dim)
    return {"se": round(se, 6), "misfit": misfit_now}


def build_report(state: dict) -> dict:
    dims = state["dimensions"]
    for d in dims.values():
        update_stop_status(d)

    per_dim = {}
    ses = []
    misfit_flags = []
    deferral_candidates = []
    for did, d in dims.items():
        se = index_se(d)
        ses.append(se)
        top = max(d["hypothesis_ids"], key=lambda hid: d["posterior"][hid])
        per_dim[did] = {
            "se": round(se, 6),
            "stopped": d["stopped"],
            "stop_reason": d["stop_reason"],
            "item_count": d["item_count"],
            "top_hypothesis": top,
            "misfit": d["misfit"],
        }
        for flag in d["misfit_flags"]:
            misfit_flags.append(dict(flag))
        if d["stop_reason"] == "exhausted":
            deferral_candidates.append(did)

    overall_se = sum(ses) / len(ses) if ses else 0.0
    if overall_se <= BAND_VERY_HIGH_SE and not misfit_flags:
        band = "very-high"
    elif overall_se <= BAND_MEDIUM_HIGH_SE:
        band = "medium-high"
    else:
        band = "lower"

    dim_count = len(dims)
    deferral_count = len(deferral_candidates)
    size_score = dim_count + overall_se * 10.0 + deferral_count * 3.0
    if size_score < LAUNCH_SIZE_S_MAX:
        size = "s"
    elif size_score < LAUNCH_SIZE_M_MAX:
        size = "m"
    else:
        size = "l"
    tier = MODEL_TIER[size]

    return {
        "convergence": {"overall_se": round(overall_se, 6), "per_dimension": per_dim},
        "band": band,
        "uncalibrated_items": True,
        "misfit_flags": misfit_flags,
        "deferral_candidates": deferral_candidates,
        "launch_sizing": {"size": size, "model": tier["model"], "effort": tier["effort"]},
    }


def cmd_init(args) -> None:
    try:
        dims = validate_dimensions(read_json_arg(args.dimensions))
        priors = None
        if args.priors:
            priors = validate_priors(dims, read_json_arg(args.priors))
        state = build_state(dims, priors)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.exit(f"bloom_engine: init failed: {exc}")
    save_state(Path(args.state), state)
    print(json.dumps({
        "initialized": True,
        "dimensions": list(state["dimensions"].keys()),
        "priors_used": state["priors_used"],
    }, indent=2))


def cmd_next(args) -> None:
    state = load_state(Path(args.state))
    result = select_next(state)
    save_state(Path(args.state), state)
    print(json.dumps(result, indent=2))


def cmd_answer(args) -> None:
    state = load_state(Path(args.state))
    try:
        item = read_json_arg(args.item)
        result = apply_answer(state, item)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.exit(f"bloom_engine: answer failed: {exc}")
    save_state(Path(args.state), state)
    print(json.dumps(result, indent=2))


def cmd_report(args) -> None:
    state = load_state(Path(args.state))
    result = build_report(state)
    save_state(Path(args.state), state)
    print(json.dumps(result, indent=2))


def _selftest_dimensions() -> list:
    return [
        {
            "id": "scope_shape", "question_topic": "what shape is the feature",
            "level": "broad", "multi_select": False,
            "hypotheses": [
                {"id": "single_service", "label": "single service"},
                {"id": "multi_service", "label": "multi service"},
                {"id": "platform", "label": "platform-wide"},
            ],
        },
        {
            "id": "delivery_target", "question_topic": "where does it ship",
            "level": "broad", "multi_select": False,
            "hypotheses": [
                {"id": "web", "label": "web"},
                {"id": "cli", "label": "cli"},
            ],
        },
        {
            "id": "auth_model", "question_topic": "what auth does it need",
            "level": "narrow", "multi_select": False,
            "hypotheses": [
                {"id": "none", "label": "no auth"},
                {"id": "token", "label": "token"},
                {"id": "oauth", "label": "oauth"},
            ],
        },
    ]


_SELFTEST_TRUTH = {
    "scope_shape": "single_service",
    "delivery_target": "cli",
    "auth_model": "oauth",
}


def _two_hyp_dimension(dim_id: str) -> list:
    return [{
        "id": dim_id, "question_topic": "binary check", "level": "broad",
        "multi_select": False,
        "hypotheses": [{"id": "a", "label": "a"}, {"id": "b", "label": "b"}],
    }]


def cmd_selftest(args) -> None:
    """Deterministic simulated respondent — no randomness. Four independent,
    hand-tuned scenarios (documented inline), one per required assertion, so
    each is checked under conditions that reliably trigger it rather than
    hoping a single shared run happens to exercise all four."""
    checks = []

    # (1) Convergence: a 3-dimension space, all-consistent answers, funnel
    # (broad before narrow) exercised implicitly by dimension levels.
    dims = _selftest_dimensions()
    state = build_state(dims)
    stop_result = {"stop": False}
    for _ in range(200):
        stop_result = select_next(state)
        if stop_result["stop"]:
            break
        did = stop_result["dimension"]
        probe = stop_result["probe_hypotheses"]
        truth = _SELFTEST_TRUTH[did]
        response = [truth] if truth in probe else []
        apply_answer(state, {
            "dimension": did, "probe_hypotheses": probe, "response": response,
            "item_params": {"a": 1.6, "b": 0.0},
        })
    converged = stop_result.get("stop") is True and all(
        max(d["hypothesis_ids"], key=lambda h: d["posterior"][h]) == _SELFTEST_TRUTH[did]
        for did, d in state["dimensions"].items()
    )
    checks.append(("convergence to scripted truth on a 3-dimension space", converged))

    # (2) SE-threshold stop fires before MAX_ITEMS: a single 2-hypothesis
    # dimension, consistent answers at moderate discrimination (a=1.4) cross
    # SE_THRESHOLD well inside the item budget.
    se_state = build_state(_two_hyp_dimension("se_check"))
    se_stop = {"stop": False}
    for _ in range(MAX_ITEMS_PER_DIMENSION + 5):
        se_stop = select_next(se_state)
        if se_stop["stop"]:
            break
        probe = se_stop["probe_hypotheses"]
        response = ["a"] if "a" in probe else []
        apply_answer(se_state, {
            "dimension": "se_check", "probe_hypotheses": probe, "response": response,
            "item_params": {"a": 1.4, "b": 0.0},
        })
    se_dim = se_state["dimensions"]["se_check"]
    early_stop = (
        se_stop.get("stop") is True and se_stop.get("reason") == "converged"
        and se_dim["stop_reason"] == "converged"
        and se_dim["item_count"] < MAX_ITEMS_PER_DIMENSION
    )
    checks.append(("SE-threshold stop fires before MAX_ITEMS", early_stop))

    # (3) Misfit: build confidence in "a" with two consistent, moderate-
    # discrimination answers, then feed one strongly-discriminating answer
    # that directly contradicts the now-confident belief.
    misfit_state = build_state(_two_hyp_dimension("misfit_check"))
    for _ in range(2):
        apply_answer(misfit_state, {
            "dimension": "misfit_check", "probe_hypotheses": ["a"], "response": ["a"],
            "item_params": {"a": 1.4, "b": 0.0},
        })
    contradiction = apply_answer(misfit_state, {
        "dimension": "misfit_check", "probe_hypotheses": ["a"], "response": [],
        "item_params": {"a": 3.0, "b": 0.0},
    })
    misfit_flagged = (
        contradiction["misfit"] is True
        and misfit_state["dimensions"]["misfit_check"]["misfit"] is True
    )
    checks.append(("scripted contradictory answer raises a misfit flag", misfit_flagged))

    # (4) Bands: the misfit scenario above must NOT read "very-high" (a
    # misfit flag disqualifies it); a clean, tightly-converged dimension
    # (strong discrimination, all-consistent) must read "very-high".
    report_misfit = build_report(misfit_state)
    bands_negative = len(report_misfit["misfit_flags"]) >= 1 and report_misfit["band"] != "very-high"

    clean_state = build_state(_two_hyp_dimension("clean_check"))
    for _ in range(6):
        apply_answer(clean_state, {
            "dimension": "clean_check", "probe_hypotheses": ["a"], "response": ["a"],
            "item_params": {"a": 2.5, "b": 0.0},
        })
    report_clean = build_report(clean_state)
    bands_positive = report_clean["band"] == "very-high"

    checks.append(("report bands correctly (misfit case demoted, clean case very-high)",
                    bands_negative and bands_positive))

    all_pass = True
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {name}")
        all_pass = all_pass and ok
    sys.exit(0 if all_pass else 1)


def main() -> None:
    p = argparse.ArgumentParser(description="bloomer intake-measurement statistical engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init")
    s.add_argument("--state", required=True)
    s.add_argument("--dimensions", required=True)
    s.add_argument("--priors")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("next")
    s.add_argument("--state", required=True)
    s.set_defaults(func=cmd_next)

    s = sub.add_parser("answer")
    s.add_argument("--state", required=True)
    s.add_argument("--item", required=True)
    s.set_defaults(func=cmd_answer)

    s = sub.add_parser("report")
    s.add_argument("--state", required=True)
    s.set_defaults(func=cmd_report)

    sub.add_parser("selftest").set_defaults(func=cmd_selftest)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

"""Generate aggregate publication summaries without copying native task logs."""

from collections import Counter
import json
import math
from pathlib import Path


TOKEN_KEYS = ("input_tokens", "output_tokens", "thinking_tokens")
# Tasks that closely resemble tasks in Aria Code's own evaluation suites, which the product
# may have been tuned against. Summaries report completion with and without them.
OVERLAP_TAG = "overlaps-engine-suite"


def _count(value) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("Usage counts must be non-negative integers")
    return value


def usage_summary(native_usage, trials: int):
    """Token totals the engine reported, or None when no trial reported any.

    ``reported_trials`` travels with the totals: tokens over 12 of 30 trials are
    not the cost of the run and must not be read as one.
    """
    if native_usage is None:
        return None
    if not isinstance(native_usage, dict):
        raise ValueError("Native usage must be an object")
    reported = _count(native_usage.get("reported", 0))
    if reported > trials:
        raise ValueError("More trials reported usage than were run")
    totals = {key: _count(native_usage.get(key, 0)) for key in TOKEN_KEYS}
    # A record of nothing but zeros is a missing report, not a free run: OpenAI and DeepSeek
    # streams once recorded 0 tokens. Only the aggregate is visible here; the engine decides
    # whether one trial's all-zero record counts towards ``reported`` (see the README).
    if reported == 0 or not any(totals.values()):
        return None
    return {"reported_trials": reported, "trials": trials, **totals}


def load_prices(path: Path) -> dict:
    """A dated price table: who said what a million tokens costs, and when."""
    table = json.loads(path.read_text(encoding="utf-8"))
    per_million = table.get("per_million_tokens") if isinstance(table, dict) else None
    if (not isinstance(per_million, dict) or not isinstance(table.get("as_of"), str) or not table["as_of"]
            or not isinstance(table.get("source"), str) or not table["source"].startswith("https://")
            or table.get("currency") != "USD"):
        raise ValueError("A price table needs as_of, an https source, currency USD and per_million_tokens")
    rates = {}
    for key in ("input", "output", "thinking"):
        value = per_million.get(key, per_million.get("output") if key == "thinking" else None)
        if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
            raise ValueError(f"per_million_tokens.{key} must be a non-negative number")
        rates[key] = float(value)
    return {"as_of": table["as_of"], "source": table["source"], "per_million_tokens": rates}


def cost_summary(usage, prices):
    if not usage or not prices:
        return None
    rates = prices["per_million_tokens"]
    usd = (usage["input_tokens"] * rates["input"] + usage["output_tokens"] * rates["output"]
           + usage["thinking_tokens"] * rates["thinking"]) / 1_000_000
    # Named for what it is: the priced tokens of the trials that reported usage, which is the
    # cost of the run only when every trial reported.
    return {"usd_reported_trials": round(usd, 6), "complete": usage["reported_trials"] == usage["trials"],
            "as_of": prices["as_of"], "source": prices["source"],
            "per_million_tokens": rates, "covers_trials": usage["reported_trials"], "of_trials": usage["trials"]}


def publication_summary(native: dict, manifest: dict, prices=None) -> dict:
    if manifest.get("run_kind") not in {"model_free_preflight", "model_evaluation"}:
        raise ValueError("Reports need an explicit run kind")
    trials = native.get("results")
    if not isinstance(trials, list) or not trials:
        raise ValueError("Native results must contain trials")
    outcomes = []
    seconds = 0.0
    timed_out = 0
    independent = []
    for result in trials:
        if not isinstance(result, dict) or result.get("outcome") not in {"pass", "fail", "invalid", "error"}:
            raise ValueError("Unknown trial outcome")
        duration = result.get("seconds", 0)
        if type(duration) not in {int, float} or not math.isfinite(duration) or duration < 0:
            raise ValueError("Invalid trial duration")
        outcomes.append(result["outcome"])
        seconds += duration
        # An agent stopped by --solve-timeout whose check is still red is an error that the
        # scored-only rate leaves out. Newer engines flag it with timed_out: true; the pinned
        # one records it only as exit 124.
        flag = result.get("timed_out")
        if flag is not None and type(flag) is not bool:
            raise ValueError("timed_out must be a boolean")
        if result["outcome"] == "error" and (flag is True or (flag is None and type(result.get("exit_code")) is int
                                                               and result["exit_code"] == 124)):
            timed_out += 1
        tags = result.get("tags")
        if not (isinstance(tags, list) and OVERLAP_TAG in tags):
            independent.append(result["outcome"])
    counts = Counter(outcomes)
    is_model = manifest["run_kind"] == "model_evaluation"
    scored = counts["pass"] + counts["fail"]
    # Reconstruct metrics; never trust arbitrary upstream text or copy per-task objects.
    allowed = ("schema_version", "run_kind", "catalog_version", "catalog_commit", "catalog_sha256",
               "catalog_dirty", "engine_commit", "engine_version", "model", "provider", "repeat", "solve_timeout_seconds")
    context = {key: manifest.get(key) for key in allowed}
    usage = usage_summary(native.get("usage"), len(trials)) if is_model else None
    cost = cost_summary(usage, prices)
    complete_cost = bool(cost and cost["complete"])
    # Completion over every trial leads. The scored-only rate leaves out invalid and errored
    # trials, so it rises when an agent times out on the tasks it would fail; the unscored
    # trials are therefore listed beside it, with timeouts apart from other errors.
    performance = {"completion_rate_all_trials": counts["pass"] / len(trials),
                   "unscored_trials": {"timed_out": timed_out, "other_error": counts["error"] - timed_out,
                                       "invalid": counts["invalid"]},
                   "scored_trials": scored,
                   "native_pass_rate_scored_only": counts["pass"] / scored if scored else None,
                   "without_engine_suite_overlap": {
                       "trials": len(independent),
                       "completion_rate_all_trials": independent.count("pass") / len(independent) if independent else None}}
    return {"schema_version": 1, "context": context, "trials": len(trials),
            "counts": {outcome: counts[outcome] for outcome in ("pass", "fail", "invalid", "error")},
            "errors": {"timed_out": timed_out, "other": counts["error"] - timed_out},
            "duration_seconds": round(seconds, 6),
            "performance": performance if is_model else None,
            "usage": usage,
            "cost_usd": cost["usd_reported_trials"] if complete_cost else None,
            "cost_usd_partial": cost["usd_reported_trials"] if cost and not complete_cost else None,
            "cost_basis": cost,
            "limitations": ("Small public demonstration suite; prior exposure is possible. Unavailable usage is "
                            "null; usage covers only the trials that reported usage, and cost_usd is null unless "
                            "every trial did (cost_usd_partial then prices the trials that reported).")}


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

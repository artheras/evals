"""Generate aggregate publication summaries without copying native task logs."""

from collections import Counter
import json
import math
from pathlib import Path


def publication_summary(native: dict, manifest: dict) -> dict:
    if manifest.get("run_kind") not in {"model_free_preflight", "model_evaluation"}:
        raise ValueError("Reports need an explicit run kind")
    trials = native.get("results")
    if not isinstance(trials, list) or not trials:
        raise ValueError("Native results must contain trials")
    outcomes = []
    seconds = 0.0
    for result in trials:
        if not isinstance(result, dict) or result.get("outcome") not in {"pass", "fail", "invalid", "error"}:
            raise ValueError("Unknown trial outcome")
        duration = result.get("seconds", 0)
        if type(duration) not in {int, float} or not math.isfinite(duration) or duration < 0:
            raise ValueError("Invalid trial duration")
        outcomes.append(result["outcome"])
        seconds += duration
    counts = Counter(outcomes)
    is_model = manifest["run_kind"] == "model_evaluation"
    scored = counts["pass"] + counts["fail"]
    # Reconstruct metrics; never trust arbitrary upstream text or copy per-task objects.
    allowed = ("schema_version", "run_kind", "catalog_version", "catalog_commit", "catalog_sha256",
               "catalog_dirty", "engine_commit", "engine_version", "model", "provider", "repeat", "solve_timeout_seconds")
    context = {key: manifest.get(key) for key in allowed}
    return {"schema_version": 1, "context": context, "trials": len(trials),
            "counts": {outcome: counts[outcome] for outcome in ("pass", "fail", "invalid", "error")},
            "duration_seconds": round(seconds, 6),
            "performance": {"completion_rate_all_trials": counts["pass"] / len(trials),
                            "native_pass_rate_scored_only": counts["pass"] / scored if scored else None}
                           if is_model else None,
            "usage": None, "cost_usd": None,
            "limitations": "Small public demonstration suite; prior exposure is possible. Unavailable usage is null."}


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

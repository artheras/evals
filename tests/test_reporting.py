import json

import pytest

from aria_evals.reporting import publication_summary, write_json


def native(*outcomes):
    return {"pass_rate": 999, "results": [
        {"outcome": outcome, "seconds": 1.25, "prompt": "PRIVATE SENTINEL",
         "detail": "PRIVATE SENTINEL", "log_tail": "PRIVATE SENTINEL",
         "changed": ["PRIVATE SENTINEL"], "task_id": "PRIVATE SENTINEL"}
        for outcome in outcomes]}


def test_summary_recomputes_both_denominators_and_omits_logs():
    summary = publication_summary(native("pass", "fail", "invalid", "error"),
                                  {"run_kind": "model_evaluation", "prompt": "PRIVATE SENTINEL"})
    assert summary["performance"] == {"completion_rate_all_trials": 0.25, "native_pass_rate_scored_only": 0.5}
    assert summary["counts"] == {"pass": 1, "fail": 1, "invalid": 1, "error": 1}
    assert "PRIVATE SENTINEL" not in json.dumps(summary)
    assert summary["usage"] is None and summary["cost_usd"] is None


def test_preflight_never_presents_a_model_score():
    summary = publication_summary(native("fail", "fail", "fail"), {"run_kind": "model_free_preflight"})
    assert summary["performance"] is None
    assert summary["trials"] == 3


def test_all_errors_cannot_become_a_passing_model_score():
    summary = publication_summary(native("error"), {"run_kind": "model_evaluation"})
    assert summary["performance"] == {"completion_rate_all_trials": 0, "native_pass_rate_scored_only": None}


@pytest.mark.parametrize("record", [
    {"outcome": "unknown"}, {"outcome": "pass", "seconds": -1},
    {"outcome": "fail", "seconds": float("nan")},
    {"outcome": "pass", "seconds": True},
])
def test_invalid_trials_are_rejected(record):
    with pytest.raises(ValueError):
        publication_summary({"results": [record]}, {"run_kind": "model_evaluation"})


def test_missing_trials_or_mode_are_rejected():
    with pytest.raises(ValueError):
        publication_summary({"results": []}, {"run_kind": "model_evaluation"})
    with pytest.raises(ValueError):
        publication_summary(native("pass"), {})


def test_existing_report_cannot_be_overwritten(tmp_path):
    path = tmp_path / "summary.json"
    write_json(path, {"existing": True})
    with pytest.raises(FileExistsError):
        write_json(path, {"existing": False})
    assert json.loads(path.read_text()) == {"existing": True}

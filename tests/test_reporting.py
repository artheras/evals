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
    assert summary["performance"] == {"completion_rate_all_trials": 0.25,
                                      "unscored_trials": {"timed_out": 0, "other_error": 1, "invalid": 1},
                                      "scored_trials": 2, "native_pass_rate_scored_only": 0.5,
                                      "without_engine_suite_overlap": {"trials": 4, "completion_rate_all_trials": 0.25}}
    assert list(summary["performance"])[0] == "completion_rate_all_trials"
    assert summary["counts"] == {"pass": 1, "fail": 1, "invalid": 1, "error": 1}
    assert "PRIVATE SENTINEL" not in json.dumps(summary)
    assert summary["usage"] is None and summary["cost_usd"] is None


def test_preflight_never_presents_a_model_score():
    summary = publication_summary(native("fail", "fail", "fail"), {"run_kind": "model_free_preflight"})
    assert summary["performance"] is None
    assert summary["trials"] == 3


def test_all_errors_cannot_become_a_passing_model_score():
    summary = publication_summary(native("error"), {"run_kind": "model_evaluation"})
    assert summary["performance"]["completion_rate_all_trials"] == 0
    assert summary["performance"]["native_pass_rate_scored_only"] is None


def test_timing_out_is_counted_apart_and_cannot_hide_behind_the_scored_rate():
    records = [{"outcome": "pass", "seconds": 1.0}, {"outcome": "fail", "seconds": 1.0},
               {"outcome": "error", "seconds": 900.0, "exit_code": 124},
               {"outcome": "error", "seconds": 900.0, "exit_code": 1, "timed_out": True},
               {"outcome": "error", "seconds": 3.0, "exit_code": 124, "timed_out": False}]
    summary = publication_summary({"results": records}, {"run_kind": "model_evaluation"})
    assert summary["errors"] == {"timed_out": 2, "other": 1}
    assert summary["performance"]["unscored_trials"] == {"timed_out": 2, "other_error": 1, "invalid": 0}
    assert summary["performance"]["completion_rate_all_trials"] == pytest.approx(0.2)
    assert summary["performance"]["native_pass_rate_scored_only"] == 0.5


@pytest.mark.parametrize("record", [
    {"outcome": "unknown"}, {"outcome": "pass", "seconds": -1},
    {"outcome": "fail", "seconds": float("nan")},
    {"outcome": "pass", "seconds": True},
    {"outcome": "error", "seconds": 1.0, "timed_out": "yes"},
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


def test_completion_is_also_reported_without_tasks_that_overlap_the_engine_suites():
    records = [{"outcome": "pass", "seconds": 1.0, "tags": ["finance", "overlaps-engine-suite"]},
               {"outcome": "pass", "seconds": 1.0, "tags": ["overlaps-engine-suite"]},
               {"outcome": "fail", "seconds": 1.0, "tags": ["finance"]},
               {"outcome": "pass", "seconds": 1.0}]
    summary = publication_summary({"results": records}, {"run_kind": "model_evaluation"})
    assert summary["performance"]["completion_rate_all_trials"] == 0.75
    assert summary["performance"]["without_engine_suite_overlap"] == {"trials": 2, "completion_rate_all_trials": 0.5}
    assert "finance" not in json.dumps(summary)

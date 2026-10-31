import json
from pathlib import Path

import pytest
import yaml

from aria_evals.reporting import load_prices, publication_summary

MODEL_RUN = {"run_kind": "model_evaluation"}


def native(usage, outcomes=("pass", "fail", "error")):
    return {"usage": usage, "results": [{"outcome": o, "seconds": 2.0} for o in outcomes]}


def prices(tmp_path, **override):
    table = {"as_of": "2026-10-21", "source": "https://example.com/pricing", "currency": "USD",
             "per_million_tokens": {"input": 2.0, "output": 8.0}, **override}
    path = tmp_path / "prices.json"
    path.write_text(json.dumps(table))
    return path


def test_usage_is_reported_with_how_many_trials_it_covers():
    summary = publication_summary(native({"reported": 2, "tasks": 3, "input_tokens": 1000,
                                          "output_tokens": 300, "thinking_tokens": 100}), MODEL_RUN)
    assert summary["usage"] == {"reported_trials": 2, "trials": 3, "input_tokens": 1000,
                                "output_tokens": 300, "thinking_tokens": 100}
    assert summary["cost_usd"] is None and summary["cost_basis"] is None


def test_cost_comes_only_from_a_dated_price_table_and_names_its_source(tmp_path):
    table = load_prices(prices(tmp_path))
    summary = publication_summary(native({"reported": 3, "input_tokens": 1_000_000, "output_tokens": 500_000,
                                          "thinking_tokens": 250_000}), MODEL_RUN, table)
    # thinking defaults to the output rate: 2 + 0.5*8 + 0.25*8 = 8
    assert summary["cost_usd"] == pytest.approx(8.0) and summary["cost_usd_partial"] is None
    assert summary["cost_basis"]["complete"] is True
    assert summary["cost_basis"]["as_of"] == "2026-10-21"
    assert summary["cost_basis"]["source"] == "https://example.com/pricing"
    assert (summary["cost_basis"]["covers_trials"], summary["cost_basis"]["of_trials"]) == (3, 3)


def test_partial_usage_never_reads_as_the_cost_of_the_run(tmp_path):
    summary = publication_summary(native({"reported": 2, "input_tokens": 1_000_000, "output_tokens": 0,
                                          "thinking_tokens": 0}), MODEL_RUN, load_prices(prices(tmp_path)))
    assert summary["cost_usd"] is None
    assert summary["cost_usd_partial"] == pytest.approx(2.0)
    assert summary["cost_basis"]["complete"] is False
    assert (summary["cost_basis"]["covers_trials"], summary["cost_basis"]["of_trials"]) == (2, 3)


@pytest.mark.parametrize("usage", [None, {"reported": 0, "input_tokens": 0},
                                   {"reported": 3, "input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0}])
def test_no_reported_usage_stays_null_rather_than_zero(usage, tmp_path):
    summary = publication_summary(native(usage), MODEL_RUN, load_prices(prices(tmp_path)))
    assert summary["usage"] is None and summary["cost_usd"] is None and summary["cost_usd_partial"] is None


@pytest.mark.parametrize("usage", [
    {"reported": 4, "input_tokens": 1}, {"reported": 1, "input_tokens": -5},
    {"reported": 1, "input_tokens": 1.5}, {"reported": True}, ["not", "an", "object"],
])
def test_impossible_usage_is_rejected(usage):
    with pytest.raises(ValueError):
        publication_summary(native(usage), MODEL_RUN)


def test_a_preflight_never_reports_usage():
    summary = publication_summary(native({"reported": 3, "input_tokens": 9}, ("fail",) * 3),
                                  {"run_kind": "model_free_preflight"})
    assert summary["usage"] is None


@pytest.mark.parametrize("override", [{"as_of": ""}, {"source": "http://insecure.example"},
                                      {"currency": "EUR"}, {"per_million_tokens": {"input": -1, "output": 1}},
                                      {"per_million_tokens": {"input": 1}}])
def test_an_incomplete_price_table_is_refused(tmp_path, override):
    with pytest.raises(ValueError):
        load_prices(prices(tmp_path, **override))


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "model-eval.yml"


def test_model_runs_are_started_by_hand_and_cannot_write_to_the_repository():
    doc = yaml.safe_load(WORKFLOW.read_text())
    triggers = doc.get(True) or doc.get("on")
    assert set(triggers) == {"workflow_dispatch"}
    assert doc["permissions"] == {"contents": "read"}
    steps = doc["jobs"]["evaluate"]["steps"]
    assert any("aria-evals check" in str(step.get("run", "")) for step in steps)
    text = WORKFLOW.read_text()
    assert "secrets.OPENAI_API_KEY" in text and "echo $OPENAI_API_KEY" not in text
    for step in steps:
        uses = step.get("uses", "")
        if uses:
            assert "@" in uses and len(uses.split("@")[1].split()[0]) == 40, f"pin {uses} to a commit"


def test_only_the_selected_providers_key_reaches_any_step():
    # The agent runs shell commands without prompts and inherits the run step's environment.
    doc = yaml.safe_load(WORKFLOW.read_text())
    for step in doc["jobs"]["evaluate"]["steps"]:
        env = step.get("env", {})
        assert not [name for name in env if name.endswith("_API_KEY")], step.get("name")
        with_secrets = [name for name, value in env.items() if "secrets." in str(value)]
        assert with_secrets in ([], ["SELECTED_KEY"]), step.get("name")
        if with_secrets:
            value = " ".join(env["SELECTED_KEY"].split())
            for provider in ("openai", "deepseek", "google", "anthropic"):
                assert f"(inputs.provider == '{provider}' && secrets.{provider.upper()}_API_KEY)" in value
            assert value.endswith("|| '' }}")
    assert doc.get("env") is None and doc["jobs"]["evaluate"].get("env") is None


def test_the_step_summary_shows_json_as_code():
    assert "echo '```json'" in WORKFLOW.read_text()

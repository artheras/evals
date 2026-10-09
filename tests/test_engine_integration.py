"""Free reference controls through the official engine; never invoke an agent."""

from pathlib import Path

import pytest

from aria_evals.cli import engine_identity, resolve_model
from aria_evals.catalog import validate_catalog
from solutions import SOLUTIONS

harness = pytest.importorskip("aria_code.evals.harness")
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("fixture", sorted(SOLUTIONS))
def test_native_engine_accepts_reference_with_graders_hidden(fixture):
    catalog = validate_catalog(ROOT)
    engine_identity(catalog["manifest"]["engine"])
    _, tasks = harness.load_suite(catalog["suite_path"])
    task = next(task for task in tasks if task.fixture == fixture)
    def solve(prompt, workspace):
        assert all(not (workspace / name).exists() for name in task.hidden)
        SOLUTIONS[fixture](workspace)
    result = harness.run_task(task, solver=solve, fixtures_root=catalog["fixture_root"])
    assert result.outcome == "pass", result.detail + "\n" + result.log


def test_native_provider_contract_keeps_explicit_routing():
    assert resolve_model("chatgpt", "demo-model") == ("openai", "openai/demo-model")
    assert resolve_model("openai", "openai/demo-model") == ("openai", "openai/demo-model")
    assert resolve_model("ollama", "hf.co/example/model") == ("ollama", "ollama/hf.co/example/model")
    with pytest.raises(ValueError):
        resolve_model("openai", "anthropic/demo-model")

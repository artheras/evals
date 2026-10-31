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


EXIT_NOW = "import os\nos._exit({code})\n"
HACKS = {
    "pytest_py": ("maze_route", {"pytest.py": "raise SystemExit(0)\n"}),
    "sitecustomize_py": ("maze_route", {"sitecustomize.py": EXIT_NOW.format(code=0)}),
    "pytest_ini": ("semver_order", {"pytest.ini": "[pytest]\naddopts = --collect-only\n"}),
    "shadowed_numpy": ("mesh_box", {"numpy.py": EXIT_NOW.format(code=0)}),
    "controller_exit_0": ("ctl_cartpole", {"controller.py": EXIT_NOW.format(code=0)}),
    "controller_exit_127": ("ctl_swingup", {"controller.py": EXIT_NOW.format(code=127)}),
}


@pytest.mark.parametrize("hack", sorted(HACKS))
def test_native_engine_does_not_score_a_hack_as_pass(hack):
    # What this repository controls: the verify command and the graders. The engine's own
    # treatment of new files and exit 127 is tested in Aria Code.
    fixture, files = HACKS[hack]
    catalog = validate_catalog(ROOT)
    _, tasks = harness.load_suite(catalog["suite_path"])
    task = next(task for task in tasks if task.fixture == fixture)
    def solve(prompt, workspace):
        for name, text in files.items():
            (workspace / name).write_text(text)
    result = harness.run_task(task, solver=solve, fixtures_root=catalog["fixture_root"])
    assert result.outcome == "fail", result.outcome + ": " + result.detail + "\n" + result.log


def test_native_provider_contract_keeps_explicit_routing():
    assert resolve_model("chatgpt", "demo-model") == ("openai", "openai/demo-model")
    assert resolve_model("openai", "openai/demo-model") == ("openai", "openai/demo-model")
    assert resolve_model("ollama", "hf.co/example/model") == ("ollama", "ollama/hf.co/example/model")
    with pytest.raises(ValueError):
        resolve_model("openai", "anthropic/demo-model")

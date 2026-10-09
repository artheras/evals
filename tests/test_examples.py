"""Calibration for independently authored public examples, without model calls."""

from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from solutions import SOLUTIONS, TRAPS


FIXTURES = Path(__file__).resolve().parents[1] / "evals" / "fixtures"
GRADERS = {
    "maze_route": "test_route.py", "bracket_repair": "test_brackets.py",
    "word_histogram": "test_histogram.py",
}
OUTPUTS = {
    "maze_route": "route.txt", "bracket_repair": "normalized.txt",
    "word_histogram": "histogram.csv",
}
INPUTS = {"maze_route": "maze.txt", "bracket_repair": "fragments.txt", "word_histogram": "source.txt"}


def _prepare(tmp_path, fixture):
    destination = tmp_path / "sandbox"
    shutil.copytree(FIXTURES / fixture, destination)
    return destination


def _grade(workspace, fixture):
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--noconftest", "-p", "no:cacheprovider", GRADERS[fixture]],
        cwd=workspace, capture_output=True, text=True, timeout=20,
    )


@pytest.mark.parametrize("fixture", sorted(GRADERS))
def test_a_missing_artifact_cannot_pass(tmp_path, fixture):
    result = _grade(_prepare(tmp_path, fixture), fixture)
    assert result.returncode == 1, "A missing artifact must be a grading failure, not an infrastructure error."


@pytest.mark.parametrize("fixture", sorted(GRADERS))
def test_reference_solution_passes(tmp_path, fixture):
    workspace = _prepare(tmp_path, fixture)
    SOLUTIONS[fixture](workspace)
    result = _grade(workspace, fixture)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("fixture,trap", [
    (fixture, trap) for fixture in sorted(TRAPS) for trap in sorted(TRAPS[fixture])
])
def test_each_deliberate_mistake_is_rejected(tmp_path, fixture, trap):
    workspace = _prepare(tmp_path, fixture)
    TRAPS[fixture][trap](workspace)
    result = _grade(workspace, fixture)
    assert result.returncode == 1, "A deliberate mistake must produce a grading failure."


@pytest.mark.parametrize("fixture", sorted(GRADERS))
def test_reference_solution_only_creates_its_required_artifact(tmp_path, fixture):
    workspace = _prepare(tmp_path, fixture)
    before = {path.name: path.read_bytes() for path in workspace.iterdir() if path.is_file()}
    SOLUTIONS[fixture](workspace)
    assert {path.name for path in workspace.iterdir()} == set(before) | {OUTPUTS[fixture]}
    assert all((workspace / name).read_bytes() == content for name, content in before.items())


@pytest.mark.parametrize("fixture", sorted(GRADERS))
def test_output_symlink_is_rejected(tmp_path, fixture):
    workspace = _prepare(tmp_path, fixture)
    SOLUTIONS[fixture](workspace)
    artifact = workspace / OUTPUTS[fixture]
    outside = tmp_path / "outside-artifact"
    artifact.rename(outside)
    artifact.symlink_to(outside)
    assert _grade(workspace, fixture).returncode == 1


@pytest.mark.parametrize("fixture", sorted(GRADERS))
def test_changing_the_input_is_rejected(tmp_path, fixture):
    workspace = _prepare(tmp_path, fixture)
    SOLUTIONS[fixture](workspace)
    with (workspace / INPUTS[fixture]).open("a") as handle:
        handle.write("changed input\n")
    assert _grade(workspace, fixture).returncode == 1

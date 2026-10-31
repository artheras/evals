"""Calibration for independently authored public examples, without model calls."""

from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import pytest
import yaml

from solutions import SOLUTIONS, TRAPS


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evals" / "fixtures"
# Grade with the exact command the engine runs, so calibration covers the verifier's isolation.
VERIFY = {task["fixture"]: task["verify"] for task in yaml.safe_load((ROOT / "evals/suites/public.yaml").read_text())["tasks"]}
GRADERS = {
    "maze_route": "test_route.py", "bracket_repair": "test_brackets.py",
    "word_histogram": "test_histogram.py",
    "log_compress": "test_compress.py",
    "semver_order": "test_semver.py",
    "region_totals": "test_totals.py",
    "json_flatten": "test_flatten.py",
    "amortization": "test_schedule.py",
    "fifo_gains": "test_gains.py",
    "max_drawdown": "test_drawdown.py",
    "largest_remainder": "test_weights.py",
    "dock_schedule": "test_dock.py",
    "billable_weight": "test_charges.py",
    "pick_sequence": "test_picks.py",
    "reorder_plan": "test_reorder.py",
    "fw_ringbuf": "test_ringbuf.py",
    "fw_pid": "test_pid.py",
    "fw_crc16": "test_crc16.py",
    "fw_debounce": "test_debounce.py",
    "fw_q15": "test_q15.py",
    "ctl_swingup": "test_control.py",
    "ctl_cartpole": "test_control.py",
    "ctl_reach": "test_control.py",
    "ctl_speedlimit": "test_control.py",
    "ctl_softlimits": "test_control.py",
    "mesh_box": "test_mesh.py",
    "mesh_plate_hole": "test_mesh.py",
    "mesh_hull": "test_mesh.py",
    "mesh_units": "test_mesh.py",
    "mesh_repair": "test_mesh.py",
}
OUTPUTS = {
    "maze_route": "route.txt", "bracket_repair": "normalized.txt",
    "word_histogram": "histogram.csv",
    "log_compress": "compressed.log",
    "semver_order": "ordered.txt",
    "region_totals": "totals.csv",
    "json_flatten": "flat.txt",
    "amortization": "schedule.csv",
    "fifo_gains": "gains.csv",
    "max_drawdown": "drawdown.json",
    "largest_remainder": "weights.csv",
    "dock_schedule": "schedule.csv",
    "billable_weight": "charges.csv",
    "pick_sequence": "picklist.csv",
    "reorder_plan": "reorder.csv",
    "fw_ringbuf": "ringbuf.c",
    "fw_pid": "pid.c",
    "fw_crc16": "crc16.c",
    "fw_debounce": "debounce.c",
    "fw_q15": "q15.c",
    "ctl_swingup": "controller.py",
    "ctl_cartpole": "controller.py",
    "ctl_reach": "controller.py",
    "ctl_speedlimit": "controller.py",
    "ctl_softlimits": "controller.py",
    "mesh_box": "box.obj",
    "mesh_plate_hole": "plate.obj",
    "mesh_hull": "hull.obj",
    "mesh_units": "bracket_mm.obj",
    "mesh_repair": "fixed.obj",
}
INPUTS = {"maze_route": "maze.txt", "bracket_repair": "fragments.txt", "word_histogram": "source.txt",
    "log_compress": "events.log",
    "semver_order": "versions.txt",
    "region_totals": "customers.csv",
    "json_flatten": "config.json",
    "amortization": "loan.txt",
    "fifo_gains": "trades.csv",
    "max_drawdown": "prices.csv",
    "largest_remainder": "holdings.csv",
    "dock_schedule": "appointments.csv",
    "billable_weight": "rates.csv",
    "pick_sequence": "locations.csv",
    "reorder_plan": "stock.csv",
    "fw_ringbuf": "ringbuf.h",
    "fw_pid": "pid.h",
    "fw_crc16": "crc16.h",
    "fw_debounce": "debounce.h",
    "fw_q15": "q15.h",
    "ctl_swingup": "pendulum.xml",
    "ctl_cartpole": "cartpole.xml",
    "ctl_reach": "arm.xml",
    "ctl_speedlimit": "carriage.xml",
    "ctl_softlimits": "arm.xml",
    "mesh_box": "spec.json",
    "mesh_plate_hole": "spec.json",
    "mesh_hull": "points.csv",
    "mesh_units": "bracket_in.obj",
    "mesh_repair": "broken.obj",
}


def _prepare(tmp_path, fixture):
    destination = tmp_path / "sandbox"
    shutil.copytree(FIXTURES / fixture, destination)
    return destination


def _grade(workspace, fixture):
    command = [sys.executable if word == "{python}" else word for word in shlex.split(VERIFY[fixture])]
    assert command[-1] == GRADERS[fixture]
    return subprocess.run(command, cwd=workspace, capture_output=True, text=True, timeout=60)


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


# ── Planted files and hostile controllers ────────────────────────────────────────────────────
# The grader runs inside the agent's workspace after the agent's turn. Anything the agent leaves
# there must not be able to turn the check green. Each case is planted beside an answer that is
# missing (or, for controllers, otherwise correct), so a PASS could only come from the hack.
# Whether the engine also rejects new .py or config files, or how it reads exit 127, is decided
# in Aria Code; these tests cover what this repository controls: the verify command and graders.

EXIT_NOW = "import os\nos._exit(0)\n"
PLANTED = {
    "pytest_py": {"pytest.py": "raise SystemExit(0)\n"},
    "sitecustomize_py": {"sitecustomize.py": EXIT_NOW, "usercustomize.py": EXIT_NOW},
    "conftest_py": {"conftest.py": EXIT_NOW},
    "pytest_ini_collect_only": {"pytest.ini": "[pytest]\naddopts = --collect-only\n"},
    "pyproject_collect_only": {"pyproject.toml": '[tool.pytest.ini_options]\naddopts = "--collect-only"\n'},
    "ini_pythonpath_shadow": {"pytest.ini": "[pytest]\npythonpath = .\n", "numpy.py": EXIT_NOW},
    "shadowed_imports": {name + ".py": EXIT_NOW for name in
                         ("numpy", "mujoco", "trimesh", "decimal", "csv", "json", "hashlib", "subprocess", "tempfile")},
}


@pytest.mark.parametrize("fixture,hack", [
    (fixture, hack) for fixture in sorted(GRADERS) for hack in sorted(PLANTED)
])
def test_files_planted_in_the_workspace_cannot_pass(tmp_path, fixture, hack):
    workspace = _prepare(tmp_path, fixture)
    for name, text in PLANTED[hack].items():
        (workspace / name).write_text(text)
    result = _grade(workspace, fixture)
    assert result.returncode == 1, result.stdout + result.stderr


def test_a_planted_pytest_module_did_pass_the_unisolated_command(tmp_path):
    # The reason the verify command starts with -I: plain `-m` puts the workspace first on sys.path.
    workspace = _prepare(tmp_path, "maze_route")
    (workspace / "pytest.py").write_text(PLANTED["pytest_py"]["pytest.py"])
    plain = [sys.executable, "-m", "pytest", "-q", "--noconftest", "-p", "no:cacheprovider", GRADERS["maze_route"]]
    assert subprocess.run(plain, cwd=workspace, capture_output=True, timeout=60).returncode == 0
    assert _grade(workspace, "maze_route").returncode == 1


CONTROLS = sorted(fixture for fixture in GRADERS if fixture.startswith("ctl_"))
HOSTILE = {
    "exit_0_on_import": lambda source: EXIT_NOW + source,
    "exit_127_on_import": lambda source: "import os\nos._exit(127)\n" + source,
    "sys_exit_on_import": lambda source: "raise SystemExit(0)\n" + source,
    "exit_0_mid_episode": lambda source: source + (
        "\n_calls = [0]\n_real = control\n\ndef control(t, qpos, qvel):\n"
        "    _calls[0] += 1\n    if _calls[0] == 100:\n        import os\n        os._exit(0)\n"
        "    return _real(t, qpos, qvel)\n"),
    "exit_127_mid_episode": lambda source: source + (
        "\n_real = control\n\ndef control(t, qpos, qvel):\n"
        "    if t > 0.5:\n        import os\n        os._exit(127)\n    return _real(t, qpos, qvel)\n"),
    # The grader asserts with numpy and simulates with mujoco; neither may be reachable from here.
    "patches_the_grader": lambda source: (
        "import sys, numpy, mujoco\n"
        "numpy.abs = lambda x: numpy.zeros_like(numpy.asarray(x, dtype=float))\n"
        "numpy.hypot = lambda *a: numpy.zeros_like(numpy.asarray(a[0], dtype=float))\n"
        "mujoco.mj_step = lambda *a, **k: None\n"
        "for name, module in list(sys.modules.items()):\n"
        "    if name.startswith('_pytest') or name == 'pytest':\n"
        "        setattr(module, 'exit', lambda *a, **k: None)\n"
        "def control(t, qpos, qvel):\n    return [0.0] * 8\n"),
    "returns_nothing_useful": lambda source: "def control(t, qpos, qvel):\n    return [0.0] * 8\n",
}


@pytest.mark.parametrize("fixture,hack", [(fixture, hack) for fixture in CONTROLS for hack in sorted(HOSTILE)])
def test_a_hostile_controller_cannot_pass(tmp_path, fixture, hack):
    workspace = _prepare(tmp_path, fixture)
    SOLUTIONS[fixture](workspace)
    controller = workspace / "controller.py"
    controller.write_text(HOSTILE[hack](controller.read_text()))
    result = _grade(workspace, fixture)
    assert result.returncode == 1, result.stdout + result.stderr


@pytest.mark.parametrize("fixture", CONTROLS)
def test_a_correct_controller_may_print(tmp_path, fixture):
    # The controller's stdout is not the reply channel, so debugging output cannot corrupt it.
    workspace = _prepare(tmp_path, fixture)
    SOLUTIONS[fixture](workspace)
    controller = workspace / "controller.py"
    controller.write_text(controller.read_text() + (
        "\n_real = control\n\ndef control(t, qpos, qvel):\n"
        "    print('{\"u\": [1e9]}', t)\n    return _real(t, qpos, qvel)\n"))
    result = _grade(workspace, fixture)
    assert result.returncode == 0, result.stdout + result.stderr

"""Public original grader: move a two-link arm's tip to a point given in Cartesian coordinates."""

from hashlib import sha256
import importlib.util
import math
from pathlib import Path

import mujoco
import numpy as np


HERE = Path(__file__).parent
SOURCE = HERE / "controller.py"
MODEL = HERE / "arm.xml"
INPUTS = {
    "arm.xml": "9bba69d867dc6eb3ef2f0d320def6c87af75d4cf3b0da5832a21e5d84f5d04a8",
    "target.json": "570eaf13a89e49a77c4de0bc06cf4563635bd24aea030ef89343672e080cdfac",
}
INITIAL_QPOS = [0.0, 0.0]
DURATION = 5.0
TARGET = (0.45, 0.55)


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _controller():
    assert SOURCE.is_file() and not SOURCE.is_symlink(), "Create controller.py as a regular file."
    spec = importlib.util.spec_from_file_location("submitted_controller", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    control = getattr(module, "control", None)
    assert callable(control), "controller.py must define control(t, qpos, qvel)."
    return control


def simulate():
    """Run the episode and return the time, positions, velocities and applied controls per step."""
    _check_inputs()
    control = _controller()
    model = mujoco.MjModel.from_xml_path(str(MODEL))
    data = mujoco.MjData(model)
    data.qpos[:] = INITIAL_QPOS
    mujoco.mj_forward(model, data)
    steps = int(round(DURATION / model.opt.timestep))
    times, qpos, qvel, ctrl, extra = [], [], [], [], []
    for _ in range(steps):
        command = np.asarray(control(float(data.time), data.qpos.copy(), data.qvel.copy()), dtype=float).reshape(-1)
        assert command.shape == (model.nu,), f"control must return {model.nu} value(s), got {command.shape}."
        assert np.all(np.isfinite(command)), "control returned a value that is not finite."
        data.ctrl[:] = command
        data.qfrc_applied[:] = disturbance(float(data.time), model.nv)
        mujoco.mj_step(model, data)
        times.append(data.time)
        qpos.append(data.qpos.copy())
        qvel.append(data.qvel.copy())
        ctrl.append(data.ctrl.copy())
        extra.append(observe(model, data))
    return np.array(times), np.array(qpos), np.array(qvel), np.array(ctrl), np.array(extra)


def disturbance(t, nv):
    return np.zeros(nv)


def observe(model, data):
    return data.site_xpos[model.site('tip').id][:2].copy()


def test_inputs_are_unchanged():
    _check_inputs()


def test_the_tip_reaches_the_target_and_stays():
    t, _, _, _, tip = simulate()
    distance = np.hypot(tip[:, 0] - TARGET[0], tip[:, 1] - TARGET[1])
    late = t >= 3.0
    assert distance[late].max() < 0.01, f"From 3 s the tip must stay within 1 cm of the target; worst {distance[late].max() * 100:.1f} cm."


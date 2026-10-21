"""Public original grader: move a carriage 1 m without ever exceeding a speed limit."""

from hashlib import sha256
import importlib.util
import math
from pathlib import Path

import mujoco
import numpy as np


HERE = Path(__file__).parent
SOURCE = HERE / "controller.py"
MODEL = HERE / "carriage.xml"
INPUTS = {
    "carriage.xml": "e24722de69044e9914c70b1af5e98b281709d69112281f473b619711ce27b4aa",
}
INITIAL_QPOS = [0.0]
DURATION = 5.0


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
    return np.zeros(0)


def test_inputs_are_unchanged():
    _check_inputs()


def test_it_arrives_without_breaking_the_speed_limit():
    t, q, qd, _, _ = simulate()
    assert np.abs(qd[:, 0]).max() <= 0.5, f"The speed limit is 0.5 m/s; it reached {np.abs(qd[:, 0]).max():.3f} m/s."
    late = t >= 3.5
    assert np.abs(q[late, 0] - 1.0).max() < 0.01, f"From 3.5 s it must stay within 1 cm of 1 m; worst {np.abs(q[late, 0] - 1.0).max() * 100:.1f} cm."


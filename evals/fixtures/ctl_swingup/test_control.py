"""Public original grader: swing a torque-limited pendulum up and balance it."""

from hashlib import sha256
import importlib.util
import math
from pathlib import Path

import mujoco
import numpy as np


HERE = Path(__file__).parent
SOURCE = HERE / "controller.py"
MODEL = HERE / "pendulum.xml"
INPUTS = {
    "pendulum.xml": "fa07cd14a6559ff08c4fbf68ec022d736bb72b1e0969982d61de3f681f6106b0",
}
INITIAL_QPOS = [0.0]
DURATION = 10.0


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
    # From 6 s to 9 s: 0.1 s pushes of 0.6 N·m every 0.5 s, alternating direction.
    if 6.0 <= t < 9.0 and (t - 6.0) % 0.5 < 0.1:
        return np.full(nv, 0.6 if int((t - 6.0) / 0.5) % 2 == 0 else -0.6)
    return np.zeros(nv)


def observe(model, data):
    return np.zeros(0)


def test_inputs_are_unchanged():
    _check_inputs()


def test_the_pendulum_is_balanced_upright_and_recovers_from_pushes():
    t, q, qd, _, _ = simulate()
    error = np.abs((q[:, 0] - math.pi + math.pi) % (2 * math.pi) - math.pi)
    held = t >= 5.0
    assert error[held].max() < 0.15, f"From 5 s it must stay within 0.15 rad of upright, pushes included; worst {error[held].max():.3f} rad."
    final = t >= 9.5
    assert error[final].max() < 0.02, f"In the last 0.5 s it must be within 0.02 rad of upright; worst {error[final].max():.3f} rad."
    assert np.abs(qd[final, 0]).max() < 0.2, "In the last 0.5 s it must be nearly still."


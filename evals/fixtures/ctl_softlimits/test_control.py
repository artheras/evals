"""Public original grader: follow a schedule of joint targets without crossing soft limits."""

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
    "arm.xml": "b461772f8ce1b4ab0cc92018f6e98ab311f19ba6f6667ca3732702dd8c31efd0",
    "targets.json": "c54805538df9c73bf585e28408c21b66e3db4fdbaa46829ee05268e7d34bd062",
}
INITIAL_QPOS = [0.0, 0.0]
DURATION = 6.0
LIMITS = [[-1.0, 1.0], [-1.2, 1.2]]
SCHEDULE = [(0.0, [0.5, -0.3]), (2.0, [1.4, 0.2]), (4.0, [-0.2, -1.6])]


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


def test_targets_are_reached_within_the_soft_limits():
    t, q, _, _, _ = simulate()
    for joint, (low, high) in enumerate(LIMITS):
        worst = max(low - q[:, joint].min(), q[:, joint].max() - high, 0.0)
        assert worst <= 0.02, f"Joint {joint} went {worst:.3f} rad past its soft limit."
    edges = [start for start, _ in SCHEDULE[1:]] + [DURATION]
    for (start, target), end in zip(SCHEDULE, edges):
        clamped = [min(max(value, low), high) for value, (low, high) in zip(target, LIMITS)]
        window = (t >= end - 0.5) & (t < end)
        error = np.abs(q[window] - np.array(clamped)).max()
        assert error < 0.02, f"In the last 0.5 s before {end} s the joints must be within 0.02 rad of {clamped}; worst {error:.3f}."


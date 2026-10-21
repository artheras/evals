"""Public original grader: balance an inverted pendulum on a cart and bring the cart home."""

from hashlib import sha256
import importlib.util
import math
from pathlib import Path

import mujoco
import numpy as np


HERE = Path(__file__).parent
SOURCE = HERE / "controller.py"
MODEL = HERE / "cartpole.xml"
INPUTS = {
    "cartpole.xml": "5fabf104e77db12f965473065f7191c7b36ad78cdb5d164c003d1843e57f4aef",
}
INITIAL_QPOS = [0.0, 0.15]
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
    return np.zeros(nv)


def observe(model, data):
    return np.zeros(0)


def test_inputs_are_unchanged():
    _check_inputs()


def test_the_pole_stays_up_and_the_cart_comes_back():
    t, q, _, _, _ = simulate()
    assert np.abs(q[:, 1]).max() < 0.5, f"The pole fell: it reached {np.abs(q[:, 1]).max():.2f} rad."
    assert np.abs(q[:, 0]).max() < 1.0, f"The cart left the 1 m track: it reached {np.abs(q[:, 0]).max():.2f} m."
    late = t >= 8.0
    assert np.abs(q[late, 1]).max() < 0.02, "In the last 2 s the pole must be within 0.02 rad of upright."
    assert np.abs(q[late, 0]).max() < 0.1, "In the last 2 s the cart must be within 0.1 m of where it started."


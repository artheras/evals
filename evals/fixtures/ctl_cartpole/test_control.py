"""Public original grader: balance an inverted pendulum on a cart and bring the cart home."""

from hashlib import sha256
import json
import math
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time

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


# The submitted controller runs in its own interpreter, started with -I so neither the
# workspace nor PYTHON* variables reach its import path. It only receives (t, qpos, qvel)
# and returns commands; the simulation and every assertion stay in this process, which the
# controller cannot patch. A controller process that ends before the episode does, with any
# exit status, fails the check.
CONTROLLER_BUDGET = 120.0
CHILD = r"""
import importlib.util, json, os, sys, traceback
import numpy as np
reply = os.fdopen(os.dup(1), "w")
os.dup2(2, 1)
sys.stdout = sys.stderr
def send(message):
    reply.write(json.dumps(message) + "\n")
    reply.flush()
try:
    spec = importlib.util.spec_from_file_location("submitted_controller", sys.argv[1])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    control = getattr(module, "control", None)
except Exception:
    send({"error": "controller.py could not be loaded:\n" + traceback.format_exc(limit=-3)})
    raise SystemExit(1)
if not callable(control):
    send({"error": "controller.py must define control(t, qpos, qvel)."})
    raise SystemExit(1)
send({"ready": True})
for line in sys.stdin:
    t, qpos, qvel = json.loads(line)
    try:
        command = control(t, np.array(qpos, dtype=float), np.array(qvel, dtype=float))
        command = np.asarray(command, dtype=float).reshape(-1).tolist()
    except Exception:
        send({"error": "control raised:\n" + traceback.format_exc(limit=-3)})
        raise SystemExit(1)
    send({"u": command})
"""


class _Controller:
    """controller.py's control function, called across a process boundary."""

    def __init__(self):
        assert SOURCE.is_file() and not SOURCE.is_symlink(), "Create controller.py as a regular file."
        self._log = tempfile.TemporaryFile()
        self._process = subprocess.Popen(
            [sys.executable, "-I", "-c", CHILD, str(SOURCE)], cwd=HERE,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._log,
        )
        self._lines = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()
        self._deadline = time.monotonic() + CONTROLLER_BUDGET
        assert self._receive().get("ready") is True, "The controller process did not start correctly."

    def _read(self):
        for line in self._process.stdout:
            self._lines.put(line)
        self._lines.put(None)

    def _ended(self):
        try:
            code = self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            code = "unknown"
        self._log.seek(0)
        tail = self._log.read().decode(errors="replace")[-1000:]
        return AssertionError(f"The controller process ended before the episode did (exit {code}). {tail}".rstrip())

    def _receive(self):
        try:
            line = self._lines.get(timeout=max(0.0, self._deadline - time.monotonic()))
        except queue.Empty:
            raise AssertionError(f"The controller used more than {CONTROLLER_BUDGET:.0f} s in total.") from None
        if line is None:
            raise self._ended()
        try:
            message = json.loads(line)
        except ValueError:
            raise AssertionError("The controller process sent something that is not a reply.") from None
        assert isinstance(message, dict), "The controller process sent something that is not a reply."
        if "error" in message:
            raise AssertionError(str(message["error"]))
        return message

    def __call__(self, t, qpos, qvel):
        try:
            self._process.stdin.write((json.dumps([t, qpos.tolist(), qvel.tolist()]) + "\n").encode())
            self._process.stdin.flush()
        except (BrokenPipeError, OSError):
            raise self._ended() from None
        command = self._receive().get("u")
        assert isinstance(command, list), "The controller process sent something that is not a reply."
        return command

    def close(self):
        self._process.kill()
        self._process.wait()
        for stream in (self._process.stdin, self._process.stdout):
            try:
                stream.close()
            except OSError:
                pass
        self._log.close()


def simulate():
    """Run the episode and return the time, positions, velocities and applied controls per step."""
    _check_inputs()
    model = mujoco.MjModel.from_xml_path(str(MODEL))
    data = mujoco.MjData(model)
    data.qpos[:] = INITIAL_QPOS
    mujoco.mj_forward(model, data)
    steps = int(round(DURATION / model.opt.timestep))
    times, qpos, qvel, ctrl, extra = [], [], [], [], []
    control = _Controller()
    try:
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
    finally:
        control.close()
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


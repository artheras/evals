"""Reference answers and deliberate mistakes for the physical-AI public tasks.

Firmware tasks are answered with C source, control tasks with a Python controller, and
3D tasks with a mesh. Each mistake is a plausible error; the calibration tests require the
hidden grader to reject every one of them and to accept the reference.
"""

from pathlib import Path


def _writer(name, text):
    def write(workspace: Path) -> None:
        (workspace / name).write_text(text, encoding="utf-8")
    return write


# ── firmware ─────────────────────────────────────────────────────────────────────────────────

RINGBUF = r'''#include "ringbuf.h"

void rb_init(ringbuf_t *rb) { rb->head = rb->tail = rb->count = 0; }

bool rb_push(ringbuf_t *rb, uint8_t value) {
    if (rb->count == RB_CAPACITY) return false;
    rb->data[rb->tail] = value;
    rb->tail = (rb->tail + 1) % RB_CAPACITY;
    rb->count++;
    return true;
}

bool rb_pop(ringbuf_t *rb, uint8_t *out) {
    if (rb->count == 0) return false;
    *out = rb->data[rb->head];
    rb->head = (rb->head + 1) % RB_CAPACITY;
    rb->count--;
    return true;
}

size_t rb_count(const ringbuf_t *rb) { return rb->count; }
'''
RINGBUF_ONE_SHORT = RINGBUF.replace("if (rb->count == RB_CAPACITY) return false;",
                                    "if (rb->count == RB_CAPACITY - 1) return false;")
RINGBUF_OVERWRITES = RINGBUF.replace(
    "if (rb->count == RB_CAPACITY) return false;",
    "if (rb->count == RB_CAPACITY) { rb->head = (rb->head + 1) % RB_CAPACITY; rb->count--; }")
RINGBUF_WRITES_ON_EMPTY = RINGBUF.replace("if (rb->count == 0) return false;",
                                          "if (rb->count == 0) { *out = 0; return false; }")

PID = r'''#include "pid.h"

static double clamp(double x, double lo, double hi) { return x < lo ? lo : (x > hi ? hi : x); }

void pid_init(pid_ctrl_t *pid, double kp, double ki, double kd, double out_min, double out_max) {
    pid->kp = kp; pid->ki = ki; pid->kd = kd;
    pid->out_min = out_min; pid->out_max = out_max;
    pid->integral = 0.0; pid->prev_measurement = 0.0; pid->has_prev = 0;
}

double pid_update(pid_ctrl_t *pid, double setpoint, double measurement, double dt) {
    double error = setpoint - measurement;
    pid->integral = clamp(pid->integral + pid->ki * error * dt, pid->out_min, pid->out_max);
    double derivative = pid->has_prev ? -pid->kd * (measurement - pid->prev_measurement) / dt : 0.0;
    pid->prev_measurement = measurement;
    pid->has_prev = 1;
    return clamp(pid->kp * error + pid->integral + derivative, pid->out_min, pid->out_max);
}
'''
PID_WINDUP = PID.replace("pid->integral = clamp(pid->integral + pid->ki * error * dt, pid->out_min, pid->out_max);",
                         "pid->integral = pid->integral + pid->ki * error * dt;")
PID_KICK = PID.replace(
    "double derivative = pid->has_prev ? -pid->kd * (measurement - pid->prev_measurement) / dt : 0.0;\n"
    "    pid->prev_measurement = measurement;",
    "double derivative = pid->has_prev ? pid->kd * (error - pid->prev_measurement) / dt : 0.0;\n"
    "    pid->prev_measurement = error;")
PID_FIRST_STEP = PID.replace("pid->has_prev ? -pid->kd", "1 ? -pid->kd")

CRC = r'''#include "crc16.h"

uint16_t crc16_update(uint16_t crc, const uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)(data[i] << 8);
        for (int bit = 0; bit < 8; bit++)
            crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
    }
    return crc;
}

uint16_t crc16_ccitt_false(const uint8_t *data, size_t len) { return crc16_update(0xFFFF, data, len); }
'''
CRC_XMODEM = CRC.replace("crc16_update(0xFFFF, data, len)", "crc16_update(0x0000, data, len)")
CRC_FINAL_XOR = CRC.replace("{ return crc16_update(0xFFFF, data, len); }",
                            "{ return (uint16_t)(crc16_update(0xFFFF, data, len) ^ 0xFFFF); }")
CRC_REFLECTED = r'''#include "crc16.h"

uint16_t crc16_update(uint16_t crc, const uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; bit++) crc = (crc & 1) ? (uint16_t)((crc >> 1) ^ 0x8408) : (uint16_t)(crc >> 1);
    }
    return crc;
}

uint16_t crc16_ccitt_false(const uint8_t *data, size_t len) { return crc16_update(0xFFFF, data, len); }
'''

DEBOUNCE = r'''#include "debounce.h"

void debounce_init(debounce_t *d, int initial) { d->stable = initial ? 1 : 0; d->count = 0; }

int debounce_sample(debounce_t *d, int raw) {
    raw = raw ? 1 : 0;
    if (raw == d->stable) { d->count = 0; return d->stable; }
    if (++d->count >= DEBOUNCE_SAMPLES) { d->stable = raw; d->count = 0; }
    return d->stable;
}
'''
DEBOUNCE_ONE_EARLY = DEBOUNCE.replace("++d->count >= DEBOUNCE_SAMPLES", "++d->count >= DEBOUNCE_SAMPLES - 1")
DEBOUNCE_ACCUMULATES = DEBOUNCE.replace("if (raw == d->stable) { d->count = 0; return d->stable; }",
                                        "if (raw == d->stable) return d->stable;")
DEBOUNCE_NONE = r'''#include "debounce.h"

void debounce_init(debounce_t *d, int initial) { d->stable = initial ? 1 : 0; d->count = 0; }

int debounce_sample(debounce_t *d, int raw) { d->stable = raw ? 1 : 0; return d->stable; }
'''

Q15 = r'''#include "q15.h"
#include <math.h>

static q15_t saturate(long v) { return (q15_t)(v > 32767 ? 32767 : (v < -32768 ? -32768 : v)); }

q15_t q15_add(q15_t a, q15_t b) { return saturate((long)a + (long)b); }

q15_t q15_mul(q15_t a, q15_t b) {
    long product = (long)a * (long)b;
    return saturate((product + (1L << 14)) >> 15);
}

q15_t q15_from_double(double x) {
    double scaled = x * 32768.0;
    double rounded = scaled < 0 ? -floor(-scaled + 0.5) : floor(scaled + 0.5);
    if (rounded > 32767.0) return 32767;
    if (rounded < -32768.0) return -32768;
    return (q15_t)rounded;
}
'''
Q15_WRAPS = Q15.replace("q15_t q15_add(q15_t a, q15_t b) { return saturate((long)a + (long)b); }",
                        "q15_t q15_add(q15_t a, q15_t b) { return (q15_t)(a + b); }")
Q15_TRUNCATES = Q15.replace("return saturate((product + (1L << 14)) >> 15);", "return saturate(product >> 15);")
Q15_MUL_WRAPS = Q15.replace("return saturate((product + (1L << 14)) >> 15);",
                            "return (q15_t)((product + (1L << 14)) >> 15);")
Q15_HALF_EVEN = Q15.replace("double rounded = scaled < 0 ? -floor(-scaled + 0.5) : floor(scaled + 0.5);",
                            "double rounded = nearbyint(scaled);")

SOLUTIONS = {
    "fw_ringbuf": _writer("ringbuf.c", RINGBUF),
    "fw_pid": _writer("pid.c", PID),
    "fw_crc16": _writer("crc16.c", CRC),
    "fw_debounce": _writer("debounce.c", DEBOUNCE),
    "fw_q15": _writer("q15.c", Q15),
}
TRAPS = {
    "fw_ringbuf": {"one_short": _writer("ringbuf.c", RINGBUF_ONE_SHORT),
                   "overwrites_oldest": _writer("ringbuf.c", RINGBUF_OVERWRITES),
                   "writes_on_empty": _writer("ringbuf.c", RINGBUF_WRITES_ON_EMPTY)},
    "fw_pid": {"integral_windup": _writer("pid.c", PID_WINDUP),
               "derivative_kick": _writer("pid.c", PID_KICK),
               "derivative_on_first_step": _writer("pid.c", PID_FIRST_STEP)},
    "fw_crc16": {"xmodem_init": _writer("crc16.c", CRC_XMODEM),
                 "final_xor": _writer("crc16.c", CRC_FINAL_XOR),
                 "reflected": _writer("crc16.c", CRC_REFLECTED)},
    "fw_debounce": {"one_early": _writer("debounce.c", DEBOUNCE_ONE_EARLY),
                    "accumulates": _writer("debounce.c", DEBOUNCE_ACCUMULATES),
                    "no_debounce": _writer("debounce.c", DEBOUNCE_NONE)},
    "fw_q15": {"add_wraps": _writer("q15.c", Q15_WRAPS),
               "mul_truncates": _writer("q15.c", Q15_TRUNCATES),
               "mul_wraps": _writer("q15.c", Q15_MUL_WRAPS),
               "rounds_half_even": _writer("q15.c", Q15_HALF_EVEN)},
}


# ── control ──────────────────────────────────────────────────────────────────────────────────

SWINGUP = '''import math

MGL = 1.0 * 9.81 * 0.5 + 0.05 * 9.81 * 0.25          # gravity torque scale of bob and rod
INERTIA = 1.0 * 0.25 + 0.4 * 1.0 * 0.04 ** 2 + 0.05 * 0.25 / 3


def _wrap(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def control(t, qpos, qvel):
    angle, speed = float(qpos[0]), float(qvel[0])
    error = _wrap(angle - math.pi)
    if abs(error) < 0.35:                                  # close to the top: balance
        torque = -40.0 * error - 6.0 * speed
    else:                                                  # pump energy towards the upright level
        energy = 0.5 * INERTIA * speed ** 2 - MGL * math.cos(angle)
        direction = 1.0 if speed >= 0 else -1.0
        torque = 4.0 * (MGL - energy) * direction if abs(speed) > 1e-3 else 2.0
    return [max(-2.0, min(2.0, torque))]
'''
SWINGUP_PD_ONLY = '''import math


def control(t, qpos, qvel):
    return [max(-2.0, min(2.0, 40.0 * (math.pi - qpos[0]) - 6.0 * qvel[0]))]
'''
SWINGUP_DEGREES = SWINGUP.replace("error = _wrap(angle - math.pi)", "error = angle - 180.0")
SWINGUP_NO_CATCH = SWINGUP.replace("if abs(error) < 0.35:", "if False:")

CARTPOLE = '''GAINS = (-9.8194, -64.2423, -10.7995, -12.0613)   # discrete LQR on the linearised model


def control(t, qpos, qvel):
    state = (qpos[0], qpos[1], qvel[0], qvel[1])
    force = -sum(gain * value for gain, value in zip(GAINS, state))
    return [max(-10.0, min(10.0, force))]
'''
CARTPOLE_ANGLE_ONLY = '''def control(t, qpos, qvel):
    return [max(-10.0, min(10.0, 40.0 * qpos[1] + 8.0 * qvel[1]))]
'''
CARTPOLE_WRONG_SIGN = CARTPOLE.replace("force = -sum(", "force = sum(")

REACH = '''import json
import math
from pathlib import Path

L1, L2 = 0.5, 0.4
_target = json.loads((Path(__file__).parent / "target.json").read_text())


def _inverse_kinematics(x, y):
    cos_elbow = (x * x + y * y - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    elbow = math.acos(max(-1.0, min(1.0, cos_elbow)))
    shoulder = math.atan2(y, x) - math.atan2(L2 * math.sin(elbow), L1 + L2 * math.cos(elbow))
    return shoulder, elbow


GOAL = _inverse_kinematics(_target["x"], _target["y"])


def control(t, qpos, qvel):
    return [max(-5.0, min(5.0, 40.0 * (goal - q) - 6.0 * v)) for goal, q, v in zip(GOAL, qpos, qvel)]
'''
REACH_AS_ANGLES = REACH.replace('GOAL = _inverse_kinematics(_target["x"], _target["y"])',
                                'GOAL = (_target["x"], _target["y"])')
REACH_WRONG_LENGTHS = REACH.replace("L1, L2 = 0.5, 0.4", "L1, L2 = 0.5, 0.5")

SPEED = '''LIMIT = 0.45          # a margin under the 0.5 m/s limit


def control(t, qpos, qvel):
    position, speed = float(qpos[0]), float(qvel[0])
    wanted = max(-LIMIT, min(LIMIT, 4.0 * (1.0 - position)))
    force = 40.0 * (wanted - speed) + 1.0 * speed     # track the speed, cancel the rail friction
    return [max(-20.0, min(20.0, force))]
'''
SPEED_PD = '''def control(t, qpos, qvel):
    return [max(-20.0, min(20.0, 100.0 * (1.0 - qpos[0]) - 20.0 * qvel[0]))]
'''
SPEED_TIMID = SPEED.replace("LIMIT = 0.45", "LIMIT = 0.2")

SOFTLIMITS = '''import json
from pathlib import Path

_spec = json.loads((Path(__file__).parent / "targets.json").read_text())
LIMITS = _spec["limits"]
SCHEDULE = sorted((entry["from"], entry["q"]) for entry in _spec["schedule"])


RATE = 1.5           # rad/s: move the reference gradually so the joints never overshoot
_reference = None


def _target(t):
    current = SCHEDULE[0][1]
    for start, q in SCHEDULE:
        if t >= start:
            current = q
    return [min(max(value, low), high) for value, (low, high) in zip(current, LIMITS)]


def control(t, qpos, qvel):
    global _reference
    if _reference is None:
        _reference = [float(q) for q in qpos]
    step = RATE * 0.002
    _reference = [r + max(-step, min(step, goal - r)) for r, goal in zip(_reference, _target(t))]
    return [max(-8.0, min(8.0, 60.0 * (r - q) - 10.0 * v)) for r, q, v in zip(_reference, qpos, qvel)]
'''
SOFTLIMITS_NO_CLAMP = SOFTLIMITS.replace(
    "return [min(max(value, low), high) for value, (low, high) in zip(current, LIMITS)]", "return list(current)")
SOFTLIMITS_FIRST_ONLY = SOFTLIMITS.replace("        if t >= start:\n", "        if start == 0.0:\n")
SOFTLIMITS_OVERSHOOTS = SOFTLIMITS.replace("RATE = 1.5", "RATE = 1000.0").replace("60.0 * (r - q) - 10.0 * v", "300.0 * (r - q) - 1.0 * v")

SOLUTIONS.update({
    "ctl_swingup": _writer("controller.py", SWINGUP),
    "ctl_cartpole": _writer("controller.py", CARTPOLE),
    "ctl_reach": _writer("controller.py", REACH),
    "ctl_speedlimit": _writer("controller.py", SPEED),
    "ctl_softlimits": _writer("controller.py", SOFTLIMITS),
})
TRAPS.update({
    "ctl_swingup": {"pd_only": _writer("controller.py", SWINGUP_PD_ONLY),
                    "degrees": _writer("controller.py", SWINGUP_DEGREES),
                    "never_catches": _writer("controller.py", SWINGUP_NO_CATCH)},
    "ctl_cartpole": {"angle_only": _writer("controller.py", CARTPOLE_ANGLE_ONLY),
                     "wrong_sign": _writer("controller.py", CARTPOLE_WRONG_SIGN)},
    "ctl_reach": {"target_as_angles": _writer("controller.py", REACH_AS_ANGLES),
                  "wrong_link_lengths": _writer("controller.py", REACH_WRONG_LENGTHS)},
    "ctl_speedlimit": {"plain_pd": _writer("controller.py", SPEED_PD),
                       "too_timid": _writer("controller.py", SPEED_TIMID)},
    "ctl_softlimits": {"no_clamp": _writer("controller.py", SOFTLIMITS_NO_CLAMP),
                       "first_target_only": _writer("controller.py", SOFTLIMITS_FIRST_ONLY),
                       "overshoots": _writer("controller.py", SOFTLIMITS_OVERSHOOTS)},
})


# ── 3D meshes ────────────────────────────────────────────────────────────────────────────────

import json
import math

import numpy as np


def _obj(vertices, faces):
    lines = [f"v {x:.9f} {y:.9f} {z:.9f}" for x, y, z in vertices]
    lines += [f"f {a + 1} {b + 1} {c + 1}" for a, b, c in faces]
    return "\n".join(lines) + "\n"


def _read_obj(path):
    vertices, faces = [], []
    for line in path.read_text().splitlines():
        parts = line.split()
        if parts and parts[0] == "v":
            vertices.append([float(p) for p in parts[1:4]])
        elif parts and parts[0] == "f":
            faces.append([int(p.split("/")[0]) - 1 for p in parts[1:4]])
    return np.array(vertices), np.array(faces)


def _box(lo, hi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    vertices = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return vertices, faces


def solve_box(workspace, *, shift=(0, 0, 0), scale=1.0, flip=False, drop_top=False):
    spec = json.loads((workspace / "spec.json").read_text())
    lo = np.array(spec["min_corner"], float) + shift
    vertices, faces = _box(lo, lo + np.array(spec["size"], float) * scale)
    if flip:
        faces = [(a, c, b) for a, b, c in faces]
    if drop_top:
        faces = [f for f in faces if f not in ((4, 5, 6), (4, 6, 7))]
    (workspace / "box.obj").write_text(_obj(vertices, faces))


def solve_plate(workspace, *, radius_scale=1.0, segments=64, through=True, shift=(0.0, 0.0)):
    spec = json.loads((workspace / "spec.json").read_text())
    (w, h, t), (ox, oy, oz) = spec["plate"]["size"], spec["plate"]["min_corner"]
    cx, cy = spec["hole"]["centre_xy"]
    r = spec["hole"]["diameter"] / 2 * radius_scale
    ox, oy = ox + shift[0], oy + shift[1]
    cx, cy = cx + shift[0], cy + shift[1]
    corners = [math.atan2(y - cy, x - cx) for x, y in ((ox + w, oy + h), (ox, oy + h), (ox, oy), (ox + w, oy))]
    angles = sorted(set([2 * math.pi * k / segments - math.pi for k in range(segments)] + corners))
    inner, outer = [], []
    for a in angles:
        dx, dy = math.cos(a), math.sin(a)
        inner.append((cx + r * dx, cy + r * dy))
        reach = min(v for v in ((ox + w - cx) / dx if dx > 1e-12 else math.inf, (ox - cx) / dx if dx < -1e-12 else math.inf,
                                (oy + h - cy) / dy if dy > 1e-12 else math.inf, (oy - cy) / dy if dy < -1e-12 else math.inf))
        outer.append((cx + reach * dx, cy + reach * dy))
    vertices, faces = [], []

    def ring(points, z):
        vertices.extend((x, y, z) for x, y in points)
        return list(range(len(vertices) - len(points), len(vertices)))

    top_in, top_out = ring(inner, oz + t), ring(outer, oz + t)
    bot_in, bot_out = ring(inner, oz), ring(outer, oz)
    m = len(angles)
    for k in range(m):
        j = (k + 1) % m
        faces += [(top_in[k], top_out[k], top_out[j]), (top_in[k], top_out[j], top_in[j])]
        faces += [(bot_in[k], bot_out[j], bot_out[k]), (bot_in[k], bot_in[j], bot_out[j])]
        faces += [(top_out[k], bot_out[k], bot_out[j]), (top_out[k], bot_out[j], top_out[j])]
        if through:
            faces += [(top_in[k], top_in[j], bot_in[j]), (top_in[k], bot_in[j], bot_in[k])]
    if not through:   # a blind pocket: close the hole at mid-depth instead of drilling through
        mid = ring(inner, oz + t / 2)
        bottom_cap = ring([(cx, cy)], oz + t / 2)[0]
        for k in range(m):
            j = (k + 1) % m
            faces += [(top_in[k], top_in[j], mid[j]), (top_in[k], mid[j], mid[k]), (mid[k], mid[j], bottom_cap)]
            faces += [(bot_in[k], bot_in[j], bottom_cap)]
    (workspace / "plate.obj").write_text(_obj(vertices, faces))


def _hull_faces(points):
    centre = points.mean(axis=0)
    faces = []
    n = len(points)
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                normal = np.cross(points[j] - points[i], points[k] - points[i])
                length = np.linalg.norm(normal)
                if length < 1e-9:
                    continue
                normal /= length
                side = (points - points[i]) @ normal
                if np.all(side <= 1e-7) or np.all(side >= -1e-7):
                    outward = (centre - points[i]) @ normal < 0
                    faces.append((i, j, k) if outward else (i, k, j))
    return faces


def solve_hull(workspace, *, subset=None, flip=False, bounding_box=False):
    points = np.loadtxt(workspace / "points.csv", delimiter=",", skiprows=1)
    if bounding_box:
        vertices, faces = _box(points.min(axis=0), points.max(axis=0))
        (workspace / "hull.obj").write_text(_obj(vertices, faces))
        return
    if subset is not None:
        points = points[:subset]
    faces = _hull_faces(points)
    if flip:
        faces = [(a, c, b) for a, b, c in faces]
    used = sorted({v for face in faces for v in face})
    index = {old: new for new, old in enumerate(used)}
    (workspace / "hull.obj").write_text(_obj(points[used], [tuple(index[v] for v in f) for f in faces]))


def solve_units(workspace, *, factor=25.4, centre_z=False, mirror=False):
    vertices, faces = _read_obj(workspace / "bracket_in.obj")
    vertices = vertices * factor
    if mirror:
        vertices[:, 0] *= -1
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    shift = np.array([(low[0] + high[0]) / 2, (low[1] + high[1]) / 2, (low[2] + high[2]) / 2 if centre_z else low[2]])
    (workspace / "bracket_mm.obj").write_text(_obj(vertices - shift, faces))


def _consistent_winding(faces):
    """Flip triangles so every shared edge is used once in each direction (breadth-first over neighbours)."""
    from collections import defaultdict, deque

    faces = [list(f) for f in faces]
    by_edge = defaultdict(list)
    for index, face in enumerate(faces):
        for k in range(3):
            by_edge[frozenset((face[k], face[(k + 1) % 3]))].append(index)
    done = [False] * len(faces)
    for seed in range(len(faces)):
        if done[seed]:
            continue
        done[seed] = True
        queue = deque([seed])
        while queue:
            current = faces[queue.popleft()]
            directed = {(current[k], current[(k + 1) % 3]) for k in range(3)}
            for k in range(3):
                for other in by_edge[frozenset((current[k], current[(k + 1) % 3]))]:
                    if done[other]:
                        continue
                    neighbour = faces[other]
                    if any((neighbour[m], neighbour[(m + 1) % 3]) in directed for m in range(3)):
                        neighbour.reverse()          # same direction on a shared edge: flip it
                    done[other] = True
                    queue.append(other)
    return faces


def _fill_triangle_holes(faces):
    """Close each hole bounded by exactly three edges with one triangle that continues the winding."""
    from collections import Counter

    directed = Counter((f[k], f[(k + 1) % 3]) for f in faces for k in range(3))
    open_edges = [(a, b) for (a, b) in directed if (b, a) not in directed]
    following = {a: b for a, b in open_edges}
    added, seen = [], set()
    for a, b in open_edges:
        if a in seen:
            continue
        c = following.get(b)
        if c is not None and following.get(c) == a:
            added.append([a, c, b])        # runs each open edge the other way
            seen.update((a, b, c))
    return faces + added


def _signed_volume(vertices, faces):
    v = vertices[np.array(faces)]
    return float(np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2])).sum() / 6)


def solve_repair(workspace, *, fill=True, wind=True, outward=True):
    vertices, faces = _read_obj(workspace / "broken.obj")
    faces = [list(f) for f in faces]
    if wind:
        faces = _consistent_winding(faces)
    if fill:
        faces = _fill_triangle_holes(faces)
    if wind and _signed_volume(vertices, faces) < 0:
        faces = [f[::-1] for f in faces]
    if not outward:
        faces = [f[::-1] for f in faces]
    (workspace / "fixed.obj").write_text(_obj(vertices, faces))


def _copy_broken(workspace):
    (workspace / "fixed.obj").write_text((workspace / "broken.obj").read_text())


def _call(function, **options):
    return lambda workspace: function(workspace, **options)


SOLUTIONS.update({
    "mesh_box": solve_box,
    "mesh_plate_hole": solve_plate,
    "mesh_hull": solve_hull,
    "mesh_units": solve_units,
    "mesh_repair": solve_repair,
})
TRAPS.update({
    "mesh_box": {"centred": _call(solve_box, shift=(-20, -10, -5)), "centimetres": _call(solve_box, scale=0.1),
                 "inside_out": _call(solve_box, flip=True), "open_top": _call(solve_box, drop_top=True)},
    "mesh_plate_hole": {"radius_for_diameter": _call(solve_plate, radius_scale=2.0),
                        "too_few_segments": _call(solve_plate, segments=8),
                        "blind_pocket": _call(solve_plate, through=False),
                        "centred_plate": _call(solve_plate, shift=(-30.0, -20.0))},
    "mesh_hull": {"bounding_box": _call(solve_hull, bounding_box=True), "half_the_points": _call(solve_hull, subset=36),
                  "inside_out": _call(solve_hull, flip=True)},
    "mesh_units": {"centimetres": _call(solve_units, factor=2.54), "centred_in_z": _call(solve_units, centre_z=True),
                   "mirrored": _call(solve_units, mirror=True)},
    "mesh_repair": {"copied": _copy_broken, "hole_left_open": _call(solve_repair, fill=False),
                    "inside_out": _call(solve_repair, outward=False)},
})

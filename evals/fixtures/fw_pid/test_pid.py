"""Public original grader: a PID controller with anti-windup and derivative on measurement."""

from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest


HERE = Path(__file__).parent
SOURCE = HERE / "pid.c"
INPUTS = {
    "pid.h": "166cecb92313a8158e74774466b29ea65859f81336ae134a4138bad2f1695e5c",
}
HARNESS = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
static unsigned long seed_ = 20261021UL;
static unsigned rnd(void) { seed_ = seed_ * 1103515245UL + 12345UL; return (unsigned)((seed_ >> 16) & 0x7fffU); }
#define CHECK(cond, ...) do { if (!(cond)) { printf("FAIL: "); printf(__VA_ARGS__); printf("\n"); return 1; } } while (0)
#include "pid.h"
typedef struct { double kp, ki, kd, lo, hi, i, prev; int has; } ref_t;
static double clampd(double x, double lo, double hi) { return x < lo ? lo : (x > hi ? hi : x); }
static double ref_update(ref_t *r, double sp, double y, double dt) {
    double e = sp - y;
    r->i = clampd(r->i + r->ki * e * dt, r->lo, r->hi);
    double d = r->has ? -r->kd * (y - r->prev) / dt : 0.0;
    r->prev = y; r->has = 1;
    return clampd(r->kp * e + r->i + d, r->lo, r->hi);
}
int main(void) {
    const double gains[3][5] = {{2.0, 1.5, 0.05, -1.0, 1.0}, {0.8, 4.0, 0.2, -5.0, 5.0}, {5.0, 0.0, 0.0, 0.0, 2.0}};
    for (int g = 0; g < 3; g++) {
        pid_ctrl_t pid; ref_t ref = {gains[g][0], gains[g][1], gains[g][2], gains[g][3], gains[g][4], 0, 0, 0};
        pid_init(&pid, gains[g][0], gains[g][1], gains[g][2], gains[g][3], gains[g][4]);
        const double start[3] = {0.7, -0.3, 1.1};
        double y_dut = start[g], y_ref = start[g], dt = 0.01, tau = 0.4;
        for (int k = 0; k < 3000; k++) {
            double sp = k < 800 ? 3.0 : (k < 1600 ? -0.5 : 0.25 * sin(k * 0.01));
            if (k == 2200) dt = 0.02;
            double u_dut = pid_update(&pid, sp, y_dut, dt);
            double u_ref = ref_update(&ref, sp, y_ref, dt);
            CHECK(fabs(u_dut - u_ref) < 1e-9, "gain set %d, step %d: output %.12f, expected %.12f", g, k, u_dut, u_ref);
            y_dut += dt * (u_dut - y_dut) / tau;
            y_ref += dt * (u_ref - y_ref) / tau;
        }
    }
    printf("ok\n");
    return 0;
}
"""


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _compiler():
    for name in ("cc", "gcc", "clang"):
        found = shutil.which(name)
        if found:
            return found
    # 127 tells the harness the check could not run at all, so it is not scored.
    pytest.exit("no C compiler on this machine; the check cannot run", returncode=127)


def _run_harness():
    _check_inputs()
    assert SOURCE.is_file() and not SOURCE.is_symlink(), "Create pid.c as a regular file."
    compiler = _compiler()
    with tempfile.TemporaryDirectory() as scratch:
        harness = Path(scratch) / "harness.c"
        harness.write_text(HARNESS, encoding="utf-8")
        program = Path(scratch) / "harness"
        build = subprocess.run(
            [compiler, "-std=c99", "-O1", "-I", str(HERE), str(SOURCE), str(harness), "-o", str(program), "-lm"],
            capture_output=True, text=True, timeout=120,
        )
        assert build.returncode == 0, "pid.c must compile with the header: " + build.stderr[-1500:]
        try:
            run = subprocess.run([str(program)], capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired as error:
            raise AssertionError("The program did not finish within 30 seconds.") from error
    return run


def test_inputs_are_unchanged():
    _check_inputs()


def test_behaviour_matches_the_specification():
    run = _run_harness()
    assert run.returncode == 0, (run.stdout + run.stderr)[-1500:]

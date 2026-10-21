"""Public original grader: saturating Q15 fixed-point arithmetic."""

from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest


HERE = Path(__file__).parent
SOURCE = HERE / "q15.c"
INPUTS = {
    "q15.h": "e1e1c25503912cdf52963f6c4a9306c569a4138b9226eceaf542f41c177e601e",
}
HARNESS = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
static unsigned long seed_ = 20261021UL;
static unsigned rnd(void) { seed_ = seed_ * 1103515245UL + 12345UL; return (unsigned)((seed_ >> 16) & 0x7fffU); }
#define CHECK(cond, ...) do { if (!(cond)) { printf("FAIL: "); printf(__VA_ARGS__); printf("\n"); return 1; } } while (0)
#include "q15.h"
static int16_t sat(long v) { return (int16_t)(v > 32767 ? 32767 : (v < -32768 ? -32768 : v)); }
static int16_t ref_add(int16_t a, int16_t b) { return sat((long)a + (long)b); }
static int16_t ref_mul(int16_t a, int16_t b) { long p = (long)a * (long)b; return sat((p + (1L << 14)) >> 15); }
static int16_t ref_from(double x) { double s = x * 32768.0; double r = s < 0 ? -floor(-s + 0.5) : floor(s + 0.5); return sat((long)(r > 1e9 ? 1e9 : (r < -1e9 ? -1e9 : r))); }
int main(void) {
    const int16_t edges[] = {-32768, -32767, -16384, -2, -1, 0, 1, 2, 16384, 32766, 32767};
    for (int i = 0; i < 11; i++) for (int j = 0; j < 11; j++) {
        int16_t a = edges[i], b = edges[j];
        CHECK(q15_add(a, b) == ref_add(a, b), "q15_add(%d, %d) = %d, expected %d", a, b, q15_add(a, b), ref_add(a, b));
        CHECK(q15_mul(a, b) == ref_mul(a, b), "q15_mul(%d, %d) = %d, expected %d", a, b, q15_mul(a, b), ref_mul(a, b));
    }
    for (int t = 0; t < 300000; t++) {
        int16_t a = (int16_t)((rnd() << 1) ^ rnd()), b = (int16_t)((rnd() << 1) ^ rnd());
        CHECK(q15_add(a, b) == ref_add(a, b), "q15_add(%d, %d) = %d, expected %d", a, b, q15_add(a, b), ref_add(a, b));
        CHECK(q15_mul(a, b) == ref_mul(a, b), "q15_mul(%d, %d) = %d, expected %d", a, b, q15_mul(a, b), ref_mul(a, b));
    }
    const double xs[] = {0.0, 0.5, -0.5, 0.25, 1.0, -1.0, 2.0, -3.5, 0.999969482421875, 1.52587890625e-05, -1.52587890625e-05, 0.3, -0.7, 4.57763671875e-05, -4.57763671875e-05};
    for (int i = 0; i < 15; i++) CHECK(q15_from_double(xs[i]) == ref_from(xs[i]), "q15_from_double(%.17g) = %d, expected %d", xs[i], q15_from_double(xs[i]), ref_from(xs[i]));
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
    assert SOURCE.is_file() and not SOURCE.is_symlink(), "Create q15.c as a regular file."
    compiler = _compiler()
    with tempfile.TemporaryDirectory() as scratch:
        harness = Path(scratch) / "harness.c"
        harness.write_text(HARNESS, encoding="utf-8")
        program = Path(scratch) / "harness"
        build = subprocess.run(
            [compiler, "-std=c99", "-O1", "-I", str(HERE), str(SOURCE), str(harness), "-o", str(program), "-lm"],
            capture_output=True, text=True, timeout=120,
        )
        assert build.returncode == 0, "q15.c must compile with the header: " + build.stderr[-1500:]
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

"""Public original grader: a counting button debouncer."""

from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest


HERE = Path(__file__).parent
SOURCE = HERE / "debounce.c"
INPUTS = {
    "debounce.h": "56939d7990afdf26a9b92b1c942c54866990d744c6567fedc0e38d442b8d6a27",
}
HARNESS = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
static unsigned long seed_ = 20261021UL;
static unsigned rnd(void) { seed_ = seed_ * 1103515245UL + 12345UL; return (unsigned)((seed_ >> 16) & 0x7fffU); }
#define CHECK(cond, ...) do { if (!(cond)) { printf("FAIL: "); printf(__VA_ARGS__); printf("\n"); return 1; } } while (0)
#include "debounce.h"
int main(void) {
    for (int init = 0; init < 2; init++) {
        debounce_t d; debounce_init(&d, init);
        int stable = init, run = 0, raw = init;
        for (int step = 0; step < 50000; step++) {
            unsigned r = rnd() % 100;
            if (r < 6) raw = !raw;                     /* a real change */
            int sample = (r >= 6 && r < 20) ? !raw : raw; /* contact bounce */
            if (sample != stable) { run++; if (run >= DEBOUNCE_SAMPLES) { stable = sample; run = 0; } } else run = 0;
            int got = debounce_sample(&d, sample);
            CHECK(got == stable, "init %d, step %d: output %d, expected %d", init, step, got, stable);
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
    assert SOURCE.is_file() and not SOURCE.is_symlink(), "Create debounce.c as a regular file."
    compiler = _compiler()
    with tempfile.TemporaryDirectory() as scratch:
        harness = Path(scratch) / "harness.c"
        harness.write_text(HARNESS, encoding="utf-8")
        program = Path(scratch) / "harness"
        build = subprocess.run(
            [compiler, "-std=c99", "-O1", "-I", str(HERE), str(SOURCE), str(harness), "-o", str(program), "-lm"],
            capture_output=True, text=True, timeout=120,
        )
        assert build.returncode == 0, "debounce.c must compile with the header: " + build.stderr[-1500:]
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

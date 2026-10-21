"""Public original grader: a fixed-capacity FIFO ring buffer in C."""

from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest


HERE = Path(__file__).parent
SOURCE = HERE / "ringbuf.c"
INPUTS = {
    "ringbuf.h": "fa83bfbfce81f719bf18525d46caf28ca736fbaaf1ba48de2aa80b3e8003480f",
}
HARNESS = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
static unsigned long seed_ = 20261021UL;
static unsigned rnd(void) { seed_ = seed_ * 1103515245UL + 12345UL; return (unsigned)((seed_ >> 16) & 0x7fffU); }
#define CHECK(cond, ...) do { if (!(cond)) { printf("FAIL: "); printf(__VA_ARGS__); printf("\n"); return 1; } } while (0)
#include "ringbuf.h"
int main(void) {
    static unsigned char model[200000];
    size_t mh = 0, mt = 0;
    ringbuf_t rb;
    rb_init(&rb);
    CHECK(rb_count(&rb) == 0, "a new buffer must be empty");
    for (int step = 0; step < 60000; step++) {
        if (step % 20000 == 0 && step) { rb_init(&rb); mh = mt = 0; CHECK(rb_count(&rb) == 0, "rb_init must empty the buffer"); }
        int phase = (step / 300) % 3;              /* fill, drain, mixed: reach full and empty often */
        unsigned r = rnd() % 10;
        int push = phase == 0 ? r < 8 : phase == 1 ? r < 2 : r < 5;
        size_t n = mt - mh;
        if (push) {
            uint8_t v = (uint8_t)(rnd() & 0xff);
            bool ok = rb_push(&rb, v);
            if (n < RB_CAPACITY) { CHECK(ok, "step %d: push into a buffer holding %zu of %d items must succeed", step, n, RB_CAPACITY); model[mt++] = v; }
            else CHECK(!ok, "step %d: push into a full buffer must return false", step);
        } else {
            uint8_t out = 0xA5;
            bool ok = rb_pop(&rb, &out);
            if (n > 0) { CHECK(ok, "step %d: pop from a non-empty buffer must succeed", step); CHECK(out == model[mh], "step %d: pop returned %u, expected %u (FIFO order)", step, out, model[mh]); mh++; }
            else { CHECK(!ok, "step %d: pop from an empty buffer must return false", step); CHECK(out == 0xA5, "step %d: pop from an empty buffer must not write *out", step); }
        }
        CHECK(rb_count(&rb) == mt - mh, "step %d: count is %zu, expected %zu", step, rb_count(&rb), mt - mh);
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
    assert SOURCE.is_file() and not SOURCE.is_symlink(), "Create ringbuf.c as a regular file."
    compiler = _compiler()
    with tempfile.TemporaryDirectory() as scratch:
        harness = Path(scratch) / "harness.c"
        harness.write_text(HARNESS, encoding="utf-8")
        program = Path(scratch) / "harness"
        build = subprocess.run(
            [compiler, "-std=c99", "-O1", "-I", str(HERE), str(SOURCE), str(harness), "-o", str(program), "-lm"],
            capture_output=True, text=True, timeout=120,
        )
        assert build.returncode == 0, "ringbuf.c must compile with the header: " + build.stderr[-1500:]
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

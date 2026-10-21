"""Public original grader: CRC-16/CCITT-FALSE with incremental updates."""

from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest


HERE = Path(__file__).parent
SOURCE = HERE / "crc16.c"
INPUTS = {
    "crc16.h": "9b275ecf04cf787d2574ce5c2f8fd6ae8e5136f247290b302f3b51bbc7685b97",
}
HARNESS = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
static unsigned long seed_ = 20261021UL;
static unsigned rnd(void) { seed_ = seed_ * 1103515245UL + 12345UL; return (unsigned)((seed_ >> 16) & 0x7fffU); }
#define CHECK(cond, ...) do { if (!(cond)) { printf("FAIL: "); printf(__VA_ARGS__); printf("\n"); return 1; } } while (0)
#include "crc16.h"
static uint16_t ref(uint16_t crc, const uint8_t *d, size_t n) {
    for (size_t i = 0; i < n; i++) { crc ^= (uint16_t)(d[i] << 8); for (int b = 0; b < 8; b++) crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1); }
    return crc;
}
int main(void) {
    const uint8_t check[] = "123456789";
    CHECK(crc16_ccitt_false(check, 9) == 0x29B1, "CRC of \"123456789\" is 0x%04X, expected 0x29B1", crc16_ccitt_false(check, 9));
    CHECK(crc16_ccitt_false(check, 0) == 0xFFFF, "CRC of no bytes must be the initial value 0xFFFF");
    static uint8_t buf[512];
    for (int t = 0; t < 4000; t++) {
        size_t n = rnd() % 512;
        for (size_t i = 0; i < n; i++) buf[i] = (uint8_t)rnd();
        uint16_t want = ref(0xFFFF, buf, n);
        CHECK(crc16_ccitt_false(buf, n) == want, "test %d (%zu bytes): got 0x%04X, expected 0x%04X", t, n, crc16_ccitt_false(buf, n), want);
        size_t cut = n ? rnd() % (n + 1) : 0;
        uint16_t part = crc16_update(crc16_update(0xFFFF, buf, cut), buf + cut, n - cut);
        CHECK(part == want, "test %d: updating in two pieces gave 0x%04X, expected 0x%04X", t, part, want);
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
    assert SOURCE.is_file() and not SOURCE.is_symlink(), "Create crc16.c as a regular file."
    compiler = _compiler()
    with tempfile.TemporaryDirectory() as scratch:
        harness = Path(scratch) / "harness.c"
        harness.write_text(HARNESS, encoding="utf-8")
        program = Path(scratch) / "harness"
        build = subprocess.run(
            [compiler, "-std=c99", "-O1", "-I", str(HERE), str(SOURCE), str(harness), "-o", str(program), "-lm"],
            capture_output=True, text=True, timeout=120,
        )
        assert build.returncode == 0, "crc16.c must compile with the header: " + build.stderr[-1500:]
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

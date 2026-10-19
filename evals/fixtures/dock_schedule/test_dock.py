"""Public original grader: two-door dock scheduling."""

from hashlib import sha256
from pathlib import Path


HERE = Path(__file__).parent
OUT = HERE / "schedule.csv"
INPUTS = {
    "appointments.csv": "3c08f0d3155e4d5d6c33d02f60b0d67cfb7c5cdc121c3c5a86343f14f2fe2a88",
}
EXPECTED = 'id,door,start,end,wait_min\nT07,1,08:00,08:30,0\nT02,2,08:05,08:50,0\nT11,1,08:30,08:50,20\nT03,1,08:50,09:20,30\nT05,2,08:50,09:05,25\nT09,2,09:05,09:55,25\nT04,1,09:20,09:30,20\nT12,1,09:30,09:55,30\nT01,2,09:55,10:10,20\nT08,1,09:55,10:35,25\nT13,2,11:00,11:30,0\nT14,1,11:05,11:15,0\nT15,1,12:00,12:20,0\n'


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _artifact():
    assert OUT.is_file() and not OUT.is_symlink(), "Create schedule.csv as a regular file."
    return OUT.read_text()


def test_inputs_are_unchanged():
    _check_inputs()


def test_output_is_exact():
    _check_inputs()
    assert _artifact() == EXPECTED, "The output does not match the specified result."


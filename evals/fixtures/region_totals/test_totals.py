"""Public original grader: joining and aggregating order data."""

from hashlib import sha256
from pathlib import Path


HERE = Path(__file__).parent
OUT = HERE / "totals.csv"
INPUTS = {
    "customers.csv": "8760ca3d0cc0d4de00f62a96e205723d5f18a7f3077ca3caccbdff9f50a4d11c",
    "orders.csv": "71c9ba1710309fa2841af6298ea8c80da34183bec532e76dea570c0258554945",
}
EXPECTED = 'region,orders,total_cents\nWest,1,33000\nNorth,3,24050\nSouth,3,17500\nUNKNOWN,2,17500\n'


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _artifact():
    assert OUT.is_file() and not OUT.is_symlink(), "Create totals.csv as a regular file."
    return OUT.read_text()


def test_inputs_are_unchanged():
    _check_inputs()


def test_output_is_exact():
    _check_inputs()
    assert _artifact() == EXPECTED, "The output does not match the specified result."


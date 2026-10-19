"""Public original grader: volumetric billable weight and rate bands."""

from hashlib import sha256
from pathlib import Path


HERE = Path(__file__).parent
OUT = HERE / "charges.csv"
INPUTS = {
    "rates.csv": "a4b0c70a9067440f011e3bdc92fb7c6b9c4caedb824f809ba98437d1e1260da0",
    "shipments.csv": "4341351cfd595d6ffb5111255c3242e4afea2c16da80b1110bc717f259d518bd",
}
EXPECTED = 'id,billable_kg,charge\nS1,1.5,13.50\nS2,6.0,36.00\nS3,3.0,22.50\nS4,14.5,72.50\nS5,14.0,70.00\nS6,2.5,18.75\nS7,20.0,100.00\n'


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _artifact():
    assert OUT.is_file() and not OUT.is_symlink(), "Create charges.csv as a regular file."
    return OUT.read_text()


def test_inputs_are_unchanged():
    _check_inputs()


def test_output_is_exact():
    _check_inputs()
    assert _artifact() == EXPECTED, "The output does not match the specified result."


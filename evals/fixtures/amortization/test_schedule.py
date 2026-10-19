"""Public original grader: loan amortization with explicit rounding."""

from hashlib import sha256
from pathlib import Path


HERE = Path(__file__).parent
OUT = HERE / "schedule.csv"
INPUTS = {
    "loan.txt": "682d2e94be3262a7d9b79ae78816a0b5ad23515ef50fb3408176c295c915b8c5",
}
EXPECTED = 'month,payment,interest,principal,balance\n1,114.66,5.03,109.63,897.00\n2,114.66,4.49,110.17,786.83\n3,114.66,3.93,110.73,676.10\n4,114.66,3.38,111.28,564.82\n5,114.66,2.82,111.84,452.98\n6,114.66,2.26,112.40,340.58\n7,114.66,1.70,112.96,227.62\n8,114.66,1.14,113.52,114.10\n9,114.67,0.57,114.10,0.00\n'


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


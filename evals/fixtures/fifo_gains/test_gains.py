"""Public original grader: FIFO realized gains."""

from hashlib import sha256
from pathlib import Path


HERE = Path(__file__).parent
OUT = HERE / "gains.csv"
INPUTS = {
    "trades.csv": "984698541a76d6246a5dc17997feb4fe54c25effafba731cfd8faf503b90a031",
}
EXPECTED = 'date,symbol,qty,proceeds,cost,gain\n2024-02-01,AAA,120,1800.00,1240.00,560.00\n2024-02-09,BBB,70,2975.00,2880.00,95.00\n2024-03-15,AAA,60,675.00,630.00,45.00\n2024-03-20,BBB,30,1500.00,1320.00,180.00\n'


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _artifact():
    assert OUT.is_file() and not OUT.is_symlink(), "Create gains.csv as a regular file."
    return OUT.read_text()


def test_inputs_are_unchanged():
    _check_inputs()


def test_output_is_exact():
    _check_inputs()
    assert _artifact() == EXPECTED, "The output does not match the specified result."


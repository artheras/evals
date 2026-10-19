"""Public original grader: portfolio weights summing to exactly 100."""

from hashlib import sha256
from pathlib import Path


HERE = Path(__file__).parent
OUT = HERE / "weights.csv"
INPUTS = {
    "holdings.csv": "96c81d637dcc5d24bd14aff3f927ddebb1f2b7908d32e38497d19ea460a332f6",
}
EXPECTED = 'symbol,weight_percent\nAAA,6.67\nBBB,26.67\nCCC,26.67\nDDD,26.66\nEEE,13.33\n'


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _artifact():
    assert OUT.is_file() and not OUT.is_symlink(), "Create weights.csv as a regular file."
    return OUT.read_text()


def test_inputs_are_unchanged():
    _check_inputs()


def test_output_is_exact():
    _check_inputs()
    assert _artifact() == EXPECTED, "The output does not match the specified result."


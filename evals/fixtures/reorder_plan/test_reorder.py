"""Public original grader: reorder point and case rounding."""

from hashlib import sha256
from pathlib import Path


HERE = Path(__file__).parent
OUT = HERE / "reorder.csv"
INPUTS = {
    "stock.csv": "78871d25b94531608682f9cd387bba28977f4ff29f2df54ed0e5bc56ee186245",
}
EXPECTED = 'sku,order_qty\nK100,72\nK102,30\nK104,50\nK105,50\nK107,80\n'


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _artifact():
    assert OUT.is_file() and not OUT.is_symlink(), "Create reorder.csv as a regular file."
    return OUT.read_text()


def test_inputs_are_unchanged():
    _check_inputs()


def test_output_is_exact():
    _check_inputs()
    assert _artifact() == EXPECTED, "The output does not match the specified result."


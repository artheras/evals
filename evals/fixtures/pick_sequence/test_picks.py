"""Public original grader: serpentine warehouse picking."""

from hashlib import sha256
from pathlib import Path


HERE = Path(__file__).parent
OUT = HERE / "picklist.csv"
INPUTS = {
    "locations.csv": "9dd798521080e2ea1fe1a13516340892fdd0d66cb5543bb346ce3c2704bc3ee1",
    "order_lines.csv": "fbd5a9f77d30f9bd4dd7431e0948b79c6b2888798002abcf0a12f0c8a1f49d54",
}
EXPECTED = 'seq,sku,aisle,bay,total_qty\n1,A100,1,3,5\n2,A101,1,8,1\n3,B201,2,9,6\n4,B202,2,5,2\n5,B200,2,2,1\n6,C301,3,1,2\n7,C300,3,4,1\n8,D400,4,7,5\n9,D401,4,3,1\n10,E500,5,6,1\n'


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _artifact():
    assert OUT.is_file() and not OUT.is_symlink(), "Create picklist.csv as a regular file."
    return OUT.read_text()


def test_inputs_are_unchanged():
    _check_inputs()


def test_output_is_exact():
    _check_inputs()
    assert _artifact() == EXPECTED, "The output does not match the specified result."


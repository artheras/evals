"""Public original grader: Semantic Versioning precedence."""

from hashlib import sha256
from pathlib import Path


HERE = Path(__file__).parent
OUT = HERE / "ordered.txt"
INPUTS = {
    "versions.txt": "61001e09c30d947675ca03321bda5abbd0b67834ffdd94d03ac0dcc253178170",
}
EXPECTED = '0.9.9\n1.0.0-alpha\n1.0.0-alpha.1\n1.0.0-alpha.beta\n1.0.0-beta\n1.0.0-beta.2\n1.0.0-beta.11\n1.0.0-rc.1\n1.0.0+build5\n1.0.0\n1.2.0\n1.2.9\n1.2.10\n1.10.0\n'


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _artifact():
    assert OUT.is_file() and not OUT.is_symlink(), "Create ordered.txt as a regular file."
    return OUT.read_text()


def test_inputs_are_unchanged():
    _check_inputs()


def test_output_is_exact():
    _check_inputs()
    assert _artifact() == EXPECTED, "The output does not match the specified result."


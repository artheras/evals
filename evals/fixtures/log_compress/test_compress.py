"""Public original grader: run-length compression of a log."""

from hashlib import sha256
from pathlib import Path


HERE = Path(__file__).parent
OUT = HERE / "compressed.log"
INPUTS = {
    "events.log": "2126f1d54e6ca968f013d61563901fc21c868ca0c9390318b0bf33361581b2f9",
}
EXPECTED = 'INFO service started\n3x WARN disk 91%\n2x INFO heartbeat\nERROR db timeout\n4x INFO heartbeat\nWARN disk 91%\n2x ERROR db timeout\nINFO service stopped\n'


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _artifact():
    assert OUT.is_file() and not OUT.is_symlink(), "Create compressed.log as a regular file."
    return OUT.read_text()


def test_inputs_are_unchanged():
    _check_inputs()


def test_output_is_exact():
    _check_inputs()
    assert _artifact() == EXPECTED, "The output does not match the specified result."


"""Public original grader: maximum drawdown with recovery."""

from hashlib import sha256
import json
from pathlib import Path


HERE = Path(__file__).parent
OUT = HERE / "drawdown.json"
INPUTS = {
    "prices.csv": "28298ca370a71f9f19f617ef754ae6c0eb6ff0fa1ac1bb4392fe5afaa718e2d8",
}
EXPECTED = {'max_drawdown_pct': 42.22, 'peak_date': '2024-01-05', 'trough_date': '2024-01-09', 'recovery_date': '2024-01-11'}


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _artifact():
    assert OUT.is_file() and not OUT.is_symlink(), "Create drawdown.json as a regular file."
    return OUT.read_text()


def test_inputs_are_unchanged():
    _check_inputs()


def test_report_is_exact():
    _check_inputs()
    try:
        parsed = json.loads(_artifact())
    except ValueError as error:
        raise AssertionError("Write valid JSON.") from error
    assert parsed == EXPECTED, "The report does not match the expected drawdown."


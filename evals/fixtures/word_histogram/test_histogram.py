"""Public demonstration grader for an ASCII word histogram."""

import csv
from pathlib import Path


SOURCE = Path(__file__).with_name("source.txt")
OUT = Path(__file__).with_name("histogram.csv")
ORIGINAL = (
    "Clouds drift; gears click.\nGEARS click, clouds drift!\n"
    "A cloud is not clouds; a gear is not gears.\n"
)
EXPECTED = {
    "a": 2, "click": 2, "cloud": 1, "clouds": 3, "drift": 2,
    "gear": 1, "gears": 3, "is": 2, "not": 2,
}


def _rows():
    assert SOURCE.is_file() and not SOURCE.is_symlink(), "The input must be a regular file."
    assert SOURCE.read_text() == ORIGINAL, "The supplied source text must remain unchanged."
    assert OUT.is_file() and not OUT.is_symlink(), "Create histogram.csv as a regular file."
    with OUT.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["token", "count"], "Use exactly the token,count header."
        rows = list(reader)
    assert len(rows) == len(EXPECTED), "Include each distinct token exactly once."
    assert all(None not in row and None not in row.values() for row in rows), "Each row needs two fields."
    return rows


def test_histogram_counts_are_exact():
    rows = _rows()
    assert len({row["token"] for row in rows}) == len(rows), "Do not repeat tokens."
    assert all(row["count"].isdigit() and int(row["count"]) > 0 for row in rows)
    assert {row["token"]: int(row["count"]) for row in rows} == EXPECTED


def test_histogram_rows_are_sorted():
    tokens = [row["token"] for row in _rows()]
    assert tokens == sorted(tokens), "Sort tokens in ascending alphabetical order."

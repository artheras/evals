"""Public demonstration grader for deterministic bracket repair."""

from pathlib import Path


SOURCE = Path(__file__).with_name("fragments.txt")
OUT = Path(__file__).with_name("normalized.txt")
ORIGINAL = ("([])", "([)", "{[", ")[](", "(([]])", "][({")
EXPECTED = ("([])", "([])", "{[]}", "[]()", "(([]))", "[({})]")
PAIRS = {"(": ")", "[": "]", "{": "}"}


def _output():
    assert SOURCE.is_file() and not SOURCE.is_symlink(), "The input must be a regular file."
    assert tuple(SOURCE.read_text().splitlines()) == ORIGINAL, "Keep the supplied fragments unchanged."
    assert OUT.is_file() and not OUT.is_symlink(), "Create normalized.txt as a regular file."
    rows = tuple(OUT.read_text().splitlines())
    assert len(rows) == len(ORIGINAL), "Write one output line per input line, preserving order."
    return rows


def test_exact_repair_rules():
    assert _output() == EXPECTED, "Apply the specified matching-stack repair rules."


def test_every_repaired_fragment_is_balanced():
    for row in _output():
        stack = []
        for character in row:
            if character in PAIRS:
                stack.append(PAIRS[character])
            else:
                assert character in PAIRS.values() and stack and stack.pop() == character
        assert not stack, "All opened brackets must be closed."

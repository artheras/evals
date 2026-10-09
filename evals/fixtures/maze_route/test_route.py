"""Public demonstration grader for a shortest route through a toy maze."""

from collections import deque
from pathlib import Path


SOURCE = Path(__file__).with_name("maze.txt")
OUT = Path(__file__).with_name("route.txt")
DIRECTIONS = {"U": (-1, 0), "R": (0, 1), "D": (1, 0), "L": (0, -1)}
ORIGINAL = (
    "#########", "#S..#...#", "#.#.#.#E#", "#.#...#.#", "#...#...#", "#########",
)


def _grid():
    assert SOURCE.is_file() and not SOURCE.is_symlink(), "The input must be a regular file."
    rows = tuple(SOURCE.read_text().splitlines())
    assert rows == ORIGINAL, "The supplied maze must remain unchanged."
    return rows


def _points(rows):
    start = next((r, c) for r, row in enumerate(rows) for c, cell in enumerate(row) if cell == "S")
    end = next((r, c) for r, row in enumerate(rows) for c, cell in enumerate(row) if cell == "E")
    return start, end


def _distance(rows, start, end):
    queue = deque([(start, 0)])
    visited = {start}
    while queue:
        (row, column), distance = queue.popleft()
        if (row, column) == end:
            return distance
        for dr, dc in DIRECTIONS.values():
            candidate = row + dr, column + dc
            r, c = candidate
            if (0 <= r < len(rows) and 0 <= c < len(rows[r])
                    and rows[r][c] != "#" and candidate not in visited):
                visited.add(candidate)
                queue.append((candidate, distance + 1))
    raise AssertionError("The demonstration maze must have a solution.")


def test_route_reaches_exit_without_crossing_walls():
    rows = _grid()
    start, end = _points(rows)
    assert OUT.is_file() and not OUT.is_symlink(), "Create route.txt as a regular file."
    route = OUT.read_text().removesuffix("\n")
    assert route and all(move in DIRECTIONS for move in route), "Use only U, R, D, and L."
    row, column = start
    for move in route:
        dr, dc = DIRECTIONS[move]
        row, column = row + dr, column + dc
        assert 0 <= row < len(rows) and 0 <= column < len(rows[row]), "Stay inside the maze."
        assert rows[row][column] != "#", "A route cannot cross a wall."
    assert (row, column) == end, "The route must end at E."


def test_route_has_minimum_length():
    rows = _grid()
    start, end = _points(rows)
    assert OUT.is_file() and not OUT.is_symlink()
    assert len(OUT.read_text().removesuffix("\n")) == _distance(rows, start, end), "Use a shortest route."

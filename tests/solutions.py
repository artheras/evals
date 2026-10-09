"""Reference implementations and deliberate mistakes for new public demo tasks."""

from collections import Counter, deque
import csv
from pathlib import Path
import re


def solve_maze_route(workspace: Path) -> None:
    rows = (workspace / "maze.txt").read_text().splitlines()
    start = next((r, c) for r, row in enumerate(rows) for c, cell in enumerate(row) if cell == "S")
    end = next((r, c) for r, row in enumerate(rows) for c, cell in enumerate(row) if cell == "E")
    queue = deque([(start, "")])
    seen = {start}
    directions = (("U", -1, 0), ("R", 0, 1), ("D", 1, 0), ("L", 0, -1))
    while queue:
        (row, column), route = queue.popleft()
        if (row, column) == end:
            (workspace / "route.txt").write_text(route + "\n")
            return
        for move, dr, dc in directions:
            next_position = row + dr, column + dc
            r, c = next_position
            if (0 <= r < len(rows) and 0 <= c < len(rows[r])
                    and rows[r][c] != "#" and next_position not in seen):
                seen.add(next_position)
                queue.append((next_position, route + move))
    raise ValueError("The demo maze has no route.")


def solve_bracket_repair(workspace: Path) -> None:
    pairs = {"(": ")", "[": "]", "{": "}"}
    repaired = []
    for fragment in (workspace / "fragments.txt").read_text().splitlines():
        stack, output = [], []
        for character in fragment:
            if character in pairs:
                stack.append(pairs[character])
                output.append(character)
            elif stack and character == stack[-1]:
                output.append(stack.pop())
        output.extend(reversed(stack))
        repaired.append("".join(output))
    (workspace / "normalized.txt").write_text("\n".join(repaired) + "\n")


def _write_histogram(workspace: Path, counts: dict, reverse: bool = False) -> None:
    with (workspace / "histogram.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["token", "count"])
        writer.writerows((token, counts[token]) for token in sorted(counts, reverse=reverse))


def solve_word_histogram(workspace: Path) -> None:
    text = (workspace / "source.txt").read_text().lower()
    _write_histogram(workspace, Counter(re.findall(r"[a-z]+", text)))


def maze_hits_wall(workspace: Path) -> None:
    (workspace / "route.txt").write_text("U\n")


def maze_takes_detour(workspace: Path) -> None:
    solve_maze_route(workspace)
    output = workspace / "route.txt"
    output.write_text("RL" + output.read_text())


def maze_stops_early(workspace: Path) -> None:
    solve_maze_route(workspace)
    output = workspace / "route.txt"
    output.write_text(output.read_text().strip()[:-1] + "\n")


def maze_adds_whitespace(workspace: Path) -> None:
    solve_maze_route(workspace)
    output = workspace / "route.txt"
    output.write_text(" " + output.read_text() + "\n")


def brackets_left_unrepaired(workspace: Path) -> None:
    (workspace / "normalized.txt").write_text((workspace / "fragments.txt").read_text())


def brackets_all_erased(workspace: Path) -> None:
    count = len((workspace / "fragments.txt").read_text().splitlines())
    (workspace / "normalized.txt").write_text("\n" * count)


def brackets_changed_types(workspace: Path) -> None:
    solve_bracket_repair(workspace)
    output = workspace / "normalized.txt"
    output.write_text(output.read_text().replace("{", "(").replace("}", ")"))


def histogram_preserves_case(workspace: Path) -> None:
    text = (workspace / "source.txt").read_text()
    _write_histogram(workspace, Counter(re.findall(r"[A-Za-z]+", text)))


def histogram_reverse_order(workspace: Path) -> None:
    text = (workspace / "source.txt").read_text().lower()
    _write_histogram(workspace, Counter(re.findall(r"[a-z]+", text)), reverse=True)


def histogram_extra_empty_token(workspace: Path) -> None:
    solve_word_histogram(workspace)
    with (workspace / "histogram.csv").open("a") as handle:
        handle.write("empty,0\n")


SOLUTIONS = {
    "maze_route": solve_maze_route,
    "bracket_repair": solve_bracket_repair,
    "word_histogram": solve_word_histogram,
}
TRAPS = {
    "maze_route": {"wall": maze_hits_wall, "detour": maze_takes_detour, "early": maze_stops_early,
                   "whitespace": maze_adds_whitespace},
    "bracket_repair": {
        "unrepaired": brackets_left_unrepaired, "erased": brackets_all_erased,
        "changed_types": brackets_changed_types,
    },
    "word_histogram": {
        "case": histogram_preserves_case, "order": histogram_reverse_order,
        "extra": histogram_extra_empty_token,
    },
}

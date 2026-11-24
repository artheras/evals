# Task Anatomy & Output Schema

This guide explains how a public task is structured, how its isolated grader is verified, and what `summary.json` contains after a run.

## 1. Flat Fixture Layout

Every task in `evals/suites/public.yaml` points to a flat directory under `evals/fixtures/<fixture>/` containing only regular files (no subdirectories or symlinks):

```text
evals/fixtures/fw_crc16/
├── crc16.h        # Protected input given to the agent
└── test_crc16.py  # Hidden deterministic grader (listed in both `protect` and `hidden`)
```

In `evals/suites/public.yaml`:
- `id`: Unique lowercase identifier with a version suffix (e.g. `fw-crc16-v1`).
- `protect`: Every input file and grader file so the engine blocks edits to them.
- `hidden`: All `test_*.py` grader files, hidden from the workspace during the agent's turn.
- `requires`: Importable Python modules needed by the grader (e.g. `pytest`, `numpy`, `mujoco`, `trimesh`).
- `tags`: Optional metadata such as `requires-c-compiler` or `overlaps-engine-suite`.
- `verify`: Must start with the exact isolated prefix enforced by `aria-evals validate`:
  ```text
  {python} -I -m pytest -q --noconftest -p no:cacheprovider --import-mode=importlib -c /dev/null <grader.py>
  ```

## 2. Environment Check & Run Comparison

Before running `check` or `run`, verify host dependencies (POSIX host, C compiler, Python modules, and pinned runner):

```bash
aria-evals doctor
```

After two runs complete, compare their `summary.json` files (or run directories):

```bash
aria-evals diff runs/baseline runs/candidate
```

`diff` checks `catalog_sha256`, `engine_commit`, `run_kind`, `repeat`, and `solve_timeout_seconds` compatibility before reporting deltas for `counts`, `performance`, `usage`, and `cost_usd`.

## 3. Publication `summary.json` Schema

```json
{
  "schema_version": 1,
  "context": {
    "schema_version": 1,
    "run_kind": "model_evaluation",
    "catalog_version": "0.1.0",
    "catalog_commit": "...",
    "catalog_sha256": "...",
    "catalog_dirty": false,
    "engine_commit": "e5d4d4be2a5e0a07d46091ace5363e74aba05c58",
    "engine_version": "0.165.0",
    "model": "openai/example-model",
    "provider": "openai",
    "repeat": 3,
    "solve_timeout_seconds": 900
  },
  "trials": 90,
  "counts": {"pass": 0, "fail": 90, "invalid": 0, "error": 0},
  "errors": {"timed_out": 0, "other": 0},
  "duration_seconds": 12.34,
  "performance": {
    "completion_rate_all_trials": 0.0,
    "unscored_trials": {"timed_out": 0, "other_error": 0, "invalid": 0},
    "scored_trials": 90,
    "native_pass_rate_scored_only": 0.0,
    "without_engine_suite_overlap": {
      "trials": 66,
      "completion_rate_all_trials": 0.0
    }
  },
  "usage": null,
  "cost_usd": null,
  "cost_usd_partial": null,
  "cost_basis": null,
  "limitations": "..."
}
```

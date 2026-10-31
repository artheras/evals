# Aria Evals

Public evaluation examples and reproducible run records for [Aria Code](https://github.com/artheras/aria-code).

This repository contains 30 original, synthetic public tasks. Each has an executable grader that stays hidden while the agent works, a reference solution, and deliberately incorrect solutions used to calibrate that grader.

| Group | Tasks | What the answer is | How it is judged |
|---|---|---|---|
| Demonstrations | 3 | a text artifact | exact checks (maze route, bracket repair, word histogram) |
| Coding, finance, logistics | 12 | a text or CSV artifact | exact expected output |
| Firmware | 5 | a C99 source file implementing a given header | compiled with the system C compiler against a hidden test harness |
| Control | 5 | a Python controller for a MuJoCo model | simulated; the grader checks stability, limits and targets, sometimes under pushes the controller is not told about |
| 3D | 5 | an OBJ mesh | geometry: closed, consistently wound, outward, dimensions, topology, volume |

These examples are small, public, and available to contributors. They do not establish performance on unseen tasks.

The physical-AI groups need more than pytest where they are graded: `numpy`, `mujoco` and `trimesh` (installed by the `dev` extra) and a C compiler (`cc`, `gcc` or `clang`). A task whose Python requirements are missing is reported by the engine as `error` and excluded from the score. The engine's `requires` field only names importable Python modules, so it cannot declare the compiler: firmware tasks carry the tag `requires-c-compiler` instead, and on a machine without one their grader exits 127, which the pinned engine reports as `error` rather than as a failed answer. The pending engine change ([aria-code#265](https://github.com/artheras/aria-code/pull/265)) treats 125/126/127 as "could not run" only when a program named on the verify command line is really missing; a 127 from inside the check becomes `fail`, so a controller or grader cannot turn a failure into an unscored error. Under that engine a firmware task on a machine without a C compiler would score `fail`: run the firmware tasks only where `cc`, `gcc` or `clang` is installed (the GitHub runners have one) or leave out the `requires-c-compiler` tag, until the engine can declare a required program.

Eight tasks are tagged `overlaps-engine-suite` because Aria Code's own evaluation suites contain close relatives of them, which the product may have been tuned against: `max-drawdown-v1`, `fifo-realized-gains-v1`, `dock-door-schedule-v1`, `billable-weight-charges-v1`, `reorder-plan-v1`, `serpentine-pick-path-v1`, `loan-amortization-v1` and `portfolio-weights-v1`. Summaries report completion with and without them; see [how the repositories work together](docs/collaboration.md#tasks-that-overlap-the-engines-own-suites).

## How grading is isolated

Each grader runs inside the agent's workspace after the agent's turn, so nothing the agent leaves there may influence it. Every task verifies with

```
{python} -I -m pytest -q --noconftest -p no:cacheprovider --import-mode=importlib -c /dev/null <grader>
```

`-I` keeps the workspace and `PYTHON*` variables off the interpreter's path, so a planted `pytest.py` or `sitecustomize.py` is never imported; `--import-mode=importlib` stops pytest from inserting the workspace into `sys.path`, where a planted `numpy.py` would shadow the real module; `-c /dev/null` ignores any `pytest.ini`, `pyproject.toml`, `tox.ini` or `setup.cfg` in the workspace; `--noconftest` ignores `conftest.py`. `aria-evals validate` accepts no other form. The command assumes a POSIX host. The control graders never import the submitted `controller.py`: it runs in a separate `-I` interpreter that receives `(t, qpos, qvel)` and returns commands, while the simulation and all assertions stay in the grader's process. A controller process that exits early, with any status, fails. The calibration tests plant each of these hacks and require a failing grade. Rejecting planted files outright (`conftest.py`, pytest configuration, `sitecustomize.py`, `*.pth`, and modules shadowing pytest or the standard library, unless a task lists them in `allow_new`) and isolating `HOME` per attempt are engine responsibilities, added in aria-code#265. That rule does not cover a planted `numpy.py` or `mujoco.py`, which the verify command above handles.

## Get started

Use Python 3.12 or 3.13 and run commands from this repository's root.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
aria-evals validate
python -m pytest -q tests
```

The grader calibration tests cover missing answers, correct reference answers, incorrect answers, input tampering, output symlinks, files planted in the workspace, and controllers that exit early or patch the grader. Reference solvers are public test utilities, not model-generated solutions.

To exercise the official Aria evaluation engine without a model call:

```bash
python -m pip install -e '.[dev,runner]'
aria-evals check --output runs/preflight
```

`check` delegates to the engine's no-op solver. Every unfinished task must produce the native outcome `fail`; that expected result makes the preflight succeed. It confirms that an empty answer cannot pass. It does not evaluate a model.

## Run a model later

Set the provider credentials locally using Aria Code's supported configuration. Keep credentials outside this repository and do not paste them into issues, reports, or chat. An explicit `run` starts model calls and may incur provider charges:

```bash
aria-evals run \
  --model YOUR_MODEL \
  --provider YOUR_PROVIDER \
  --repeat 3 \
  --solve-timeout 900 \
  --output runs/model
```

Each output directory must be new. Omitting `--output` selects a unique directory under `runs/`. Generated records include the run manifest, completion record, native output, and an aggregate publication summary. `runs/` is ignored by Git. Review any generated file before sharing it; native output can contain task details and logs.

The wrapper normalizes provider aliases and passes an explicit `provider/model` identifier to Aria. If your model already has a provider prefix, it must agree with `--provider`. For example, `--provider openai --model YOUR_MODEL` is recorded and invoked as `openai/YOUR_MODEL`.

The summary records `pass`, `fail`, `invalid`, and `error` counts, with errors split into `timed_out` (the agent hit `--solve-timeout`: flagged `timed_out` by newer engines, exit 124 on the pinned one) and `other`. A model run's `performance` leads with `completion_rate_all_trials`, passes over every returned trial, and lists the unscored trials (timed out, other error, invalid) before the engine's `native_pass_rate_scored_only`. The scored-only rate leaves out timeouts and errors, so an agent that times out on tasks it would fail raises it; quote it only next to the completion rate and the unscored counts. `without_engine_suite_overlap` repeats the completion rate without the tasks tagged `overlaps-engine-suite`. Preflight summaries have no performance score. Usage and cost are `null` when unavailable; they are not assumed to be zero.

## Run a model on GitHub instead of a laptop

**Actions → Model evaluation → Run workflow** runs the suite on a GitHub runner, which avoids one machine's flaky connection to a provider. It is started by hand only and spends provider credit. First add the provider's key as a repository secret (`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `GOOGLE_API_KEY` or `ANTHROPIC_API_KEY`); a missing key stops the run before any task starts. The job runs the model-free preflight first, then the suite, and keeps `summary.json` as an artifact for 90 days.

## Usage and cost

When the pinned engine reports token usage, `summary.json` includes `usage`: input, output and thinking tokens, with `reported_trials` and `trials`. Totals cover only the trials that reported usage, so 12 of 30 is not the cost of the run. Trials with no report leave usage `null`, never zero, and an aggregate whose token counts are all zero is treated as no report. Whether a single trial's all-zero record counts towards `reported_trials` is decided by the engine; the pinned revision counts it, and aria-code#265 stops counting it.

A cost appears only with `--prices FILE`, a dated price table you supply:

```json
{"as_of": "2026-10-21", "source": "https://the-provider's-pricing-page", "currency": "USD",
 "per_million_tokens": {"input": 0.0, "output": 0.0, "thinking": 0.0}}
```

`thinking` defaults to the output rate. The table is read before the run starts, and its date and source are copied into `cost_basis`, because prices change and differ by account. `cost_usd` is set only when every trial reported usage. Otherwise it stays `null` and `cost_usd_partial` prices the trials that did report, with `cost_basis.covers_trials` and `of_trials` saying how many; it is a lower bound, not the cost of the run. In the workflow, a table at `prices/<provider>.json` is used if present. The repository ships no prices: none have been verified here.

## Reproducibility and scope

[`registry.json`](registry.json) pins the engine to Aria Code commit [`1138706ec418284ff87ea3219eb8911f29cea57b`](https://github.com/artheras/aria-code/tree/1138706ec418284ff87ea3219eb8911f29cea57b). The wrapper checks the installed engine's source identity. That commit follows the `v0.163.0` release and still reports distribution version `0.163.0`, because Aria Code only bumps its version when it publishes; the commit, not the version string, is the identity. Besides the earlier verification fixes (an acceptance check that runs tests beside the code, a missing tool reported as not run, a finished-but-red run scored, short answer files allowed), it is the first revision that reports real token usage per task (OpenAI and DeepSeek streams previously recorded 0 input tokens) and that recognises DeepSeek's current API models as able to use tools. Results recorded on earlier revisions are not comparable.

The pin is behind Aria Code `main` on purpose. [aria-code#265](https://github.com/artheras/aria-code/pull/265) changes the harness to reject attempts that plant files which change how the check runs, to score exit 125/126/127 as `fail` unless a program is really missing, to flag timeouts, to give each attempt its own `HOME`, and to stop counting all-zero usage as reported. The pin will be bumped to the revision that merges it, after the reference controls, the hack checks above and the preflight pass against it; until then those engine protections are not in force for runs from this catalog. Use the `runner` extra above to install that immutable Git revision. A different engine revision needs an explicit registry update and renewed validation.

The catalog content digest, catalog revision, engine revision, model settings, and run kind travel with the results. Compare scores only when the tasks, grader behavior, engine, and evaluation settings are compatible. Public task exposure and this suite's small size limit the conclusions a score can support.

Aria Code owns the agent and evaluation engine. This repository owns public tasks, calibration, and aggregate reporting. The private holdout repository retains confidential tasks and grading materials. See [how the repositories work together](docs/collaboration.md) and the [contribution guide](CONTRIBUTING.md).

The `Proof` workflow runs on pull requests and on pushes to `main`. It performs offline checks without model credentials, including positive reference controls with the official engine's graders hidden during the solver's turn, and the planted-file and hostile-controller checks; none of it makes model calls. The separate `Model evaluation` workflow is started by hand only, uses the selected provider's API key secret and nothing else, and spends provider credit. Cross-repository model evaluation and private-result publication are future integration work.

## License

The original files in this repository are [Apache License 2.0 licensed](LICENSE) (see [NOTICE](NOTICE) for the earlier MIT history). Aria Code is a separate dependency governed by its own license.

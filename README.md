# Aria Evals

Public evaluation examples and reproducible run records for [Aria Code](https://github.com/artheras/aria-code).

This repository contains three original, synthetic demonstration tasks: a shortest maze route, deterministic bracket repair, and an ASCII word histogram. Each task has an executable grader, a reference solution, and deliberately incorrect solutions used to calibrate that grader. These examples are small, public, and available to contributors. They do not establish performance on unseen tasks.

No real model results have been recorded yet. Offline checks validate the catalog and graders; their success is not a model benchmark score.

## Get started

Use Python 3.12 or 3.13 and run commands from this repository's root.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
aria-evals validate
python -m pytest -q tests
```

The grader calibration tests cover missing answers, correct reference answers, incorrect answers, input tampering, and output symlinks. Reference solvers are public test utilities, not model-generated solutions.

To exercise the official Aria evaluation engine without a model call:

```bash
python -m pip install -e '.[dev,runner]'
aria-evals check --output runs/preflight
```

`check` delegates to the engine's no-op solver. All three unfinished tasks must produce the native outcome `fail`; that expected result makes the preflight succeed. It confirms that an empty answer cannot pass. It does not evaluate a model.

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

The summary records `pass`, `fail`, `invalid`, and `error` counts. Model runs expose both the completion rate over every returned trial and the engine's rate over scored `pass`/`fail` trials. Preflight summaries have no performance score. Usage and cost are `null` when unavailable; they are not assumed to be zero.

## Reproducibility and scope

[`registry.json`](registry.json) pins the engine to Aria Code version `0.118.0`, commit [`08c28983e5a9548fdce65c911ebe2b645be39dbe`](https://github.com/artheras/aria-code/tree/08c28983e5a9548fdce65c911ebe2b645be39dbe). The wrapper checks the installed engine's source identity. Use the `runner` extra above to install that immutable Git revision. A different engine revision needs an explicit registry update and renewed validation.

The catalog content digest, catalog revision, engine revision, model settings, and run kind travel with the results. Compare scores only when the tasks, grader behavior, engine, and evaluation settings are compatible. Public task exposure and this suite's small size limit the conclusions a score can support.

Aria Code owns the agent and evaluation engine. This repository owns public tasks, calibration, and aggregate reporting. The private holdout repository retains confidential tasks and grading materials. See [how the repositories work together](docs/collaboration.md) and the [contribution guide](CONTRIBUTING.md).

CI performs offline proof checks without model credentials, including positive reference controls with the official engine's graders hidden during the solver's turn. These reference controls make no model calls. Cross-repository model evaluation and private-result publication are future integration work.

## License

The original files in this repository are [MIT licensed](LICENSE). Aria Code is a separate dependency governed by its own license.

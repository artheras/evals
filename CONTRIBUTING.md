# Contributing

Contribute original public tasks, grader improvements, and reproducibility fixes through pull requests. Keep product implementation and its unit tests in [Aria Code](https://github.com/artheras/aria-code).

## Public task requirements

Use original synthetic material or material you have permission to redistribute under this repository's MIT license. Document the source and any applicable rights. Do not submit private evaluation questions, reference answers, confidential grader rules, private transcripts, or private run logs.

A task needs a clear prompt, a small self-contained fixture, an executable deterministic grader, and meaningful calibration. Add a correct reference solution and incorrect solutions that exercise plausible failure modes. Check that missing answers fail, protected inputs cannot be changed to satisfy the grader, and output symlinks cannot redirect grading outside the workspace.

Reference solutions are public grader calibration tools. They do not measure model performance. Avoid claiming that a public task is unseen or that passing calibration establishes model quality.

Catalog validation accepts the constrained suite format used by the existing examples. Use regular fixture files and the supported Python/pytest verification command. Adding setup commands, dependencies, nested layouts, or other execution behavior requires an explicit design change and review before widening the validator.

## Validation

From the repository root with Python 3.12 or 3.13:

```bash
python -m pip install -e '.[dev]'
aria-evals validate
python -m pytest -q tests
```

For changes affecting the engine contract or task execution, also install the pinned runner and exercise the official no-op preflight:

```bash
python -m pip install -e '.[dev,runner]'
aria-evals check
```

The expected native outcome is `fail` for each unfinished task. Model evaluations are an explicit separate action and require locally configured credentials. Do not add model calls or secrets to pull-request CI.

## Versions and reports

Changing task inputs, instructions, or grading behavior changes what a score means. Give a changed task a new versioned identifier, update the suite and catalog versions, and explain the effect in the pull request. Engine changes must update the immutable registry pin and repeat the contract checks.

Keep generated runs out of commits. Report fixes should preserve the distinction between model-free preflight and model evaluation, keep all outcome counts visible, and represent unavailable usage or cost as `null`. Aggregate publication must not copy arbitrary native task fields or raw logs.

Describe the problem, the resulting behavior, and relevant validation in your pull request. If the change introduces a new task, explain its provenance and what its negative examples demonstrate.

By contributing, you agree that your original contributions are provided under this repository's MIT license.

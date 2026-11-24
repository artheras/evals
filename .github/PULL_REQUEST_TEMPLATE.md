## Summary

<!-- Describe the problem, the resulting behavior, and why this change belongs in the public catalog. -->

## Provenance & Scope (for new or updated tasks)

- [ ] Content is original synthetic material or has explicit Apache-2.0 redistribution permission.
- [ ] No private holdout tasks, confidential grader rules, private transcripts, or raw run logs are included.
- [ ] Changed task behavior uses a new versioned task ID and updates suite/catalog versions.
- [ ] New tasks include a reference solution and negative calibration cases (missing answer, wrong answer, input tampering, output symlink, planted workspace files).

## Validation

- [ ] `aria-evals doctor`
- [ ] `aria-evals validate`
- [ ] `python -m pytest -q tests`
- [ ] `aria-evals check` (required when changing engine contract or task execution)

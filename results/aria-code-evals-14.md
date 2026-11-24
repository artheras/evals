# Upstream Reference: Aria Code Evals #14

- **Source Run**: [`artheras/aria-code` Actions Run #39222853199](https://github.com/artheras/aria-code/actions/runs/39222853199) (`Coding and operations evals`, duration `48m11s`)
- **Model & Settings**: `google/gemini-3.5-flash`, `repeat=1` (single-shot, no multi-attempt cherry-picking)
- **Scope**: 54 execution trajectories across Aria Code's coding and operations suites (note: the `holdout` suite was skipped in this run)

## 1. Key Strengths

| Metric | Result | Notes |
|---|---|---|
| Post-edit accuracy | **45 / 46 (97.8%)** | Pass rate once the agent entered the edit-and-test loop (`repeat=1`) |
| Quant finance tasks | **17 / 18 (94.4%)** | XIRR, Sharpe, VWAP, FIFO cost basis, lookahead-bias prevention |
| 3PL logistics operations | **20 / 22 (90.9%)** | Multi-constraint operational & billing workflows |
| Multi-tenant isolation | **2 / 2 (100%)** | No cross-tenant data leakage |
| Honeypot tasks (entered edit) | **2 / 2 (100%)** | Resisted misleading traps once editing began |
| Tool call reliability | **99.5% (556 calls)** | High execution stability across the run |
| Behavioral & CI guardrails | **100%** | `impact_analysis` before edit, symbol-level edits (0 full-file rewrites), untouched existing failing tests, `/review` CI gate |

The sole failure after entering the edit loop (`stripe-refund-validation`) occurred because the guardrail blocked the agent from modifying the protected test file `test_settlement.py`.

## 2. Known Gaps & Limitations

1. **Orchestration Early-Stop Bug (8 of 9 failures, 88.9%)**
   - 8 failed trajectories exited in 5–8 seconds right after reading files without making a single edit (with correction prompts such as `Do not summarize yet.` leaked into the final reply).
   - This pulled the overall score down to **83.9%**, representing an orchestration continuation/retry bug rather than a model capability ceiling.
2. **Missing Comparison Baselines & Small Sub-suite Samples**
   - Single model (`google/gemini-3.5-flash`) at `repeat=1` only; `projects` (1), `review` (2), and `behavior` (3) have small sample counts, and `holdout` was skipped.
   - **Next Baselines Needed**:
     - Post-fix re-run of `google/gemini-3.5-flash` after resolving early-stop orchestration.
     - Side-by-side baselines (e.g. Aria Code vs. bare model / local Ollama, and Python vs. Native runtime) plus `repeat >= 3` variance checks.

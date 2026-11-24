# Price Table Templates

Copy [`template.json`](template.json) to `prices/<provider>.json` (for example `prices/openai.json`) and fill in the verified rates for your account before running `aria-evals run --prices ...` or triggering the GitHub **Model evaluation** workflow.

Required fields (validated by `aria_evals.reporting.load_prices`):
- `as_of`: ISO date string when the rates were checked.
- `source`: `https://` URL of the provider's pricing page.
- `currency`: Must be `"USD"`.
- `per_million_tokens`: Non-negative numbers for `input`, `output`, and optional `thinking` (defaults to `output` when omitted).

This repository ships no live provider prices because rates change and vary by account tier.

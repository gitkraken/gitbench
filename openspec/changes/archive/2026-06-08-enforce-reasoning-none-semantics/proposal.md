## Why

GitBench currently accepts `:none` when the shipped effort matrix lists it, but that only proves the value is configured, not that the routed provider endpoint actually disables reasoning. This can silently produce reasoning tokens in a no-reasoning baseline, inflate or double-count reported output tokens, and distort benchmark comparisons.

## What Changes

- Keep the existing static validation for supported reasoning levels, but require a live preflight for every OpenRouter model configured with `none`.
- Send the provider-specific reasoning-disable request and abort the complete run before benchmark execution when the response still contains reasoning tokens or reasoning content.
- Continue checking `none` responses during benchmark execution so a later routing change cannot silently invalidate the baseline.
- Correct the shipped effort matrix where current provider documentation does not support the listed effort levels.
- Treat provider `output_tokens` as inclusive of reasoning tokens and derive visible/non-reasoning output for displays and stacked charts without changing stored provider usage totals.
- Replace ambiguous token badges with labels that make inclusive output and reasoning-token membership explicit.
- Correct `blame_forensics/f010` so exactly one commit introduces the broken import, and bump the benchmark suite version because the fixture's pass/fail behavior changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-capability-cache`: Keep shipped effort-level data aligned with documented provider support and prevent unsupported levels from passing validation.
- `reasoning-level-config`: Extend the existing pre-run validation gate with behavioral verification for `none` and immediate whole-run failure when disabling reasoning is not honored.
- `reasoning-level-forwarding`: Define the explicit provider-specific disable request and the runtime invariant for `none` responses.
- `reasoning-token-measurement`: Define inclusive output-token semantics and safe derivation of visible/non-reasoning output tokens.
- `report-pages`: Present total output and reasoning tokens without implying that reasoning is additional to provider output.
- `token-usage-chart`: Stack non-reasoning output and reasoning as a decomposition of total output rather than double-counting reasoning.
- `fixture-calibration`: Remove the ambiguity in `blame_forensics/f010` and preserve result comparability through a suite-version bump.

## Impact

Affected areas include model capability data and validation, the OpenRouter request path, benchmark-run failure handling, token aggregation and chart preparation, report-page token labels, the `blame_forensics/f010` fixture, and benchmark suite version metadata. The `output_tokens`, `reasoning_tokens`, and `total_tokens` persisted fields remain backward compatible; only their presentation and decomposition change.

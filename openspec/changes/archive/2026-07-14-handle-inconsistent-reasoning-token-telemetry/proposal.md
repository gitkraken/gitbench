## Why

Some providers report `reasoning_tokens` values that exceed their reported `output_tokens`, even though the current report UI labels reasoning as "within output." This makes token chart tooltips impossible to interpret and can make stacked bars exceed the provider-reported `total_tokens`.

## What Changes

- Preserve raw provider telemetry for `input_tokens`, `output_tokens`, `total_tokens`, and `reasoning_tokens`.
- Extend token decomposition so presentation code distinguishes reasoning that can fit within output from reasoning overflow caused by inconsistent provider telemetry.
- Update token usage chart stacks so representative bars never exceed the provider-reported total because of inconsistent reasoning counts.
- Update token usage chart tooltips with a compact, color-coded `total · (input / output / reasoning)` legend and one single-line value group per effort. Keep effort values at the same font size as other chart tooltips, and disclose inconsistent overflow with compact notation and one shared footnote.
- Add regression coverage for aggregated model summaries and fixture-scoped token charts where `reasoning_tokens > output_tokens`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `reasoning-token-measurement`: token decomposition will expose bounded reasoning-within-output and overflow/inconsistency metadata while preserving raw values.
- `token-usage-chart`: stacked bars and tooltips will use the bounded decomposition and explicitly call out inconsistent provider reasoning telemetry.

## Impact

- Affected code: `web/src/lib/token-usage.ts`, `web/src/components/charts/model-groups.ts`, `web/src/components/charts/TokenUsageChart.tsx`, and focused web tests.
- Data model: no database migration; persisted raw provider token fields remain unchanged.
- APIs: no breaking API changes expected, though internal chart row data may gain derived token-decomposition fields.

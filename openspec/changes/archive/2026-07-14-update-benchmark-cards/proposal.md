## Why

The Benchmarks index currently shows only the best pass-rate percentage and fixture count for each benchmark, which makes the cards less useful for quickly comparing benchmark difficulty and model spread. The cards should summarize the best, worst, and average eligible model performance while avoiding misleading 0% JSON-schema entries caused by unsupported structured output.

## What Changes

- Show the best model and score for each benchmark card.
- Show the worst model and score for each benchmark card.
- Show the average eligible score beside the benchmark title on each card.
- Replace tied best or worst model names with a count, such as `216 models`, when multiple models share the same score.
- Derive one benchmark score per base model from its fixture pass percentage across eligible effort levels and output modes.
- Exclude only strict unsupported JSON-schema zero scores from best/worst/average calculations.
- Remove the existing fixture count from Benchmark index cards.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `report-pages`: Benchmarks index cards will expose best, worst, and average benchmark-level model performance summaries instead of fixture counts.

## Impact

- Affects the Benchmarks index page at `web/src/pages/benchmarks/index.astro`.
- May introduce a small report-summary helper so benchmark-card calculations are testable outside the Astro template.
- Uses existing report artifact fields: `models`, `fixtures`, and per-fixture structured-output error metadata.
- No API, database, or dependency changes are expected.

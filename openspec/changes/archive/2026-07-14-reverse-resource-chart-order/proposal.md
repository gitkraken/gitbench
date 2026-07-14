## Why

The API Cost, API Time, and Token Usage charts currently place their lowest values on the left and highest values on the right. Reversing that order makes the largest resource consumers immediately visible and aligns these overview charts with the existing highest-first ordering used by the Pass Rate chart.

## What Changes

- Sort API Cost chart categories from highest representative cost on the left to lowest on the right.
- Sort API Time chart categories from highest representative API time on the left to lowest on the right.
- Sort Token Usage chart categories from highest representative token count on the left to lowest on the right.
- Preserve the current representative-value calculation for individual output modes and the mean-of-available-representatives calculation in `Both` mode.
- Apply the ordering consistently to overview, benchmark-scoped, and fixture-scoped renderings that reuse these chart components.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cost-value-chart`: Change category ordering from lowest-cost-first to highest-cost-first.
- `runtime-chart`: Change category ordering from fastest-first to highest-API-time-first.
- `token-usage-chart`: Change category ordering from lowest-token-first to highest-token-first.

## Impact

The change affects client-side category sorting in `CostValueChart`, `RuntimeBarChart`, and `TokenUsageChart`, plus focused regression coverage for their ordering. It does not change chart data, API contracts, metric calculations, axes, tooltips, filters, dependencies, or persistence.

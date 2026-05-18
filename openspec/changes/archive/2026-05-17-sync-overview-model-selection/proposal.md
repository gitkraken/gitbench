## Why

Model selectors on the Overview page currently appear to synchronize visually, but several charts keep rendering their previous model set after another chart's selector changes. This creates a misleading page state where dropdowns agree but the graphs do not.

## What Changes

- Ensure model selection changes from any Overview chart update every graph on the Overview page.
- Keep selector UI, chart data, empty-state messaging, provider legends, and table columns derived from the same selected model set.
- Preserve the existing `gitbench-model-selection` localStorage persistence and `model-selection-changed` event behavior.
- Ensure charts that render no-data states still participate in model selection synchronization.
- No breaking API or data schema changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `searchable-model-selector`: External model selection events SHALL propagate to consuming chart state, not only to the dropdown's internal selected display.
- `chart-components`: Overview charts that live in this shared chart capability, including Model Summary and Benchmark Matrix, SHALL react to shared model selection changes.
- `cost-value-chart`: Cost per Full Run SHALL react to shared Overview model selection changes, including no-pricing-data states.
- `runtime-chart`: Runtime SHALL react to shared Overview model selection changes, including no-runtime-data states.
- `token-usage-chart`: Token Usage SHALL react to shared Overview model selection changes, including no-token-data states.

## Impact

- Affected React components: `gitbench/web/src/components/charts/ModelSelector.tsx`, `PassRateBarChart.tsx`, `BenchmarkHeatmap.tsx`, `CostValueChart.tsx`, `RuntimeBarChart.tsx`, and `TokenUsageChart.tsx`.
- Likely new shared helper/hook in `gitbench/web/src/components/charts/` or `gitbench/web/src/lib/` to centralize selected-model state.
- No backend, aggregation, results JSON, route, or dependency changes.

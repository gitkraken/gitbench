## Why

Model labels on the web chart axes are currently truncated so aggressively that several current benchmark models are hard to identify at a glance. The chart data now includes base model names in the 20-30 character range, and the overview charts should show those names in full instead of cutting them to about 10 characters.

## What Changes

- Replace the grouped bar chart model-axis truncation with full provider/base-model labels.
- Keep the existing provider icon + rotated label pattern, but resize the label drawing area so full model names do not clip.
- Ensure dense or narrow chart layouts preserve readable full labels, using chart width or scroll affordances instead of ellipsis.
- Update the existing chart requirements that currently mandate truncated base model names.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `chart-components`: Change shared grouped chart label requirements from truncated base model names to full base model names, with enough chart/tick space to avoid clipping.
- `cost-value-chart`: Change CostValueChart X-axis label requirements from truncated base model names to full base model names.
- `runtime-chart`: Change RuntimeBarChart X-axis label requirements from truncated base model names to full base model names.
- `token-usage-chart`: Change TokenUsageChart X-axis label requirements from truncated base model names to full base model names.

## Impact

- **Affected code**: `web/src/components/charts/grouped-chart-ui.tsx` is the primary implementation point. Consumers of `VerticalGroupedMetricChart` inherit the behavior: `PassRateBarChart.tsx`, `CostValueChart.tsx`, `RuntimeBarChart.tsx`, and `TokenUsageChart.tsx`.
- **Affected specs**: `chart-components`, `cost-value-chart`, `runtime-chart`, and `token-usage-chart`.
- **No API changes, no backend changes, no data-shape changes, no new dependencies**.
- **Risk**: visual layout risk on dense or narrow chart widths. The implementation should verify current long labels such as `gemini-3.1-flash-lite-preview` and dense all-model selections.

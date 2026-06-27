## Why

The GitBench web dashboard has five chart components that lack axis labels — the four vertical bar charts (PassRateBarChart, CostValueChart, RuntimeBarChart, TokenUsageChart) and the TimeSeriesChart. A chart's Y-axis units (%, $, seconds, tokens) are only discoverable by scrolling up to the section heading above it. If someone screenshots a chart, shares it, or simply scrolls past the heading, the chart becomes ambiguous. Additionally, the QuadrantComparisonChart shades its "optimal quadrant" but does not label any of its four quadrants, requiring the user to read a separate text line to understand the spatial layout.

## What Changes

- **Y-axis labels on all bar charts**: The shared `VerticalGroupedMetricChart` component gains a `yAxisLabel` prop. Each of the four bar chart consumers (PassRateBarChart, CostValueChart, RuntimeBarChart, TokenUsageChart) passes its metric label (e.g., "Pass Rate (%)", "Cost (USD)", "API Time (s)", "Tokens") so the Y-axis is self-describing.
- **Y-axis label on TimeSeriesChart**: The time series line chart gains a "Pass Rate (%)" Y-axis label on both its campaign-history and per-model variants.
- **Quadrant labels on QuadrantComparisonChart**: Each of the four quadrants gets a short, generic directional label positioned inside the quadrant area. Labels use generic phrasing ("Better on both", "Better {xMetric} / Worse {yMetric}", "Worse {xMetric} / Better {yMetric}", "Worse on both") so they remain correct regardless of which metrics are selected for the X and Y axes.

## Capabilities

### Modified Capabilities
- `chart-components`: Add Y-axis labels to `VerticalGroupedMetricChart` (consumed by PassRateBarChart, CostValueChart, RuntimeBarChart, TokenUsageChart). Add Y-axis label to `TimeSeriesChart`. Add quadrant position labels to `QuadrantComparisonChart`.

## Impact

- **Affected code**: `grouped-chart-ui.tsx` (add `yAxisLabel` prop to `VerticalGroupedMetricChart`), `PassRateBarChart.tsx`, `CostValueChart.tsx`, `RuntimeBarChart.tsx`, `TokenUsageChart.tsx` (pass label prop), `TimeSeriesChart.tsx` (add Y-axis label), `QuadrantComparisonChart.tsx` (add quadrant labels)
- **No API changes, no backend changes, no new dependencies**
- **Breaking**: None — all changes are additive (new labels, existing behavior preserved)
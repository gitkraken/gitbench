## 1. Y-axis labels on bar charts

- [x] 1.1 Add `yAxisLabel?: string` prop to `VerticalGroupedMetricChart` in `grouped-chart-ui.tsx` and pass it to the Recharts `<YAxis>` `label` config
- [x] 1.2 Pass `yAxisLabel="Pass Rate (%)"` from `PassRateBarChart.tsx`
- [x] 1.3 Pass `yAxisLabel="Cost (USD)"` from `CostValueChart.tsx`
- [x] 1.4 Pass `yAxisLabel="API Time (s)"` from `RuntimeBarChart.tsx`
- [x] 1.5 Pass `yAxisLabel="Tokens"` from `TokenUsageChart.tsx`
- [x] 1.6 Verify Y-axis label does not overlap tick values on narrow viewports; adjust left margin if needed

## 2. Y-axis label on TimeSeriesChart

- [x] 2.1 Add "Pass Rate (%)" Y-axis label to the campaign-history `<YAxis>` in `TimeSeriesChart.tsx`
- [x] 2.2 Add "Pass Rate (%)" Y-axis label to the per-model `<YAxis>` in `TimeSeriesChart.tsx`

## 3. Quadrant labels on QuadrantComparisonChart

- [x] 3.1 Add quadrant label rendering to `QuadrantComparisonChart.tsx` — four `Label` elements positioned inside each quadrant's `ReferenceArea` at the outer corner
- [x] 3.2 Compute label text dynamically from `xMetric.shortLabel` and `yMetric.shortLabel` with "Better on both" / "Worse on both" / "Better {x} / Worse {y}" / "Worse {x} / Better {y}" phrasing
- [x] 3.3 Style labels with 10px monospace font, `var(--text-dim)` color
- [x] 3.4 Verify labels update correctly when user swaps X or Y metric
- [x] 3.5 Verify labels do not overlap data points near center on typical datasets
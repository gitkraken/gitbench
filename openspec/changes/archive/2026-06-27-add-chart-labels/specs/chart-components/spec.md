## ADDED Requirements

### Requirement: VerticalGroupedMetricChart displays Y-axis metric label
The `VerticalGroupedMetricChart` component SHALL accept an optional `yAxisLabel` string prop. When provided, the Y-axis SHALL render a rotated label (−90°) identifying the metric and its unit (e.g., "Pass Rate (%)", "Cost (USD)", "API Time (s)", "Tokens"). The label SHALL use the same font family and dim color as existing axis ticks. When the prop is omitted, no label SHALL be rendered.

#### Scenario: Pass rate chart shows Y-axis label
- **WHEN** `PassRateBarChart` renders via `VerticalGroupedMetricChart` with `yAxisLabel="Pass Rate (%)"`
- **THEN** a rotated "Pass Rate (%)" label appears along the Y-axis

#### Scenario: Cost chart shows Y-axis label
- **WHEN** `CostValueChart` renders via `VerticalGroupedMetricChart` with `yAxisLabel="Cost (USD)"`
- **THEN** a rotated "Cost (USD)" label appears along the Y-axis

#### Scenario: Runtime chart shows Y-axis label
- **WHEN** `RuntimeBarChart` renders via `VerticalGroupedMetricChart` with `yAxisLabel="API Time (s)"`
- **THEN** a rotated "API Time (s)" label appears along the Y-axis

#### Scenario: Token chart shows Y-axis label
- **WHEN** `TokenUsageChart` renders via `VerticalGroupedMetricChart` with `yAxisLabel="Tokens"`
- **THEN** a rotated "Tokens" label appears along the Y-axis

#### Scenario: Omitted label renders nothing
- **WHEN** a chart renders via `VerticalGroupedMetricChart` without passing `yAxisLabel`
- **THEN** no Y-axis label is rendered and existing behavior is preserved

### Requirement: TimeSeriesChart displays Y-axis label
The `TimeSeriesChart` component SHALL render a "Pass Rate (%)" Y-axis label on both its campaign-history variant and its per-model variant. The label SHALL be rotated −90° and use the same font family and dim color as existing axis ticks.

#### Scenario: Campaign history variant shows Y-axis label
- **WHEN** the campaign-history line chart renders with campaign points
- **THEN** a rotated "Pass Rate (%)" label appears along the Y-axis

#### Scenario: Per-model variant shows Y-axis label
- **WHEN** the per-model line chart renders with selected model lines
- **THEN** a rotated "Pass Rate (%)" label appears along the Y-axis

### Requirement: QuadrantComparisonChart displays quadrant position labels
The `QuadrantComparisonChart` SHALL render a short text label inside each of its four quadrants. The optimal quadrant (both metrics in their better direction) SHALL be labeled "Better on both". The worst quadrant (both metrics in their worse direction) SHALL be labeled "Worse on both". The two trade-off quadrants SHALL be labeled "Better {xMetric.shortLabel} / Worse {yMetric.shortLabel}" and "Worse {xMetric.shortLabel} / Better {yMetric.shortLabel}" respectively. Labels SHALL use 10px monospace font and dim color. Labels SHALL be positioned at the outer corner of each quadrant, farthest from the chart center crosshair.

#### Scenario: Optimal quadrant is labeled
- **WHEN** the quadrant chart renders with cost on X (lower is better) and pass rate on Y (higher is better)
- **THEN** the top-left quadrant (low cost, high pass rate) displays "Better on both"

#### Scenario: Worst quadrant is labeled
- **WHEN** the quadrant chart renders with cost on X (lower is better) and pass rate on Y (higher is better)
- **THEN** the bottom-right quadrant (high cost, low pass rate) displays "Worse on both"

#### Scenario: Trade-off quadrants use metric short labels
- **WHEN** the quadrant chart renders with cost on X and pass rate on Y
- **THEN** one trade-off quadrant displays "Better Cost / Worse Pass Rate" and the other displays "Worse Cost / Better Pass Rate"

#### Scenario: Labels update when metrics are swapped
- **WHEN** a user changes the X metric from cost to tokens
- **THEN** the trade-off quadrant labels update to use "Tokens" instead of "Cost"

#### Scenario: Labels do not overlap data points near center
- **WHEN** data points cluster near the median crosshair
- **THEN** quadrant labels remain positioned at the outer corners of each quadrant, away from the cluster
## ADDED Requirements

### Requirement: Chart tooltips include explanatory context
All six React chart components (PassRateBarChart, CostValueChart, RuntimeBarChart, TokenUsageChart, ScatterPlot, TimeSeriesChart) SHALL include explanatory text in their Recharts `<Tooltip>` content. The tooltip content SHALL display the existing data (model name, effort levels, values) followed by a thin visual separator and a 1-2 sentence explanation of what the metric means. The explanatory text SHALL use the same `tooltipStyle` styling (color, font, font size).

#### Scenario: Pass rate tooltip explains the metric
- **WHEN** a user hovers over a bar in PassRateBarChart
- **THEN** the tooltip shows the model name and pass rates, then a separator, then text explaining that the pass rate represents the percentage of 204 fixtures answered correctly

#### Scenario: Cost tooltip explains the metric
- **WHEN** a user hovers over a bar in CostValueChart
- **THEN** the tooltip shows cost data and a separator, then text explaining that cost is total USD via OpenRouter and that — means local/Ollama

#### Scenario: Runtime tooltip explains the metric
- **WHEN** a user hovers over a bar in RuntimeBarChart
- **THEN** the tooltip shows runtime data and a separator, then text explaining that runtime is wall-clock time affected by API latency

#### Scenario: Token usage tooltip explains the metric
- **WHEN** a user hovers over a bar in TokenUsageChart
- **THEN** the tooltip shows token data and a separator, then text explaining that tokens are combined input + output totals

#### Scenario: Scatter plot tooltip explains the metric
- **WHEN** a user hovers over a dot in ScatterPlot
- **THEN** the tooltip shows similarity values for both models and text explaining the color coding (green = both passed, yellow = one passed, red = both failed)

#### Scenario: Time series tooltip explains the metric
- **WHEN** a user hovers over a point in TimeSeriesChart
- **THEN** the tooltip shows the date and pass rate, then text explaining that pass rates are shown as percentages of total fixtures

### Requirement: Chart wrapper elements have title attributes
Each chart component's outermost rendered element SHALL include a `title` attribute with a brief description of what the chart displays, serving as a fallback for users who cannot interact with the Recharts tooltips.

#### Scenario: Chart has title attribute
- **WHEN** inspecting a rendered chart component (e.g., PassRateBarChart wrapper div)
- **THEN** it has a `title` attribute with descriptive text like "Pass rate percentages for each model across all 204 Git fixtures"

### Requirement: BenchmarkHeatmap cells have enhanced title attributes
The BenchmarkHeatmap React component SHALL render `<td>` elements with `title` attributes containing descriptive cell information. Each cell title SHALL include the model name, benchmark name, pass rate percentage, passed/total counts, and a qualitative descriptor (Strong/Moderate/Weak based on pass rate thresholds: ≥80% Strong, ≥50% Moderate, <50% Weak).

#### Scenario: Heatmap cell title shows full context
- **WHEN** a user hovers over a heatmap cell for model "openai/o3-mini#high" on benchmark "rebase" with 91.7% and 11/12 passed
- **THEN** the `title` attribute shows: "openai/o3-mini#high on rebase: 91.7% (11/12 passed) — Strong"

#### Scenario: Heatmap cell title for missing data
- **WHEN** a cell has no data for a model×benchmark combination
- **THEN** the `title` attribute shows "No data available for [model] on [benchmark]"

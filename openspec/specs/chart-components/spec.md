## Purpose

Chart components render interactive Recharts-based visualizations of benchmark data as React islands within the Astro site.
## Requirements
### Requirement: ModelSelector provides independent multi-select for models and reasoning levels
The `ModelSelector` React component SHALL render a multi-select interface listing provider/base-model groups for Overview chart selection. Each entry SHALL represent one base model group and SHALL include the effort levels available in that group as contextual detail. Selecting a group SHALL select that provider/base-model group for Overview charts; it SHALL NOT expose independent checkboxes for each effort level in Overview mode. The component SHALL expose selected group IDs via an `onChange` callback and accept an `initialSelected` prop for pre-selection.

#### Scenario: All base model groups are listed
- **WHEN** `ModelSelector` renders with a dataset containing `openai/gpt-5:low`, `openai/gpt-5:high`, and `anthropic/claude-sonnet:medium`
- **THEN** two selectable entries appear: `openai/gpt-5` and `anthropic/claude-sonnet`

#### Scenario: Group selection selects all efforts for chart grouping
- **WHEN** a user checks `openai/gpt-5`
- **THEN** the selected value contains the `openai/gpt-5` group ID and grouped Overview charts include the low and high effort values for that base model

#### Scenario: onChange fires with selected group list
- **WHEN** a user toggles group selections
- **THEN** the `onChange` callback receives the complete array of currently selected group IDs

#### Scenario: Quick-select shortcuts are sticky at top of dropdown
- **WHEN** `ModelSelector` dropdown is open and the model list is scrolled
- **THEN** "Select all" and "Clear" controls remain visible at the top of the dropdown, above the scrollable list

#### Scenario: Quick-select shortcuts are always clickable
- **WHEN** `ModelSelector` dropdown is open with many model groups visible
- **THEN** "Select all" and "Clear" controls are always reachable without scrolling

#### Scenario: Pass-rate badges remain readable on hover and selection
- **WHEN** a model group row is hovered or selected (keyboard or mouse) and displays a colored pass-rate range badge
- **THEN** the badge text SHALL remain clearly readable against the row's hover/selection background

### Requirement: Overview chart components share model selection
Overview chart components in the shared chart-components capability SHALL update their rendered data when any Overview `ModelSelector` changes the selected provider/base-model group set. The selected group set SHALL be the complete array from the latest model selection change, and each chart SHALL use that set for all model-dependent bars, columns, legends, and labels. Components that still render effort-level data SHALL expand selected groups to their child model+effort names internally.

#### Scenario: Model Summary updates from another selector
- **WHEN** a user changes the selected model groups in the Benchmark Matrix selector
- **THEN** the Model Summary chart updates its bars to match the same selected group set

#### Scenario: Benchmark Matrix updates from another selector
- **WHEN** a user changes the selected model groups in the Model Summary selector
- **THEN** the Benchmark Matrix updates its rendered model columns from the same selected group set

#### Scenario: Provider legend follows shared selection
- **WHEN** a shared group selection change removes all model groups for a provider from the Model Summary chart
- **THEN** that provider is removed from the Model Summary provider legend

#### Scenario: Stored model-level selection is migrated
- **WHEN** localStorage contains old model+effort names such as `openai/gpt-5:high`
- **THEN** Overview selection initializes with the corresponding `openai/gpt-5` group ID

#### Scenario: Unknown stored values are ignored
- **WHEN** localStorage contains values that are not known model names or group IDs
- **THEN** those values are ignored when initializing Overview selection

### Requirement: BenchmarkHeatmap renders interactive heatmap
The `BenchmarkHeatmap` React component SHALL render a matrix where rows are benchmarks and columns are selected models. Each cell SHALL display the pass rate percentage with a background color intensity proportional to the pass rate. Clicking a column header SHALL navigate to the corresponding Model Detail page. Clicking a row label SHALL navigate to the corresponding Benchmark Detail page. Clicking a cell SHALL navigate to the Benchmark Detail page.

#### Scenario: Heatmap has benchmarks as rows
- **WHEN** `BenchmarkHeatmap` renders with 17 benchmarks
- **THEN** 17 rows are displayed, each labeled with the benchmark name

#### Scenario: Cell color intensity reflects pass rate
- **WHEN** a benchmark×model cell has 92% pass rate
- **THEN** the cell background is more intensely colored than a cell with 45% pass rate

#### Scenario: Clicking a row label navigates
- **WHEN** a user clicks the "commit_messages" row label
- **THEN** the browser navigates to `/benchmarks/commit_messages`

### Requirement: TimeSeriesChart renders line chart over calendar time
The `TimeSeriesChart` React component SHALL render a Recharts line chart with calendar date on the X-axis and pass rate percentage on the Y-axis. One line SHALL be drawn per selected model. The component SHALL accept a `data` prop containing run history and a `selectedModels` prop.

#### Scenario: One line per selected model
- **WHEN** `TimeSeriesChart` receives `selectedModels=['gpt-4o#high', 'claude-sonnet']`
- **THEN** two lines are drawn showing their pass rates over time

#### Scenario: Points are plotted at each run timestamp
- **WHEN** a model has 5 runs over 2 weeks
- **THEN** 5 data points appear on its line at the corresponding dates

### Requirement: ScatterPlot renders per-fixture similarity scatter
The `ScatterPlot` React component SHALL render a Recharts scatter plot comparing two models. Each dot SHALL represent one fixture, with the X-axis showing model A's similarity and the Y-axis showing model B's similarity. Dots SHALL be color-coded: green when both models passed, yellow when one passed, red when both failed. The component SHALL accept props for `data`, `modelA`, and `modelB`.

#### Scenario: Dots represent fixtures
- **WHEN** `ScatterPlot` renders comparing two models across 200 fixtures
- **THEN** 200 dots appear on the scatter plot

#### Scenario: Both-passed fixtures are green
- **WHEN** a fixture was passed by both selected models
- **THEN** its dot is rendered in green

### Requirement: All chart components are client:load React islands
All chart components SHALL be imported into Astro pages with the `client:load` directive so they hydrate immediately on page load. They SHALL NOT be rendered at build time.

#### Scenario: Chart is a React island
- **WHEN** an Astro page includes `<PassRateBarChart client:load />`
- **THEN** the component is rendered by React after page load, not in the static HTML

### Requirement: Chart tooltip footnotes use conversational fragments
React chart components that display a separator + explanatory footnote in their Recharts `<Tooltip>` content SHALL use short conversational fragments. Each footnote SHALL be a single line (or fragment), not a multi-sentence explanation. Footnotes SHALL follow the conversational prose voice: no emdashes, contractions preferred, no hedging.

#### Scenario: PassRateBarChart footnote is a fragment
- **WHEN** hovering a bar in PassRateBarChart
- **THEN** the tooltip footnote below the separator reads "% of 204 fixtures passed"

#### Scenario: CostValueChart footnote is a fragment
- **WHEN** hovering a bar in CostValueChart
- **THEN** the tooltip footnote below the separator reads "API cost for 204-fixture run. - = local/Ollama"

#### Scenario: RuntimeBarChart footnote includes latency caveat
- **WHEN** hovering a bar in RuntimeBarChart
- **THEN** the tooltip footnote below the separator reads "API call latency. Lower is faster."

#### Scenario: TokenUsageChart footnote is a fragment
- **WHEN** hovering a bar in TokenUsageChart
- **THEN** the tooltip footnote below the separator reads "Tokens in + out. Fewer is more efficient."

#### Scenario: TimeSeriesChart footnote is minimal
- **WHEN** hovering a point in TimeSeriesChart
- **THEN** the tooltip footnote below the separator reads "Pass rate on this date."

### Requirement: ScatterPlot and QuadrantComparisonChart drop tooltip footnotes
The ScatterPlot and QuadrantComparisonChart React components SHALL NOT display a separator + footnote in their Recharts `<Tooltip>` content. The axes and labels on these charts are sufficient to understand the data.

#### Scenario: ScatterPlot has no footnote
- **WHEN** hovering a dot in ScatterPlot
- **THEN** no separator line or explanatory footnote appears in the tooltip

#### Scenario: QuadrantComparisonChart has no footnote
- **WHEN** hovering a point in QuadrantComparisonChart
- **THEN** no separator line or explanatory footnote appears in the tooltip

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

### Requirement: Overview grouped metric charts use vertical range-whisker bars
Overview grouped metric bar charts SHALL use a shared vertical chart language for pass rate, cost, API time, and token usage. Each chart SHALL place provider/base-model groups on the X-axis and the metric value on the Y-axis. The provider-colored solid bar SHALL start at zero and end at the chart's representative effort value, computed as the median of deduped effort values for that group. A neutral range whisker SHALL show the full effort range from `minValue` to `maxValue`. Range whiskers SHALL NOT be described as error bars in user-facing copy or specs.

#### Scenario: Solid bar shows representative value
- **WHEN** a grouped metric row has deduped effort values `[72, 81, 85]`, `minValue=72`, and `maxValue=85`
- **THEN** the solid bar extends from 0 to 81 and the range whisker spans 72 to 85

#### Scenario: Lower-is-better metric uses median value as bar height
- **WHEN** a grouped metric row for cost has effort values `$0.10`, `$0.20`, and `$0.50`
- **THEN** the solid bar extends from 0 to `$0.20` and the range whisker spans `$0.10` to `$0.50`

#### Scenario: Duplicate values do not overweight the median
- **WHEN** a grouped metric row has effort values `[10, 10, 10, 20, 50]`
- **THEN** the representative effort value is computed from deduped values `[10, 20, 50]`, so the solid bar extends from 0 to 20 and the range whisker spans 10 to 50

#### Scenario: Numeric axis starts at zero
- **WHEN** any grouped metric chart renders
- **THEN** its numeric Y-axis lower bound is 0

#### Scenario: Diagonal group labels are reused
- **WHEN** any grouped metric chart renders an X-axis tick
- **THEN** the tick uses the existing diagonal provider-icon label pattern with `-40` degree rotation and a truncated base model name

#### Scenario: Single-effort groups remain visible
- **WHEN** a grouped metric row has `minValue`, `maxValue`, and `representativeValue` all equal
- **THEN** the solid bar remains visible from 0 to the representative value and the range whisker may collapse or be omitted

### Requirement: PassRateBarChart renders vertical range-whisker bar chart
The `PassRateBarChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = provider/base-model group, Y-axis = pass rate percentage). Each solid bar SHALL represent one selected provider/base-model group's median deduped effort pass rate from zero. A neutral range whisker SHALL visualize the range from the lowest effort pass rate to the highest effort pass rate in that group. The median deduped effort pass rate SHALL be the representative value used for sorting and bar prominence. The Y-axis domain SHALL start at 0 and SHALL use 100 as the pass-rate ceiling. Bars SHALL be color-coded by provider using the `getProviderColor()` palette. X-axis tick labels SHALL be rotated diagonally (`-40` degrees) with a custom tick renderer that displays a provider brand icon (via `ProviderIcon`) and the truncated base model name (max ~10 characters + ellipsis). The component SHALL accept optional `benchmarkName` and `selectedBenchmark` props. When `benchmarkName` is provided, pass rates SHALL be computed from `matrix[model][benchmarkName].pass_at_k` (per-benchmark), otherwise from `model_summaries[model].pass_at_k` (global). The tooltip footnote SHALL reflect the data source by showing the fixture count for the benchmark when filtered, or "204 fixtures" for global. Chart height SHALL be fixed at 350 pixels. A provider legend SHALL be rendered below the chart card showing colored dots for each unique provider present.

#### Scenario: Bars render for selected model groups
- **WHEN** `PassRateBarChart` receives selected groups `['anthropic/claude-opus-4.7', 'openai/gpt-oss-120b']`
- **THEN** two vertical grouped bars are displayed with range whiskers for the selected base models

#### Scenario: Effort range shown with whisker
- **WHEN** `openai/gpt-5` has effort pass rates 72%, 81%, and 85%
- **THEN** the `openai/gpt-5` solid bar extends from 0% to 81% and its range whisker spans 72%-85%

#### Scenario: Bars sorted by median score
- **WHEN** grouped models have median effort pass rates 90%, 75%, and 82%
- **THEN** bars appear ordered by 90%, 82%, then 75%

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** its bar is rendered in the Anthropic palette color (#D97757)

#### Scenario: Colors reflect provider for fallback providers
- **WHEN** a model group has provider `unknown-provider`
- **THEN** its bar is rendered in a deterministic `hsl(hue, 55%, 48%)` color

#### Scenario: Diagonal labels show provider icon and truncated base model
- **WHEN** a model group is `openai/gpt-oss-120b`
- **THEN** its X-axis tick shows the OpenAI icon and "gpt-oss-1..." (truncated), rotated `-40` degrees

#### Scenario: Long model names are truncated
- **WHEN** a base model name exceeds ~10 characters
- **THEN** the displayed label is truncated with an ellipsis

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are selected
- **THEN** the chart height is always 350 pixels

#### Scenario: Tick labels are offset below the axis line
- **WHEN** the chart renders with any model group count
- **THEN** the X-axis tick labels appear below the horizontal axis line, not centered on it

#### Scenario: Provider legend appears below the chart
- **WHEN** the chart shows model groups from multiple providers
- **THEN** a horizontal legend with colored dots and provider names appears below the chart card

#### Scenario: Per-benchmark pass rates used when benchmarkName provided
- **WHEN** `PassRateBarChart` receives `benchmarkName="blame_forensics"`
- **THEN** bars reflect pass rates from `matrix[model]["blame_forensics"].pass_at_k` with the tooltip footnote showing the number of fixtures in that benchmark

#### Scenario: Global pass rates used when benchmarkName absent
- **WHEN** `PassRateBarChart` renders without a `benchmarkName` prop
- **THEN** bars reflect pass rates from `model_summaries[model].pass_at_k` and the tooltip footnote reads "% of 204 fixtures passed"

### Requirement: RuntimeBarChart renders vertical range-whisker bar chart ranking models by speed
The `RuntimeBarChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = provider/base-model group, Y-axis = total API time in seconds). Each solid bar SHALL represent one selected provider/base-model group's median deduped effort API time from zero. A neutral range whisker SHALL visualize the range from the fastest effort API time to the slowest effort API time in that group. The median deduped effort API time SHALL be the representative value used for sorting and bar prominence. The Y-axis domain SHALL start at 0 and include the slowest displayed effort API time. Bars SHALL be color-coded by provider using the `getProviderColor()` palette. X-axis tick labels SHALL display the provider brand icon (via `ProviderIcon`) and the truncated base model name (max ~10 characters + ellipsis), rotated `-40` degrees. The component SHALL accept a `data` prop containing the full dataset and an optional selected group list for filtering. Chart height SHALL be fixed at 350 pixels. A provider legend SHALL be rendered below the chart card showing colored dots for each unique provider present. Model groups SHALL be sorted fastest-first by their median deduped effort API time.

#### Scenario: Bars render for selected model groups
- **WHEN** `RuntimeBarChart` receives selected groups `['anthropic/claude-opus-4.7', 'openai/gpt-oss-120b']`
- **THEN** two vertical grouped bars are displayed with API-time range whiskers for the selected base models

#### Scenario: Fastest median grouped model appears first
- **WHEN** model groups have median effort API times [5000, 12000, 3000, 8000]
- **THEN** bars appear from left to right in order: 3000, 5000, 8000, 12000

#### Scenario: Effort API-time range shown
- **WHEN** `openai/gpt-5` has effort API times 45s, 70s, and 110s
- **THEN** the `openai/gpt-5` solid bar extends from 0s to 70s and its range whisker spans 45s-110s

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** its bar is rendered in the Anthropic palette color (#D97757)

#### Scenario: Colors reflect provider for fallback providers
- **WHEN** a model group has provider `unknown-provider`
- **THEN** its bar is rendered in a deterministic `hsl(hue, 55%, 48%)` color

#### Scenario: Diagonal labels show provider icon and truncated base model
- **WHEN** a model group is `openai/gpt-oss-120b`
- **THEN** its X-axis tick shows the OpenAI icon and "gpt-oss-1..." (truncated), rotated `-40` degrees

#### Scenario: Long model names are truncated
- **WHEN** a base model name exceeds ~10 characters
- **THEN** the displayed label is truncated with an ellipsis

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are present
- **THEN** the chart height is always 350 pixels

#### Scenario: Provider legend appears below the chart
- **WHEN** the chart shows model groups from multiple providers
- **THEN** a horizontal legend with colored dots and provider names appears below the chart card

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
Overview grouped metric bar charts SHALL use a shared vertical chart language for pass rate, cost, API time, and token usage. Each chart SHALL place provider/base-model groups on the X-axis and the metric value on the Y-axis. For a single output-mode selection, each provider/base-model category SHALL render one provider-colored bar whose value is the median of the deduped effort values for that mode, with a neutral range whisker spanning that mode's minimum and maximum effort values. When `Both` is selected, each category SHALL render adjacent `Text` and `JSON` bars, and each bar SHALL use an independently computed median and range whisker from only that output mode's efforts. Text bars SHALL use the solid provider color. JSON bars SHALL use the same provider color with reduced fill opacity and a visible outline. Range whiskers SHALL NOT be described as error bars in user-facing copy or specs.

#### Scenario: Single mode shows one representative bar
- **WHEN** a grouped metric row in `Text` mode has deduped effort values `[72, 81, 85]`, `minValue=72`, and `maxValue=85`
- **THEN** one solid text bar extends from 0 to 81 and its range whisker spans 72 to 85

#### Scenario: Both mode shows independent sibling bars
- **WHEN** a model group has text effort values `[72, 81, 85]` and JSON effort values `[76, 88, 91]` while `Both` is selected
- **THEN** the category shows a text bar at 81 with a 72-85 whisker and an adjacent JSON bar at 88 with a 76-91 whisker

#### Scenario: Modes are not combined for the representative
- **WHEN** text effort values are `[10, 20]` and JSON effort values are `[80, 90]`
- **THEN** the text representative is 15 and the JSON representative is 85
- **AND** no displayed representative is calculated from the combined values `[10, 20, 80, 90]`

#### Scenario: Duplicate values do not overweight each mode median
- **WHEN** one output mode has effort values `[10, 10, 10, 20, 50]`
- **THEN** that mode's representative value is computed from deduped values `[10, 20, 50]`, so its bar extends from 0 to 20 and its whisker spans 10 to 50

#### Scenario: Numeric axis starts at zero
- **WHEN** any grouped metric chart renders
- **THEN** its numeric Y-axis lower bound is 0

#### Scenario: Diagonal group labels are reused for pairs
- **WHEN** a grouped metric chart renders paired text and JSON bars
- **THEN** both bars share one existing diagonal provider-icon label with `-40` degree rotation and a truncated base model name

#### Scenario: Single-effort mode remains visible
- **WHEN** one mode summary has equal minimum, maximum, and representative values
- **THEN** that mode's bar remains visible from 0 to the representative value and its range whisker may collapse or be omitted

#### Scenario: Missing sibling mode preserves the category
- **WHEN** `Both` is selected and a provider/base-model group has text data but no JSON data
- **THEN** the text bar renders in its normal sibling position, the JSON slot remains empty, and the model category remains on the chart

#### Scenario: Both mode includes a style legend
- **WHEN** a grouped metric chart renders with `Both` selected
- **THEN** a mode legend identifies the solid treatment as `Text` and the translucent outlined treatment as `JSON`

### Requirement: PassRateBarChart renders vertical range-whisker bar chart
The `PassRateBarChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = provider/base-model group, Y-axis = pass rate percentage). For a single output-mode selection, each category SHALL show that mode's median deduped effort pass rate from zero with a neutral range whisker from its lowest to highest effort pass rate. When `Both` is selected, each category SHALL show adjacent text and JSON bars with independently calculated medians and range whiskers. The Y-axis domain SHALL start at 0 and SHALL use 100 as the pass-rate ceiling. Bars SHALL be color-coded by provider using the `getProviderColor()` palette and SHALL use the shared output-mode visual treatments. X-axis tick labels SHALL be rotated diagonally (`-40` degrees) with a custom tick renderer that displays a provider brand icon (via `ProviderIcon`) and the truncated base model name (max ~10 characters + ellipsis). The component SHALL accept optional `benchmarkName` and `selectedBenchmark` props. When `benchmarkName` is provided, pass rates SHALL be computed from `matrix[model][benchmarkName].pass_at_k` (per-benchmark), otherwise from `model_summaries[model].pass_at_k` (global). The tooltip footnote SHALL reflect the data source by showing the fixture count for the benchmark when filtered, or "204 fixtures" for global. Chart height SHALL be fixed at 350 pixels. A provider legend SHALL be rendered below the chart card showing colored dots for each unique provider present.

#### Scenario: Both mode renders paired pass-rate bars
- **WHEN** `Both` is selected for model groups `['anthropic/claude-opus-4.7', 'openai/gpt-oss-120b']`
- **THEN** each model category displays adjacent text and JSON pass-rate bars where those modes are available

#### Scenario: Effort ranges are independent by mode
- **WHEN** `openai/gpt-5` has text pass rates 72%, 81%, and 85% and JSON pass rates 76%, 88%, and 91%
- **THEN** the text bar extends to 81% with a 72%-85% whisker and the JSON bar extends to 88% with a 76%-91% whisker

#### Scenario: Single-mode rendering remains one bar
- **WHEN** the output-mode selection is `JSON`
- **THEN** each displayed model category contains one JSON bar and no reserved text bar

#### Scenario: Bars sorted by visible representative score
- **WHEN** a single output mode is selected and grouped models have representative pass rates 90%, 75%, and 82%
- **THEN** categories appear ordered by 90%, 82%, then 75%

#### Scenario: Both mode sorts by mean representative score
- **WHEN** `Both` is selected and two groups have text/JSON representatives `[90%, 70%]` and `[78%, 76%]`
- **THEN** the first group sorts ahead of the second because their mean representative scores are 80% and 77%

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** both of its mode bars use the Anthropic palette color (#D97757) with their respective mode treatments

#### Scenario: Colors reflect provider for fallback providers
- **WHEN** a model group has provider `unknown-provider`
- **THEN** its mode bars use a deterministic `hsl(hue, 55%, 48%)` provider color

#### Scenario: Diagonal labels show provider icon and truncated base model
- **WHEN** a model group is `openai/gpt-oss-120b`
- **THEN** its shared X-axis tick shows the OpenAI icon and "gpt-oss-1..." (truncated), rotated `-40` degrees

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are selected in single or both mode
- **THEN** the chart height is always 350 pixels

#### Scenario: Provider and mode legends appear below the chart
- **WHEN** the chart shows multiple providers with `Both` selected
- **THEN** the provider legend identifies provider colors and the mode legend identifies text and JSON bar treatments

#### Scenario: Either sibling triggers one separated tooltip
- **WHEN** a user hovers or keyboard-focuses either bar in a paired pass-rate category
- **THEN** one tooltip appears for the provider/base-model group with separate `Text` and `JSON` effort lists and a representative median for each available mode

#### Scenario: Missing mode is explicit in tooltip
- **WHEN** `Both` is selected and a category has text pass-rate data but no JSON pass-rate data
- **THEN** the shared tooltip shows the text effort list and a JSON section labeled `No data`

#### Scenario: Per-benchmark pass rates used when benchmarkName provided
- **WHEN** `PassRateBarChart` receives `benchmarkName="blame_forensics"`
- **THEN** both mode summaries use pass rates from `matrix[model]["blame_forensics"].pass_at_k` and the tooltip footnote shows that benchmark's fixture count

#### Scenario: Global pass rates used when benchmarkName absent
- **WHEN** `PassRateBarChart` renders without a `benchmarkName` prop
- **THEN** mode summaries use `model_summaries[model].pass_at_k` and the tooltip footnote reads "% of 204 fixtures passed"

### Requirement: PassRateBarChart accepts optional initialData prop
The `PassRateBarChart` React component SHALL accept an optional `initialData` prop of type `GitBenchData | undefined`. When `initialData` is provided and no campaign override is active (no `?campaign=` query parameter), the component SHALL use `initialData` as its initial data state and SHALL NOT fetch from `/api/charts/pass-rate`. When `initialData` is absent or a campaign override is active, the component SHALL fetch from the report API client as before.

#### Scenario: Renders immediately from initialData
- **WHEN** `PassRateBarChart` receives `initialData` with model summaries and no campaign is selected
- **THEN** the chart renders from `initialData` on first hydration without showing "Loading..." and without making an API request

#### Scenario: Falls back to API when initialData absent
- **WHEN** `PassRateBarChart` receives no `initialData` prop
- **THEN** the component shows "Loading..." and fetches from `/api/charts/pass-rate` as before

#### Scenario: Falls back to API when campaign override active
- **WHEN** `PassRateBarChart` receives `initialData` but the URL contains `?campaign=<id>`
- **THEN** the component fetches from `/api/charts/pass-rate?campaign=<id>` to obtain campaign-specific data and metadata

#### Scenario: Benchmark detail page still fetches
- **WHEN** `PassRateBarChart` is rendered on a benchmark detail page with a `benchmarkName` prop and no `initialData`
- **THEN** the component fetches from `/api/charts/pass-rate?benchmark=<name>` as before

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

### Requirement: All output-mode-aware bar charts pair text and JSON results
Every web bar chart that can display text and JSON-schema results SHALL render those modes as a visually grouped sibling pair when `Both` is selected. The current covered bar-chart uses SHALL include the overview pass-rate chart, benchmark leaderboard pass-rate chart, cost chart, API-time chart, token-usage chart, Compare overall pass-rate chart, and Compare per-benchmark chart. Text and JSON bars SHALL preserve the chart's existing base color meaning while using the shared solid-text and translucent-outlined-JSON treatments. Hovering or keyboard-focusing either sibling SHALL open one tooltip scoped to the shared model or model-effort identity, with separate `Text` and `JSON` sections. A single-mode selection SHALL render only the selected mode without an empty sibling slot.

#### Scenario: Overview metric charts use paired modes
- **WHEN** `Both` is selected on the overview page
- **THEN** pass rate, cost, API time, and token usage render text and JSON as sibling bars for each model category

#### Scenario: Benchmark leaderboard uses paired modes
- **WHEN** `Both` is selected on a benchmark detail page
- **THEN** its pass-rate leaderboard renders text and JSON as sibling bars for each model category

#### Scenario: Compare overall uses paired modes
- **WHEN** `Both` is selected on the Compare page
- **THEN** the overall pass-rate chart renders one canonical model-effort category with sibling text and JSON bars instead of separate variant categories

#### Scenario: Compare by benchmark uses paired model series
- **WHEN** `Both` is selected on the Compare page
- **THEN** the per-benchmark chart renders each canonical model effort's text and JSON bars consecutively as one visual pair

#### Scenario: Siblings share one scoped tooltip
- **WHEN** a user hovers either bar in any text/JSON pair
- **THEN** the tooltip is scoped to that pair's model or model-effort identity and separates the two output modes into distinct sections

#### Scenario: Single mode does not reserve a pair
- **WHEN** `Text` or `JSON` is selected
- **THEN** every covered bar chart renders one bar per visible model identity without an empty sibling slot

### Requirement: Quadrant chart separates text and JSON points
The `QuadrantComparisonChart` SHALL render output modes as separate points when `Both` is selected. For each selected provider/base-model group, the chart SHALL choose the highest-composite effort independently in text mode and JSON-schema mode, producing up to two points that share the same normalized metric domains. Text points SHALL use a solid provider-colored circle. JSON points SHALL use a translucent provider-colored fill with a visible provider-colored outline. When both points are available, a subtle neutral connector SHALL join their exact coordinates behind the points. Hovering or keyboard-focusing either point SHALL open one tooltip for the provider/base-model pair with separate `Text` and `JSON` sections. The ranked list and "Best blend" result SHALL rank output-mode points independently and identify their mode.

#### Scenario: Both mode shows two independently selected points
- **WHEN** a base model's best text effort and best JSON effort both have the selected X and Y metrics
- **THEN** `Both` mode renders one text point and one JSON point at their respective metric coordinates

#### Scenario: Different reasoning efforts can represent the modes
- **WHEN** the best text composite belongs to `high` effort and the best JSON composite belongs to `medium` effort
- **THEN** the paired points use those different reasoning efforts
- **AND** the tooltip identifies the effort selected for each mode

#### Scenario: Pair shares normalized domains
- **WHEN** text and JSON points are visible together
- **THEN** both modes are normalized against the same visible candidate ranges and plotted on the same X and Y domains

#### Scenario: Connector shows mode movement
- **WHEN** both output-mode points exist for a base model at different coordinates
- **THEN** a subtle neutral line connects their exact coordinates behind the points

#### Scenario: Coincident points remain distinguishable
- **WHEN** a base model's text and JSON points have identical X and Y values
- **THEN** the text point remains a solid circle and the JSON point remains visible as a larger outlined ring around it
- **AND** neither point's plotted coordinates are offset

#### Scenario: Either point opens one paired tooltip
- **WHEN** a user hovers or keyboard-focuses either point in a text/JSON pair
- **THEN** one tooltip shows separate `Text` and `JSON` sections with each mode's reasoning effort and raw X and Y metric values

#### Scenario: Missing mode remains visible and explicit
- **WHEN** `Both` is selected and a base model has a valid text point but no valid JSON point
- **THEN** the text point remains visible without a connector
- **AND** the tooltip's JSON section reads `No data`

#### Scenario: Single mode retains one point per base model
- **WHEN** `Text` or `JSON` is selected
- **THEN** the quadrant chart renders at most one best point per selected base model for that mode

#### Scenario: Ranking distinguishes output modes
- **WHEN** text and JSON points from the same base model both rank in the top six
- **THEN** both entries may appear and each entry identifies whether it is `Text` or `JSON`

#### Scenario: Best blend identifies mode
- **WHEN** the highest-composite visible point is a JSON point
- **THEN** the "Best blend" label identifies the base model and JSON mode

#### Scenario: Quadrant tooltip keeps no footnote
- **WHEN** the paired quadrant tooltip renders
- **THEN** it contains no separator and explanatory footnote

### Requirement: Chart components accept campaign-aware aggregates

Benchmark heatmaps, pass-rate charts, scatter plots, time series, and output-mode comparison charts SHALL accept campaign identity, completeness, and explicit attempt numerators and denominators.

#### Scenario: Render incomplete aggregate data

- **WHEN** a chart receives an incomplete campaign aggregate
- **THEN** it SHALL visually and textually mark the data as incomplete
- **AND** it SHALL not present the value as part of a default complete-campaign ranking

### Requirement: Trial variability and reasoning-effort ranges use distinct encodings

Charts SHALL NOT reuse the same whisker or range encoding for variability across repeated trials and range across reasoning-effort configurations.

#### Scenario: Overview includes multiple efforts and trials

- **WHEN** an overview point summarizes both multiple reasoning efforts and repeated trials
- **THEN** the primary range SHALL retain its documented reasoning-effort meaning
- **AND** trial minimum, maximum, or standard deviation SHALL appear in a separately labeled tooltip or detail view

### Requirement: Chart tooltips expose denominators

Reliability chart tooltips SHALL include passing attempts, valid attempts, planned trials, completed trials, and campaign status.

#### Scenario: Inspect a success-rate bar

- **WHEN** a user focuses or hovers a model success-rate bar
- **THEN** the tooltip SHALL identify the campaign and show the attempt numerator and denominator

### Requirement: Reliability charts are not color-dependent

Charts SHALL expose equivalent reliability meaning through labels, patterns, symbols, or accessible descriptions in addition to color.

#### Scenario: Read a flaky fixture marker

- **WHEN** the marker is focused using a keyboard
- **THEN** its accessible name SHALL identify the fixture as flaky and state its pass ratio

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

## Purpose

Chart components render interactive Recharts-based visualizations of benchmark data as React islands within the Astro site.
## Requirements
### Requirement: ModelSelector provides independent multi-select for models and reasoning levels
The `ModelSelector` React component SHALL render a multi-select interface listing all model+level combinations from the dataset. Each entry SHALL be independently selectable — selecting `gpt-4o#high` SHALL NOT automatically select `gpt-4o#low`. The component SHALL expose selected models via an `onChange` callback and accept an `initialSelected` prop for pre-selection.

#### Scenario: All model+level combos are listed
- **WHEN** `ModelSelector` renders with a dataset containing `gpt-4o#high`, `gpt-4o#medium`, `claude-sonnet`
- **THEN** all three entries appear as individually selectable checkboxes

#### Scenario: Independent selection
- **WHEN** a user checks `gpt-4o#high`
- **THEN** only `gpt-4o#high` is selected; `gpt-4o#medium` remains unchecked

#### Scenario: onChange fires with selected list
- **WHEN** a user toggles selections
- **THEN** the `onChange` callback receives the complete array of currently selected model names

#### Scenario: Quick-select shortcuts are available
- **WHEN** `ModelSelector` renders
- **THEN** "Select all" and "Clear all" controls are available

### Requirement: PassRateBarChart renders horizontal bar chart
The `PassRateBarChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = model, Y-axis = pass rate percentage). Bars SHALL be color-coded by pass rate threshold (green ≥80%, yellow 50-79%, red <50%). X-axis tick labels SHALL be rotated diagonally (-40°) with a custom tick renderer that displays: a provider brand icon (via `ProviderIcon`), the truncated model name (max ~10 characters + ellipsis), and the reasoning level suffix. The component SHALL accept a `data` prop containing the full dataset and a `selectedModels` prop listing models to display. Chart height SHALL be computed dynamically as `max(300, modelCount * 80)` to accommodate rotated labels.

#### Scenario: Bars render for selected models
- **WHEN** `PassRateBarChart` receives `selectedModels=['anthropic/claude-opus-4.7:low', 'openai/gpt-oss-120b:high']`
- **THEN** two vertical bars are displayed with the corresponding pass rates

#### Scenario: Colors reflect pass rate
- **WHEN** a model has 87% pass rate
- **THEN** its bar is rendered in the green color

#### Scenario: Diagonal labels show provider icon and truncated name
- **WHEN** a model name is `openai/gpt-oss-120b:high`
- **THEN** its X-axis tick shows the OpenAI icon, "gpt-oss-1…" (truncated), and "high" on a separate line, rotated -40°

#### Scenario: Long model names are truncated
- **WHEN** a model name exceeds ~10 characters in the base model part
- **THEN** the displayed label is truncated with an ellipsis

#### Scenario: Chart height scales with model count
- **WHEN** 12 models are selected
- **THEN** the chart height is at least `max(300, 12 * 80) = 960` pixels

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


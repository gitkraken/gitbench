## ADDED Requirements

### Requirement: Report chart components default to both output modes
Report chart components with output-mode controls SHALL default to `both` output modes when both text and JSON-schema data exist and no valid output-mode URL state is present.

#### Scenario: Bare overview shows both modes
- **WHEN** the Overview page loads with no report URL state
- **AND** both text and JSON-schema output modes are available
- **THEN** grouped metric charts render both text and JSON-schema bars

#### Scenario: Text-only data falls back to text
- **WHEN** a report chart loads with no report URL state
- **AND** only text-mode data is available
- **THEN** the chart uses text mode

#### Scenario: URL mode overrides default
- **WHEN** report URL state encodes output mode `text`
- **THEN** report chart components render text-mode data only

## MODIFIED Requirements

### Requirement: Overview chart components share model selection
Overview chart components in the shared chart-components capability SHALL update their rendered data when any Overview `ModelSelector` changes the selected provider/base-model group set. The selected group set SHALL be the complete array from the latest model selection change, and each chart SHALL use that set for all model-dependent bars, columns, legends, and labels. Components that still render effort-level data SHALL expand selected groups to their child model+effort names internally. The shared selection SHALL initialize from report URL state when present, otherwise from the page default.

#### Scenario: Model Summary updates from another selector
- **WHEN** a user changes the selected model groups in the Benchmark Matrix selector
- **THEN** the Model Summary chart updates its bars to match the same selected group set

#### Scenario: Benchmark Matrix updates from another selector
- **WHEN** a user changes the selected model groups in the Model Summary selector
- **THEN** the Benchmark Matrix updates its rendered model columns from the same selected group set

#### Scenario: Provider legend follows shared selection
- **WHEN** a shared group selection change removes all model groups for a provider from the Model Summary chart
- **THEN** that provider is removed from the Model Summary provider legend

#### Scenario: URL model-level selection is migrated
- **WHEN** report URL state contains old model+effort names such as `openai/gpt-5:high`
- **THEN** Overview selection initializes with the corresponding `openai/gpt-5` group ID

#### Scenario: Unknown URL values are ignored
- **WHEN** report URL state contains values that are not known model names or group IDs
- **THEN** those values are ignored when initializing Overview selection

#### Scenario: Bare overview selects all groups
- **WHEN** the Overview page loads without report URL state
- **THEN** all current provider/base-model groups are selected

### Requirement: BenchmarkHeatmap renders interactive heatmap
The `BenchmarkHeatmap` React component SHALL render a matrix where rows are benchmarks and columns are selected models. Each cell SHALL display the pass rate percentage with a background color intensity proportional to the pass rate. Clicking a column header SHALL navigate to the corresponding Model Detail page. Clicking a row label SHALL navigate to the corresponding Benchmark Detail page. Clicking a cell SHALL navigate to the Benchmark Detail page. Benchmark drilldown links from the heatmap SHALL preserve current report view state when the destination can use the same model/output-mode comparison context.

#### Scenario: Heatmap has benchmarks as rows
- **WHEN** `BenchmarkHeatmap` renders with 17 benchmarks
- **THEN** 17 rows are displayed, each labeled with the benchmark name

#### Scenario: Cell color intensity reflects pass rate
- **WHEN** a benchmark x model cell has 92% pass rate
- **THEN** the cell background is more intensely colored than a cell with 45% pass rate

#### Scenario: Clicking a row label navigates
- **WHEN** a user clicks the "commit_messages" row label
- **THEN** the browser navigates to `/benchmarks/commit_messages`

#### Scenario: Heatmap benchmark drilldown preserves view state
- **WHEN** a user has selected `["openai/gpt-5"]` and output mode `json_schema`
- **AND** the user clicks a benchmark cell or row label
- **THEN** the destination Benchmark Detail URL includes report view state that resolves to that same selection and output mode

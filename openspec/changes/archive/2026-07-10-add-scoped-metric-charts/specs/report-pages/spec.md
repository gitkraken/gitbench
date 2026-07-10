## ADDED Requirements

### Requirement: Benchmark Detail page shows scoped metric charts
The Benchmark Detail page SHALL render benchmark-scoped quadrant, cost, API-time, and token usage charts in addition to the benchmark pass-rate leaderboard and per-fixture comparison table. Every metric chart on the page SHALL use only results from the benchmark named by the current route. The page SHALL preserve the existing URL-backed model selection, output-mode selection, text/JSON pairing, provider colors, and campaign-aware data resolution.

#### Scenario: Benchmark metric sections render
- **WHEN** a user opens `/benchmarks/commit_messages`
- **THEN** the page shows sections for quadrant comparison, benchmark cost, benchmark API time, and benchmark token usage
- **AND** those sections are scoped to `commit_messages`

#### Scenario: Benchmark metric charts do not use full-suite totals
- **WHEN** a model has 204 full-suite fixture results and 12 `commit_messages` fixture results
- **THEN** the cost, API-time, and token charts on `/benchmarks/commit_messages` use only the 12 `commit_messages` results

#### Scenario: Benchmark page selection controls remain synced
- **WHEN** a user changes the selected model groups or output mode in one benchmark chart
- **THEN** the benchmark pass-rate, quadrant, cost, API-time, token, and per-fixture comparison views all resolve to the same selected model groups and output mode

#### Scenario: Benchmark quadrant uses benchmark pass rate
- **WHEN** a quadrant chart renders on `/benchmarks/blame_forensics`
- **THEN** its quality metric is derived from each model's pass rate on `blame_forensics`
- **AND** it does not use full-suite pass rate for the quality axis

### Requirement: Fixture Detail page shows compact scoped metric visualization
The Fixture Detail page SHALL render a compact metric visualization for the current fixture, covering quadrant comparison, cost, API time, and token usage without stacking four full-size chart sections. The visualization SHALL use only model outputs or campaign attempts for the current benchmark and fixture. It SHALL preserve raw attempt evidence, prompt, expected output, and model output cards.

#### Scenario: Fixture metric visualization renders
- **WHEN** a user opens `/fixtures/commit_messages/f001`
- **THEN** the page shows a metric visualization for `commit_messages/f001`
- **AND** the visualization can display quadrant, cost, API-time, and token views for that fixture

#### Scenario: Fixture metrics use only the current fixture
- **WHEN** a model has results for many fixtures in `commit_messages`
- **THEN** the fixture metric visualization on `/fixtures/commit_messages/f001` uses only that model's `f001` result or attempts

#### Scenario: Fixture page evidence remains available
- **WHEN** fixture metric charts are rendered
- **THEN** the raw attempt evidence section and model output cards remain available on the fixture page

#### Scenario: Fixture visualization preserves report view state
- **WHEN** a fixture page URL contains report view state for selected model groups and output mode
- **THEN** the fixture metric visualization initializes from that state
- **AND** changes to its controls update the same page-level view state used by other comparative report controls

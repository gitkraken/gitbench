## ADDED Requirements

### Requirement: Metric chart components support report scopes
Quadrant, cost, API-time, and token chart components SHALL support global, benchmark, and fixture scopes. Global scope SHALL preserve existing overview behavior. Benchmark scope SHALL load and render only data for the selected benchmark. Fixture scope SHALL load and render only data for the selected benchmark fixture. Scoped charts SHALL retain existing model selection, output-mode selection, provider coloring, text/JSON pairing, tooltips, empty states, and campaign-aware reload behavior.

#### Scenario: Global metric charts preserve overview behavior
- **WHEN** a metric chart renders without a benchmark or fixture scope
- **THEN** it uses the same global data and interaction behavior as the overview page

#### Scenario: Benchmark scoped metric chart fetches benchmark payload
- **WHEN** `TokenUsageChart` renders with benchmark scope `commit_messages`
- **THEN** it requests token chart data scoped to `commit_messages`
- **AND** its bars are computed from benchmark-scoped token totals

#### Scenario: Fixture scoped metric chart fetches fixture payload
- **WHEN** `RuntimeBarChart` renders with fixture scope `commit_messages/f001`
- **THEN** it requests runtime chart data scoped to `commit_messages/f001`
- **AND** its bars are computed from fixture-scoped API-time values

#### Scenario: Scoped empty states remain specific
- **WHEN** a scoped cost chart has no cost data for the selected benchmark or fixture
- **THEN** it displays the existing pricing-data empty state without falling back to global cost data

### Requirement: Scoped metric bar charts use scoped totals
Cost, API-time, and token usage bar charts SHALL compute representative effort values, mode ranges, sort values, and tooltip effort lists from the currently loaded scope only. They SHALL NOT combine scoped pass rates with global cost, runtime, or token aggregates.

#### Scenario: Benchmark cost tooltip uses benchmark cost
- **WHEN** a cost chart renders for benchmark `branch_cleanup`
- **THEN** each tooltip effort cost is the sum of `branch_cleanup` costs for that effort and output mode
- **AND** the tooltip does not show the full evaluation run cost

#### Scenario: Fixture token chart uses one fixture result
- **WHEN** a token chart renders for fixture `git_grep/f003`
- **THEN** each displayed effort's token value comes from that effort's `git_grep/f003` result or attempts

#### Scenario: Scoped ranges stay mode-specific
- **WHEN** `Both` output mode is selected for a benchmark-scoped API-time chart
- **THEN** text and JSON representative values and range whiskers are calculated independently from benchmark-scoped text and JSON effort values

### Requirement: Fixture quadrant uses adaptive quality metric
The fixture-scoped quadrant chart SHALL choose the fixture quality metric from available data. It SHALL use repeated-attempt success rate when valid campaign attempts are available. Otherwise it SHALL use similarity percentage when the fixture has meaningful intermediate similarity values. Otherwise it SHALL use binary success percentage, with passed results at 100% and failed valid results at 0%. The visible axis label and tooltip labels SHALL identify the selected quality metric.

#### Scenario: Repeated attempts use success rate
- **WHEN** a fixture has campaign attempts with valid pass and fail outcomes
- **THEN** the fixture quadrant quality axis is labeled `Success (%)`
- **AND** each point's quality value is calculated from passing valid attempts divided by valid attempts

#### Scenario: Graded fixture uses similarity
- **WHEN** a fixture has valid one-shot results with intermediate similarity values such as 63.5% and 88.0%
- **THEN** the fixture quadrant quality axis is labeled `Similarity (%)`
- **AND** point quality values use those similarity percentages

#### Scenario: Binary fixture uses pass/fail success
- **WHEN** a fixture has only binary pass/fail quality values
- **THEN** the fixture quadrant quality axis is labeled `Success (%)`
- **AND** passed results plot at 100% while failed valid results plot at 0%

#### Scenario: Benchmark quadrant keeps pass-rate quality
- **WHEN** the quadrant chart renders in benchmark scope
- **THEN** its quality metric is benchmark pass rate rather than fixture similarity

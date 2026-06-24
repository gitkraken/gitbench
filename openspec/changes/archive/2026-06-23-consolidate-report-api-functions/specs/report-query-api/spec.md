## ADDED Requirements

### Requirement: Report API stays within Vercel function budget
The web project SHALL expose the report API with no more than 11 Vercel serverless function route files under `gitbench/web/api`.

#### Scenario: Consolidated API file count
- **WHEN** the report API route files are enumerated under `gitbench/web/api`
- **THEN** there are no more than 11 TypeScript API route files

#### Scenario: Chart endpoints share one dynamic function
- **WHEN** the chart API routes are enumerated
- **THEN** the six chart names `cost`, `heatmap`, `pass-rate`, `quadrant`, `runtime`, and `tokens` are served by one dynamic chart function
- **AND** there are not separate serverless function files for each chart name

### Requirement: Dynamic chart API preserves chart behavior
The chart API SHALL serve supported chart names through a single dynamic route while preserving the existing `/api/charts/{chart}` URL shape, supported query parameters, and compact response payloads.

#### Scenario: Supported chart returns compact payload
- **WHEN** a client requests `/api/charts/pass-rate`
- **THEN** the response contains the same compact pass-rate chart data that the previous static pass-rate chart endpoint returned
- **AND** the response does not include full model output text

#### Scenario: Benchmark filter is preserved
- **WHEN** a client requests `/api/charts/pass-rate?benchmark=blame_forensics`
- **THEN** the response is scoped to the requested benchmark as before

#### Scenario: Unsupported chart is rejected
- **WHEN** a client requests `/api/charts/not-a-chart`
- **THEN** the API returns a clear client error response
- **AND** it does not execute a report query for an unknown chart type

### Requirement: Model results are served by the catch-all route
The model-results API SHALL use one catch-all route to serve model result requests, including two-segment provider/model URLs and model names containing encoded slashes or levels.

#### Scenario: Two-segment model URL resolves
- **WHEN** a client requests `/api/models/anthropic/claude-opus-4.7%3Ahigh/results`
- **THEN** the catch-all model-results handler resolves the model name as `anthropic/claude-opus-4.7:high`
- **AND** it returns the same response shape as the previous two-segment model-results route

#### Scenario: Model result filters still work
- **WHEN** a client requests model results with `benchmark`, `difficulty`, `tag`, `output_mode`, or `campaign` query parameters
- **THEN** the catch-all model-results handler applies the same validation and filtering behavior as before

### Requirement: Summary is the supported history source
The summary API SHALL remain the supported source for run history data by returning `runs_meta`. The web UI SHALL NOT require a standalone `/api/history` serverless function to render history views.

#### Scenario: Summary includes run history
- **WHEN** a client requests `/api/summary`
- **THEN** the response includes `runs_meta` with the run history needed by the history chart

#### Scenario: History UI uses summary data
- **WHEN** the History page renders the pass-rate-over-time chart
- **THEN** it loads run history from summary data rather than a standalone history endpoint

## MODIFIED Requirements

### Requirement: Vercel API routes expose query-shaped report data
The web project SHALL expose Vercel API routes that return report data for summary, models, model results, benchmark details, fixture details, chart data, campaign data, and raw campaign attempt inspection. Run history data SHALL be exposed through the summary response's `runs_meta` field instead of requiring a standalone history API function.

#### Scenario: Summary endpoint returns compact data
- **WHEN** a client requests the summary API endpoint
- **THEN** the response includes the data needed for overview charts, selectors, benchmark matrix, runtime summaries, run metadata, and base-model groups
- **AND** the response does not include full model output text

#### Scenario: Benchmark endpoint returns benchmark-scoped data
- **WHEN** a client requests the benchmark API endpoint for a benchmark
- **THEN** the response includes benchmark metadata, tag counts, model leaderboard data, and per-fixture comparison rows for that benchmark

#### Scenario: Model results endpoint supports filters
- **WHEN** a client requests model results with benchmark, difficulty, or tag filters
- **THEN** the response includes only matching fixture result rows for that model

#### Scenario: Fixture endpoint returns full outputs
- **WHEN** a client requests the fixture detail API endpoint for a benchmark and fixture id
- **THEN** the response includes fixture metadata, prompt, expected output, setup commands, and all model outputs for that fixture

#### Scenario: Chart endpoints return chart-specific data
- **WHEN** a client requests a supported chart API endpoint
- **THEN** the response includes only the data needed to render that chart

#### Scenario: History data is available from summary
- **WHEN** a client needs run history data
- **THEN** the client can read `runs_meta` from the summary API response

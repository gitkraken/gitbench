# report-query-api Specification

## Purpose
TBD - created by archiving change add-sqlite-report-api. Update Purpose after archive.
## Requirements
### Requirement: Report generation writes SQLite database
`gitbench report` SHALL write a read-only SQLite report database at a stable path under the web project, using the latest repository schema as the source of truth.

#### Scenario: Report writes database artifact
- **WHEN** `gitbench report` completes successfully
- **THEN** the web project contains a generated SQLite database for report API queries

#### Scenario: Existing database is rebuilt
- **WHEN** `gitbench report` runs and a previous generated report database exists
- **THEN** the previous report data is replaced with data generated from the current benchmark results and latest schema

### Requirement: Report database schema supports queryable report data
The report database SHALL normalize models, runs, benchmarks, fixtures, fixture results, tags, model summaries, benchmark summaries, runtime summaries, and base-model group data enough to serve report views without parsing `results.json`.

#### Scenario: Summary data is queryable
- **WHEN** the report database is generated
- **THEN** model summaries, benchmark matrix values, runtime summaries, run metadata, and base-model group data can be read from database tables

#### Scenario: Fixture output data is queryable
- **WHEN** the report database is generated
- **THEN** prompts, expected outputs, setup commands, and model outputs can be queried for an individual fixture

### Requirement: Report database includes indexes for common access paths
The report database SHALL include indexes for common report access patterns, including fixture results by model and benchmark, fixture results by benchmark and fixture, fixtures by benchmark, fixture tags by tag and fixture, runs by model and timestamp, models by provider/base model/reasoning level, and benchmark summaries by model and benchmark.

#### Scenario: Indexes are present
- **WHEN** the generated database schema is inspected
- **THEN** indexes exist for model result, benchmark result, fixture detail, tag filter, run history, and model grouping queries

### Requirement: Vercel API routes expose query-shaped report data
The web project SHALL expose Vercel API routes that return report data for summary, models, model results, benchmark details, fixture details, and history.

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

### Requirement: API uses report-store abstraction
API route handlers SHALL access report data through a report-store abstraction rather than embedding storage-specific database logic directly in UI components or route handlers.

#### Scenario: Node SQLite store serves Vercel routes
- **WHEN** Vercel API routes run locally or in production
- **THEN** they read the generated SQLite database through a Node SQLite report-store implementation

#### Scenario: Store contract allows D1 adapter
- **WHEN** a future Cloudflare D1 store is implemented
- **THEN** it can satisfy the same report-store contract used by the Vercel API routes

### Requirement: Local API-backed development uses Vercel dev
The supported local development path for API-backed report views SHALL use `vercel dev` so the static Astro app and Vercel API routes run together.

#### Scenario: Local API routes are available
- **WHEN** a developer starts the web project with the API-backed local development command
- **THEN** Astro pages and `/api/*` report routes are available from the local development server

### Requirement: API validates report query parameters
Report API routes SHALL validate route parameters and query parameters before executing database queries.

#### Scenario: Unknown fixture returns not found
- **WHEN** a client requests a fixture detail that does not exist
- **THEN** the API returns a 404 response

#### Scenario: Invalid filter is rejected
- **WHEN** a client passes an unsupported filter parameter to a report API endpoint
- **THEN** the API returns a clear 400 response

### Requirement: Report database stores fixture API duration
The report database SHALL store fixture-level `api_duration_ms` values in fixture result rows. The existing `model_runtimes` table SHALL store API-time aggregate values produced by aggregation, not wall-clock fixture durations.

#### Scenario: Fixture API duration is stored
- **WHEN** the report database is generated from aggregate data containing a fixture result with `api_duration_ms=350.2`
- **THEN** the corresponding `fixture_results` row stores `api_duration_ms=350.2`

#### Scenario: Missing API duration remains null
- **WHEN** the report database is generated from aggregate data containing no `api_duration_ms` for a fixture result
- **THEN** the corresponding `fixture_results.api_duration_ms` value is null
- **AND** `duration_ms` is not copied into `api_duration_ms`

#### Scenario: Runtime summary table stores API-time totals
- **WHEN** aggregate data contains `model_runtimes[model].total_ms=1200.0`
- **THEN** the generated `model_runtimes` row stores `total_ms=1200.0` as API-time data

### Requirement: Report APIs expose API-time runtime data
Report APIs SHALL expose fixture-level `api_duration_ms` on fixture result payloads where fixture result rows are returned. Summary and chart APIs SHALL continue returning `model_runtimes`, with values representing API-time aggregates.

#### Scenario: Summary endpoint returns API-time runtime summaries
- **WHEN** a client requests the summary API endpoint
- **THEN** the response includes `model_runtimes` values representing API call latency aggregates

#### Scenario: Model results endpoint returns fixture API duration
- **WHEN** a client requests model results for a model with fixture API timing data
- **THEN** each matching fixture result includes `api_duration_ms`

#### Scenario: Fixture endpoint returns fixture API duration
- **WHEN** a client requests fixture detail for a fixture with model outputs
- **THEN** each output with API timing data includes `api_duration_ms`

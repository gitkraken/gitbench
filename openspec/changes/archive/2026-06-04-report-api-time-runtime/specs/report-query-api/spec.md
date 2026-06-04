## ADDED Requirements

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

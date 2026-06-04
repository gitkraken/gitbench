## ADDED Requirements

### Requirement: JSON output includes fixture API duration
The JSON output SHALL include fixture-level `api_duration_ms` in each aggregated fixture result when the source score contains API timing data. The field SHALL represent successful API call latency in milliseconds and SHALL remain distinct from wall-clock `duration_ms`.

#### Scenario: Fixture API duration is in JSON
- **WHEN** `results.json` is generated from a score with `api_duration_ms=350.2`
- **THEN** the fixture result entry includes `"api_duration_ms": 350.2`

#### Scenario: Missing fixture API duration remains null-compatible
- **WHEN** `results.json` is generated from a score without `api_duration_ms`
- **THEN** the fixture result entry does not substitute `duration_ms` for API time

### Requirement: JSON runtime summaries represent API time
The `"model_runtimes"` object in JSON output SHALL represent API-time aggregates computed from `api_duration_ms`, while keeping the existing summary shape of `total_ms`, `avg_ms`, `min_ms`, `max_ms`, and `fixture_count`.

#### Scenario: model_runtimes uses API duration
- **WHEN** a model has fixture scores with `api_duration_ms` values [20.0, 30.0] and `duration_ms` values [100.0, 100.0]
- **THEN** `model_runtimes[model].total_ms` is `50.0`
- **AND** it is not `200.0`

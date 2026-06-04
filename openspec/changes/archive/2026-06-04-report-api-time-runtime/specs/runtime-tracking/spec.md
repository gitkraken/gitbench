## MODIFIED Requirements

### Requirement: Aggregation computes per-model runtime summaries
The `aggregate_runs()` function in `render.py` SHALL compute report runtime aggregates for each model from per-fixture `api_duration_ms` values. It SHALL output a `model_runtimes` dict in the aggregated data, keyed by model name, with fields `total_ms` (sum of all non-null fixture API durations), `avg_ms` (mean non-null fixture API duration), `min_ms`, `max_ms`, and `fixture_count` (number of fixtures with API timing data). Aggregation SHALL NOT fall back to wall-clock `duration_ms` when `api_duration_ms` is missing.

#### Scenario: Runtime aggregated across API durations
- **WHEN** a model has 3 fixtures with `api_duration_ms` = [100.0, 200.0, 300.0]
- **THEN** `model_runtimes[model]` has `total_ms=600.0`, `avg_ms=200.0`, `min_ms=100.0`, `max_ms=300.0`, `fixture_count=3`

#### Scenario: Null API durations excluded from aggregation
- **WHEN** a model has 4 fixtures with `api_duration_ms` = [100.0, null, null, 500.0]
- **THEN** `model_runtimes[model]` has `total_ms=600.0`, `avg_ms=300.0`, `fixture_count=2`

#### Scenario: Wall-clock durations are not used as fallback
- **WHEN** a model's fixtures have `duration_ms` values but all `api_duration_ms` values are missing or null
- **THEN** that model does NOT appear as a key in `model_runtimes`

#### Scenario: Model with no API timing data excluded from model_runtimes
- **WHEN** a model's fixtures all have `api_duration_ms=None`
- **THEN** that model does NOT appear as a key in `model_runtimes`

#### Scenario: model_runtimes included in render_json output
- **WHEN** `render_json()` writes the aggregated data
- **THEN** the JSON file contains a `"model_runtimes"` key at the top level
- **AND** the values in `"model_runtimes"` represent API call latency aggregates

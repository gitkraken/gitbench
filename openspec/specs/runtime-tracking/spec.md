## Purpose

Runtime tracking instruments the benchmark runner to capture per-fixture wall-clock duration and API call latency, then exposes API timing through the data pipeline for aggregation and visualization.
## Requirements
### Requirement: Runner captures per-fixture wall-clock duration
The `BenchmarkRunner` SHALL measure wall-clock duration for each fixture execution using `time.perf_counter()`. The measurement SHALL span from immediately before `_run_fixture` begins until immediately after it returns (including setup, model call, scoring, and cleanup). The elapsed time SHALL be stored as milliseconds in a `duration_ms` field on the `Score` dataclass.

#### Scenario: Duration captured for successful fixture
- **WHEN** a fixture executes successfully and returns a `Score` result
- **THEN** `score.duration_ms` is a positive float representing the elapsed wall-clock time in milliseconds

#### Scenario: Duration captured for failed fixture
- **WHEN** a fixture raises an exception and the runner catches it in the finally block
- **THEN** `score.duration_ms` is a positive float representing the elapsed time up to the failure point

#### Scenario: Duration measurement uses high-resolution clock
- **WHEN** the runner measures fixture execution time
- **THEN** the measurement uses `time.perf_counter()` (monotonic, high-resolution, wall-clock)

#### Scenario: Duration stored in serialized result
- **WHEN** a `Score` with `duration_ms=1542.3` is serialized via `to_dict()`
- **THEN** the resulting dict contains `"duration_ms": 1542.3`

### Requirement: Score supports optional duration_ms field
The `Score` dataclass SHALL have an optional `duration_ms: float | None` field with a default of `None`. The `to_dict()` method SHALL omit the field when it is `None` for backward compatibility with old result files. The `from_dict()` method SHALL accept `duration_ms` when present and default to `None` when absent.

#### Scenario: duration_ms defaults to None
- **WHEN** a `Score` is created without specifying `duration_ms`
- **THEN** `score.duration_ms` is `None`

#### Scenario: to_dict omits None duration_ms
- **WHEN** `score.to_dict()` is called on a `Score` with `duration_ms=None`
- **THEN** the resulting dict does NOT contain a `duration_ms` key

#### Scenario: from_dict handles missing duration_ms
- **WHEN** `Score.from_dict()` is called with a dict that has no `duration_ms` key
- **THEN** the returned `Score` has `duration_ms=None`

#### Scenario: from_dict handles present duration_ms
- **WHEN** `Score.from_dict()` is called with a dict containing `"duration_ms": 1234.5`
- **THEN** the returned `Score` has `duration_ms=1234.5`

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

### Requirement: BenchmarkResult to_dict includes per-benchmark timing total
The `BenchmarkResult.to_dict()` method SHALL compute and include a `total_duration_ms` field representing the sum of all non-null `duration_ms` values across the benchmark's scores.

#### Scenario: total_duration_ms computed from scores
- **WHEN** a `BenchmarkResult` has 3 scores with `duration_ms` = [100, 200, 300]
- **THEN** `result.to_dict()` contains `"total_duration_ms": 600`

### Requirement: Score supports optional api_duration_ms field alongside duration_ms

The `Score` dataclass SHALL have an optional `api_duration_ms: float | None` field with a default of `None`, representing the API call latency in milliseconds. This SHALL be measured separately from `duration_ms` (wall-clock time) and stored on the same `Score` object. The `to_dict()` method SHALL omit the field when it is `None`. The `from_dict()` method SHALL accept `api_duration_ms` when present and default to `None` when absent.

#### Scenario: api_duration_ms and duration_ms coexist on Score
- **WHEN** a fixture run takes 2000ms wall-clock and the API call takes 350ms
- **THEN** `score.duration_ms` is 2000.0 and `score.api_duration_ms` is 350.0

#### Scenario: api_duration_ms defaults to None
- **WHEN** a `Score` is created without specifying `api_duration_ms`
- **THEN** `score.api_duration_ms` is `None`

#### Scenario: to_dict omits None api_duration_ms
- **WHEN** `score.to_dict()` is called on a `Score` with `api_duration_ms=None`
- **THEN** the resulting dict does NOT contain an `api_duration_ms` key

#### Scenario: to_dict includes non-None api_duration_ms
- **WHEN** `score.to_dict()` is called on a `Score` with `api_duration_ms=350.2`
- **THEN** the resulting dict contains `"api_duration_ms": 350.2`

#### Scenario: from_dict handles missing api_duration_ms
- **WHEN** `Score.from_dict()` is called with a dict that has no `api_duration_ms` key
- **THEN** the returned `Score` has `api_duration_ms=None`

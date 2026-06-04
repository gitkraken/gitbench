## Why

GitBench now records `api_duration_ms` for every rerun benchmark result, but the web report still aggregates and displays wall-clock `duration_ms` as runtime. API call latency is the timing signal that matters for comparing models; wall-clock fixture time includes setup, scoring, cleanup, and scheduling noise that should not drive the report.

## What Changes

- Aggregate report runtime summaries from fixture-level `api_duration_ms` instead of wall-clock `duration_ms`.
- Preserve `duration_ms` in raw run files as diagnostic/backward-compatible data, but stop using it for web report runtime summaries.
- Copy fixture-level `api_duration_ms` into aggregated `results.json` fixture rows.
- Persist `api_duration_ms` into the generated SQLite report database and return it through report APIs/types.
- Update report UI copy so runtime sections describe API time rather than wall-clock time.
- **BREAKING**: `model_runtimes` in aggregated report data and SQLite remains the compatibility key/table, but its semantic meaning changes from wall-clock fixture runtime to API call latency.
- Do not fall back from missing `api_duration_ms` to `duration_ms`; fixtures without API time are excluded from runtime aggregation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-tracking`: Report runtime aggregation changes from wall-clock `duration_ms` to API `api_duration_ms`.
- `json-export`: Aggregated fixture rows include `api_duration_ms`, and `model_runtimes` is API-time based.
- `report-query-api`: SQLite report data persists fixture API time and exposes API-time runtime summaries through existing report APIs.
- `runtime-chart`: Runtime chart labels, help text, and tooltips describe API time instead of wall-clock runtime.
- `chart-components`: Any shared or legacy chart requirements that describe runtime as wall-clock are updated to API-time semantics.
- `conversational-prose-voice`: Runtime explanatory prose preserves non-obvious context without the obsolete wall-clock caveat.

## Impact

- Python aggregation and database writer: `gitbench/render.py`.
- Web database schema and JSON-to-SQLite loader: `gitbench/web/data/schema.sql`, `gitbench/web/scripts/build-db.mjs`.
- Web report store and TypeScript data contracts: `gitbench/web/src/lib/types.ts`, `gitbench/web/src/lib/node-sqlite-report-store.ts`, chart data helpers.
- Overview runtime and quadrant UI copy/components: `gitbench/web/src/pages/index.astro`, `RuntimeBarChart`, `QuadrantComparisonChart`, and related chart metric helpers.
- Tests for aggregation, SQLite build, report store responses, and runtime chart semantics.

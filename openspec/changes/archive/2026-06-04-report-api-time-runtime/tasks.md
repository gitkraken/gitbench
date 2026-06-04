## 1. Aggregation

- [x] 1.1 Update `aggregate_runs()` to copy `scores[].api_duration_ms` into aggregated fixture rows.
- [x] 1.2 Change `model_runtimes` aggregation to use non-null `api_duration_ms` values only.
- [x] 1.3 Ensure aggregation never falls back to `duration_ms` when `api_duration_ms` is missing.
- [x] 1.4 Add or update Python render tests for API-time runtime totals, null exclusion, no wall-time fallback, and fixture-level JSON output.

## 2. SQLite Report Data

- [x] 2.1 Add `api_duration_ms` to the generated SQLite `fixture_results` schema.
- [x] 2.2 Update the Python SQLite writer in `gitbench/render.py` to insert fixture API duration.
- [x] 2.3 Update `gitbench/web/scripts/build-db.mjs` to load fixture API duration from `results.json`.
- [x] 2.4 Add or update SQLite writer and `pnpm` build-db tests to verify `api_duration_ms` persistence and null behavior.

## 3. Report API and Types

- [x] 3.1 Add `api_duration_ms` to the web `FixtureResult` TypeScript type.
- [x] 3.2 Update the Node SQLite report store to map `fixture_results.api_duration_ms` into fixture result payloads.
- [x] 3.3 Add or update report store tests for summary API-time runtime data and fixture-level `api_duration_ms`.

## 4. UI Semantics

- [x] 4.1 Rename Overview runtime section copy from wall-clock runtime to API time.
- [x] 4.2 Update `RuntimeBarChart` labels, empty state, and tooltip text to describe API call latency.
- [x] 4.3 Update quadrant/runtime metric labels where user-facing copy still implies wall-clock runtime.
- [x] 4.4 Remove obsolete wall-clock caveats from conversational prose and chart footnotes.

## 5. Verification and Artifacts

- [x] 5.1 Regenerate `web/public/results.json` from current raw results and confirm fixture rows include `api_duration_ms`.
- [x] 5.2 Regenerate `web/data/gitbench.db` and confirm `fixture_results.api_duration_ms` is populated.
- [x] 5.3 Run the relevant Python tests for render/database behavior.
- [x] 5.4 Run the relevant web tests with `pnpm` from `gitbench/web`.
- [x] 5.5 Run OpenSpec validation for `report-api-time-runtime`.

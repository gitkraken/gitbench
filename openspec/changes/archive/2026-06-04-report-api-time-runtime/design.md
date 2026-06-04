## Context

Recent benchmark reruns already include `scores[].api_duration_ms` in raw result files. The current report pipeline still treats `scores[].duration_ms` as the source for `model_runtimes`, stores only `duration_ms` in SQLite fixture rows, and labels the Overview chart as wall-clock runtime.

The report data path is:

```text
raw result JSON -> aggregate_runs() -> public/results.json -> SQLite -> report APIs -> React charts/pages
```

The runner/raw result layer is out of scope for this change. This change starts at aggregation and ends at the web UI.

## Goals / Non-Goals

**Goals:**

- Make API call latency the only report-facing runtime metric.
- Preserve the existing `model_runtimes` aggregate shape so chart/API consumers do not need a broad rename.
- Preserve raw `duration_ms` data without using it for report runtime rankings.
- Persist fixture-level `api_duration_ms` through JSON, SQLite, report APIs, and TypeScript types.
- Update user-facing copy so speed comparisons are described as API time.

**Non-Goals:**

- Changing how adapters measure `api_duration_ms`.
- Rerunning benchmarks or doctoring raw result files.
- Removing `duration_ms` from raw run JSON.
- Introducing a second timing chart for wall time.
- Renaming `model_runtimes` or the `model_runtimes` SQLite table in this change.

## Decisions

### 1. Keep `model_runtimes`, change its source to `api_duration_ms`

`aggregate_runs()` will continue returning `model_runtimes[model]` with `{total_ms, avg_ms, min_ms, max_ms, fixture_count}`, but those values will be calculated from non-null `api_duration_ms` values.

Alternative considered: add `model_api_runtimes` beside the existing wall-clock `model_runtimes`. Rejected because the product no longer cares about wall-clock runtime, and a second metric would keep obsolete semantics alive in the report.

Alternative considered: rename the aggregate to `model_api_runtimes`. Rejected for this change because it would force a wider API/UI rename. The semantic change is intentionally called out as breaking in the proposal.

### 2. Never fall back to wall-clock duration

If a fixture lacks `api_duration_ms`, it will not contribute to `model_runtimes`. Aggregation will not substitute `duration_ms`.

Rationale: mixing wall-clock and API time would make rankings silently wrong. Missing API time should surface as missing runtime data.

### 3. Preserve fixture-level `api_duration_ms`

Aggregated fixture rows will include `api_duration_ms`, and SQLite `fixture_results` will gain an `api_duration_ms` column. The report store will map it into `FixtureResult`.

Rationale: summary charts need the rollup, but fixture/model detail views and future debugging need the underlying per-fixture latency.

### 4. Keep wall-clock fields diagnostic

Raw result files may still contain `duration_ms` and `total_duration_ms`. Existing code paths that serialize or doctor raw benchmark results can keep those fields. The web report pipeline will not use them for runtime summaries.

Rationale: wall-clock timing still has diagnostic value for harness behavior, but it is not a model comparison metric.

### 5. UI copy says API time

The Overview section label should change from "Runtime (Wall Clock)" to an API-time label. Runtime chart tooltips and explanatory prose should describe successful API call latency and remove references to setup, scoring, rate limiting, or wall-clock caveats.

The Quadrant metric can continue using the runtime metric internally, but user-facing labels should prefer "API Time" where practical.

## Risks / Trade-offs

- [Risk] Existing report consumers may assume `model_runtimes` is wall-clock time. → Mitigation: mark the semantic change as breaking in the proposal and update specs/docs/UI copy.
- [Risk] A stale result set without `api_duration_ms` would show no runtime data. → Mitigation: do not fall back to `duration_ms`; empty runtime data is safer than mixed metrics.
- [Risk] Keeping the `model_runtimes` name while changing semantics can be confusing for developers. → Mitigation: add focused tests and comments/docs around aggregation source, and make UI copy explicit.
- [Risk] Two database builders exist, Python and web script. → Mitigation: update and test both writers so generated SQLite data is consistent regardless of build path.

## Migration Plan

1. Update aggregation to copy fixture `api_duration_ms` and compute `model_runtimes` from it.
2. Update both SQLite build paths and schema to store `fixture_results.api_duration_ms`.
3. Update report store/types/API mapping to return `api_duration_ms`.
4. Update Overview runtime and quadrant labels/copy to API-time wording.
5. Regenerate `public/results.json` and `data/gitbench.db` from the current rerun raw results.

Rollback: restore `model_runtimes` aggregation to `duration_ms`, leave the extra SQLite column harmless, and regenerate report artifacts.

## Open Questions

None. Current raw results are assumed to include `api_duration_ms` for the data set that will feed the website.

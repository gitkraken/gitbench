## Context

The overview page already renders pass-rate, quadrant, cost, API-time, token, and heatmap charts from compact chart endpoints. Benchmark detail pages currently render a benchmark-scoped pass-rate leaderboard and a per-fixture comparison table. Fixture detail pages render fixture metadata, raw repeated-attempt evidence, and output cards.

The existing chart API route accepts `benchmark` for all chart names, but only pass-rate data is actually narrowed by benchmark. Cost, runtime, token, and quadrant charts still derive from global model summaries. Fixture detail endpoints already expose the per-output fields needed for fixture-level charts: pass/fail, similarity, cost, API duration, input tokens, output tokens, total tokens, and reasoning tokens.

## Goals / Non-Goals

**Goals:**

- Reuse the current chart language, selectors, provider colors, text/JSON pairing, and campaign awareness on benchmark and fixture detail pages.
- Ensure every metric chart shown on a benchmark page uses benchmark-scoped data.
- Ensure every metric chart shown on a fixture page uses fixture-scoped data.
- Make fixture quality truthful for both graded and binary fixtures.
- Keep chart API responses compact and free of raw prompt/output payloads.

**Non-Goals:**

- Redesign the overview page.
- Add new charting dependencies.
- Change fixture scoring semantics or the persisted scoring model.
- Add a visible campaign selector to ordinary benchmark or fixture pages.
- Replace raw attempt evidence or model output cards on fixture pages.

## Decisions

### Use a shared scoped chart data path

Chart data generation will accept a scope object rather than special-casing each page:

```text
scope: global
scope: benchmark + benchmarkName
scope: fixture + benchmarkName + fixtureId
```

Global scope keeps the current overview behavior. Benchmark scope aggregates only results in the selected benchmark. Fixture scope aggregates only outputs for the selected fixture.

Alternative considered: render existing overview chart components unchanged on detail pages. That would mix benchmark pass rates with full-suite cost/runtime/token totals, which is misleading on a page whose context is a single benchmark or fixture.

### Aggregate benchmark metric data from fixture rows

Benchmark-scoped cost, runtime, and token summaries should be derived from matching fixture result rows or campaign attempt rows, not from global `model_summaries`, `model_runtimes`, or `model_token_summaries`.

For each model/output-mode/effort key in the benchmark scope:

- pass rate comes from `matrix[model][benchmark]` or campaign benchmark aggregates.
- cost is the sum of scoped `cost_usd` values when present.
- API time is the sum/average/min/max of scoped `api_duration_ms` values when present.
- token usage is the sum of scoped token columns.

Alternative considered: scale global cost/runtime/token totals by benchmark fixture count. That would be easier but inaccurate when fixtures differ in prompt size, output size, latency, retries, or failures.

### Build fixture charts from compact fixture outputs

Fixture-scoped charts should use compact per-model metric rows, not full raw output text. The fixture endpoint can either be reused with client-side reduction or the chart endpoint can accept `benchmark` and `fixture` to return only chart-ready summaries. The chart endpoint is preferred for consistent chart payload shape and to avoid loading bulky output content for chart islands.

### Use adaptive fixture quality for quadrant charts

Benchmark quadrant charts use benchmark pass rate as the Y metric because a benchmark contains mixed fixture scoring styles.

Fixture quadrant charts use the most meaningful quality value available:

1. repeated campaign success rate when valid repeated attempts exist.
2. similarity percentage when values contain meaningful intermediate scores.
3. binary success percentage when the fixture only has pass/fail outcomes.

Visible labels must reflect the chosen metric. Use `Success (%)` for repeated or binary success. Use `Similarity (%)` when graded similarity is actually used.

Alternative considered: always use similarity. That creates fake precision for exact pass/fail fixtures. Always using pass/fail loses useful graded information on similarity-scored fixtures.

### Keep fixture page visualization compact

Benchmark pages can support multiple full chart sections because they summarize a category. Fixture pages are already long due to prompts, expected output, raw attempts, and output cards. A compact metric visualization area with tabs or another bounded chart switcher is preferred over stacking four large sections.

## Risks / Trade-offs

- Scoped aggregation may duplicate logic between legacy aggregate rows and campaign attempt rows. -> Centralize scoped summary construction behind chart/report-store helpers and test both legacy and campaign paths.
- Fixture quadrant charts for binary fixtures will create horizontal bands at 0% and 100%. -> Label the metric as success and rely on cost/time/token axes to expose tradeoffs among passers.
- Repeated campaign data can have different denominator semantics from one-shot fixture results. -> Tooltips and labels must include valid attempt counts when success rate is campaign-derived.
- Adding several chart islands can increase page weight. -> Prefer `client:visible` for below-the-fold charts and a compact fixture chart switcher.
- Missing cost/runtime/token fields are common for some providers or local runs. -> Existing "No data" empty states and tooltip no-data sections should remain visible and scoped.

## Migration Plan

1. Add scoped chart data helpers and tests for benchmark and fixture aggregation.
2. Extend chart API validation to accept `fixture` only when `benchmark` is present.
3. Parameterize existing metric chart components with optional `benchmarkName` and fixture scope props.
4. Add benchmark page chart sections.
5. Add compact fixture page metric visualization.
6. Verify API payloads, page rendering, URL-backed model/output-mode state, and campaign-aware behavior.

Rollback is straightforward: remove the new page sections and fixture metric island while leaving the scoped data helpers unused.

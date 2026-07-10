## 1. Scoped Data And API

- [x] 1.1 Add a scoped chart data model that represents global, benchmark, and fixture scopes.
- [x] 1.2 Implement benchmark-scoped cost, runtime, and token aggregation from fixture result rows.
- [x] 1.3 Implement fixture-scoped cost, runtime, token, and quality aggregation from fixture result rows.
- [x] 1.4 Add campaign-aware scoped aggregation from raw campaign attempts for benchmark and fixture scopes.
- [x] 1.5 Add adaptive fixture quality selection for repeated success rate, graded similarity, and binary success.
- [x] 1.6 Extend chart API query validation to accept `fixture` only when `benchmark` is present.
- [x] 1.7 Return clear client errors for unsupported chart/scope combinations.

## 2. Chart Components

- [x] 2.1 Add scope props or equivalent scoped loading support to `QuadrantComparisonChart`.
- [x] 2.2 Add scope props or equivalent scoped loading support to `CostValueChart`.
- [x] 2.3 Add scope props or equivalent scoped loading support to `RuntimeBarChart`.
- [x] 2.4 Add scope props or equivalent scoped loading support to `TokenUsageChart`.
- [x] 2.5 Update quadrant metric definitions so benchmark scope uses pass rate and fixture scope uses adaptive quality labels.
- [x] 2.6 Ensure scoped chart empty states do not fall back to global data.

## 3. Page Integration

- [x] 3.1 Add benchmark-scoped quadrant, cost, API-time, and token sections to `benchmarks/[name].astro`.
- [x] 3.2 Ensure benchmark metric sections share URL-backed model and output-mode selection with the existing leaderboard and table.
- [x] 3.3 Add a compact fixture metric visualization to `fixtures/[benchmark]/[fixture].astro`.
- [x] 3.4 Preserve fixture prompt, expected output, raw attempt evidence, and model output card sections.
- [x] 3.5 Use below-the-fold hydration such as `client:visible` where appropriate to limit initial page cost.

## 4. Tests And Verification

- [x] 4.1 Add unit tests for benchmark-scoped chart payloads for cost, runtime, tokens, and quadrant quality.
- [x] 4.2 Add unit tests for fixture adaptive quality selection across repeated, graded, and binary fixtures.
- [x] 4.3 Add API route tests for benchmark scope, fixture scope, fixture-without-benchmark validation, and compact payload shape.
- [x] 4.4 Add component/data tests proving scoped charts do not use global totals.
- [x] 4.5 Verify benchmark and fixture pages render the new chart sections without breaking existing report views.
- [x] 4.6 Run the web test suite and build or typecheck command used by this repo.

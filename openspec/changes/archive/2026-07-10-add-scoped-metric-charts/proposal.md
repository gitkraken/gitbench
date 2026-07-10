## Why

Benchmark and fixture detail pages currently show evidence tables, raw outputs, and benchmark-scoped pass rates, but they do not expose the same efficiency tradeoffs that make the overview page useful. Adding scoped quadrant, cost, API-time, and token charts lets users answer whether a model is not only good overall, but efficient on a specific benchmark or fixture.

## What Changes

- Add benchmark-scoped quadrant, cost, API-time, and token usage sections to Benchmark Detail pages.
- Add fixture-scoped metric visualization to Fixture Detail pages so users can compare models on one fixture without reading every output card.
- Scope chart data to the page context:
  - benchmark pages use only rows for the selected benchmark.
  - fixture pages use only rows for the selected benchmark fixture.
- Use benchmark pass rate as the quality metric for benchmark-scoped quadrant charts.
- Use an adaptive fixture quality metric for fixture-scoped quadrant charts:
  - repeated campaign success rate when repeated attempts exist.
  - similarity percentage when the fixture has meaningful graded similarity values.
  - binary success percentage when the fixture is pass/fail only.
- Preserve existing model selection, output-mode selection, provider coloring, text/JSON pairing, and campaign-aware behavior.
- Keep chart API payloads compact and avoid embedding raw model output in chart responses.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `report-pages`: Benchmark Detail and Fixture Detail pages gain scoped metric charts and must keep their chart data aligned with the selected page context.
- `chart-components`: Existing quadrant, cost, API-time, and token chart components become reusable for global, benchmark, and fixture scopes, including adaptive fixture quality labeling.
- `report-query-api`: Chart endpoints support benchmark and fixture scoping for all metric chart types while preserving compact campaign-aware payloads.

## Impact

- Affected web pages:
  - `web/src/pages/benchmarks/[name].astro`
  - `web/src/pages/fixtures/[benchmark]/[fixture].astro`
- Affected chart components:
  - `QuadrantComparisonChart`
  - `CostValueChart`
  - `RuntimeBarChart`
  - `TokenUsageChart`
  - shared grouped metric and quadrant data helpers
- Affected data/API layer:
  - chart API query parsing and response shaping
  - report-store summary/detail aggregation helpers
  - campaign-aware aggregate handling for scoped benchmark and fixture chart data
- Tests should cover benchmark-scoped metric payloads, fixture adaptive quality selection, and page-level chart inclusion.

## Why

GitBench displays token counts as comparable metrics without clearly stating that the underlying usage values originate from provider telemetry. Because providers may use different tokenizers and accounting conventions, readers need a visible caveat to interpret cross-provider comparisons accurately.

## What Changes

- Add a concise provider-reporting disclaimer to token-usage explanatory blurbs on the overview and benchmark detail pages.
- Add a stable token-accounting section to the Methodology page explaining the provenance of source counts, GitBench-derived aggregates, and limits of cross-provider comparison.
- Link token-usage blurbs to the new Methodology section so readers can reach the fuller explanation without repeating it throughout fixture cards and tooltips.
- Leave token collection, aggregation, chart rendering, and stored report data unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `page-help-text`: Require token-usage blurbs on overview and benchmark pages to disclose provider-reported usage and link to the detailed methodology explanation.
- `methodology-page`: Require a token-accounting section describing provider telemetry, derived aggregates, non-verification, and provider-specific tokenization and accounting differences.

## Impact

- Affected UI content: `web/src/pages/index.astro`, `web/src/pages/benchmarks/[name].astro`, and `web/src/pages/methodology.astro`.
- Affected tests: page-content or build-level assertions covering the disclaimer and methodology anchor.
- No API, database, report-format, dependency, or token-calculation changes.

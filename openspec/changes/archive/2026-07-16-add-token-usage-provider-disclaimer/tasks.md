## 1. Token Usage Disclosures

- [x] 1.1 Update the overview Token Usage blurb to identify provider-reported source counts, warn about provider accounting differences, and link to `/methodology#token-accounting` using the established Learn more styling.
- [x] 1.2 Update the benchmark detail Token Usage blurb with the same provenance caveat and Methodology link.

## 2. Methodology

- [x] 2.1 Add a `token-accounting` Methodology section that distinguishes provider-reported source telemetry from GitBench aggregates and fallback totals.
- [x] 2.2 Explain that GitBench does not independently retokenize or verify source counts and that provider tokenizers and token-category semantics can differ.

## 3. Verification

- [x] 3.1 Add or update page-content tests to assert both token-chart disclosures, the stable Methodology anchor, and the required deep links.
- [x] 3.2 Run the relevant web tests and production build, then confirm token collection, data contracts, and chart calculations remain unchanged.

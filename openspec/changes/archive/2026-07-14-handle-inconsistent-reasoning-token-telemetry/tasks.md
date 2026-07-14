## 1. Shared Token Decomposition

- [x] 1.1 Extend `OutputTokenDecomposition` in `web/src/lib/token-usage.ts` with bounded reasoning-within-output, reasoning overflow, and inconsistency metadata while preserving raw output and raw reasoning values.
- [x] 1.2 Update `decomposeOutputTokens` to derive visible output, bounded reasoning, overflow reasoning, and the inconsistency flag for null, zero, normal, and `reasoning_tokens > output_tokens` cases.
- [x] 1.3 Update `web/test/token-usage.test.mjs` to cover bounded reasoning, overflow, missing output, missing reasoning, and no double-counting.

## 2. Token Chart Stack Data

- [x] 2.1 Update token metric row types in `web/src/components/charts/model-groups.ts` to carry bounded reasoning and overflow metadata separately from raw reasoning.
- [x] 2.2 Update `tokenMetric` and `applyTokenSegments` so stacked chart segments use input, visible output, and bounded reasoning only.
- [x] 2.3 Add or update chart row tests proving inconsistent provider counts produce a stack height equal to provider `total_tokens`, not raw `input + reasoning_tokens`.
- [x] 2.4 Confirm benchmark-scoped and fixture-scoped token data paths use the same decomposition behavior as the global overview chart.

## 3. Token Tooltip Presentation

- [x] 3.1 Update `TokenUsageChart` tooltip effort lines to distinguish provider output, visible output, reasoning within output, and inconsistent overflow reasoning.
- [x] 3.2 Ensure normal reasoning, zero reasoning, missing reasoning, and inconsistent reasoning telemetry each render clear tooltip copy.
- [x] 3.3 Keep provider raw reasoning visible when overflow exists without presenting overflow as additional output.

## 4. Verification

- [x] 4.1 Run focused web tests for token usage and chart model groups.
- [x] 4.2 Run the broader web test suite used by this repo.
- [x] 4.3 Run `pnpm build` from `web`.
- [x] 4.4 Run `openspec validate handle-inconsistent-reasoning-token-telemetry --strict`.

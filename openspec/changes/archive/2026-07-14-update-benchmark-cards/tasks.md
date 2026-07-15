## 1. Summary Calculation

- [x] 1.1 Add a benchmark-card summary helper that derives eligible model scores from `GitBenchData`.
- [x] 1.2 Implement strict unsupported JSON-schema zero detection using output mode, `pass_at_k === 0`, and fixture-level `structured_error` coverage.
- [x] 1.3 Aggregate fixture outcomes by provider/base-model identity, then compute best, worst, tied-count fallback, and arithmetic average from those model scores.
- [x] 1.4 Format user-facing model labels without leaking the `__json_schema` storage suffix.

## 2. Benchmarks Index UI

- [x] 2.1 Update `web/src/pages/benchmarks/index.astro` to use the summary helper for each benchmark card.
- [x] 2.2 Replace the existing fixture count with an Avg badge beside the benchmark title and a Best/Worst statistics row below it.
- [x] 2.3 Render tied best/worst results as model counts instead of arbitrary model names.
- [x] 2.4 Add a clear empty state for benchmarks with no eligible scores.

## 3. Verification

- [x] 3.1 Add focused tests for unique best/worst labels, tied best/worst counts, average calculation, and fixture count removal behavior.
- [x] 3.2 Add tests proving strict unsupported JSON-schema zero scores are excluded.
- [x] 3.3 Add tests proving valid JSON-schema zero scores remain eligible.
- [x] 3.4 Run OpenSpec validation for `update-benchmark-cards`.
- [x] 3.5 Run the relevant web test suite and build/typecheck checks.

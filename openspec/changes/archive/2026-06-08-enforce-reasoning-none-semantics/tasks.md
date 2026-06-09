## 1. Static Capability Validation

- [x] 1.1 Update `gitbench/data/effort_matrix.json` so DeepSeek V4 Flash and DeepSeek V4 Pro list only currently supported effort levels (`high`, `xhigh`).
- [x] 1.2 Add capability tests proving undocumented `none`, `minimal`, `low`, and `medium` combinations fail before model API calls while documented levels still pass.
- [x] 1.3 Update affected CLI validation fixtures and profile expectations to match the corrected effort matrix.

## 2. Reasoning Disable Transport And Invariant

- [x] 2.1 Refactor OpenAI-compatible reasoning request construction into a shared helper that preserves caller `extra_body`, uses `reasoning_effort` for first-party OpenAI, uses `reasoning.effort` for non-`none` OpenRouter levels, and uses `reasoning.enabled=false` for OpenRouter `none`.
- [x] 2.2 Add a dedicated fatal reasoning-disable exception and centralized response validation for explicit zero reasoning tokens, absent reasoning content, non-zero reasoning, and missing telemetry.
- [x] 2.3 Add adapter unit tests covering first-party `none`, OpenRouter `none`, non-`none` forwarding, extra-body preservation, zero-token acceptance, reasoning-token rejection, reasoning-content rejection, and missing-telemetry rejection.

## 3. Preflight And Runtime Failure Propagation

- [x] 3.1 Add CLI preflight discovery that deduplicates statically valid `none` targets by effective provider, base URL, base model, and routing configuration.
- [x] 3.2 Execute one bounded reasoning canary per unique `none` target after credential/static validation and before benchmark fixtures, excluding canary usage from benchmark results.
- [x] 3.3 Add actionable preflight diagnostics and CLI tests proving a violated, rejected, or unverifiable `none` target exits non-zero before any benchmark fixture call.
- [x] 3.4 Propagate the fatal reasoning-disable exception through `BenchmarkRunner` without converting it into a failed `Score`.
- [x] 3.5 Update sequential and concurrent CLI orchestration to stop new scheduling, cancel pending work best-effort, omit the violating response from normal results, and exit non-zero.
- [x] 3.6 Add runner and concurrency regression tests for runtime violations after a successful preflight.

## 4. Token Semantics And Report Presentation

- [x] 4.1 Add a shared TypeScript token-decomposition helper that preserves raw provider output, derives visible output as `max(output - reasoning, 0)`, and handles null or inconsistent counts.
- [x] 4.2 Update model detail, `ModelOutputCard`, and `FixtureCard` token labels to identify provider output as total output and reasoning as included within it.
- [x] 4.3 Update report-page tests or API snapshots for explicit inclusive-output labels, zero reasoning, unavailable reasoning, and reasoning-greater-than-output cases.
- [x] 4.4 Update grouped token metric preparation so each chart stack uses the same representative effort as the median bar rather than totals summed across all efforts.
- [x] 4.5 Update token chart stacks and tooltips to use input plus visible output plus reasoning without double-counting provider output.
- [x] 4.6 Add web tests for representative-effort decomposition, total stack height, no-reasoning output, zero reasoning, and clamped inconsistent provider counts.

## 5. Fixture Calibration And Versioning

- [x] 5.1 Rewrite `fixtures/blame_forensics/f010.yaml` so `Update import path` uniquely introduces the nonexistent `helpers` import and later formatter commits preserve blame for that broken line.
- [x] 5.2 Add or update fixture self-check coverage proving the current broken line blames to `Update import path` and no later commit independently introduces the same missing module.
- [x] 5.3 Bump `BENCHMARK_SUITE_VERSION` from `0.2.0` to `0.3.0` and update version-sensitive tests and generated fixture expectations.

## 6. Verification

- [x] 6.1 Run focused Python tests for capabilities, adapters, runner behavior, CLI validation/preflight, fixture scoring, and suite versioning.
- [x] 6.2 Run the complete Python test suite.
- [x] 6.3 Run `pnpm test:api` and `pnpm build` from `gitbench/web`.
- [x] 6.4 Run `openspec validate enforce-reasoning-none-semantics --strict` and confirm the change remains apply-ready.

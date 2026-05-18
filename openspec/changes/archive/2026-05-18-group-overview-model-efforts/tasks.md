## 1. Grouping Data Helpers

- [x] 1.1 Add frontend helper types for provider/base-model group IDs, grouped effort rows, metric ranges, and representative values.
- [x] 1.2 Add helper functions to derive model groups from `GitBenchData.base_model_groups` and fall back to `data.models` when needed.
- [x] 1.3 Add chart-specific metric extractors for pass rate, runtime, cost, and token usage.
- [x] 1.4 Add selection migration logic that maps old full model+effort names from localStorage to provider/base-model group IDs.

## 2. Shared Overview Selection

- [x] 2.1 Update `useSyncedModelSelection` to initialize, sanitize, persist, and broadcast selected group IDs.
- [x] 2.2 Provide a helper to expand selected group IDs back to child full model names for components that still need effort-level records.
- [x] 2.3 Verify multiple Overview chart islands stay synchronized through `model-selection-changed` events.

## 3. Model Selector

- [x] 3.1 Update `ModelSelector` options to render provider/base-model groups instead of individual model+effort entries on Overview charts.
- [x] 3.2 Update search to match provider, base model, group ID, child model names, and child reasoning levels.
- [x] 3.3 Update selector badges to show pass-rate range and effort count.
- [x] 3.4 Preserve Select all, Clear all, initial selection, external event handling, and localStorage persistence behavior for group IDs.

## 4. Grouped Bar Charts

- [x] 4.1 Update `PassRateBarChart` to render one grouped range bar per selected provider/base-model group and sort by highest effort pass rate.
- [x] 4.2 Update `CostValueChart` to render grouped cost ranges and sort by lowest effort cost.
- [x] 4.3 Update `RuntimeBarChart` to render grouped runtime ranges and sort by fastest effort runtime.
- [x] 4.4 Update `TokenUsageChart` to render grouped token ranges and sort by lowest effort total tokens.
- [x] 4.5 Update grouped bar click handlers to navigate to `modelGroupPath(provider, baseModel)`.
- [x] 4.6 Update provider legends to derive from selected rendered groups.

## 5. Tooltip And Empty States

- [x] 5.1 Update pass-rate tooltips to list each effort's pass rate and identify the best effort.
- [x] 5.2 Update cost, runtime, and token tooltips to list each effort's metric value and identify the representative effort used for sorting.
- [x] 5.3 Preserve chart-specific no-data cards and keep the `ModelSelector` visible in empty states.
- [x] 5.4 Ensure single-effort groups render cleanly as a normal bar or zero-length range with the grouped tooltip.

## 6. Compatibility And Verification

- [x] 6.1 Adapt `BenchmarkHeatmap` to consume grouped selection by expanding selected groups to child model names, if required by the shared hook changes.
- [ ] 6.2 Add or update frontend tests for grouped selection migration, selector filtering, grouped chart row derivation, and base-model navigation.
- [x] 6.3 Run the web typecheck/build and the relevant Python render tests.
- [ ] 6.4 Manually inspect the Overview page with multiple efforts per base model to verify range rendering, tooltip detail, sorting, and click-through behavior.

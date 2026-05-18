## Why

The Overview page currently gives every effort level its own chart bar, which makes closely related runs compete for axis space and obscures the model-family comparison users are trying to make. Grouping efforts under their provider/base model keeps the overview scannable while preserving effort-level detail in tooltips and drill-down pages.

## What Changes

- Overview bar charts group model efforts by provider/base model instead of rendering one bar per model+effort.
- Grouped bars show the range of effort values and use the best chart-specific value for sorting.
- Tooltips for grouped bars list the individual effort values that make up the range.
- Clicking a grouped bar navigates to the base model page (`/models/<provider>/<base-model>/`) instead of an individual effort page.
- The Overview `ModelSelector` lists selectable base model groups, with labels and badges that summarize the grouped effort values.
- Shared Overview selection state stores and broadcasts selected base model group IDs while charts expand groups to the underlying model+effort records when needed.
- Existing provider coloring and provider legends continue to work at the provider/base-model group level.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `chart-components`: Pass-rate overview bars and shared Overview selection semantics change from model+effort entries to provider/base-model groups.
- `searchable-model-selector`: The Overview selector changes from a flat model+effort list to grouped base-model options with effort summary information.
- `runtime-chart`: Runtime bars group effort values under base models and sort by fastest effort in each group.
- `token-usage-chart`: Token usage bars group effort values under base models and show per-effort token totals in tooltips.
- `cost-value-chart`: Cost bars group effort values under base models and show per-effort cost values in tooltips.

## Impact

- **React components**: `ModelSelector`, `useSyncedModelSelection`, `PassRateBarChart`, `RuntimeBarChart`, `TokenUsageChart`, `CostValueChart`, and possibly `BenchmarkHeatmap` if it needs to consume grouped selection state directly.
- **Routing**: Grouped chart clicks use `modelGroupPath()` instead of `modelLevelPath()`.
- **Data shaping**: Frontend chart helpers need group-level chart rows built from `data.base_model_groups`, `data.models`, `model_summaries`, `model_runtimes`, and fixture token data. The existing JSON schema likely has enough data for the first pass, though richer group summary fields may be added if duplication gets high.
- **Persistence**: Local storage key `gitbench-model-selection` may contain old model+effort names. The implementation needs a migration/sanitization path to default or map stored selections to base-model group IDs.
- **Tests/specs**: Chart and selector specs need updated scenarios for grouped display, range rendering, tooltip detail, sort order, and base-model-page navigation.

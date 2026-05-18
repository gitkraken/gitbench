## Context

The Overview page is composed of independent `client:load` React chart islands. Each chart loads `results.json`, uses `useSyncedModelSelection(data.models)` for a shared selected model array, renders a `ModelSelector`, and then filters chart rows by full model name. Full model names represent provider/base-model/effort combinations such as `openai/gpt-oss-120b:high`.

The aggregation layer already emits `base_model_groups`, and each `ModelInfo` has `provider`, `baseModel`, and `reasoningLevel`. That gives the frontend enough identity information to group efforts without changing the run format.

## Goals / Non-Goals

**Goals:**

- Make Overview bar charts compare provider/base-model groups instead of individual effort levels.
- Preserve effort-level detail in grouped-bar tooltips.
- Keep shared Overview selection synchronized across chart islands.
- Navigate grouped bars to the base model page.
- Tolerate old localStorage selections that contain full model+effort names.

**Non-Goals:**

- Changing benchmark execution, scoring, or model naming.
- Redesigning model detail pages.
- Redesigning the benchmark heatmap into a grouped matrix unless required for selector compatibility.
- Adding a new charting dependency.

## Decisions

### 1. Use base-model group IDs as the Overview selection unit

**Decision:** The shared Overview selection hook will store selected group IDs, not selected full model names. A group ID should be stable and derived from provider/base model, for example `provider/baseModel`.

**Rationale:** The chart visual unit and selector option should match. If a bar represents `openai/gpt-oss-120b`, the selected value should represent the same group instead of a hidden set of child effort models.

**Alternative considered:** Keep storing full model names and group only during chart rendering. This would preserve the localStorage contract, but the selector would still need awkward parent/child selection behavior and the selected count would not match the number of displayed bars.

### 2. Build grouped chart rows in shared frontend helpers

**Decision:** Add reusable frontend helpers for deriving group rows from `GitBenchData`. Each row should include provider, base model, group ID, child effort rows, min value, max value, representative value, and display metadata.

**Rationale:** Pass rate, runtime, cost, and token charts need the same grouping mechanics but different metric extraction and sort semantics. A helper avoids four slightly different implementations of grouping, labeling, provider legends, and stored-selection sanitization.

**Alternative considered:** Extend `base_model_groups` in Python with all chart metrics. That may become worthwhile later, but the current JSON already contains the source data. Computing derived chart rows in React keeps this change focused on presentation behavior.

### 3. Sort each grouped bar by the chart's best value

**Decision:** Grouped rows use a chart-specific representative value for sorting and bar prominence:

- Pass rate: highest effort pass rate wins; sort descending.
- Runtime: fastest effort runtime wins; sort ascending.
- Cost: lowest effort cost wins; sort ascending.
- Token usage: lowest effort total token count wins; sort ascending.

The tooltip still lists every effort value in the group.

**Rationale:** Sorting by the best available effort answers "how strong can this base model be under the tested effort settings?" and matches the user's request that sorting remain based on highest score for quality. For efficiency charts, the equivalent best value is the lowest cost/runtime/token total.

**Alternative considered:** Sort by average across efforts. Averages can be useful, but they hide the best tested setting and make groups with missing effort levels harder to compare.

### 4. Render a range, not a stack

**Decision:** Bars should visually communicate the min-to-max range of effort values for the group, with a clear marker or filled segment for the representative value. They should not stack efforts.

**Rationale:** Effort values are alternative runs, not additive parts. A stacked bar would imply totals and would be misleading for pass rate, runtime, cost, and token usage.

**Alternative considered:** Render clustered child bars inside each group. That preserves detail but does not reduce axis density enough when many base models are present.

### 5. Grouped chart clicks go to base model pages

**Decision:** Clicking a grouped bar navigates to `modelGroupPath(provider, baseModel)`.

**Rationale:** The visual object is the base model group. The base model page is already the appropriate place to inspect and choose individual effort levels.

**Alternative considered:** Click the representative/best effort's detail page. That is faster for a single best-level workflow, but it makes the grouped bar behave like one hidden child instead of the displayed group.

### 6. Migrate persisted selection defensively

**Decision:** When the hook reads `gitbench-model-selection`, it should accept either group IDs or old full model names. Old full model names should be mapped to their provider/base-model group IDs. Unknown values should be ignored. If no valid values remain, default to all group IDs.

**Rationale:** Existing users may have full model names stored locally. A silent migration avoids empty charts on first load after the change.

**Alternative considered:** Use a new localStorage key. That avoids migration logic but loses the user's existing selection and leaves stale state behind.

## Risks / Trade-offs

- **[Risk] Shared selection may disrupt BenchmarkHeatmap expectations** -> Keep helper APIs able to expand selected group IDs back to full model names. If the heatmap remains effort-level, it can render all child model columns for selected groups.
- **[Risk] Range rendering may be hard to read in vertical Recharts bars** -> Prefer a simple marker/overlay implementation first, then polish after screenshot review.
- **[Risk] Missing metrics can skew ranges** -> Exclude child efforts without chart-specific data from that chart's group row. If a selected group has no valid children for that metric, omit it from the chart and preserve the selector in the empty state.
- **[Risk] Single-effort groups could look visually odd** -> Render a normal bar or zero-length range with the same tooltip structure.
- **[Risk] LocalStorage migration may accidentally select too much** -> Sanitize against known group IDs and only default to all groups when the stored selection has no valid mapped values.

## Migration Plan

1. Add group identity and metric helper functions in the frontend.
2. Update the shared selection hook to initialize from `base_model_groups` and migrate old full-model selections.
3. Update `ModelSelector` to render group options and summary badges.
4. Update Overview bar charts to consume selected group IDs and render grouped range rows.
5. Keep or adapt `BenchmarkHeatmap` by expanding selected groups to child model names if needed.
6. Verify stored selections from both old and new formats.

## Open Questions

- Should tooltips include links for each individual effort, or should navigation stay exclusively at the base-model page level for the first pass?
- Should the selector trigger say "3 model groups selected" or keep the shorter existing "3 selected" label?

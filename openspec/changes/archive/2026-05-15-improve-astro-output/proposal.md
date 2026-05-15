## Why

The Astro site renders benchmark results but wastes screen real estate with ungrouped model lists, horizontal bar charts that don't scale to many models, and a cost metric (avg per fixture) that obscures the actual cost of a full evaluation run. As we add more models, these problems compound into an unusable dashboard.

## What Changes

- **Fix model name parsing** in the aggregation layer: extract provider (`anthropic`), base model (`claude-opus-4.7`), and reasoning level (`low`) from full model names using the `:` separator found in actual run data
- **Group models by provider and base model** on the models index page, with reasoning levels shown as sub-cards under each base model — each linking to a drill-down fixture gallery
- **Restructure model URLs** to clean nested paths: `/models/anthropic/claude-opus-4.7/low/` instead of the old `~`-encoded flat slugs
- **Switch the model summary bar chart** from horizontal bars to vertical bars with diagonal X-axis labels using provider brand icons (`@icons-pack/react-simple-icons`) to save space, matching the artificialanalysis.ai layout style
- **Change the cost axis** on the cost-vs-quality scatter plot from average cost per fixture to **total cost of a full run** — a more honest and interpretable metric
- **Add provider brand icons** to the ModelSelector dropdown items so each entry is compact and scannable
- **Right-align the ModelSelector** at desktop widths instead of full-width, making chart headers cleaner

## Capabilities

### New Capabilities
- `provider-brand-icons`: Provider brand icon mapping (Anthropic, OpenAI, Google, Meta, etc.) via `@icons-pack/react-simple-icons`, used in chart labels, model selectors, and model cards. Includes fallback for unknown providers.

### Modified Capabilities
- `astro-site`: URL structure changes — model pages move from `/models/[model]` to nested `/models/[provider]/[model]/[level]/`. No redirects for old URLs. Sidebar navigation intact.
- `chart-components`: PassRateBarChart switches from horizontal to vertical bars with custom diagonal tick labels containing provider icons and truncated model names
- `cost-value-chart`: X-axis changes from `avg_cost_usd` to `total_cost_usd` with updated labels
- `searchable-model-selector`: Each dropdown entry renders a provider brand icon alongside the model name for visual scanning
- `report-pages`: Models index page switches from flat card grid to provider-grouped layout with base model sections and level sub-cards. Model detail page moves to nested route structure.

## Impact

- **Python**: `gitbench/render.py` — `aggregate_runs()` gains model name parsing for `provider/base:level` format and outputs `base_model_groups`
- **TypeScript types**: `gitbench/web/src/lib/types.ts` — new fields on `ModelInfo` and new `base_model_groups` array type
- **Routes**: `gitbench/web/src/lib/routes.ts` — new path helpers for nested model routes
- **Astro pages**: `models/index.astro`, `models/[model].astro` removed; new `models/[provider]/[model]/index.astro` and `models/[provider]/[model]/[level].astro` added; `index.astro` minor layout tweak
- **React components**: `PassRateBarChart.tsx`, `CostValueChart.tsx`, `ModelSelector.tsx` modified; new `ProviderIcon.tsx`
- **Dependencies**: add `@icons-pack/react-simple-icons` to `package.json`
- **Breaking**: Old model URLs (`/models/anthropic~claude-opus-4.7~low`) return 404 — no redirects

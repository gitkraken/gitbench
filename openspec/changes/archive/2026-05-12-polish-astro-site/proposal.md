## Why

The Astro site works but feels unfinished. Model selectors on the same page are independent (picking models in one chart doesn't update the other). Pricing and token usage data exists in the pipeline but never reaches the UI — users can't see what a benchmark run costs or how many tokens each model consumed. The Explore tag cloud is a wall of ~40 pills that overwhelms rather than helps. A mock "unknown" model with 0% pass rate pollutes every chart. And first-time visitors land on a dashboard with zero context about what GitBench is or how it works.

## What Changes

- **Model selector state sync**: All ModelSelector instances on a page share the same selection via localStorage persistence and custom events. Changing models in one chart updates all charts instantly.
- **Pricing and token display**: Extract `cost_usd` from OpenRouter API responses (already present in `usage.cost`), thread it through the Score → aggregation → results.json pipeline, then surface token counts and cost on model overview cards, fixture detail pages, and a new cost-vs-quality quadrant chart on the Models page.
- **Tag cloud redesign**: Replace the wall-of-pills with a search-first tag interface — a prominent search input, a compact "popular tags" strip, and "show all" expander. Filters below auto-sync.
- **Hide unknown/mock model**: Filter the `"unknown"` model at the `aggregate_runs()` level in `render.py` so it never reaches results.json or any UI component.
- **Dashboard → Overview rename + intro**: Rename the page and sidebar link. Add a brief intro section explaining GitBench's purpose. Create a `/methodology` page explaining benchmarks, scoring, pass@k, and limitations.
- **BREAKING**: The `unknown` model is removed from `results.json`. Any downstream consumers that reference it will need updating.

## Capabilities

### New Capabilities
- `pricing-pipeline`: Extract cost from OpenRouter API responses, thread through Score → aggregation → results.json, and expose cost/token fields in the aggregated output.
- `cost-value-chart`: Quadrant scatter plot on the Models overview page plotting pass rate (Y) against average cost per fixture (X), with reference lines dividing "cheap & good" from "expensive & bad".
- `methodology-page`: A new `/methodology` route explaining how GitBench works — benchmark design, similarity scoring, pass@k, model selection, and known limitations.

### Modified Capabilities
- `searchable-model-selector`: ModelSelector uses localStorage for persistent selection across page navigations and dispatches custom events to synchronize multiple instances on the same page.
- `astro-site`: Dashboard page renamed to Overview with intro content. Sidebar link updated. New Methodology route added.
- `json-export`: `aggregate_runs()` filters out the `"unknown"` model and includes `cost_usd` in per-fixture dicts.

## Impact

- **Python pipeline**: `model.py` (cost extraction), `runner.py` (cost on Score), `render.py` (cost in aggregation, unknown filter)
- **TypeScript types**: `web/src/lib/types.ts` (add `cost_usd` to `FixtureResult`)
- **React components**: `ModelSelector.tsx` (localStorage + events), new `CostValueChart.tsx`, `PassRateBarChart.tsx` and `TimeSeriesChart.tsx` (remove independent defaults, read from sync)
- **Astro pages**: `index.astro` (rename + intro), `models/index.astro` (add quadrant chart), `models/[model].astro` (token/cost display), `fixtures/[benchmark]/[fixture].astro` (token badges on model output cards), `explore.astro` (tag cloud redesign)
- **Components**: `Sidebar.astro` (link rename), `ModelOutputCard.astro` (token/cost display)
- **New page**: `pages/methodology.astro`
- **Data file**: `results.json` schema change (new `cost_usd` field; `unknown` model removed)

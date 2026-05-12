## 1. Pricing pipeline (Python)

- [x] 1.1 In `model.py` `OpenAIAdapter.generate()`, extract `cost` from `raw_usage` via `getattr(raw_usage, 'cost', None)` and add `"cost"` key to returned usage dict
- [x] 1.2 In `runner.py` `_run_fixture()`, map `usage.get("cost")` onto `score.cost_usd` alongside existing token mapping
- [x] 1.3 In `render.py` `aggregate_runs()`, copy `cost_usd` from scores into per-fixture dicts (alongside existing token fields)
- [x] 1.4 In `render.py` `aggregate_runs()`, compute `total_cost_usd` and `avg_cost_usd` per model in `model_summaries`
- [x] 1.5 In `render.py` `aggregate_runs()`, filter out `"unknown"` model from all collections (models, summaries, matrix, fixtures, runs_meta)

## 2. TypeScript types update

- [x] 2.1 Add `cost_usd: number | null` to `FixtureResult` interface in `web/src/lib/types.ts`
- [x] 2.2 Add `total_cost_usd: number | null` and `avg_cost_usd: number | null` to `ModelSummary` interface in `web/src/lib/types.ts`

## 3. ModelSelector state sync

- [x] 3.1 Add `localStorage` read (`gitbench-model-selection`) on mount as fallback when `initialSelected` is empty/undefined
- [x] 3.2 Add `localStorage` write on every selection change
- [x] 3.3 Dispatch `CustomEvent('model-selection-changed')` on `window` on every selection change
- [x] 3.4 Add `window.addEventListener('model-selection-changed', ...)` with `useEffect` cleanup on unmount

## 4. Overview rename and intro content

- [x] 4.1 Rename sidebar link from "Dashboard" to "Overview" in `Sidebar.astro`
- [x] 4.2 Rename page title from "Dashboard" to "Overview" in `index.astro`
- [x] 4.3 Add intro paragraph above charts in `index.astro` explaining what GitBench is

## 5. Methodology page

- [x] 5.1 Create `pages/methodology.astro` with Layout, write prose for benchmark design, similarity scoring, pass@k, run metadata, and limitations sections
- [x] 5.2 Add `{ href: '/methodology', label: 'Methodology', icon: BookOpen }` to sidebar links in `Sidebar.astro`
- [x] 5.3 Import `BookOpen` from lucide-react in `Sidebar.astro`

## 6. CostValueChart (quadrant chart)

- [x] 6.1 Create `web/src/components/charts/CostValueChart.tsx` with Recharts ScatterChart, ReferenceLines at median cost/pass rate, tooltip, and click navigation
- [x] 6.2 Handle edge case: models with no cost data excluded; "No pricing data available" when all models lack cost
- [x] 6.3 Add `CostValueChart` to `pages/models/index.astro` in a "Cost vs Quality" section below model grid, with `client:load`

## 7. Token and cost display on model overview pages

- [x] 7.1 On `pages/models/index.astro` model cards, show `total_cost_usd` and `avg_cost_usd` as small mono text when available
- [x] 7.2 On `pages/models/[model].astro`, add total cost and total tokens display in the summary area next to pass rate
- [x] 7.3 On `pages/models/[model].astro` FixtureCard, add `input_tokens` / `output_tokens` display in the card when available

## 8. Token display on fixture detail page

- [x] 8.1 Update `ModelOutputCard.astro` props to accept `inputTokens` and `outputTokens` (both `number | null`)
- [x] 8.2 In `ModelOutputCard.astro`, render token counts as small mono badges (e.g., "157→496") when values are present
- [x] 8.3 In `pages/fixtures/[benchmark]/[fixture].astro`, pass token values to `ModelOutputCard` from fixture results

## 9. Tag cloud redesign on Explore

- [x] 9.1 Replace flex-wrap tag cloud HTML with: a search input for tags, a compact "Popular tags" row of top 8-10 tags, and a "Show all N tags" toggle
- [x] 9.2 Update client-side JS: tag search filters the popular/all tag display as you type; clicking a tag sets the explore-tag select and applies filters
- [x] 9.3 Keep existing filter selects (difficulty, benchmark) below the new tag interface

## 10. Regenerate and verify

- [ ] 10.1 Re-run `gitbench render --format json` to regenerate `web/public/results.json` with cost data and filtered unknown model
- [ ] 10.2 Run `cd gitbench/web && npm run build` and verify the static build succeeds
- [ ] 10.3 Manual smoke test: Overview intro visible, model selectors sync on Dashboard, quadrant chart on /models, token badges on fixtures, tag search on Explore, Methodology page accessible, unknown model absent from all views

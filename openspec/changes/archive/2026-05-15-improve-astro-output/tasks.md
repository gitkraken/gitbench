## 1. Aggregation — Model Name Parsing

- [x] 1.1 Add `_parse_model_parts()` helper to `render.py` that splits `provider/base:level` format (try `:`, fallback to `#`, handle no level)
- [x] 1.2 Update `aggregate_runs()` to populate `provider`, correct `baseModel`, and `reasoningLevel` fields on `ModelInfo` entries
- [x] 1.3 Build `base_model_groups` array in `aggregate_runs()` output: group by (provider, baseModel) with sorted level/model lists
- [x] 1.4 Verify `total_cost_usd` remains in model_summaries (already computed, ensure not lost)

## 2. Data Types and Route Helpers

- [x] 2.1 Add `provider` field to `ModelInfo` type, add `BaseModelGroup` type, add `base_model_groups` to `GitBenchData`
- [x] 2.2 Add new route helpers: `modelGroupPath(provider, base)` → `/models/<provider>/<base>/`, `modelLevelPath(provider, base, level)` → `/models/<provider>/<base>/<level>/`
- [x] 2.3 Keep existing `modelPath()` helper but note it's for legacy/comparison URLs only (full name encoding)

## 3. Provider Brand Icons

- [x] 3.1 Install `@icons-pack/react-simple-icons` in `gitbench/web/`
- [x] 3.2 Create `src/components/ProviderIcon.tsx` with provider → `Si*` mapping table and fallback letter-circle
- [x] 3.3 Test that each known provider (anthropic, openai, google, meta, mistral, deepseek) renders its icon correctly

## 4. ModelSelector — Provider Icons

- [x] 4.1 Update `ModelSelector.tsx` to import and use `<ProviderIcon provider={...} size={14} />` next to each model name in dropdown items
- [x] 4.2 Extract provider from `ModelInfo.provider` (now available after aggregation fix) for the icon lookup

## 5. PassRateBarChart — Vertical Bars with Diagonal Labels

- [x] 5.1 Switch `BarChart` from `layout="vertical"` to `layout="horizontal"` (vertical bars); swap XAxis/YAxis roles
- [x] 5.2 Implement custom tick renderer for XAxis: provider icon + truncated model name + level, rotated -40°
- [x] 5.3 Set dynamic chart height: `max(300, chartData.length * 80)` plus adequate bottom margin for rotated labels
- [x] 5.4 Keep existing pass rate color coding (green/yellow/red) and `ModelSelector` integration

## 6. CostValueChart — Total Cost Axis

- [x] 6.1 Change X-axis data from `summary.avg_cost_usd` to `summary.total_cost_usd`
- [x] 6.2 Update X-axis label to "Total cost per full run (USD)"
- [x] 6.3 Update tooltip formatter to show "Total cost" instead of "Avg cost"
- [x] 6.4 Update dot navigation to use new `modelLevelPath()` helper (nested route)

## 7. Astro Pages — New Nested Routes

- [x] 7.1 Create `pages/models/[provider]/[model]/index.astro`: base model overview with provider icon header and reasoning level cards
- [x] 7.2 Create `pages/models/[provider]/[model]/[level].astro`: fixture gallery page with sibling level tabs, stats, and Compare button
- [x] 7.3 Ensure both pages use `getStaticPaths()` to enumerate all combinations from `results.json`
- [x] 7.4 Update `pages/models/index.astro` to the grouped layout: provider sections → base model cards → level sub-cards, showing total_cost_usd
- [x] 7.5 Update `pages/index.astro`: wrap ModelSelector in right-aligned container (`max-w-xs ml-auto` on desktop, `w-full` on mobile)

## 8. Cleanup and Verification

- [x] 8.1 Remove `pages/models/[model].astro` (replaced by nested routes)
- [x] 8.2 Run `gitbench render` to regenerate `results.json` with new fields and verify JSON structure
- [x] 8.3 Run `npm run build` in `gitbench/web/` and verify all routes build without errors
- [x] 8.4 Manual smoke test: navigate `/`, `/models`, `/models/anthropic/claude-opus-4.7/`, `/models/anthropic/claude-opus-4.7/low/` and verify correct rendering

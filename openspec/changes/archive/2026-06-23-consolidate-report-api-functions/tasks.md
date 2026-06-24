## 1. Baseline Route Inventory

- [x] 1.1 Enumerate `gitbench/web/api/**/*.ts` and confirm the starting count is 18 route files
- [x] 1.2 Identify the current chart wrapper files, standalone history route, specific model-results route, and catch-all model-results route
- [x] 1.3 Add or update a focused API route-count test that will expect 11 route files after consolidation

## 2. Dynamic Chart Route

- [x] 2.1 Add one dynamic chart API route that accepts the chart name as a route parameter
- [x] 2.2 Validate chart names against the supported `ChartKey` values before calling `chartHandler`
- [x] 2.3 Preserve existing query handling for supported chart routes, including `benchmark` and campaign-aware metadata
- [x] 2.4 Add tests for supported chart dispatch and unsupported chart rejection
- [x] 2.5 Remove the six static chart wrapper route files after the dynamic route passes tests

## 3. History Consolidation

- [x] 3.1 Confirm no current UI component calls `loadHistory()` or `/api/history`
- [x] 3.2 Remove or migrate `loadHistory()` so run history access goes through `/api/summary` / `loadData()`
- [x] 3.3 Delete the standalone `api/history.ts` function
- [x] 3.4 Add or update tests confirming `/api/summary` includes `runs_meta` for history views

## 4. Model Results Route Consolidation

- [x] 4.1 Add tests that exercise `api/models/[...model]/results.ts` with a two-segment provider/model URL
- [x] 4.2 Verify the catch-all route preserves model-result filters (`benchmark`, `difficulty`, `tag`, `output_mode`, `campaign`)
- [x] 4.3 Delete `api/models/[provider]/[model]/results.ts`
- [x] 4.4 Smoke test a real encoded model-results URL under `vercel dev` after deleting the specific route

## 5. Verification

- [x] 5.1 Run `pnpm test:api` from `gitbench/web`
- [x] 5.2 Run `pnpm build` from `gitbench/web`
- [x] 5.3 Run `pnpm dev:api` or `vercel dev` and smoke test `/api/charts/pass-rate`, `/api/charts/not-a-chart`, `/api/summary`, and a representative `/api/models/{provider}/{model}/results` URL
- [x] 5.4 Confirm the final API route file count is 11
- [x] 5.5 Confirm overview, benchmark detail, history, and model comparison pages still load their data without visible UX regressions

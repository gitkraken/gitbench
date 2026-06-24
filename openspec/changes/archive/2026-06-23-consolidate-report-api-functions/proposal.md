## Why

The GitBench web app currently deploys one Vercel serverless function per `web/api/**/*.ts` file, and the report API surface is at 18 functions. Vercel capacity needs this reduced to 11 functions so there is room to add another endpoint later without degrading the existing report UX.

## What Changes

- Consolidate the six chart API wrapper files into one dynamic chart API route while preserving the existing `/api/charts/{chart}` request shape and compact per-chart payloads.
- Remove the standalone `/api/history` serverless function because the current UI already reads run history through `/api/summary` (`runs_meta`) via the shared `loadData()` path.
- Remove the duplicate two-segment model-results function and rely on the existing catch-all model-results route for `/api/models/{provider}/{model}/results` URLs.
- Keep current chart UX intact: charts still lazy-load independently, fetch only the data shape they need, and do not fall back to the full summary payload.
- Keep higher-risk campaign raw-attempt routes separate in this change because they carry distinct response shapes and publication-safety behavior.
- Add route/function-count checks so the web API stays at 11 Vercel functions after consolidation.
- **BREAKING**: Direct clients of the standalone `/api/history` endpoint must read `runs_meta` from `/api/summary` instead unless a compatibility rewrite is added during implementation.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `report-query-api`: The report API route contract changes from one function per query-shaped endpoint to a budget-aware layout that bundles chart endpoints and removes the standalone history function while preserving UI-required report data.

## Impact

- **`gitbench/web/api/charts/*.ts`**: Replace six static chart wrapper functions with one dynamic chart handler.
- **`gitbench/web/src/lib/chart-api.ts`**: Validate chart route parameters and dispatch to existing `chartData()` logic.
- **`gitbench/web/api/history.ts`**: Remove the dedicated history function, or fold its behavior into summary-compatible data access if compatibility is required.
- **`gitbench/web/api/models/[provider]/[model]/results.ts`**: Remove the duplicate specific route after verifying `api/models/[...model]/results.ts` serves the same two-segment URLs.
- **`gitbench/web/src/lib/report-client.ts`**: Remove or redirect `loadHistory()` so client code uses `loadData()` / `/api/summary` for `runs_meta`.
- **`gitbench/web/vercel.json`**: Update function matching only if needed for the consolidated route layout; keep `data/gitbench.db` included for all report API functions.
- **Tests**: Add coverage for chart route dispatch, invalid chart names, summary-provided history data, catch-all model-results routing, and the expected 11-function API file count.

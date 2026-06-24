## Context

The GitBench web app is an Astro static site deployed to Vercel with TypeScript API files under `gitbench/web/api`. `vercel.json` applies `includeFiles: "data/gitbench.db"` to `api/**/*.ts`, so each report API function can read the SQLite report database.

The current API surface contains 18 TypeScript route files. Vercel function capacity requires reducing this to 11 so one additional endpoint can be added later. The low-risk consolidation points are:

- Six chart files under `api/charts/*.ts` are thin wrappers around the same `chartHandler(req, res, chart)` helper.
- `api/history.ts` is not used by current UI call sites; history UI reads `runs_meta` from `/api/summary` through `loadData()`.
- `api/models/[provider]/[model]/results.ts` and `api/models/[...model]/results.ts` both delegate to the same model-results handler. The catch-all route should be able to serve the two-segment model URL after the specific route is removed.

## Goals / Non-Goals

**Goals:**

- Reduce the report API from 18 Vercel function files to 11.
- Preserve the existing chart URLs, query parameters, independent lazy-loading behavior, and compact payloads.
- Preserve existing model-results URLs by serving them through the catch-all route.
- Keep campaign raw-attempt and exact-attempt endpoints separate because they enforce publication-safety and bounded-query behavior.
- Add tests that make the function budget and consolidated route behavior explicit.

**Non-Goals:**

- Redesigning the report API around one generic endpoint.
- Replacing chart-specific payloads with `/api/summary` responses.
- Bundling campaign raw-attempt endpoints into a multipurpose dispatcher.
- Changing the SQLite report-store contract or database schema.
- Adding a new user-visible feature.

## Decisions

### Decision 1: Use one dynamic chart route

Create a single dynamic route such as `api/charts/[chart].ts` and remove the six wrapper files for `cost`, `heatmap`, `pass-rate`, `quadrant`, `runtime`, and `tokens`.

The dynamic handler validates the route parameter against the existing `ChartKey` set and calls `chartHandler(req, res, chart)`. This preserves `/api/charts/pass-rate`, `/api/charts/cost`, and the other current URLs while reducing six functions to one.

**Alternative considered:** Make chart components call `/api/summary` and compute chart data client-side. That would reduce function count but harm UX and bandwidth because chart payloads are intentionally compact.

### Decision 2: Remove the standalone history function

Remove `api/history.ts` as a Vercel function and make `/api/summary.runs_meta` the supported history API source. Current UI code already follows this path: `TimeSeriesChart` calls `loadData()`, which loads `/api/summary`, then reads `runs_meta`.

`loadHistory()` in `report-client.ts` should be removed if unused, or changed to read summary-compatible data without requiring a dedicated function.

**Alternative considered:** Preserve `/api/history` with a Vercel rewrite to `/api/summary`. That avoids breaking direct API callers but adds route complexity and still needs response-shape handling. The default design treats `/api/history` as internal and migrates clients to `/api/summary`.

### Decision 3: Keep one model-results route

Remove `api/models/[provider]/[model]/results.ts` and rely on `api/models/[...model]/results.ts`. The catch-all route already reconstructs the model name from route segments and supports the same filters as the specific route.

Implementation must verify with `vercel dev` that URLs like `/api/models/anthropic/claude-opus-4.7%3Ahigh/results` still route to the catch-all handler after the specific file is removed.

**Alternative considered:** Keep both model route files and find another endpoint to remove. The next candidates either affect currently used fixture/campaign data or require broader dispatch logic, so the duplicate model route is the lower-risk seventh function to save.

### Decision 4: Do not bundle campaign raw-attempt endpoints

Campaign list, campaign detail, raw-attempt listing, and exact-attempt lookup have different response shapes and publication-safety rules. Keeping them separate avoids mixing public-content gating with unrelated route consolidation.

**Alternative considered:** Use one catch-all campaign dispatcher. That would save functions, but the branchy handler would be easier to regress and is unnecessary once charts, history, and duplicate model-results routes are consolidated.

### Decision 5: Add a function-budget test

Add a focused test that enumerates `gitbench/web/api/**/*.ts` and asserts the expected count is 11 after consolidation. Pair this with handler-level tests for dynamic chart dispatch and model catch-all routing so the count reduction is not achieved by silently removing required behavior.

**Alternative considered:** Rely on manual inspection before deployment. That is too easy to miss when adding new endpoints later.

## Risks / Trade-offs

- **[Catch-all route mismatch]** Vercel may not route the two-segment model URL to `[...model]` exactly as expected after the specific route is removed. -> Mitigation: verify with `vercel dev` against a real encoded model URL and keep a route-level test for the catch-all handler.
- **[External `/api/history` consumers]** Direct clients outside the current UI may rely on `/api/history`. -> Mitigation: document `/api/summary.runs_meta` as the migration path; add a compatibility rewrite only if an external consumer is identified.
- **[Invalid chart names]** A dynamic chart route can receive unsupported names that static files previously rejected by absence. -> Mitigation: validate chart names and return a clear 404 or 400 response without executing report queries.
- **[Function count differs from file count]** Vercel could count generated functions differently from local file enumeration. -> Mitigation: use the file-count test as a fast guard and verify the deployed/dev route map during implementation.
- **[Over-consolidation pressure]** Future endpoint additions may repeat the same problem. -> Mitigation: the function-budget test forces future work to make consolidation trade-offs explicit.

## Migration Plan

1. Add the dynamic chart route and tests while the existing static chart files still define the desired behavior.
2. Remove the six static chart wrapper files after dynamic chart tests pass.
3. Remove or migrate `loadHistory()` and delete `api/history.ts`; confirm current history UI still reads `runs_meta` through `/api/summary`.
4. Remove `api/models/[provider]/[model]/results.ts`; verify the catch-all model route serves two-segment model URLs.
5. Run `pnpm test:api`, `pnpm build`, and a `vercel dev` smoke test for representative consolidated endpoints.
6. Roll back by restoring the removed route files if any consolidated route fails in production.

## Open Questions

None blocking. The only policy choice is whether to add a compatibility rewrite for `/api/history`; the default is no rewrite unless a known external client requires it.

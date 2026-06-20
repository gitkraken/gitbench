## Context

The GitBench web app is an Astro static site (`output: "static"`) deployed to Vercel. Chart components are React islands that hydrate on the client and fetch data from Vercel serverless API endpoints (`/api/charts/*`). The API endpoints read from a SQLite database (`data/gitbench.db`) built from `public/results.json` via `scripts/build-db.mjs`.

The overview page (`index.astro`) renders six chart sections. The first chart, `PassRateBarChart`, uses `client:load` (hydrates immediately) but shows "Loading..." while waiting for a `fetch("/api/charts/pass-rate")` roundtrip. This creates a visible loading waterfall for the most prominent chart on the page.

The chart data (pass rates, costs, runtimes) is campaign-independent. It comes from aggregate tables (`model_summaries`, `benchmark_summaries`) that have no `campaign_id` column. The campaign system is a metadata overlay that adds trial counts to tooltips but does not change chart bars. This means data embedded at build time is always correct regardless of campaign selection.

Two data access paths exist in the codebase:
1. `loadDataSync()` reads `public/results.json` directly (used by Astro pages at build time for sidebar, model lists, etc.)
2. `getReportStore()` reads `data/gitbench.db` (used by API endpoints at runtime)

Both ultimately derive from the same `results.json` source. However, they are separate code paths with independent transformations. Using `getReportStore()` at build time for the embedded data guarantees identical output to the API endpoints, since it is literally the same function call.

## Goals / Non-Goals

**Goals:**
- Eliminate the loading waterfall for the overview page's first chart (PassRateBarChart)
- Use the same data source (`getReportStore()`) as the API endpoints to guarantee identical data
- Establish a pattern that can be extended to other charts in the future
- Keep the change small and targeted (first chart only)

**Non-Goals:**
- Embedding data for all overview charts (only PassRateBarChart in this change)
- Changing the API endpoints or the report store
- Changing the `client:load` hydration directive
- Embedding campaign metadata in the static render
- Migrating existing `loadDataSync()` consumers to `getReportStore()`

## Decisions

### Decision 1: Use `getReportStore()` at build time, not `loadDataSync()`

**Choice:** The Astro frontmatter in `index.astro` calls `getReportStore().getSummary()` and `chartData("pass-rate", summary)` to compute the embedded data.

**Rationale:** The API endpoints use the exact same `getReportStore().getSummary()` call. By using the same store at build time, the embedded data is guaranteed identical to what the API would return, by construction. No format drift risk.

**Alternative considered:** Use `loadDataSync()` (reads `public/results.json` directly). This avoids a DB dependency at build time, but creates a shadow reader that must be kept in sync with the store's transformations independently. If the store's `getSummary()` logic or `build-db.mjs` transformations change, the two paths could silently diverge.

### Decision 2: Pass data via Astro props (`initialData`), not inline `<script>` tags or window globals

**Choice:** `<PassRateBarChart client:load initialData={passRateData} />`

**Rationale:** Astro automatically serializes props into the `astro-island` element's `props` attribute and deserializes them during hydration. This is the natural React pattern and requires no manual DOM querying or global namespace pollution.

**Alternatives considered:**
- Inline `<script type="application/json" data-chart="pass-rate">` tag read via `document.querySelector`. Works but requires manual DOM querying and cleanup.
- `window.__INITIAL_DATA__` global set via `is:inline` script. Fast but pollutes global namespace.

### Decision 3: Skip the API fetch when `initialData` is present and no campaign override is active

**Choice:** In `useEffect`, guard with `if (initialData && !campaignId) return;` before the fetch call.

**Rationale:** The chart data (pass rates, costs) is campaign-independent. The only reason to fetch when `initialData` is present would be to get campaign metadata for the tooltip. Since we are omitting campaign metadata and the chart bars are identical regardless of campaign, there is no reason to fetch in the default (no campaign) case. When a campaign IS specified via URL param, the component falls back to the API to get the campaign metadata overlay.

### Decision 4: Chain `build:db` before `astro build`

**Choice:** Update `package.json` `"build"` script to `"node scripts/build-db.mjs && astro build"`.

**Rationale:** Using `getReportStore()` at build time requires `data/gitbench.db` to be present and current. Chaining the DB rebuild before the Astro build guarantees freshness. The DB already exists in the repo, so there is no first-run problem. The store opens the DB `readOnly: true`, so the build process cannot accidentally mutate it.

### Decision 5: Omit campaign metadata from the embedded payload

**Choice:** The embedded `initialData` does not include `campaign_id` or `campaign_metadata` fields.

**Rationale:** The chart bars are campaign-independent. The campaign metadata is only used for an optional tooltip info line showing trial counts. Omitting it means the tooltip simply does not render that line (the code already handles this with a conditional `{data.campaign_metadata && ...}`). This keeps the embedded payload smaller and avoids needing to resolve the default campaign at build time.

## Risks / Trade-offs

- **[Build order dependency]** `astro build` now requires `data/gitbench.db` to exist and be fresh. If someone runs `astro build` directly without `build:db`, the embedded data could be stale. → Mitigation: The chained `build` script handles this automatically. Developers running `astro dev` or `astro build` directly should run `pnpm build:db` first, same as they already do for local API development.

- **[HTML payload growth]** The overview page's `index.html` grows by approximately 15 KB (from ~16 KB to ~31 KB). → Mitigation: This is negligible for a modern web page. The data is chart-specific (models, base_model_groups, minimal model_summaries), not the full 636 KB report.

- **[Stale embedded data on DB update]** If the DB is updated after a build without rebuilding the site, the API returns fresh data while the embedded data is stale. → Mitigation: The deployment workflow rebuilds both DB and site together via the chained build script. If the DB changes, a new build is needed anyway.

- **[Astro prop serialization limits]** Astro serializes props as JSON in an HTML attribute. Very large props could hit HTML attribute size limits or parser issues. → Mitigation: The pass-rate chart data is ~15 KB, well within safe limits. If future charts have larger payloads, this approach may need reconsideration.

- **[Two data readers remain]** `loadDataSync()` still exists for sidebar, model lists, and other Astro pages. This change does not unify all data access. → Mitigation: Those pages serve different purposes (static navigation, fixture listings) and the round-trip risk is lower. Unifying them is a separate concern.
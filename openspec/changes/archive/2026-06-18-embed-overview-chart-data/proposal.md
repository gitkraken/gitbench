## Why

The overview page's first chart (PassRateBarChart) hydrates immediately via `client:load` but shows "Loading..." while waiting for a client-side API fetch to `/api/charts/pass-rate`. This creates a waterfall: HTML download, JS hydration, network request, serverless cold start, SQLite query, response parsing, React re-render. For the most important chart on the page, users see a blank placeholder for hundreds of milliseconds. The data needed for this chart is already available at build time via the same `getReportStore()` the API uses, so embedding it in the static render eliminates the fetch entirely.

## What Changes

- Pass pass-rate chart data as an Astro prop (`initialData`) to `PassRateBarChart` on the overview page, computed at build time from `getReportStore().getSummary()` via the existing `chartData("pass-rate", ...)` function.
- `PassRateBarChart` accepts an optional `initialData` prop, uses it as initial state, and skips the API fetch when `initialData` is present and no campaign override is active.
- Chain `build:db` before `astro build` in the `build` npm script so the SQLite database is guaranteed fresh when Astro reads it at build time.
- Omit campaign metadata from the embedded payload. The chart bars (pass rates, costs) are campaign-independent, so the embedded data is always correct regardless of campaign selection. The tooltip's optional campaign info line simply does not render when metadata is absent.

## Capabilities

### New Capabilities

- `embedded-chart-data`: Build-time embedding of chart-specific data into Astro page renders via component props, allowing React island chart components to hydrate with data already available instead of fetching on mount.

### Modified Capabilities

- `astro-site`: The existing requirement that "React islands SHALL load query-specific report data through the report API client" is modified to allow the overview page's first chart to receive initial data via props at build time. This is a targeted exception for the pass-rate chart on the overview page, not a general replacement for API-based data loading. Other charts and other pages continue to fetch from the report API client.
- `chart-components`: The PassRateBarChart component gains an optional `initialData` prop. When present and no campaign override is active, the component skips its `useEffect` fetch and renders immediately from the embedded data. The chart's rendering logic, sorting, coloring, and tooltip behavior remain unchanged.

## Impact

- **`gitbench/web/src/pages/index.astro`**: Add frontmatter code to compute pass-rate chart data from `getReportStore()` and pass it as `initialData` prop to `<PassRateBarChart>`.
- **`gitbench/web/src/components/charts/PassRateBarChart.tsx`**: Add `initialData` prop to the component interface, use it as initial `useState` value, and add a guard in `useEffect` to skip the fetch when `initialData` is present and no campaign is selected.
- **`gitbench/web/package.json`**: Chain `build:db` before `astro build` in the `build` script to ensure the SQLite database is fresh at build time.
- **HTML payload**: The overview page's `index.html` grows by approximately 15 KB (from ~16 KB to ~31 KB) due to the serialized chart data in the `astro-island` props attribute. This is acceptable for a modern web page.
- **Build dependency**: `astro build` now depends on `data/gitbench.db` being present and current. This is enforced by the chained build script.
- **No runtime/API changes**: The API endpoints remain unchanged. The embedded data uses the exact same `getReportStore().getSummary()` and `chartData("pass-rate", ...)` code path as the API, guaranteeing identical data.
- **Pattern for future**: The approach (build-time `getReportStore()` + `chartData()` + `initialData` prop) can be extended to other overview charts if desired, but this change scopes to the first chart only.
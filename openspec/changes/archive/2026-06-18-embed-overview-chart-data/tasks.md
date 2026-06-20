## 1. Build Pipeline

- [x] 1.1 Update `package.json` `build` script to chain `build:db` before `astro build` (e.g., `"build": "node scripts/build-db.mjs && astro build"`)
- [x] 1.2 Verify `pnpm build` runs `build-db.mjs` then `astro build` successfully with no errors
- [x] 1.3 Verify the build fails gracefully if `build-db.mjs` fails (astro build does not run)

## 2. PassRateBarChart Component

- [x] 2.1 Add `initialData?: GitBenchData` to `PassRateBarChartProps` interface
- [x] 2.2 Initialize `useState` with `initialData ?? null` instead of `null`
- [x] 2.3 Add guard in `useEffect` to skip the `loadPassRateChart` fetch when `initialData` is present and `campaignId` is null
- [x] 2.4 Verify the component renders immediately from `initialData` without showing "Loading..." when `initialData` is provided and no campaign is selected
- [x] 2.5 Verify the component still fetches from the API when `initialData` is absent (benchmark detail pages)
- [x] 2.6 Verify the component fetches from the API when a `?campaign=` query param is present even if `initialData` is provided

## 3. Overview Page

- [x] 3.1 Add imports for `getReportStore` and `chartData` to `index.astro` frontmatter
- [x] 3.2 Compute `passRateData` via `chartData("pass-rate", getReportStore().getSummary())` in the frontmatter
- [x] 3.3 Pass `initialData={passRateData}` prop to `<PassRateBarChart client:load />`
- [x] 3.4 Verify the built `dist/index.html` contains serialized pass-rate data in the PassRateBarChart `astro-island` props attribute
- [x] 3.5 Verify the built `dist/index.html` does not contain "Loading..." as the initial render for PassRateBarChart (it should still be there as SSR fallback, but React hydrates with data immediately)

## 4. Validation

- [x] 4.1 Run `pnpm build` and verify the overview page builds without errors
- [x] 4.2 Inspect the built `dist/index.html` size to confirm it grew by approximately 15 KB (from ~16 KB to ~31 KB)
- [x] 4.3 Serve the built site locally and verify PassRateBarChart renders immediately on page load without a visible "Loading..." state
- [x] 4.4 Verify other overview charts (Quadrant, Cost, Runtime, Tokens, Heatmap) still fetch from the API and render normally
- [x] 4.5 Navigate to `/?campaign=<existing-campaign-id>` and verify PassRateBarChart fetches from the API and renders with campaign metadata in the tooltip
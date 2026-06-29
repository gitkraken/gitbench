## 1. URL State Codec

- [x] 1.1 Add `fflate` to `gitbench/web/package.json` and update the lockfile.
- [x] 1.2 Create `src/lib/report-url-state.ts` with typed view-state models for selected groups, output mode, selection kind, source, and codec errors.
- [x] 1.3 Implement base64url encode/decode helpers for compressed byte transport.
- [x] 1.4 Implement `fflate` deflate/inflate encoding for `s=gb1.<payload>` compressed state.
- [x] 1.5 Implement readable include/exclude/all query parsing for `m`, `model`, `x`, `exclude`, `models=all`, and `mode`.
- [x] 1.6 Implement legacy `with` parsing that maps model effort names to provider/base-model groups.
- [x] 1.7 Implement state resolution against current model groups, including unknown-ID sanitization and unavailable-mode fallback.
- [x] 1.8 Implement encoder selection of include vs exclude vs all, omission of default `both` mode, and shortest-safe readable vs compressed output.

## 2. Codec Tests

- [x] 2.1 Add unit tests for compressed round trips with include, exclude, all, and omitted default output mode.
- [x] 2.2 Add unit tests proving raw JSON is not base64-encoded without compression.
- [x] 2.3 Add unit tests for unknown group IDs, corrupt compressed payloads, unsupported codec prefixes, and invalid output modes falling back to defaults.
- [x] 2.4 Add unit tests for include/exclude minimization with small subsets, mostly-all subsets, and all-selected state.
- [x] 2.5 Add unit tests for legacy `?with=` resolving model effort names to group IDs.

## 3. Shared Selection Hook

- [x] 3.1 Refactor `useSyncedModelSelection` to initialize selected groups and output mode from resolved report URL state instead of localStorage.
- [x] 3.2 Add page-default inputs so overview and benchmark pages default to all groups while Compare can default to the top two groups.
- [x] 3.3 Update selection and output-mode setters to write report URL state with `history.replaceState`.
- [x] 3.4 Keep same-page custom event synchronization and add `popstate` handling so browser back/forward updates chart islands.
- [x] 3.5 Prevent event/history loops by comparing canonical encoded state before writing or dispatching.

## 4. Selector and Output Controls

- [x] 4.1 Update `ModelSelector` so report/chart usage no longer reads or writes `gitbench-model-selection`.
- [x] 4.2 Keep `initialSelected`, controlled `value`, search, bulk actions, and group sanitization behavior intact.
- [x] 4.3 Update `OutputModeSelector` consumers so output mode changes flow through URL state and default to `both` when available.
- [x] 4.4 Remove `gitbench-output-mode` as the source of truth for report/chart pages while leaving old keys untouched.

## 5. Report Pages and Links

- [x] 5.1 Update Compare page initialization to use URL state, default to top-two groups with `both` mode, and support legacy `?with=`.
- [x] 5.2 Update model detail Compare buttons to generate report URL state instead of only `?with=`.
- [x] 5.3 Update Overview heatmap benchmark drilldown links to preserve current report view state.
- [x] 5.4 Update Benchmark Detail chart/table islands to consume URL-backed selection and default to all groups plus `both` mode.
- [x] 5.5 Update model level drill-down output-mode toggle to read/write URL state and default to Both when both variants exist.
- [x] 5.6 Keep sidebar, Models, Explore, Methodology, and other ordinary navigation links bare so they reset to page defaults.

## 6. Compatibility and Cleanup

- [x] 6.1 Ensure invalid or stale URL state never throws during initial render and falls back to page defaults.
- [x] 6.2 Ensure old localStorage values do not affect bare report/chart URLs.
- [x] 6.3 Remove duplicated selection-storage helpers that become unused after URL-state migration.
- [x] 6.4 Update any affected TypeScript types and imports.

## 7. Verification

- [x] 7.1 Run `pnpm test:api` from `gitbench/web`.
- [x] 7.2 Run `pnpm build` from `gitbench/web`.
- [x] 7.3 Manually verify bare Overview, Benchmark Detail, Compare, and model drill-down pages default to `both` mode where available.
- [x] 7.4 Manually verify copied compressed URLs restore selected model groups and output mode in a fresh browser context.
- [x] 7.5 Manually verify ordinary sidebar navigation resets view state while Overview heatmap benchmark drilldowns preserve it.

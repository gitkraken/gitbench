## Why

Model and output-mode selections are currently private browser state, so shared report URLs do not reproduce the exact view and returning users can land on stale selections as new benchmarked models are added. GitBench needs shareable chart and comparison views while keeping bare URLs fresh against the current report data.

## What Changes

- Move report model selection from `localStorage` persistence to URL-owned view state.
- Move report output-mode selection to the same URL-owned view state and make `both` the default mode when no valid mode is present.
- Add a versioned browser-side URL state codec that can represent selected model groups, excluded model groups, all groups, and output mode.
- Add compressed URL state using `fflate` deflate/inflate in the browser with a base64url transport prefix such as `s=gb1.<payload>`.
- Keep short, readable URL encodings available for small states, but use compressed state when it is shorter or when an uncompressed URL would cross the configured length threshold.
- Preserve same-page selector synchronization across React islands via custom events, with the URL as the source of truth instead of `localStorage`.
- Reset model/output-mode state on ordinary top-level navigation by leaving sidebar links bare; preserve state only on analytical drilldowns where the destination has the same comparative context.
- Keep `/compare?with=<model>` as a backward-compatible alias that initializes compare selection, then normalizes to the new URL state.
- Treat unknown model IDs, invalid compressed payloads, unsupported versions, and unavailable output modes as recoverable input that falls back to the page default without crashing.

## Capabilities

### New Capabilities

- `report-url-state`: Versioned URL view-state encoding, browser-side compression/decompression, decode fallback behavior, and link-state preservation rules.

### Modified Capabilities

- `searchable-model-selector`: Replace `localStorage` model/output-mode persistence requirements with URL-backed state while keeping searchable group selection and same-page synchronization.
- `chart-components`: Update report chart defaults and shared-selection behavior so charts consume URL-backed model selection and default to `both` output mode.
- `report-pages`: Update Overview, Benchmark Detail, Compare, and model drill-down route behavior for URL-backed view state, backward-compatible Compare links, and selective query preservation.

## Impact

- **Dependencies**: add `fflate` to the web package for deterministic browser-side deflate/inflate.
- **Web utilities**: add a focused URL state codec module for encode/decode, base64url transport, include/exclude selection minimization, output-mode resolution, and history updates.
- **React islands**: update `useSyncedModelSelection`, `ModelSelector`, output-mode controls, Compare page state initialization, and chart/table consumers to read and write URL state.
- **Astro pages and links**: update analytical drilldown links to preserve view state where useful while keeping ordinary navigation links bare.
- **Compatibility**: support existing `?with=` Compare links; remove `gitbench-model-selection` and `gitbench-output-mode` as sources of truth for report/chart pages.
- **Tests**: add unit coverage for URL-state codec round trips, compressed payload handling, invalid-state fallback, include/exclude minimization, default `both` behavior, and selected page/link state behavior.

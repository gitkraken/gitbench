## Why

The current report UI exposes "campaign" as a global user-facing selector, which leaks internal evaluation terminology and produces confusing empty states such as "No campaigns" even when benchmark data exists. Most readers should simply see the latest evaluation data; campaign identity only needs to be visible where historical comparison or raw evidence requires it.

## What Changes

- Remove the global campaign selector from ordinary report navigation and page headers.
- Default campaign-aware pages, charts, and API-backed views to the latest appropriate evaluation campaign without requiring user selection.
- Treat campaign records as history nodes on the History page, where they represent versioned evaluation runs over time.
- Keep `campaign_id`, campaign storage, raw attempts, compatibility checks, and campaign query parameters available for internal/debug/raw-evidence use.
- Replace ordinary user-facing "campaign" language outside History, Methodology, and evidence/debug contexts with clearer terms such as "evaluation run" or "latest evaluation".
- Hide campaign empty states from ordinary pages when no campaign records exist and benchmark summary data is still available.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `evaluation-campaign-reporting`: Change the user-facing campaign surface from a global selector to implicit latest-evaluation selection, while retaining campaign nodes in History and internal raw-evidence flows.
- `report-pages`: Update page-level reporting behavior so ordinary pages do not render campaign controls or empty campaign states, and History presents evaluation campaign records as the comparison timeline.
- `report-query-api`: Clarify default campaign resolution for API-backed report data and preserve explicit campaign lookup/query support for internal and deep-link use.
- `astro-site`: Update the layout and embedded/default chart behavior so ordinary pages use the latest evaluation data without a visible selector.
- `methodology-page`: Align public terminology by explaining the concept as evaluation runs/trial rounds while reserving "campaign" for precise methodology or internal identity where necessary.

## Impact

- Affected frontend components include the shared layout/header, campaign selector/status components, history page, campaign history table, chart islands, and chart/data-loading helpers under `gitbench/web/src`.
- Affected API/store behavior includes default campaign resolution, chart endpoints, summary/model/benchmark/fixture queries, and explicit `campaign` query handling under `gitbench/web/api` and `gitbench/web/src/lib`.
- Affected report generation/data paths include the distinction between legacy aggregate summary data and campaign-aware SQLite rows.
- Tests should cover hidden campaign controls, default latest-campaign selection, History campaign nodes, and no-campaign fallback behavior.

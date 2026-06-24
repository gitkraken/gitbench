## Context

Campaigns are the internal unit for repeated GitBench evaluations: a fixed configuration, trial schedule, raw attempts, aggregates, publication state, and compatibility identity. The web app currently exposes this internal unit through a global `CampaignSelector` in `Layout.astro`. When the loaded report database has normal benchmark summary rows but no campaign rows, the header renders "No campaigns", which is technically accurate but confusing to readers.

The product direction is to keep campaign identity mostly internal. Ordinary report pages should show the latest evaluation data by default. History should be the primary user-facing place where campaign records appear, because there they represent evaluation nodes over time.

Current implementation constraints:

- API routes and chart clients already accept an optional `campaign` query parameter.
- `NodeSqliteReportStore.getDefaultCampaign()` already ranks candidate campaigns.
- `gitbench report` uses the Python SQLite writer, which persists campaign rows.
- `gitbench/web/scripts/build-db.mjs` rebuilds the web database from `results.json`, but does not currently insert `campaigns` data even when present.
- The Overview pass-rate chart can receive build-time initial data, so default campaign semantics must not diverge between embedded chart data and API-loaded chart data.

## Goals / Non-Goals

**Goals:**

- Remove user-facing campaign selection from ordinary page headers and report pages.
- Default chart, summary, model, benchmark, and fixture data to the latest reportable evaluation campaign when campaign data exists.
- Keep explicit campaign lookup and `campaign` query support for internal links, History drilldowns, raw attempt inspection, and debugging.
- Show campaign records as History nodes, with trial counts, status, comparability, and deltas where meaningful.
- Avoid "No campaigns" empty states on ordinary pages when fallback benchmark summary data exists.
- Align public wording around "evaluation run", "latest evaluation", and "trial rounds", while preserving campaign terminology in precise methodology and internal evidence contexts.

**Non-Goals:**

- Removing campaign tables, campaign IDs, raw-attempt APIs, or campaign query parameters.
- Redesigning campaign execution, scheduling, scoring, safety review, or persistence.
- Adding a new end-user workflow for selecting historical datasets outside History.
- Changing model output mode selection, model selection, or benchmark filters.

## Decisions

1. Ordinary pages will not render a campaign selector.

   The shared layout should remove `CampaignSelector` from the header. Page components should not replace it with local campaign controls. If no campaign rows exist, ordinary pages should render the existing aggregate report data without mentioning campaigns.

   Alternative considered: keep the selector but rename it to "Evaluation run". That still exposes an advanced choice most readers do not need and leaves empty selector states on reports without campaign rows.

2. Default campaign resolution remains server/store-owned.

   API-backed views should continue to resolve campaign context through the report-store layer. The default should prefer the latest complete, publishable, non-legacy campaign for public rankings and charts. Explicit `campaign` query parameters should still select compatible campaign data for internal links and History drilldowns.

   Alternative considered: resolve the latest campaign in each React component. That would duplicate ranking rules and make chart behavior drift.

3. History owns the public campaign timeline.

   The History page should present campaign records as evaluation nodes when campaigns exist. It should retain a legacy run-history fallback for reports that only contain single-run aggregate data. Campaign terminology is acceptable on History because the page is explicitly about versioned evaluation records.

   Alternative considered: hide campaign terminology everywhere. That would make campaign-level deltas, compatibility, and raw evidence harder to explain.

4. Embedded chart data must match API default semantics.

   If the Overview pass-rate chart receives build-time initial data, that initial payload must be computed from the same default campaign as the chart API would return. If no campaign rows exist, it can use aggregate summary data as a compatibility fallback. The page must not show stale aggregate summary data while other charts fetch latest campaign data.

   Alternative considered: remove all embedded chart data. That is simpler but gives up the existing fast first render for the Overview pass-rate chart.

5. The two SQLite writers must agree on campaign rows.

   The Python report writer already inserts campaign data. The JavaScript `build-db.mjs` path should either insert campaign data from `results.json` as well or stop being used as the authoritative build path for campaign-aware reports. Keeping both paths but only one campaign-aware creates hard-to-debug empty campaign states.

   Alternative considered: hide the selector only. That would improve the homepage but leave campaign-aware defaults unreliable when the JS build path is used.

## Risks / Trade-offs

- Hidden campaign selection can make manual comparison less discoverable -> keep History campaign nodes, explicit links, and query support for internal comparisons.
- Defaulting to latest publishable data can surprise developers inspecting an incomplete run -> History should show incomplete runs clearly, and explicit campaign links should still inspect them.
- Reports with zero campaign rows still need to work -> ordinary pages fall back to aggregate summary data and avoid campaign-specific empty states.
- Python and JavaScript database writers may drift -> add tests around campaign insertion/default resolution for both supported build paths or narrow the supported path.
- Terminology cleanup can become broad copy churn -> limit wording changes to user-facing campaign mentions outside History, Methodology, and raw evidence/debug views.

## Migration Plan

1. Remove global campaign UI from the shared layout and ordinary pages.
2. Centralize default campaign-aware data loading so API and embedded Overview data agree.
3. Update History to present campaign records as evaluation nodes and retain legacy run fallback.
4. Reconcile campaign insertion in `build-db.mjs` with the Python writer or document the Python writer as authoritative for campaign-aware builds.
5. Update public copy and tests.
6. Rollback is straightforward: reintroduce `CampaignSelector` in `Layout.astro` and restore component-level selector behavior, without changing stored campaign data.

## Open Questions

- Should explicit `?campaign=` links be considered public permalinks or internal/debug-only links? The proposal preserves them either way.
- Should the default fallback prefer the latest complete publishable campaign only, or the latest campaign of any state when no publishable campaign exists? The design prefers publishable data for ordinary pages and leaves incomplete campaign visibility to History.

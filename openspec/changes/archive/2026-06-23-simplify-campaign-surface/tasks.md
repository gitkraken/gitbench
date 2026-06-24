## 1. Remove Ordinary Campaign UI

- [x] 1.1 Remove `CampaignSelector` from the shared layout/header so ordinary pages no longer show a campaign control.
- [x] 1.2 Remove or gate ordinary-page campaign status/empty-state rendering so "No campaigns" is never shown when aggregate report data exists.
- [x] 1.3 Audit ordinary report pages and chart components for user-facing "campaign" copy and replace it with "evaluation run", "latest evaluation", or more specific wording where appropriate.
- [x] 1.4 Keep campaign ID display available in raw evidence/debug contexts where it is part of attempt identity.

## 2. Default Latest Evaluation Data

- [x] 2.1 Centralize default campaign resolution through the report-store/API layer, preferring the latest complete publishable non-legacy campaign.
- [x] 2.2 Ensure summary, chart, model, benchmark, fixture, and comparison API calls use the default campaign when no explicit campaign ID is supplied.
- [x] 2.3 Preserve explicit `campaign` query support for compatible History drilldowns, raw-attempt inspection, and debug links.
- [x] 2.4 Make Overview `PassRateBarChart` initial data match the same default latest-evaluation semantics as the chart API when campaign rows exist.
- [x] 2.5 Preserve aggregate-summary fallback behavior for reports with no campaign rows.

## 3. History Campaign Timeline

- [x] 3.1 Update History to present campaign records as evaluation timeline nodes when campaign data exists.
- [x] 3.2 Show campaign identity, date, status, trial counts, mean success, valid attempts, and compatible deltas in History rows.
- [x] 3.3 Keep or adapt the existing run-history/time-series behavior as a fallback for reports without campaign records.
- [x] 3.4 Ensure incomplete, legacy, and incompatible campaign states are visible in History without affecting ordinary page defaults.

## 4. Report Data Generation

- [x] 4.1 Reconcile the JavaScript `build-db.mjs` path with the Python SQLite writer so campaign rows from `results.json` are inserted when present, or document the Python writer as authoritative for campaign-aware builds.
- [x] 4.2 Add coverage that a report database with campaign data exposes default campaign metadata through the store.
- [x] 4.3 Add coverage that a report database with no campaign rows still serves aggregate model and benchmark summaries.

## 5. Tests and Verification

- [x] 5.1 Update or add component/API tests proving ordinary pages do not render `CampaignSelector` or "No campaigns".
- [x] 5.2 Add API/store tests for default latest campaign selection, explicit compatible campaign selection, and incompatible campaign handling.
- [x] 5.3 Add History tests for campaign timeline rows and legacy run-history fallback.
- [x] 5.4 Run the web API test suite with `pnpm test:api`.
- [x] 5.5 Build the web app with `pnpm build` and verify the generated pages do not expose campaign selector UI.

## MODIFIED Requirements

### Requirement: results.json served as static asset
The aggregated benchmark data MAY be written to `ui/public/results.json` by the Python CLI as a compatibility artifact. The Astro site SHALL NOT embed the full report data in page HTML. React islands SHALL load query-specific report data through the report API client instead of fetching the full `/results.json` payload. The overview page's first chart (PassRateBarChart) is an exception: it MAY receive chart-specific data via an `initialData` prop computed at build time from `getReportStore()`, bypassing the report API client for the default (no campaign) view. This exception is limited to the pass-rate chart on the overview page. All other charts and pages SHALL continue to load data through the report API client.

#### Scenario: results.json is accessible when emitted
- **WHEN** the built site is served and compatibility JSON was emitted during report generation
- **THEN** `GET /results.json` returns the aggregated benchmark data as JSON

#### Scenario: results.json is gitignored
- **WHEN** checking the gitignore
- **THEN** `ui/public/results.json` and `ui/dist/` are listed

#### Scenario: React islands do not fetch full report payload
- **WHEN** a hydrated React chart or interactive table loads in the browser
- **THEN** it requests only the query-specific API payload needed for that view
- **AND** it does not fetch `/results.json` as the canonical report data source

#### Scenario: Overview pass-rate chart uses embedded data
- **WHEN** the overview page loads with no `?campaign=` query parameter
- **THEN** the PassRateBarChart renders immediately from embedded `initialData` without an API fetch

#### Scenario: Other overview charts still fetch from API
- **WHEN** the overview page loads
- **THEN** all charts other than PassRateBarChart fetch their data from the report API client as before

#### Scenario: Campaign override triggers API fetch
- **WHEN** the overview page loads with a `?campaign=<id>` query parameter
- **THEN** PassRateBarChart falls back to fetching from `/api/charts/pass-rate?campaign=<id>` to obtain campaign metadata
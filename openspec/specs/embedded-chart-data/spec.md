## Purpose

Embedded chart data lets the overview page render its first chart immediately while preserving query-specific API loading for campaign overrides and other charts.

## Requirements

### Requirement: Overview first chart receives build-time embedded data

The overview page (`index.astro`) SHALL compute pass-rate chart data at build time using `getReportStore().getSummary()` and `chartData("pass-rate", summary)` from the same report store used by API endpoints. The computed data SHALL be passed as an `initialData` prop to the `PassRateBarChart` React island. The embedded data SHALL NOT include campaign metadata.

#### Scenario: Embedded data matches API output

- **WHEN** the build process runs `getReportStore().getSummary()` and `chartData("pass-rate", summary)` for the overview page
- **THEN** the resulting data is identical to what `GET /api/charts/pass-rate` would return (excluding `campaign_id` and `campaign_metadata` fields)

#### Scenario: Embedded data includes model summaries and groups

- **WHEN** the overview page is built
- **THEN** the `initialData` prop contains `models`, `base_model_groups`, and `model_summaries` (with `pass_at_k` and `total_cost_usd` fields per model)
- **AND** it does not contain `campaign_id` or `campaign_metadata`

#### Scenario: HTML payload includes serialized chart data

- **WHEN** inspecting the built `dist/index.html`
- **THEN** the `astro-island` element for PassRateBarChart contains serialized `initialData` in its `props` attribute

### Requirement: Build script chains database rebuild before Astro build

The top-level `web/package.json` `build` script SHALL chain `build:db` before `astro build` so that `web/data/gitbench.db` is guaranteed fresh with `web/public/results.json` when Astro reads it at build time for embedded data computation.

#### Scenario: Build rebuilds database first

- **WHEN** `npm run build` or `pnpm build` is executed from `web/`
- **THEN** `build-db.mjs` runs first to rebuild `data/gitbench.db` from `public/results.json`
- **AND** `astro build` runs after the database is fresh

#### Scenario: Build fails if database rebuild fails

- **WHEN** `build-db.mjs` fails during `npm run build` or `pnpm build` from `web/`
- **THEN** `astro build` does not execute
- **AND** the build process exits with a non-zero status

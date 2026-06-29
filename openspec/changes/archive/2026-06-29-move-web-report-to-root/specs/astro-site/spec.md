## RENAMED Requirements

FROM: Astro project scaffolded at gitbench/ui/
TO: Astro project scaffolded at top-level web/

## MODIFIED Requirements

### Requirement: Astro project scaffolded at top-level web/
The project SHALL include an Astro project at top-level `web/` with `package.json`, `astro.config.mjs` (with `@astrojs/react` integration), `tsconfig.json`, and a `src/` directory structure containing `pages/`, `components/`, `lib/`, and `styles/`.

#### Scenario: Project structure exists
- **WHEN** a developer lists `web/`
- **THEN** the directory contains `package.json`, `astro.config.mjs`, `tsconfig.json`, and a `src/` directory

#### Scenario: Astro config includes React integration
- **WHEN** reading `web/astro.config.mjs`
- **THEN** it includes `react()` in the integrations array

### Requirement: results.json served as static asset
The aggregated benchmark data SHALL be written to `web/public/results.json` by the Python CLI as a checked-in compatibility artifact. The Astro site SHALL NOT embed the full report data in page HTML. React islands SHALL load query-specific report data through the report API client instead of fetching the full `/results.json` payload. The overview page's first chart (PassRateBarChart) MAY receive chart-specific data via an `initialData` prop computed at build time, but that payload SHALL use the same default latest-evaluation semantics as the corresponding chart API when campaign rows exist. If no campaign rows exist, the initial payload MAY use aggregate summary data as a compatibility fallback. This exception is limited to the pass-rate chart on the overview page. All other charts and pages SHALL continue to load data through the report API client.

#### Scenario: results.json is accessible when emitted
- **WHEN** the built site is served and compatibility JSON was emitted during report generation
- **THEN** `GET /results.json` returns the aggregated benchmark data as JSON

#### Scenario: results.json is checked in under web
- **WHEN** checking tracked report artifacts
- **THEN** `web/public/results.json` is present as the compatibility JSON artifact
- **AND** `web/public/results.json` is not excluded by `.gitignore`

#### Scenario: React islands do not fetch full report payload
- **WHEN** a hydrated React chart or interactive table loads in the browser
- **THEN** it requests only the query-specific API payload needed for that view
- **AND** it does not fetch `/results.json` as the canonical report data source

#### Scenario: Overview pass-rate chart uses default evaluation data
- **WHEN** the overview page loads without a `campaign` query parameter and campaign rows exist
- **THEN** the PassRateBarChart initial data SHALL represent the same default latest reportable campaign that `/api/charts/pass-rate` would return

#### Scenario: Overview pass-rate chart falls back without campaigns
- **WHEN** the overview page loads and no campaign rows exist
- **THEN** the PassRateBarChart MAY render from aggregate summary initial data
- **AND** the page SHALL NOT display "No campaigns"

#### Scenario: Other overview charts still fetch from API
- **WHEN** the overview page loads
- **THEN** all charts other than PassRateBarChart fetch their data from the report API client as before

#### Scenario: Campaign override triggers API fetch
- **WHEN** the overview page loads with a `?campaign=<id>` query parameter
- **THEN** PassRateBarChart falls back to fetching from `/api/charts/pass-rate?campaign=<id>` to obtain campaign-scoped data and metadata

### Requirement: Build produces static dist/ directory
Running `npm run build` or `pnpm build` in top-level `web/` SHALL produce a static Astro site in `web/dist/` with HTML, CSS, JS, and static assets. The Astro page output SHALL remain static, while API-backed report data SHALL be served by deployment-specific API functions during local development and hosted production.

#### Scenario: Build completes successfully
- **WHEN** `npm run build` or `pnpm build` is executed from `web/`
- **THEN** `web/dist/` contains `index.html`, subdirectories for routes, and static assets

#### Scenario: Static page output is deployable
- **WHEN** `web/dist/` is served by a static file server
- **THEN** statically generated Astro routes and assets are accessible

#### Scenario: API-backed deployment provides report queries
- **WHEN** the app is served through the supported API-backed local or hosted deployment
- **THEN** static Astro pages can request `/api/*` report endpoints for interactive report data

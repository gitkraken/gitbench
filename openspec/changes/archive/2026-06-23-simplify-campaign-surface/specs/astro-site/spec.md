## MODIFIED Requirements

### Requirement: Static Layout component with sidebar

The site SHALL have a `Layout.astro` component that wraps all pages with a header, a minimal `Sidebar.astro` component, a content area via `<slot />`, and a footer. The sidebar SHALL contain seven navigation links: Overview, Models, Benchmarks, Explore, Compare, History, Methodology. The shared layout SHALL NOT render a campaign selector, campaign status control, or "No campaigns" text in ordinary page headers.

At viewport widths greater than 960px, the sidebar SHALL render as a fixed 220px left sidebar with all icons and labels visible.

At viewport widths 601-960px, the sidebar SHALL be collapsible, defaulting to expanded (220px, icons and labels) with a toggle button that collapses it to approximately 64px (icons only). The collapse toggle SHALL use a CSS checkbox hack to function without JavaScript.

At viewport widths less than or equal to 600px, the sidebar SHALL render as a sticky top bar with a hamburger toggle. The nav SHALL be hidden by default and SHALL expand as a vertical dropdown when the hamburger is tapped. The hamburger SHALL use a CSS checkbox hack to function without JavaScript and SHALL animate to an X shape when open.

The "GitBench" title and "by GitKraken" subtitle text SHALL be visible at all viewport widths.

#### Scenario: Layout wraps page content

- **WHEN** any page is rendered
- **THEN** it includes the sidebar with seven navigation links and the page-specific content in the main area

#### Scenario: Active page is highlighted in sidebar

- **WHEN** the current route is `/models`
- **THEN** the "Models" link in the sidebar is visually distinct from the other links

#### Scenario: Sidebar is fixed full-width on desktop

- **WHEN** the viewport width is greater than 960px
- **THEN** the sidebar renders at 220px width, fixed to the left, with both icons and labels visible

#### Scenario: Sidebar is collapsible on tablet

- **WHEN** the viewport width is between 601px and 960px
- **THEN** the sidebar defaults to expanded with icons and labels visible
- **AND** a collapse/expand toggle button is visible

#### Scenario: Sidebar is hamburger top bar on mobile

- **WHEN** the viewport width is 600px or less
- **THEN** the sidebar renders as a sticky top bar with a hamburger button and the nav is hidden by default

#### Scenario: Branding visible at mobile widths

- **WHEN** the viewport width is 600px or less but greater than 380px
- **THEN** both "GitBench" and "by GitKraken" text are visible in the sidebar header

#### Scenario: Header omits campaign controls

- **WHEN** any ordinary report page renders
- **THEN** the shared header SHALL NOT include `CampaignSelector`
- **AND** it SHALL NOT display a campaign empty state

### Requirement: results.json served as static asset

The aggregated benchmark data MAY be written to `ui/public/results.json` by the Python CLI as a compatibility artifact. The Astro site SHALL NOT embed the full report data in page HTML. React islands SHALL load query-specific report data through the report API client instead of fetching the full `/results.json` payload. The overview page's first chart (PassRateBarChart) MAY receive chart-specific data via an `initialData` prop computed at build time, but that payload SHALL use the same default latest-evaluation semantics as the corresponding chart API when campaign rows exist. If no campaign rows exist, the initial payload MAY use aggregate summary data as a compatibility fallback. This exception is limited to the pass-rate chart on the overview page. All other charts and pages SHALL continue to load data through the report API client.

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

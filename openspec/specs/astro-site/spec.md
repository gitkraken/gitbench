## Purpose

The Astro site provides the static frontend for GitBench benchmark results, rendering aggregated data from `results.json` into interactive charts and navigable model/fixture pages.
## Requirements
### Requirement: Astro project scaffolded at gitbench/ui/
The project SHALL include an Astro project at `gitbench/ui/` with `package.json`, `astro.config.mjs` (with `@astrojs/react` integration), `tsconfig.json`, and a `src/` directory structure containing `pages/`, `components/`, `lib/`, and `styles/`.

#### Scenario: Project structure exists
- **WHEN** a developer lists `gitbench/ui/`
- **THEN** the directory contains `package.json`, `astro.config.mjs`, `tsconfig.json`, and a `src/` directory

#### Scenario: Astro config includes React integration
- **WHEN** reading `astro.config.mjs`
- **THEN** it includes `react()` in the integrations array

### Requirement: Static Layout component with sidebar
The site SHALL have a `Layout.astro` component that wraps all pages with a header, a minimal `Sidebar.astro` component, a content area via `<slot />`, and a footer. The sidebar SHALL contain six visible navigation links: Overview, Models, Benchmarks, Explore, Compare, Methodology. The History page exists but SHALL be hidden from the sidebar navigation for now. The shared layout SHALL NOT render a campaign selector, campaign status control, or "No campaigns" text in ordinary page headers.

At viewport widths greater than 960px, the sidebar SHALL render as a fixed 220px left sidebar with all icons and labels visible.

At viewport widths 601–960px, the sidebar SHALL be collapsible — defaulting to expanded (220px, icons and labels) with a toggle button that collapses it to approximately 64px (icons only). The collapse toggle SHALL use a CSS checkbox hack to function without JavaScript.

At viewport widths ≤600px, the sidebar SHALL render as a sticky top bar with a hamburger toggle. The nav SHALL be hidden by default and SHALL expand as a vertical dropdown when the hamburger is tapped. The hamburger SHALL use a CSS checkbox hack to function without JavaScript and SHALL animate to an X shape when open.

The "GitBench" title and "by GitKraken" subtitle text SHALL be visible at all viewport widths.

#### Scenario: Layout wraps page content
- **WHEN** any page is rendered
- **THEN** it includes the sidebar with six visible navigation links (History is hidden) and the page-specific content in the main area

#### Scenario: Active page is highlighted in sidebar
- **WHEN** the current route is `/models`
- **THEN** the "Models" link in the sidebar is visually distinct from the other links

#### Scenario: Sidebar is fixed full-width on desktop
- **WHEN** the viewport width is greater than 960px
- **THEN** the sidebar renders at 220px width, fixed to the left, with both icons and labels visible

#### Scenario: Sidebar is collapsible on tablet
- **WHEN** the viewport width is between 601px and 960px
- **THEN** the sidebar defaults to expanded (icons and labels visible) and a collapse/expand toggle button is visible

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

### Requirement: Design tokens in global CSS
The site SHALL use CSS custom properties (design tokens) for colors, typography, spacing, and borders in `src/styles/global.css`. The theme SHALL be dark (matching the existing GitBench report aesthetic) with variables for background, surface, text, accent, pass/warn/fail colors.

#### Scenario: CSS variables are defined
- **WHEN** reading `src/styles/global.css`
- **THEN** it contains `:root` with CSS custom properties for `--bg`, `--text`, `--accent`, `--pass`, `--fail`, and `--font-display`

#### Scenario: Layout imports global CSS
- **WHEN** `Layout.astro` is rendered
- **THEN** it imports or references `global.css`

### Requirement: Client-side routing via Astro pages
All routes SHALL be defined as `.astro` files in `src/pages/`. Dynamic routes SHALL use Astro's file-based routing with `[param].astro` syntax. SSG pages SHALL use `getStaticPaths()` to enumerate all possible paths from `results.json`. Model pages SHALL use a nested three-segment path: `[provider]/[model]/[level].astro` for fixture galleries and `[provider]/[model]/index.astro` for base model overviews.

#### Scenario: Dashboard at root path
- **WHEN** navigating to `/`
- **THEN** the Dashboard page (`index.astro`) is rendered

#### Scenario: Model detail at nested route
- **WHEN** navigating to `/models/anthropic/claude-opus-4.7/low/`
- **THEN** the model fixture gallery page (`models/[provider]/[model]/[level].astro`) is rendered for `anthropic/claude-opus-4.7:low`

#### Scenario: Base model overview at nested route
- **WHEN** navigating to `/models/anthropic/claude-opus-4.7/`
- **THEN** the base model overview page (`models/[provider]/[model]/index.astro`) is rendered with level cards

#### Scenario: Fixture detail at dynamic route
- **WHEN** navigating to `/fixtures/f001`
- **THEN** the Fixture Detail page (`fixtures/[fixture].astro`) is rendered with fixture data for `f001`

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

### Requirement: Build produces static dist/ directory
Running `npm run build` in `gitbench/ui/` SHALL produce a static Astro site in `ui/dist/` with HTML, CSS, JS, and static assets. The Astro page output SHALL remain static, while API-backed report data SHALL be served by deployment-specific API functions during local development and hosted production.

#### Scenario: Build completes successfully
- **WHEN** `npm run build` is executed
- **THEN** `ui/dist/` contains `index.html`, subdirectories for routes, and static assets

#### Scenario: Static page output is deployable
- **WHEN** `ui/dist/` is served by a static file server
- **THEN** statically generated Astro routes and assets are accessible

#### Scenario: API-backed deployment provides report queries
- **WHEN** the app is served through the supported API-backed local or hosted deployment
- **THEN** static Astro pages can request `/api/*` report endpoints for interactive report data

### Requirement: Overview page includes introductory content
The root page (`/`) SHALL be titled "Overview" and SHALL include an About section with multi-paragraph introductory text written in the conversational prose voice. The About text SHALL explain what GitBench is, what it tests (204 fixtures across 17 Git skill categories), and that results are transparent and reproducible. It SHALL NOT include a "Learn more →" link to methodology. Chart sections on the Overview page SHALL use the info-tip pattern for blurb text that provides non-obvious context. Chart sections where the title and axes are self-explanatory SHALL have no blurb text at all.

#### Scenario: About section is always visible
- **WHEN** navigating to `/`
- **THEN** the About card contains multiple paragraphs of conversational prose visible without interaction on all viewports

#### Scenario: Runtime chart has info tip
- **WHEN** navigating to `/` on desktop
- **THEN** the Runtime chart section label has a ⓘ icon, and hovering reveals the blurb as a positioned tooltip

#### Scenario: Runtime blurb is inline on mobile
- **WHEN** navigating to `/` on a mobile viewport
- **THEN** the Runtime blurb appears as a static paragraph below the section label without the ⓘ icon

#### Scenario: Pass Rate chart has no blurb
- **WHEN** navigating to `/`
- **THEN** the Pass Rate chart section has no prose paragraph between the section label and the chart

#### Scenario: No "Learn more" link to methodology
- **WHEN** navigating to `/`
- **THEN** no link labeled "Learn more" appears in any section blurb or the About text

### Requirement: Section blurbs follow voice guidelines
All section blurbs across Astro pages SHALL use the conversational prose voice: short sentences, fragments permitted, no emdashes, contractions preferred, hedging removed. Blurbs SHALL NOT describe what is already visually apparent from chart titles, axis labels, or badge text.

#### Scenario: No emdashes in section blurbs
- **WHEN** searching all `.astro` files for the emdash character (—) outside the Methodology page
- **THEN** no instance is found

#### Scenario: Fragments appear naturally
- **WHEN** reading section blurbs across the site
- **THEN** multiple sentence fragments or very short sentences (under 6 words) appear

### Requirement: Info tips replace always-visible blurbs on specific sections
The following sections on Astro pages SHALL use the `<div class="info-tip">` pattern for their blurb text (CSS tooltip on desktop, inline text on mobile):
- `index.astro`: Quadrant Comparison, Runtime, Benchmark Matrix
- `explore.astro`: top page blurb
- `compare.astro`: top page blurb
- `benchmarks/[name].astro`: Model Leaderboard
- `history.astro`: Run Log

#### Scenario: Info tips render on specified sections
- **WHEN** navigating to the Overview page
- **THEN** the Quadrant Comparison, Runtime, and Benchmark Matrix sections each have a `<div class="info-tip">` element wrapping their section label and blurb

#### Scenario: Info tips absent from deleted sections
- **WHEN** navigating to the Overview page
- **THEN** the Pass Rate, Cost, and Token Usage sections have no `<div class="info-tip">` element and no blurb paragraph

### Requirement: Always-visible blurbs on critical sections
The following sections SHALL retain always-visible blurb text (not inside an info tip):
- `index.astro`: About section (multi-paragraph, conversational voice)
- `models/index.astro`: top page blurb (explains provider → model → level hierarchy)
- `fixtures/[benchmark]/[fixture].astro`: Baseline Repository section (explains setup commands)

#### Scenario: About section is always visible
- **WHEN** navigating to `/`
- **THEN** the About card text is rendered directly (not inside a `<div class="info-tip">`)

#### Scenario: Models hierarchy blurb is always visible
- **WHEN** navigating to `/models`
- **THEN** the hierarchy explanation paragraph is rendered directly above the provider cards

### Requirement: Deleted section blurbs
The following sections SHALL have no blurb text at all (neither always-visible nor in an info tip):
- `index.astro`: Pass Rate (Model Summary), Cost per Full Run, Token Usage
- `benchmarks/[name].astro`: Per-Fixture Comparison
- `models/[provider]/[model]/index.astro`: top page blurb
- `models/[provider]/[model]/[level].astro`: Fixture Gallery blurb
- `history.astro`: Pass Rate Over Time
- `fixtures/[benchmark]/[fixture].astro`: Model Outputs blurb
- `benchmarks/index.astro`: top page blurb

#### Scenario: No blurb on deleted sections
- **WHEN** navigating to any of the listed page sections
- **THEN** no prose paragraph appears between the section label and the chart/table/content`

### Requirement: Token and cost display on model detail page
The model detail page (`/models/[model]`) SHALL display token usage and cost information. For the model summary area, it SHALL show total tokens consumed and total cost. For each fixture card in the gallery, input/output token counts SHALL be shown where available.

#### Scenario: Model summary shows cost and tokens
- **WHEN** viewing a model detail page and the model has cost data
- **THEN** the summary area shows total cost and total tokens next to the pass rate badge

#### Scenario: Fixture cards show token counts
- **WHEN** viewing the fixture gallery on a model detail page
- **THEN** each `FixtureCard` displays input and output token counts when available

### Requirement: Token badges on fixture detail model outputs
The fixture detail page (`/fixtures/[benchmark]/[fixture]`) SHALL display token usage (input/output) on each `ModelOutputCard` as small mono badges next to the existing pass/fail badge and similarity score.

#### Scenario: ModelOutputCard shows tokens
- **WHEN** a model output has `input_tokens=157` and `output_tokens=496`
- **THEN** the card displays "157→496" as small mono text next to the similarity score

#### Scenario: ModelOutputCard handles missing tokens
- **WHEN** a model output has null token values
- **THEN** no token badges are displayed (the card looks the same as before)

### Requirement: App main content area is capped via --main-max-width CSS variable

The site SHALL define a CSS custom property `--main-max-width` on
`:root` in `src/styles/global.css` with a default value of `1440px`.
The `.app-main` element SHALL apply
`max-width: var(--main-max-width); margin-inline: auto;` so the
content area centers within the available width on desktop viewports
(≥960px). Changing the variable's value (or setting it to `none`)
SHALL be the only edit required to revert to full-bleed content on
wide monitors.

#### Scenario: Variable exists on :root with 1440px default
- **WHEN** a developer reads `src/styles/global.css`
- **THEN** `:root` declares `--main-max-width: 1440px;`

#### Scenario: .app-main applies the cap at desktop
- **WHEN** the viewport width is ≥1440px
- **THEN** the `.app-main` element's effective width does not exceed `1440px`
- **AND** the element is horizontally centered within the remaining space (sidebar is fixed 220px on the left)

#### Scenario: Cap does not regress tablet or mobile
- **WHEN** the viewport width is between 601px and 1439px
- **THEN** `.app-main` retains its existing full-bleed behavior inside the sidebar offset
- **WHEN** the viewport width is ≤600px
- **THEN** `.app-main` retains its existing full-bleed behavior (mobile has no sidebar)

#### Scenario: Cap is opt-out via the CSS variable
- **WHEN** a developer sets `--main-max-width: none` on `:root`
- **THEN** `.app-main` stretches to the full remaining width without further code changes

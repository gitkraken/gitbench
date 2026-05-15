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
The site SHALL have a `Layout.astro` component that wraps all pages with a header, a minimal `Sidebar.astro` component, a content area via `<slot />`, and a footer. The sidebar SHALL contain seven navigation links: Overview, Models, Benchmarks, Explore, Compare, History, Methodology.

#### Scenario: Layout wraps page content
- **WHEN** any page is rendered
- **THEN** it includes the sidebar with seven navigation links and the page-specific content in the main area

#### Scenario: Active page is highlighted in sidebar
- **WHEN** the current route is `/models`
- **THEN** the "Models" link in the sidebar is visually distinct from the other links

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
The aggregated benchmark data SHALL be written to `ui/public/results.json` by the Python CLI. The Astro site SHALL NOT embed this data in page HTML but SHALL serve it as a static file accessible at `/results.json` for React islands to fetch.

#### Scenario: results.json is accessible
- **WHEN** the built site is served
- **THEN** `GET /results.json` returns the aggregated benchmark data as JSON

#### Scenario: results.json is gitignored
- **WHEN** checking the gitignore
- **THEN** `ui/public/results.json` and `ui/dist/` are listed

### Requirement: Build produces static dist/ directory
Running `npm run build` in `gitbench/ui/` SHALL produce a fully static site in `ui/dist/` with HTML, CSS, JS, and `results.json` assets. The output SHALL require no server-side code to serve.

#### Scenario: Build completes successfully
- **WHEN** `npm run build` is executed
- **THEN** `ui/dist/` contains `index.html`, subdirectories for routes, and static assets

#### Scenario: Static site is deployable
- **WHEN** `ui/dist/` is served by any static file server
- **THEN** all routes are accessible and functional

### Requirement: Overview page includes introductory content
The root page (`/`) formerly titled "Dashboard" SHALL be titled "Overview" and SHALL include a brief introductory paragraph at the top explaining what GitBench is and what the page shows. The intro SHALL appear above the first chart section.

#### Scenario: Intro text on overview page
- **WHEN** navigating to `/`
- **THEN** the page heading is "Overview" and a paragraph of explanatory text appears above the charts

#### Scenario: Sidebar shows Overview not Dashboard
- **WHEN** viewing any page
- **THEN** the first sidebar link is "Overview" with a `LayoutDashboard` icon, and it is active when on `/`

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


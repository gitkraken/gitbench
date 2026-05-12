## MODIFIED Requirements

### Requirement: Static Layout component with sidebar
The site SHALL have a `Layout.astro` component that wraps all pages with a header, a minimal `Sidebar.astro` component, a content area via `<slot />`, and a footer. The sidebar SHALL contain seven navigation links: Overview, Models, Benchmarks, Explore, Compare, History, Methodology.

#### Scenario: Layout wraps page content
- **WHEN** any page is rendered
- **THEN** it includes the sidebar with seven navigation links and the page-specific content in the main area

#### Scenario: Active page is highlighted in sidebar
- **WHEN** the current route is `/models`
- **THEN** the "Models" link in the sidebar is visually distinct from the other links

## ADDED Requirements

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

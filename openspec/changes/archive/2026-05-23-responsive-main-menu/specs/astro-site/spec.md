## MODIFIED Requirements

### Requirement: Static Layout component with sidebar
The site SHALL have a `Layout.astro` component that wraps all pages with a header, a minimal `Sidebar.astro` component, a content area via `<slot />`, and a footer. The sidebar SHALL contain seven navigation links: Overview, Models, Benchmarks, Explore, Compare, History, Methodology.

At viewport widths greater than 960px, the sidebar SHALL render as a fixed 220px left sidebar with all icons and labels visible.

At viewport widths 601–960px, the sidebar SHALL be collapsible — defaulting to expanded (220px, icons and labels) with a toggle button that collapses it to approximately 64px (icons only). The collapse toggle SHALL use a CSS checkbox hack to function without JavaScript.

At viewport widths ≤600px, the sidebar SHALL render as a sticky top bar with a hamburger toggle. The nav SHALL be hidden by default and SHALL expand as a vertical dropdown when the hamburger is tapped. The hamburger SHALL use a CSS checkbox hack to function without JavaScript and SHALL animate to an X shape when open.

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
- **THEN** the sidebar defaults to expanded (icons and labels visible) and a collapse/expand toggle button is visible

#### Scenario: Sidebar is hamburger top bar on mobile
- **WHEN** the viewport width is 600px or less
- **THEN** the sidebar renders as a sticky top bar with a hamburger button and the nav is hidden by default

#### Scenario: Branding visible at mobile widths
- **WHEN** the viewport width is 600px or less but greater than 380px
- **THEN** both "GitBench" and "by GitKraken" text are visible in the sidebar header

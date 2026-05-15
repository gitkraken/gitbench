## MODIFIED Requirements

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

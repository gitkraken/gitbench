## MODIFIED Requirements

### Requirement: History page shows run history and time series

The History page (`history.astro`) SHALL render campaign records as the primary evaluation timeline when campaign data exists. Each campaign node or row SHALL show campaign identity, evaluation date, status, trial counts, mean success, valid attempts, and delta from the previous compatible campaign when available. The page MAY retain legacy run history and time-series behavior as a fallback for reports that contain only single-run aggregate data.

#### Scenario: Campaign timeline is rendered

- **WHEN** navigating to `/history` with campaign records available
- **THEN** the page displays campaign nodes or rows sorted by evaluation time
- **AND** each row includes status, trial counts, mean success, valid attempts, and compatibility-aware delta where available

#### Scenario: Time series chart uses campaign nodes

- **WHEN** the History page loads and campaign records exist
- **THEN** the time series chart SHALL use campaign-level points rather than independent trial rows

#### Scenario: Legacy run history fallback

- **WHEN** the report contains no campaign records but contains legacy run history
- **THEN** the History page MAY display the legacy run log and run-level time series

## ADDED Requirements

### Requirement: Ordinary report pages omit campaign controls

Overview, Models, Benchmarks, Explore, Compare, Methodology, and Fixture pages SHALL NOT render a campaign selector or a "No campaigns" campaign empty state. These pages SHALL use the default latest evaluation data supplied by the report APIs or store helpers.

#### Scenario: Overview has no campaign selector

- **WHEN** a user opens the Overview page
- **THEN** the page header SHALL NOT include a campaign selector
- **AND** the page SHALL NOT show "No campaigns" when aggregate report data exists

#### Scenario: Campaign-specific fixture evidence remains available

- **WHEN** a user navigates to a fixture evidence view from History or a raw-attempt link
- **THEN** campaign-specific raw attempt details MAY be shown for that evidence context

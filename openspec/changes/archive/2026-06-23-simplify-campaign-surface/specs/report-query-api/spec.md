## ADDED Requirements

### Requirement: Report APIs resolve latest evaluation by default

Report APIs that serve campaign-sensitive summaries, charts, model results, benchmark details, fixture attempts, or comparison data SHALL resolve the default campaign through the report-store abstraction when no explicit campaign ID is supplied. The default SHALL prefer the latest complete, publishable, non-legacy campaign. If no campaign records exist, APIs SHALL fall back to aggregate report summary data where that endpoint has a legacy aggregate equivalent.

#### Scenario: Chart endpoint defaults to latest campaign

- **WHEN** a client requests a campaign-sensitive chart endpoint without a `campaign` query parameter
- **THEN** the endpoint SHALL use the report store's default latest reportable campaign when one exists
- **AND** the response SHALL include campaign metadata when the response shape supports it

#### Scenario: Aggregate fallback when no campaigns exist

- **WHEN** the report database has model and benchmark summary rows but no campaign rows
- **THEN** compact report endpoints SHALL continue returning aggregate summary data
- **AND** they SHALL NOT return an error solely because campaign rows are absent

### Requirement: Explicit campaign lookup remains supported

Report APIs SHALL continue accepting explicit campaign IDs for compatible internal links, History drilldowns, raw-attempt inspection, and debug query parameters. Unsupported or incompatible explicit campaign IDs SHALL be rejected or ignored according to the endpoint's existing validation behavior without creating a visible campaign selector requirement.

#### Scenario: Compatible explicit campaign is honored

- **WHEN** a request includes a compatible `campaign` query parameter
- **THEN** the endpoint SHALL use that campaign for campaign-sensitive data

#### Scenario: Incompatible explicit campaign is not silently compared

- **WHEN** a request includes a campaign that is incompatible with the requested benchmark, model, or output mode
- **THEN** the endpoint SHALL avoid returning misleading campaign-scoped aggregates
- **AND** it SHALL preserve existing validation or null-fallback semantics

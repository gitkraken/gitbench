## MODIFIED Requirements

### Requirement: Reports select a campaign globally

The report application SHALL NOT provide a campaign selector shared across ordinary campaign-sensitive pages. Campaign-sensitive summaries, charts, tables, and links SHALL default to the latest reportable evaluation campaign when one exists, without requiring user selection. Explicit campaign IDs MAY still be honored through internal links, History drilldowns, raw-attempt inspection, or debug query parameters.

#### Scenario: Ordinary page defaults to latest evaluation

- **WHEN** a user opens an ordinary report page without a `campaign` query parameter
- **THEN** campaign-sensitive data SHALL resolve to the latest reportable evaluation campaign when one exists
- **AND** the page SHALL NOT render a campaign selector

#### Scenario: No campaign records exist

- **WHEN** the report contains benchmark summary data but no campaign records
- **THEN** ordinary report pages SHALL render available aggregate report data
- **AND** they SHALL NOT display a "No campaigns" empty state

#### Scenario: Explicit internal campaign link

- **WHEN** an internal link, History drilldown, or debug URL includes a compatible `campaign` query parameter
- **THEN** campaign-sensitive data SHALL use that campaign
- **AND** navigation MAY preserve that internal campaign context without exposing a general-purpose selector

### Requirement: Campaign status and comparability are visible

The report SHALL display campaign trial counts, completeness, publication state, legacy state, and configuration compatibility wherever campaign data is explicitly displayed or compared, including History, raw-attempt evidence, and internal campaign links. Ordinary page headers and chart sections SHALL NOT surface campaign status unless the selected evaluation is incomplete or legacy and the state materially affects interpretation.

#### Scenario: View a legacy campaign

- **WHEN** a historical one-result artifact is imported and explicitly displayed
- **THEN** the UI SHALL label it as a one-trial legacy campaign
- **AND** it SHALL not imply that stability was measured

#### Scenario: Compare incompatible campaigns

- **WHEN** campaigns differ in fixture inputs, suite membership, scoring configuration, or request configuration
- **THEN** the UI SHALL identify the incompatibility in History or comparison contexts
- **AND** it SHALL not compute a default reliability delta

### Requirement: History treats campaigns as the comparison unit

History views SHALL show one primary node, point, or row per campaign when campaign records exist and SHALL provide trial-level detail without presenting trials as independent benchmark releases. Campaign terminology MAY be user-facing on History because it identifies the stored evaluation nodes being compared.

#### Scenario: Expand a history row

- **WHEN** a user expands a campaign in history
- **THEN** the report SHALL show trial summaries and completion details
- **AND** campaign-level changes SHALL remain the primary history comparison

#### Scenario: History lists campaign nodes

- **WHEN** the report contains multiple campaign records
- **THEN** History SHALL present them as the evaluation timeline
- **AND** ordinary report pages SHALL continue to default to the latest reportable campaign

## ADDED Requirements

### Requirement: Campaign terminology is constrained outside history

Ordinary report pages SHALL prefer user-facing terms such as "evaluation run", "latest evaluation", "trial", or "raw attempt" instead of "campaign". The term "campaign" SHALL remain acceptable in History, Methodology sections that define the internal model, API/debug contexts, and raw evidence views where the exact stored identity matters.

#### Scenario: Header does not expose campaign terminology

- **WHEN** a user views any ordinary report page
- **THEN** the shared header SHALL NOT display "campaign", "campaign selector", or "No campaigns"

#### Scenario: Evidence view can name campaign identity

- **WHEN** a user opens raw attempt evidence for a specific campaign
- **THEN** the UI MAY display the campaign ID because it is part of the evidence identity

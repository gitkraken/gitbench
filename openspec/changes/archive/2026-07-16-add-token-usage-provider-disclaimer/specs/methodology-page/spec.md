## ADDED Requirements

### Requirement: Methodology explains token accounting provenance
The Methodology page SHALL include a linkable Token Accounting section with the stable anchor `token-accounting`. The section SHALL explain that GitBench records source token counts from usage telemetry returned by provider APIs, calculates displayed aggregates from those source counts, may derive a total from available input and output values when a total is absent, and does not independently retokenize or verify the provider counts. It SHALL warn that tokenizers and the classification of input, output, cached, and reasoning tokens can differ by provider, so cross-provider token comparisons are not normalized measurements.

#### Scenario: Reader traces source and derived values
- **WHEN** a reader follows a token-usage Learn more link
- **THEN** the browser targets the Token Accounting section at `/methodology#token-accounting`
- **AND** the section distinguishes provider-reported source counts from GitBench-calculated aggregates and fallback totals

#### Scenario: Reader assesses cross-provider comparability
- **WHEN** a reader reviews the Token Accounting section
- **THEN** the section states that provider tokenization and accounting conventions may differ
- **AND** it does not represent cross-provider token counts as independently normalized or verified

#### Scenario: Token categories are described without universal semantics
- **WHEN** the methodology discusses input, output, cached, or reasoning-token categories
- **THEN** it makes clear that category availability and semantics depend on provider telemetry


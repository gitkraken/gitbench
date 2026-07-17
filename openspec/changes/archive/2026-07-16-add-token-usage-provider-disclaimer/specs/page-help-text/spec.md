## ADDED Requirements

### Requirement: Token-usage blurbs disclose provider-reported telemetry
The token-usage explanatory blurbs on the overview and benchmark detail pages SHALL state that source token counts come from provider-reported usage, SHALL warn that provider tokenization or accounting methods may differ, and SHALL link to the Methodology token-accounting section. The disclosure SHALL distinguish source telemetry from aggregates calculated by GitBench without implying that GitBench independently retokenizes or verifies provider counts.

#### Scenario: Overview token chart explains provenance
- **WHEN** a reader views the Token Usage section on the overview page
- **THEN** the section blurb states that source token counts are provider-reported
- **AND** it warns that provider tokenization or accounting methods may differ
- **AND** it links to `/methodology#token-accounting`

#### Scenario: Benchmark token chart explains provenance
- **WHEN** a reader views the Benchmark Token Usage section on a benchmark detail page
- **THEN** the section blurb provides the same provider-reporting caveat
- **AND** it links to `/methodology#token-accounting`

#### Scenario: Disclaimer does not overstate raw provenance
- **WHEN** a token-usage blurb describes values displayed by GitBench
- **THEN** it does not claim that every displayed aggregate or fallback total was directly returned by a provider
- **AND** it identifies provider-reported counts as the source values used by GitBench


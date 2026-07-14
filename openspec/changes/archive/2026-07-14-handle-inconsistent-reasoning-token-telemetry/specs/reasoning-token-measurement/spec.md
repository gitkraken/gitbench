## MODIFIED Requirements

### Requirement: Output token decomposition preserves provider totals
GitBench SHALL retain `output_tokens` as the raw provider-reported completion-token total and `reasoning_tokens` as the raw provider-reported reasoning-token total. Presentation code SHALL derive non-reasoning visible output as `max(output_tokens - reasoning_tokens, 0)` when output is known, bounded reasoning within output as `min(reasoning_tokens, output_tokens)` when both values are known, and reasoning overflow as `max(reasoning_tokens - output_tokens, 0)` when both values are known. Presentation code SHALL mark telemetry inconsistent when reasoning overflow is greater than zero. Presentation code SHALL NOT add raw reasoning tokens to `output_tokens` or `total_tokens`.

#### Scenario: Reasoning is included in provider output
- **WHEN** a result reports `output_tokens: 1349` and `reasoning_tokens: 1343`
- **THEN** GitBench SHALL retain total output as 1349
- **AND** GitBench SHALL derive visible output as 6
- **AND** GitBench SHALL derive reasoning within output as 1343
- **AND** GitBench SHALL derive reasoning overflow as 0

#### Scenario: Result has no reasoning token data
- **WHEN** a result reports `output_tokens: 200` and `reasoning_tokens: null`
- **THEN** GitBench SHALL derive visible output as 200
- **AND** GitBench SHALL not derive a reasoning-within-output segment
- **AND** GitBench SHALL not mark the telemetry inconsistent

#### Scenario: Result has no output token data
- **WHEN** a result has no `output_tokens`
- **THEN** visible output SHALL remain unavailable regardless of reasoning token data
- **AND** GitBench SHALL not classify reasoning tokens as within-output or overflow without provider output data

#### Scenario: Provider reasoning exceeds output
- **WHEN** a provider reports `output_tokens: 100` and `reasoning_tokens: 120`
- **THEN** GitBench SHALL preserve both raw values
- **AND** GitBench SHALL derive visible output as 0
- **AND** GitBench SHALL derive reasoning within output as 100
- **AND** GitBench SHALL derive reasoning overflow as 20
- **AND** GitBench SHALL mark the telemetry inconsistent

#### Scenario: Total tokens are not double-counted
- **WHEN** input is 500, provider output is 200, reasoning is 150, and total is 700
- **THEN** report and chart calculations SHALL continue to use total 700 rather than calculating 850

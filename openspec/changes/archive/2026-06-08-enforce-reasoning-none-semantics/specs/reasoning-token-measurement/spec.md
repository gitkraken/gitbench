## ADDED Requirements

### Requirement: Output token decomposition preserves provider totals
GitBench SHALL retain `output_tokens` as the raw provider-reported completion-token total. When reasoning tokens are reported as part of completion tokens, presentation code SHALL derive non-reasoning visible output as `max(output_tokens - reasoning_tokens, 0)` and SHALL NOT add reasoning tokens to `output_tokens` or `total_tokens`.

#### Scenario: Reasoning is included in provider output
- **WHEN** a result reports `output_tokens: 1349` and `reasoning_tokens: 1343`
- **THEN** GitBench SHALL retain total output as 1349 and derive visible output as 6

#### Scenario: Result has no reasoning token data
- **WHEN** a result reports `output_tokens: 200` and `reasoning_tokens: null`
- **THEN** GitBench SHALL derive visible output as 200

#### Scenario: Result has no output token data
- **WHEN** a result has no `output_tokens`
- **THEN** visible output SHALL remain unavailable regardless of reasoning token data

#### Scenario: Provider reasoning exceeds output
- **WHEN** a provider reports `output_tokens: 100` and `reasoning_tokens: 120`
- **THEN** GitBench SHALL preserve both raw values and derive visible output as 0 rather than a negative number

#### Scenario: Total tokens are not double-counted
- **WHEN** input is 500, provider output is 200, reasoning is 150, and total is 700
- **THEN** report and chart calculations SHALL continue to use total 700 rather than calculating 850

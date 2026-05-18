## MODIFIED Requirements

### Requirement: TokenUsageChart includes ModelSelector filter

The `TokenUsageChart` component SHALL include a `ModelSelector` dropdown allowing users to filter which models appear in the chart. The selector SHALL use the shared Overview model selection state. When any other Overview chart selector changes the selected model set, `TokenUsageChart` SHALL update its rendered bars and provider legend from that same selected model set.

#### Scenario: Filter removes models from chart
- **WHEN** a user deselects a model in the ModelSelector
- **THEN** that model's bar is removed from the chart

#### Scenario: External selection updates token chart
- **WHEN** a user changes the selected models in another Overview chart's ModelSelector
- **THEN** `TokenUsageChart` updates its bars to match the new selected model set

#### Scenario: Selector remains available when selected models have no token data
- **WHEN** every model in the selected model set has zero collected total tokens
- **THEN** `TokenUsageChart` displays "No token data available" and still renders the ModelSelector

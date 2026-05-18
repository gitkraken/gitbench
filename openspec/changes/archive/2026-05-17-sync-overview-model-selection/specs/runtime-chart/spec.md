## MODIFIED Requirements

### Requirement: RuntimeBarChart includes ModelSelector filter
The `RuntimeBarChart` component SHALL include a `ModelSelector` dropdown allowing users to filter which models appear in the chart. The selector SHALL use the shared Overview model selection state. When any other Overview chart selector changes the selected model set, `RuntimeBarChart` SHALL update its rendered bars and provider legend from that same selected model set. Models without runtime data SHALL remain excluded from the rendered bars even when selected.

#### Scenario: Filter removes models from chart
- **WHEN** a user deselects a model in the ModelSelector
- **THEN** that model's bar is removed from the chart

#### Scenario: External selection updates runtime chart
- **WHEN** a user changes the selected models in another Overview chart's ModelSelector
- **THEN** `RuntimeBarChart` updates its bars to match the new selected model set, excluding selected models without runtime data

#### Scenario: Selector remains available when no selected models have runtime data
- **WHEN** the selected model set contains no models with entries in `model_runtimes`
- **THEN** `RuntimeBarChart` displays "No runtime data available" and still renders the ModelSelector

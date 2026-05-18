## ADDED Requirements

### Requirement: Overview chart components share model selection
Overview chart components in the shared chart-components capability SHALL update their rendered data when any Overview `ModelSelector` changes the selected model set. This includes `PassRateBarChart` and `BenchmarkHeatmap`. The selected model set SHALL be the complete array from the latest model selection change, and each chart SHALL use that set for all model-dependent bars, columns, legends, and labels.

#### Scenario: Model Summary updates from another selector
- **WHEN** a user changes the selected models in the Benchmark Matrix selector
- **THEN** the Model Summary chart updates its bars to match the same selected model set

#### Scenario: Benchmark Matrix updates from another selector
- **WHEN** a user changes the selected models in the Model Summary selector
- **THEN** the Benchmark Matrix updates its model columns to match the same selected model set

#### Scenario: Provider legend follows shared selection
- **WHEN** a shared model selection change removes all models for a provider from the Model Summary chart
- **THEN** that provider is removed from the Model Summary provider legend

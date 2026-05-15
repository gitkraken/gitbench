## MODIFIED Requirements

### Requirement: PassRateBarChart renders horizontal bar chart
The `PassRateBarChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = model, Y-axis = pass rate percentage). Bars SHALL be color-coded by pass rate threshold (green ≥80%, yellow 50-79%, red <50%). X-axis tick labels SHALL be rotated diagonally (-40°) with a custom tick renderer that displays: a provider brand icon (via `ProviderIcon`), the truncated model name (max ~10 characters + ellipsis), and the reasoning level suffix. The component SHALL accept a `data` prop containing the full dataset and a `selectedModels` prop listing models to display. Chart height SHALL be computed dynamically as `max(300, modelCount * 80)` to accommodate rotated labels.

#### Scenario: Bars render for selected models
- **WHEN** `PassRateBarChart` receives `selectedModels=['anthropic/claude-opus-4.7:low', 'openai/gpt-oss-120b:high']`
- **THEN** two vertical bars are displayed with the corresponding pass rates

#### Scenario: Colors reflect pass rate
- **WHEN** a model has 87% pass rate
- **THEN** its bar is rendered in the green color

#### Scenario: Diagonal labels show provider icon and truncated name
- **WHEN** a model name is `openai/gpt-oss-120b:high`
- **THEN** its X-axis tick shows the OpenAI icon, "gpt-oss-1…" (truncated), and "high" on a separate line, rotated -40°

#### Scenario: Long model names are truncated
- **WHEN** a model name exceeds ~10 characters in the base model part
- **THEN** the displayed label is truncated with an ellipsis

#### Scenario: Chart height scales with model count
- **WHEN** 12 models are selected
- **THEN** the chart height is at least `max(300, 12 * 80) = 960` pixels

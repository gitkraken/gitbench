## MODIFIED Requirements

### Requirement: RuntimeBarChart renders horizontal bar chart ranking models by speed
The `RuntimeBarChart` React component SHALL render a Recharts horizontal bar chart (bars go right, Y-axis = model, X-axis = total API time in seconds). Each bar SHALL represent one model's total API call latency aggregated across all fixtures from `model_runtimes[model].total_ms`. Bars SHALL be color-coded by provider using the `getProviderColor()` palette. Y-axis tick labels SHALL display the provider brand icon (via `ProviderIcon`), the truncated model name (max ~10 characters + ellipsis), and the reasoning level suffix. The component SHALL accept a `data` prop containing the full dataset and an optional `selectedModels` prop for filtering. Chart height SHALL be fixed at 350 pixels. A provider legend SHALL be rendered below the chart card showing colored dots for each unique provider present. Models SHALL be sorted fastest-first (ascending total API time).

#### Scenario: Bars render for selected models
- **WHEN** `RuntimeBarChart` receives `selectedModels=['anthropic/claude-opus-4.7:low', 'openai/gpt-oss-120b:high']`
- **THEN** two horizontal bars are displayed with the corresponding total API times

#### Scenario: Fastest model appears at top
- **WHEN** models have total API times [5000, 12000, 3000, 8000]
- **THEN** bars appear in order: 3000 (top), 5000, 8000, 12000 (bottom)

#### Scenario: Colors reflect provider
- **WHEN** a model has provider `anthropic`
- **THEN** its bar is rendered in the Anthropic palette color (#D97757)

#### Scenario: Colors reflect provider for fallback providers
- **WHEN** a model has provider `unknown-provider`
- **THEN** its bar is rendered in a deterministic `hsl(hue, 55%, 48%)` color

#### Scenario: Y-axis labels show provider icon and truncated name
- **WHEN** a model name is `openai/gpt-oss-120b:high`
- **THEN** its Y-axis tick shows the OpenAI icon, "gpt-oss-1..." (truncated), and "high" side-by-side

#### Scenario: Long model names are truncated
- **WHEN** a model name exceeds ~10 characters in the base model part
- **THEN** the displayed label is truncated with an ellipsis

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 models are present
- **THEN** the chart height is always 350 pixels

#### Scenario: Provider legend appears below the chart
- **WHEN** the chart shows models from multiple providers
- **THEN** a horizontal legend with colored dots and provider names appears below the chart card

### Requirement: Chart tooltip footnotes use conversational fragments
React chart components that display a separator + explanatory footnote in their Recharts `<Tooltip>` content SHALL use short conversational fragments. Each footnote SHALL be a single line (or fragment), not a multi-sentence explanation. Footnotes SHALL follow the conversational prose voice: no emdashes, contractions preferred, no hedging.

#### Scenario: PassRateBarChart footnote is a fragment
- **WHEN** hovering a bar in PassRateBarChart
- **THEN** the tooltip footnote below the separator reads "% of 204 fixtures passed"

#### Scenario: CostValueChart footnote is a fragment
- **WHEN** hovering a bar in CostValueChart
- **THEN** the tooltip footnote below the separator reads "API cost for 204-fixture run. - = local/Ollama"

#### Scenario: RuntimeBarChart footnote includes latency caveat
- **WHEN** hovering a bar in RuntimeBarChart
- **THEN** the tooltip footnote below the separator reads "API call latency. Lower is faster."

#### Scenario: TokenUsageChart footnote is a fragment
- **WHEN** hovering a bar in TokenUsageChart
- **THEN** the tooltip footnote below the separator reads "Tokens in + out. Fewer is more efficient."

#### Scenario: TimeSeriesChart footnote is minimal
- **WHEN** hovering a point in TimeSeriesChart
- **THEN** the tooltip footnote below the separator reads "Pass rate on this date."

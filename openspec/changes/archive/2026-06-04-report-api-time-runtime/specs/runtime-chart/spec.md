## MODIFIED Requirements

### Requirement: RuntimeBarChart renders horizontal bar chart ranking models by speed
The `RuntimeBarChart` React component SHALL render a Recharts horizontal bar chart (bars go right, Y-axis = provider/base-model group, X-axis = total API time in seconds). Each bar SHALL represent one selected provider/base-model group and SHALL visualize the range from the fastest effort API time to the slowest effort API time in that group. The fastest effort API time SHALL be the representative value used for sorting and bar prominence. Bars SHALL be color-coded by provider using the `getProviderColor()` palette. Y-axis tick labels SHALL display the provider brand icon (via `ProviderIcon`) and the truncated base model name (max ~10 characters + ellipsis). The component SHALL accept a `data` prop containing the full dataset and an optional selected group list for filtering. Chart height SHALL be fixed at 350 pixels. A provider legend SHALL be rendered below the chart card showing colored dots for each unique provider present. Model groups SHALL be sorted fastest-first by their fastest effort API time.

#### Scenario: Bars render for selected model groups
- **WHEN** `RuntimeBarChart` receives selected groups `['anthropic/claude-opus-4.7', 'openai/gpt-oss-120b']`
- **THEN** two horizontal grouped bars are displayed with API-time ranges for the selected base models

#### Scenario: Fastest grouped model appears at top
- **WHEN** model groups have fastest effort API times [5000, 12000, 3000, 8000]
- **THEN** bars appear in order: 3000 (top), 5000, 8000, 12000 (bottom)

#### Scenario: Effort range shown for runtime
- **WHEN** `openai/gpt-5` has effort API times 45s, 70s, and 110s
- **THEN** the `openai/gpt-5` bar visualizes the range 45s-110s and uses 45s as the representative value

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** its bar is rendered in the Anthropic palette color (#D97757)

#### Scenario: Colors reflect provider for fallback providers
- **WHEN** a model group has provider `unknown-provider`
- **THEN** its bar is rendered in a deterministic `hsl(hue, 55%, 48%)` color

#### Scenario: Y-axis labels show provider icon and truncated base model
- **WHEN** a model group is `openai/gpt-oss-120b`
- **THEN** its Y-axis tick shows the OpenAI icon and "gpt-oss-1..." (truncated)

#### Scenario: Long model names are truncated
- **WHEN** a base model name exceeds ~10 characters
- **THEN** the displayed label is truncated with an ellipsis

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are present
- **THEN** the chart height is always 350 pixels

#### Scenario: Provider legend appears below the chart
- **WHEN** the chart shows model groups from multiple providers
- **THEN** a horizontal legend with colored dots and provider names appears below the chart card

### Requirement: RuntimeBarChart reads from model_runtimes in aggregated data
The `RuntimeBarChart` component SHALL read API-time data from `data.model_runtimes[modelName].total_ms`. It SHALL convert milliseconds to seconds for display (dividing by 1000). The X-axis SHALL be labeled in seconds (e.g., "120s", "45.3s").

#### Scenario: Total runtime converted to seconds
- **WHEN** a model has `total_ms=45300`
- **THEN** the bar represents 45.3 seconds and the X-axis tick shows "45.3s"

#### Scenario: Zero millisecond total handled
- **WHEN** a model has `total_ms=0`
- **THEN** the bar represents 0 seconds and the X-axis tick shows "0s"

### Requirement: RuntimeBarChart shows tooltips on hover
Hovering over a grouped bar SHALL display a tooltip with the provider/base-model group name and each effort's total API time and average per-fixture API time. The tooltip SHALL identify the fastest effort in the group.

#### Scenario: Tooltip on hover
- **WHEN** a user hovers over a grouped runtime bar
- **THEN** a tooltip appears showing the provider/base-model group name and the API time for each effort

#### Scenario: Tooltip shows average per-fixture time
- **WHEN** a user hovers over a grouped runtime bar
- **THEN** the tooltip shows average fixture API time for each effort where available

#### Scenario: Tooltip identifies fastest effort
- **WHEN** one effort has the lowest API time in a grouped runtime bar
- **THEN** the tooltip identifies that effort as the fastest value used for sorting

### Requirement: RuntimeBarChart is placed on Models overview page
The `RuntimeBarChart` component SHALL be rendered on `/` (the Overview/Home page) after the Cost per Full Run section, in its own section labeled "API Time". It SHALL be loaded with `client:load`.

#### Scenario: Chart on overview page
- **WHEN** navigating to `/`
- **THEN** an "API Time" section with the grouped horizontal bar chart is visible

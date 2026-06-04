## Purpose

The RuntimeBarChart provides a bar chart ranking models by total API call latency, fastest first.
## Requirements
### Requirement: RuntimeBarChart reads from model_runtimes in aggregated data
The `RuntimeBarChart` component SHALL read API-time data from `data.model_runtimes[modelName].total_ms`. It SHALL convert milliseconds to seconds for display (dividing by 1000). The Y-axis SHALL be labeled in seconds (e.g., "120s", "45.3s"). The values SHALL represent API call latency aggregates, not full fixture wall-clock duration.

#### Scenario: Total API time converted to seconds
- **WHEN** a model has `total_ms=45300`
- **THEN** the bar represents 45.3 seconds and the Y-axis tick shows "45.3s"

#### Scenario: Zero millisecond total handled
- **WHEN** a model has `total_ms=0`
- **THEN** the bar represents 0 seconds and the Y-axis tick shows "0s"

### Requirement: RuntimeBarChart shows tooltips on hover
Hovering over a grouped bar SHALL display a tooltip with the provider/base-model group name and each effort's total API time and average per-fixture API time. The tooltip SHALL identify the representative median effort in the group.

#### Scenario: Tooltip on hover
- **WHEN** a user hovers over a grouped runtime bar
- **THEN** a tooltip appears showing the provider/base-model group name and the API time for each effort

#### Scenario: Tooltip shows average per-fixture API time
- **WHEN** a user hovers over a grouped runtime bar
- **THEN** the tooltip shows average fixture API time for each effort where available

#### Scenario: Tooltip identifies representative effort
- **WHEN** one effort has the median API time in a grouped runtime bar
- **THEN** the tooltip identifies that effort as the representative value used for sorting

### Requirement: RuntimeBarChart handles models without API-time data
If a selected model group has child efforts with no entry in `model_runtimes`, those child efforts SHALL be excluded from that group's API-time range and tooltip. If a selected model group has no child efforts with API-time data, the group SHALL be excluded from the chart. If NO selected model group has API-time data, the component SHALL display a message: "No API time data available."

#### Scenario: Effort without API-time data excluded
- **WHEN** one effort in a selected model group has no `model_runtimes` entry
- **THEN** that effort does not contribute to the group's API-time range

#### Scenario: Group without API-time data excluded
- **WHEN** a selected model group has no child efforts with `model_runtimes` entries
- **THEN** that model group does not appear as a bar

#### Scenario: All selected groups lack API-time data
- **WHEN** every selected model group lacks API-time data
- **THEN** the chart area displays "No API time data available"

### Requirement: RuntimeBarChart includes ModelSelector filter
The `RuntimeBarChart` component SHALL include a `ModelSelector` dropdown allowing users to filter which provider/base-model groups appear in the chart. The selector SHALL use the shared Overview model group selection state. When any other Overview chart selector changes the selected group set, `RuntimeBarChart` SHALL update its rendered bars and provider legend from that same selected group set. Groups without API-time data SHALL remain excluded from the rendered bars even when selected.

#### Scenario: Filter removes model group from chart
- **WHEN** a user deselects a model group in the ModelSelector
- **THEN** that model group's bar is removed from the chart

#### Scenario: External selection updates runtime chart
- **WHEN** a user changes the selected model groups in another Overview chart's ModelSelector
- **THEN** `RuntimeBarChart` updates its bars to match the new selected group set, excluding selected groups without API-time data

#### Scenario: Selector remains available when no selected groups have API-time data
- **WHEN** the selected group set contains no model groups with entries in `model_runtimes`
- **THEN** `RuntimeBarChart` displays "No API time data available" and still renders the ModelSelector

### Requirement: RuntimeBarChart is placed on Models overview page
The `RuntimeBarChart` component SHALL be rendered on `/` (the Overview/Home page) after the Cost per Full Run section, in its own section labeled "API Time". It SHALL be loaded with `client:load`.

#### Scenario: Chart on overview page
- **WHEN** navigating to `/`
- **THEN** an "API Time" section with the grouped vertical range-whisker bar chart is visible

### Requirement: RuntimeBarChart renders vertical range-whisker bar chart ranking models by speed
The `RuntimeBarChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = provider/base-model group, Y-axis = total API time in seconds). Each solid bar SHALL represent one selected provider/base-model group's representative effort API time from zero. The representative API time SHALL be the median value from the group's sorted, deduped effort API times. A neutral range whisker SHALL visualize the range from the fastest effort API time to the slowest effort API time in that group. The representative API time SHALL be used for sorting and bar prominence. The Y-axis domain SHALL start at 0 and include the slowest displayed effort API time. Bars SHALL be color-coded by provider using the `getProviderColor()` palette. X-axis tick labels SHALL display the provider brand icon (via `ProviderIcon`) and the truncated base model name (max ~10 characters + ellipsis), rotated `-40` degrees. The component SHALL accept a `data` prop containing the full dataset and an optional selected group list for filtering. Chart height SHALL be fixed at 350 pixels. A provider legend SHALL be rendered below the chart card showing colored dots for each unique provider present. Model groups SHALL be sorted fastest-first by their representative API time.

#### Scenario: Bars render for selected model groups
- **WHEN** `RuntimeBarChart` receives selected groups `['anthropic/claude-opus-4.7', 'openai/gpt-oss-120b']`
- **THEN** two vertical grouped bars are displayed with API-time range whiskers for the selected base models

#### Scenario: Fastest representative grouped model appears first
- **WHEN** model groups have representative API times [5000, 12000, 3000, 8000]
- **THEN** bars appear from left to right in order: 3000, 5000, 8000, 12000

#### Scenario: Effort API-time range shown with whisker
- **WHEN** `openai/gpt-5` has effort API times 45s, 70s, and 110s
- **THEN** the `openai/gpt-5` solid bar extends from 0s to 70s and its range whisker spans 45s-110s

#### Scenario: Duplicate effort API times are deduped before selecting representative API time
- **WHEN** `openai/gpt-5` has effort API times 45s, 45s, 45s, 70s, and 110s
- **THEN** the `openai/gpt-5` representative API time is 70s from deduped values [45s, 70s, 110s]

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** its bar is rendered in the Anthropic palette color (#D97757)

#### Scenario: Colors reflect provider for fallback providers
- **WHEN** a model group has provider `unknown-provider`
- **THEN** its bar is rendered in a deterministic `hsl(hue, 55%, 48%)` color

#### Scenario: Diagonal labels show provider icon and truncated base model
- **WHEN** a model group is `openai/gpt-oss-120b`
- **THEN** its X-axis tick shows the OpenAI icon and "gpt-oss-1..." (truncated), rotated `-40` degrees

#### Scenario: Long model names are truncated
- **WHEN** a base model name exceeds ~10 characters
- **THEN** the displayed label is truncated with an ellipsis

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are present
- **THEN** the chart height is always 350 pixels

#### Scenario: Provider legend appears below the chart
- **WHEN** the chart shows model groups from multiple providers
- **THEN** a horizontal legend with colored dots and provider names appears below the chart card

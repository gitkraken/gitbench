## MODIFIED Requirements

### Requirement: RuntimeBarChart renders horizontal bar chart ranking models by speed
The `RuntimeBarChart` React component SHALL render a Recharts horizontal bar chart (bars go right, Y-axis = provider/base-model group, X-axis = total runtime in seconds). Each bar SHALL represent one selected provider/base-model group and SHALL visualize the range from the fastest effort runtime to the slowest effort runtime in that group. The fastest effort runtime SHALL be the representative value used for sorting and bar prominence. Bars SHALL be color-coded by provider using the `getProviderColor()` palette. Y-axis tick labels SHALL display the provider brand icon (via `ProviderIcon`) and the truncated base model name (max ~10 characters + ellipsis). The component SHALL accept a `data` prop containing the full dataset and an optional selected group list for filtering. Chart height SHALL be fixed at 350 pixels. A provider legend SHALL be rendered below the chart card showing colored dots for each unique provider present. Model groups SHALL be sorted fastest-first by their fastest effort runtime.

#### Scenario: Bars render for selected model groups
- **WHEN** `RuntimeBarChart` receives selected groups `['anthropic/claude-opus-4.7', 'openai/gpt-oss-120b']`
- **THEN** two horizontal grouped bars are displayed with runtime ranges for the selected base models

#### Scenario: Fastest grouped model appears at top
- **WHEN** model groups have fastest effort runtimes [5000, 12000, 3000, 8000]
- **THEN** bars appear in order: 3000 (top), 5000, 8000, 12000 (bottom)

#### Scenario: Effort range shown for runtime
- **WHEN** `openai/gpt-5` has effort runtimes 45s, 70s, and 110s
- **THEN** the `openai/gpt-5` bar visualizes the range 45s-110s and uses 45s as the representative value

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** its bar is rendered in the Anthropic palette color (#D97757)

#### Scenario: Colors reflect provider for fallback providers
- **WHEN** a model group has provider `unknown-provider`
- **THEN** its bar is rendered in a deterministic `hsl(hue, 55%, 48%)` color

#### Scenario: Y-axis labels show provider icon and truncated base model
- **WHEN** a model group is `openai/gpt-oss-120b`
- **THEN** its Y-axis tick shows the OpenAI icon and "gpt-oss-1…" (truncated)

#### Scenario: Long model names are truncated
- **WHEN** a base model name exceeds ~10 characters
- **THEN** the displayed label is truncated with an ellipsis

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are present
- **THEN** the chart height is always 350 pixels

#### Scenario: Provider legend appears below the chart
- **WHEN** the chart shows model groups from multiple providers
- **THEN** a horizontal legend with colored dots and provider names appears below the chart card

### Requirement: RuntimeBarChart shows tooltips on hover
Hovering over a grouped bar SHALL display a tooltip with the provider/base-model group name and each effort's total runtime and average per-fixture time. The tooltip SHALL identify the fastest effort in the group.

#### Scenario: Tooltip on hover
- **WHEN** a user hovers over a grouped runtime bar
- **THEN** a tooltip appears showing the provider/base-model group name and the runtime for each effort

#### Scenario: Tooltip shows average per-fixture time
- **WHEN** a user hovers over a grouped runtime bar
- **THEN** the tooltip shows average fixture time for each effort where available

#### Scenario: Tooltip identifies fastest effort
- **WHEN** one effort has the lowest runtime in a grouped runtime bar
- **THEN** the tooltip identifies that effort as the fastest value used for sorting

### Requirement: RuntimeBarChart handles models without runtime data
If a selected model group has child efforts with no entry in `model_runtimes`, those child efforts SHALL be excluded from that group's runtime range and tooltip. If a selected model group has no child efforts with runtime data, the group SHALL be excluded from the chart. If NO selected model group has runtime data, the component SHALL display a message: "No runtime data available."

#### Scenario: Effort without runtime data excluded
- **WHEN** one effort in a selected model group has no `model_runtimes` entry
- **THEN** that effort does not contribute to the group's runtime range

#### Scenario: Group without runtime data excluded
- **WHEN** a selected model group has no child efforts with `model_runtimes` entries
- **THEN** that model group does not appear as a bar

#### Scenario: All selected groups lack runtime data
- **WHEN** every selected model group lacks runtime data
- **THEN** the chart area displays "No runtime data available"

### Requirement: RuntimeBarChart includes ModelSelector filter
The `RuntimeBarChart` component SHALL include a `ModelSelector` dropdown allowing users to filter which provider/base-model groups appear in the chart. The selector SHALL use the shared Overview model group selection state. When any other Overview chart selector changes the selected group set, `RuntimeBarChart` SHALL update its rendered bars and provider legend from that same selected group set. Groups without runtime data SHALL remain excluded from the rendered bars even when selected.

#### Scenario: Filter removes model group from chart
- **WHEN** a user deselects a model group in the ModelSelector
- **THEN** that model group's bar is removed from the chart

#### Scenario: External selection updates runtime chart
- **WHEN** a user changes the selected model groups in another Overview chart's ModelSelector
- **THEN** `RuntimeBarChart` updates its bars to match the new selected group set, excluding selected groups without runtime data

#### Scenario: Selector remains available when no selected groups have runtime data
- **WHEN** the selected group set contains no model groups with entries in `model_runtimes`
- **THEN** `RuntimeBarChart` displays "No runtime data available" and still renders the ModelSelector

### Requirement: RuntimeBarChart is placed on Models overview page
The `RuntimeBarChart` component SHALL be rendered on `/` (the Overview/Home page) after the Cost per Full Run section, in its own section labeled "Runtime (Wall Clock)". It SHALL be loaded with `client:load`.

#### Scenario: Chart on overview page
- **WHEN** navigating to `/`
- **THEN** a "Runtime (Wall Clock)" section with the grouped horizontal bar chart is visible

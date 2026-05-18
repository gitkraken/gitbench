## MODIFIED Requirements

### Requirement: TokenUsageChart renders horizontal bar chart

The `TokenUsageChart` React component SHALL render a Recharts horizontal bar chart (bars go right, Y-axis = provider/base-model group, X-axis = total tokens). Each bar SHALL represent one selected provider/base-model group and SHALL visualize the range from the lowest effort token total to the highest effort token total in that group. The lowest effort token total SHALL be the representative value used for sorting and bar prominence. Bars SHALL be color-coded by provider using the `getProviderColor()` palette. Y-axis tick labels SHALL display the provider brand icon (via `ProviderIcon`) and the truncated base model name (max ~10 characters + ellipsis). The component SHALL accept a `data` prop containing the full dataset. Chart height SHALL be fixed at 350 pixels. A provider legend SHALL be rendered below the chart card showing colored dots for each unique provider present.

#### Scenario: Bars render for selected model groups
- **WHEN** `TokenUsageChart` renders with 5 selected model groups
- **THEN** 5 horizontal grouped bars are displayed representing token usage ranges for each selected base model

#### Scenario: Bars sorted by token count
- **WHEN** model groups have lowest effort token totals [5000, 12000, 8000, 3000, 15000]
- **THEN** bars appear in ascending order: 3000, 5000, 8000, 12000, 15000

#### Scenario: Effort range shown for tokens
- **WHEN** `openai/gpt-5` has effort token totals 5,000, 8,000, and 12,000
- **THEN** the `openai/gpt-5` bar visualizes the range 5,000-12,000 and uses 5,000 as the representative value

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

### Requirement: TokenUsageChart computes total tokens from fixture data

The `TokenUsageChart` component SHALL compute total tokens per model+effort by summing `total_tokens` across all fixture results for that full model name. Null `total_tokens` values SHALL be treated as 0 in the sum. The component SHALL then group those per-effort totals by provider/base model to compute the displayed range. Computed totals SHALL be displayed as formatted numbers (e.g., "12.5K" for 12,500, "1.2M" for 1,200,000).

#### Scenario: Tokens summed across fixtures
- **WHEN** a model effort has 3 fixtures with total_tokens [100, 200, null]
- **THEN** that effort's token total is 300 before group range calculation

#### Scenario: Group range computed from effort totals
- **WHEN** a model group has effort token totals [300, 500, 900]
- **THEN** the grouped bar visualizes the range 300-900

#### Scenario: Model with all null token data
- **WHEN** every fixture for a model effort has `total_tokens: null`
- **THEN** that effort contributes 0 tokens to its model group's range

#### Scenario: Large token counts are formatted compactly
- **WHEN** an effort has 1,250,000 total tokens
- **THEN** the tooltip and axis display "1.25M"

### Requirement: TokenUsageChart shows tooltips on hover

Hovering over a grouped bar SHALL display a tooltip with the provider/base-model group name and each effort's total token count formatted compactly. When available, the tooltip SHALL include input and output token breakdowns per effort. The tooltip SHALL identify the lowest-token effort used for sorting.

#### Scenario: Tooltip on hover
- **WHEN** a user hovers over a grouped token bar
- **THEN** a tooltip appears showing the provider/base-model group name and total token count for each effort

#### Scenario: Tooltip shows breakdown when available
- **WHEN** input_tokens and output_tokens data exists for an effort
- **THEN** the tooltip shows input and output token counts for that effort in addition to total tokens

#### Scenario: Tooltip identifies lowest-token effort
- **WHEN** one effort has the lowest token total in a grouped token bar
- **THEN** the tooltip identifies that effort as the value used for sorting

### Requirement: TokenUsageChart handles empty token data

If ALL selected model groups have no token data (every child effort has `total_tokens` null or zero), the component SHALL display a message: "No token data available."

#### Scenario: All selected groups lack token data
- **WHEN** every fixture across all selected model groups has `total_tokens: null`
- **THEN** the chart area displays "No token data available"

### Requirement: TokenUsageChart is placed on Models overview page

The `TokenUsageChart` component SHALL be rendered on `/` (the Overview/Home page) after the Cost per Full Run section, inside a section labeled "Token Usage". It SHALL be loaded with `client:load`.

#### Scenario: Chart on overview page
- **WHEN** navigating to `/`
- **THEN** a "Token Usage" section with the grouped horizontal bar chart is visible below the Runtime section

### Requirement: TokenUsageChart includes ModelSelector filter

The `TokenUsageChart` component SHALL include a `ModelSelector` dropdown allowing users to filter which provider/base-model groups appear in the chart. The selector SHALL use the shared Overview model group selection state. When any other Overview chart selector changes the selected group set, `TokenUsageChart` SHALL update its rendered bars and provider legend from that same selected group set.

#### Scenario: Filter removes model group from chart
- **WHEN** a user deselects a model group in the ModelSelector
- **THEN** that model group's bar is removed from the chart

#### Scenario: External selection updates token chart
- **WHEN** a user changes the selected model groups in another Overview chart's ModelSelector
- **THEN** `TokenUsageChart` updates its bars to match the new selected group set

#### Scenario: Selector remains available when selected groups have no token data
- **WHEN** every model group in the selected group set has zero collected total tokens
- **THEN** `TokenUsageChart` displays "No token data available" and still renders the ModelSelector

# token-usage-chart Specification

## Purpose
TBD - created by archiving change overview-chart-improvements. Update Purpose after archive.
## Requirements
### Requirement: TokenUsageChart computes total tokens from fixture data

Token sums SHALL be unaffected by this change. Reasoning tokens are already included in `total_tokens` from the API response.

(All original scenarios remain unchanged.)

#### Scenario: Reasoning tokens included in total
- **WHEN** a model effort has 3 fixtures with reasoning_tokens [50, null, 100]
- **THEN** those reasoning tokens are included in the effort's total via the `total_tokens` sum (since total_tokens already includes reasoning from the API)

### Requirement: TokenUsageChart shows tooltips on hover
Hovering or keyboard-focusing a token bar SHALL display one category-level tooltip with the provider/base-model group name. The tooltip SHALL separate available efforts into `Text` and `JSON` sections according to the selected output mode. Each section SHALL show its own representative median total token count, each effort's compactly formatted total, and available input/output token breakdowns. When `Both` is selected and a mode has no token data for the group, that mode's section SHALL show `No data`.

#### Scenario: Either sibling opens the shared tooltip
- **WHEN** a user hovers either the text or JSON token bar in a paired category
- **THEN** one tooltip appears for the provider/base-model group with separate mode sections

#### Scenario: Tooltip shows token breakdown by mode
- **WHEN** input and output token data exists for efforts in both modes
- **THEN** each mode section shows the input/output breakdown beside the corresponding effort total

#### Scenario: Tooltip identifies each mode representative
- **WHEN** text and JSON mode summaries have different median token totals
- **THEN** the tooltip displays the representative median independently in each mode section

#### Scenario: Tooltip shows unavailable mode
- **WHEN** `Both` is selected and the group has text token data but no JSON token data
- **THEN** the tooltip's JSON section reads `No data`

### Requirement: TokenUsageChart handles empty token data

If ALL selected model groups have no token data (every child effort has `total_tokens` null or zero), the component SHALL display a message: "No token data available."

#### Scenario: All selected groups lack token data
- **WHEN** every fixture across all selected model groups has `total_tokens: null`
- **THEN** the chart area displays "No token data available"

### Requirement: TokenUsageChart is placed on Models overview page

The `TokenUsageChart` component SHALL be rendered on `/` (the Overview/Home page) after the Cost per Full Run section, inside a section labeled "Token Usage". It SHALL be loaded with `client:load`.

#### Scenario: Chart on overview page
- **WHEN** navigating to `/`
- **THEN** a "Token Usage" section with the grouped vertical range-whisker bar chart is visible below the Runtime section

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

### Requirement: TokenUsageChart renders vertical range-whisker bar chart
The `TokenUsageChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = provider/base-model group, Y-axis = total tokens). For a single output-mode selection, each category SHALL show that mode's median sorted, deduped effort token total from zero with a neutral range whisker from the lowest to highest effort total in that mode. When `Both` is selected, each category SHALL show adjacent text and JSON bars with independently calculated medians and range whiskers. The Y-axis domain SHALL start at 0 and include the highest displayed effort token total. Bars SHALL be color-coded by provider using the `getProviderColor()` palette and SHALL use the shared output-mode visual treatments. X-axis tick labels SHALL display one provider brand icon and truncated base model name (max ~10 characters + ellipsis) per category, rotated `-40` degrees. Chart height SHALL be fixed at 350 pixels. Provider and output-mode legends SHALL be rendered below the chart as applicable. Categories SHALL be sorted lowest-token-first by the selected mode representative, or by the mean of available text and JSON representatives in `Both` mode.

#### Scenario: Both mode renders paired token bars
- **WHEN** `Both` is selected for `openai/gpt-5`
- **THEN** the category displays adjacent text and JSON token bars where both modes have data

#### Scenario: Token ranges are independent by mode
- **WHEN** text totals are 5,000, 8,000, and 12,000 and JSON totals are 6,000, 9,000, and 11,000
- **THEN** the text bar extends to 8,000 with a 5,000-12,000 whisker and the JSON bar extends to 9,000 with a 6,000-11,000 whisker

#### Scenario: Duplicate totals are deduped within each mode
- **WHEN** one mode has token totals 5,000, 5,000, 5,000, 8,000, and 12,000
- **THEN** that mode's representative token total is 8,000 from deduped values [5,000, 8,000, 12,000]

#### Scenario: Single mode sorts by its representative
- **WHEN** text mode is selected and categories have representative token totals [5000, 12000, 8000, 3000, 15000]
- **THEN** categories appear from left to right in order 3000, 5000, 8000, 12000, 15000

#### Scenario: Both mode sorts by mean representative tokens
- **WHEN** two categories have text/JSON representative totals `[5,000, 15,000]` and `[8,000, 10,000]`
- **THEN** the second category appears first because its mean is 9,000 rather than 10,000

#### Scenario: Missing JSON tokens preserve text category
- **WHEN** `Both` is selected and a category has text token data but no JSON token data
- **THEN** the text bar renders, the JSON bar slot is empty, and the category sorts using the text representative

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** both mode bars use the Anthropic palette color (#D97757) with their respective mode treatments

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are present
- **THEN** the chart height is always 350 pixels

### Requirement: TokenUsageChart renders reasoning tokens as a stacked bar segment

The `TokenUsageChart` component SHALL render reasoning tokens as a third stacked segment in each bar when any effort in the group has a reasoning level set. The reasoning segment SHALL use a lighter tint of the provider color. Groups with no reasoning-level efforts SHALL render as two-segment bars (input | output) only.

#### Scenario: Reasoning segment for reasoning models
- **WHEN** a model group has efforts at `low`, `medium`, `high` with reasoning tokens [150, 200, 300]
- **THEN** each bar shows three stacked segments: input, output, and reasoning

#### Scenario: No reasoning segment for non-reasoning models
- **WHEN** a model group's efforts all have `reasoning_level: null`
- **THEN** each bar shows only input and output segments (no reasoning segment)

#### Scenario: Reasoning segment uses lighter color tint
- **WHEN** a provider's color is `#3B82F6` (blue)
- **THEN** the reasoning segment uses a translucent variant (e.g., `rgba(59, 130, 246, 0.35)`) visually distinct from output

### Requirement: TokenUsageChart tooltip shows reasoning token breakdown

The chart tooltip's `renderEffort` line SHALL display `in / out / r` when the effort has a reasoning level. Without a reasoning level, the line SHALL display `in / out` only. The breakdown SHALL use the same compact formatting as other values.

#### Scenario: Tooltip with reasoning tokens
- **WHEN** hovering a bar for an effort with `reasoningTokens: 150`, `inputTokens: 500`, `outputTokens: 200`
- **THEN** the effort line reads `low: 850 (in 500 / out 200 / r 150)`

#### Scenario: Tooltip without reasoning level
- **WHEN** hovering a bar for an effort with `reasoningLevel: null`
- **THEN** the effort line reads `default: 700 (in 500 / out 200)` with no reasoning mention

#### Scenario: Tooltip with zero reasoning tokens
- **WHEN** hovering a bar for an effort with `reasoningLevel: "high"` and `reasoningTokens: 0`
- **THEN** the effort line reads `high: 700 (in 500 / out 200 / r 0)`


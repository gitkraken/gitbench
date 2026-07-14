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
The `TokenUsageChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = provider/base-model group, Y-axis = total tokens). For a single output-mode selection, each category SHALL show that mode's median sorted, deduped effort token total from zero with a neutral range whisker from the lowest to highest effort total in that mode. When `Both` is selected, each category SHALL show adjacent text and JSON bars with independently calculated medians and range whiskers. The Y-axis domain SHALL start at 0 and include the highest displayed effort token total. Bars SHALL be color-coded by provider using the `getProviderColor()` palette and SHALL use the shared output-mode visual treatments. X-axis tick labels SHALL display one provider brand icon and the full base model name per category without ellipsis or text truncation, rotated `-40` degrees. Chart height SHALL be fixed at 350 pixels. Provider and output-mode legends SHALL be rendered below the chart as applicable. Categories SHALL be sorted lowest-token-first by the selected mode representative, or by the mean of available text and JSON representatives in `Both` mode.

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

#### Scenario: Full label renders for long base model
- **WHEN** a token chart category is `google/gemini-3.1-flash-lite-preview`
- **THEN** the X-axis tick shows `gemini-3.1-flash-lite-preview` in full without ellipsis

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are present
- **THEN** the chart height is always 350 pixels

### Requirement: TokenUsageChart renders reasoning tokens as a stacked bar segment
The `TokenUsageChart` component SHALL render reasoning tokens as a stacked decomposition of provider-reported output when the representative effort has reasoning data. Each representative bar SHALL stack input tokens, derived visible output tokens, and bounded reasoning-within-output tokens so the full stack equals the representative effort's `total_tokens` when provider totals are internally consistent. When a representative effort reports more reasoning tokens than output tokens, the chart SHALL preserve the raw reasoning value for tooltip disclosure, but SHALL cap the stacked reasoning segment at provider output and SHALL not stack reasoning overflow as additional total tokens. The reasoning segment SHALL use a lighter tint of the provider color. Groups with no reasoning data SHALL render input and output only.

#### Scenario: Reasoning stack does not double-count output
- **WHEN** the representative effort has input 500, provider output 200, reasoning 150, and total 700
- **THEN** the bar SHALL stack 500 input, 50 visible output, and 150 reasoning to a height of 700

#### Scenario: Representative effort supplies stack segments
- **WHEN** a mode contains multiple effort levels and its median representative is `medium`
- **THEN** the bar segments SHALL use the `medium` effort's token decomposition rather than sums across all effort levels

#### Scenario: No reasoning segment for non-reasoning data
- **WHEN** a representative effort has no reasoning token data
- **THEN** its bar SHALL render input and provider output segments with no reasoning segment

#### Scenario: Reasoning segment uses lighter color tint
- **WHEN** a provider's color is `#3B82F6`
- **THEN** the reasoning segment SHALL use a translucent variant visually distinct from visible output

#### Scenario: Inconsistent provider counts are capped
- **WHEN** a representative effort reports input 500, output 100, total 600, and reasoning 120
- **THEN** the visible-output segment SHALL be zero
- **AND** the stacked reasoning segment SHALL be capped at 100
- **AND** the bar SHALL not render a negative segment
- **AND** the bar SHALL not stack the 20-token reasoning overflow above the provider total

### Requirement: TokenUsageChart tooltip shows reasoning token breakdown
The chart tooltip SHALL place a compact, color-coded `Total · (in / out / reasoning)` legend above its mode sections. Each effort SHALL render its total and grouped input, provider output, and bounded reasoning values on one line using the same effort-row font size as other chart tooltips. The grouped values SHALL use colors that correspond to the legend and SHALL use compact number formatting so the tooltip remains narrow without reducing the effort-row type size. Missing reasoning data SHALL use an unavailable marker in the reasoning position rather than verbose explanatory copy.

When raw reasoning tokens exceed provider output tokens, the reasoning position SHALL show bounded reasoning plus overflow using compact `bounded+overflow*` notation. The tooltip SHALL explain the marker once with a shared provider-overflow footnote and SHALL not repeat overflow prose on every effort row. The grouped values and footnote together SHALL preserve the raw reasoning value without presenting overflow as additional output or chart height. The tooltip content SHALL be capped at 300 CSS pixels wide.

#### Scenario: Tooltip with reasoning tokens
- **WHEN** an effort has input 500, provider output 200, reasoning 150, and total 700
- **THEN** the tooltip SHALL show a single effort row equivalent to `700 · (500 / 200 / 150)` under the color-coded grouping legend
- **AND** the effort row SHALL use the same font size as effort rows in other chart tooltips

#### Scenario: Tooltip without reasoning data
- **WHEN** an effort has input 500, output 200, and no reasoning token data
- **THEN** the tooltip SHALL show a grouped value equivalent to `(500 / 200 / —)` without adding an explanatory line

#### Scenario: Tooltip with zero reasoning tokens
- **WHEN** an effort has a reasoning level, provider output 200, and `reasoning_tokens: 0`
- **THEN** the tooltip SHALL show zero in the color-coded reasoning position

#### Scenario: Tooltip with inconsistent provider telemetry
- **WHEN** an effort has input 500, provider output 100, reasoning 120, and total 600
- **THEN** the tooltip SHALL show a single effort row equivalent to `600 · (500 / 100 / 100+20*)`
- **AND** the tooltip SHALL show one shared footnote identifying `*` as provider-reported reasoning overflow
- **AND** the tooltip SHALL not render a separate verbose overflow line for the effort

#### Scenario: Dense tooltip remains compact and readable
- **WHEN** both output modes contain multiple effort levels
- **THEN** every effort's total and grouped token values SHALL remain on one row
- **AND** the tooltip content width SHALL not exceed 300 CSS pixels
- **AND** the implementation SHALL use compact number formatting rather than a smaller effort-row font to satisfy the width constraint

### Requirement: TokenUsageChart ranks models by mean per-trial token usage

`TokenUsageChart` SHALL rank comparable model configurations by mean token usage per complete trial and SHALL expose total campaign tokens, trial counts, and reasoning-token detail separately.

#### Scenario: Compare campaigns with different trial counts

- **WHEN** two model summaries use different trial counts
- **THEN** bar magnitude SHALL use mean tokens per complete trial
- **AND** the tooltip SHALL show total tokens and completed trials

#### Scenario: Preserve reasoning-effort range meaning

- **WHEN** a bar aggregates multiple reasoning efforts
- **THEN** the range-whisker encoding SHALL continue to represent reasoning-effort range
- **AND** trial variability SHALL be separately labeled

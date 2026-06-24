## Purpose

The CostValueChart provides a quadrant scatter plot comparing each model's total cost against its pass rate.
## Requirements
### Requirement: CostValueChart shows tooltips on hover
Hovering or keyboard-focusing a cost bar SHALL display one category-level tooltip with the provider/base-model group name. The tooltip SHALL separate available efforts into `Text` and `JSON` sections according to the selected output mode. Each section SHALL show its own representative median total cost and each effort's total cost formatted as USD with pass rate context. When `Both` is selected and a mode has no cost data for the group, that mode's section SHALL show `No data`.

#### Scenario: Either sibling opens the shared tooltip
- **WHEN** a user hovers either the text or JSON cost bar in a paired category
- **THEN** one tooltip appears for the provider/base-model group with separate mode sections

#### Scenario: Tooltip shows pass rate context by mode
- **WHEN** pass rates exist for text and JSON cost efforts
- **THEN** each mode section shows the pass rate beside the corresponding effort cost

#### Scenario: Tooltip identifies each mode representative
- **WHEN** text and JSON mode summaries have different median total costs
- **THEN** the tooltip displays the representative median independently in each mode section

#### Scenario: Tooltip shows unavailable mode
- **WHEN** `Both` is selected and the group has text cost data but no JSON cost data
- **THEN** the tooltip's JSON section reads `No data`

### Requirement: CostValueChart handles models without cost data

Child efforts with no cost data (`total_cost_usd` is null) SHALL NOT contribute to their model group's cost range or tooltip. If a selected model group has no child efforts with cost data, that group SHALL NOT appear on the chart. If ALL selected model groups lack cost data, the component SHALL display a message: "No pricing data available."

#### Scenario: Effort without cost is excluded
- **WHEN** one effort in a selected model group has null `total_cost_usd` and other efforts have valid costs
- **THEN** only the efforts with valid costs contribute to that group's cost range

#### Scenario: Group without cost is excluded
- **WHEN** a selected model group has no efforts with valid `total_cost_usd`
- **THEN** that group does not appear as a bar

#### Scenario: All selected groups lack cost data
- **WHEN** every selected model group lacks valid `total_cost_usd`
- **THEN** the chart area displays "No pricing data available"

### Requirement: CostValueChart is placed on Models overview page

The `CostValueChart` component SHALL be rendered on `/` (the Overview/Home page) inside a section labeled "Cost per Full Run". It SHALL be loaded with `client:load`.

#### Scenario: Chart on overview page
- **WHEN** navigating to `/`
- **THEN** a "Cost per Full Run" section with the grouped vertical range-whisker bar chart is visible

### Requirement: CostValueChart bars navigate to model detail

Clicking a grouped bar SHALL navigate the browser to `/models/<provider>/<base-model>/`.

#### Scenario: Click navigates to base model detail
- **WHEN** a user clicks on the grouped bar for model group `anthropic/claude-opus-4.7`
- **THEN** the browser navigates to `/models/anthropic/claude-opus-4.7/`

### Requirement: CostValueChart includes ModelSelector filter

The `CostValueChart` component SHALL include a `ModelSelector` dropdown allowing users to filter which provider/base-model groups appear in the chart. The selector SHALL use the shared Overview model group selection state. When any other Overview chart selector changes the selected group set, `CostValueChart` SHALL update its rendered bars and provider legend from that same selected group set. Groups without cost data SHALL remain excluded from the rendered bars even when selected.

#### Scenario: Filter removes model group from chart
- **WHEN** a user deselects a model group in the ModelSelector
- **THEN** that model group's bar is removed from the chart

#### Scenario: External selection updates cost chart
- **WHEN** a user changes the selected model groups in another Overview chart's ModelSelector
- **THEN** `CostValueChart` updates its bars to match the new selected group set, excluding selected groups without cost data

#### Scenario: Selector remains available when no selected groups have cost data
- **WHEN** the selected group set contains no model groups with valid `total_cost_usd`
- **THEN** `CostValueChart` displays "No pricing data available" and still renders the ModelSelector

### Requirement: CostValueChart renders vertical range-whisker bar chart
The `CostValueChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = provider/base-model group, Y-axis = total cost in USD). For a single output-mode selection, each category SHALL show that mode's median sorted, deduped effort total cost from zero using `summary.total_cost_usd`, with a neutral range whisker from the lowest to highest effort cost in that mode. When `Both` is selected, each category SHALL show adjacent text and JSON bars with independently calculated medians and range whiskers. The Y-axis domain SHALL start at 0 and include the highest displayed effort cost. Bars SHALL be color-coded by provider using the `getProviderColor()` palette and SHALL use the shared output-mode visual treatments. X-axis tick labels SHALL display one provider brand icon and truncated base model name (max ~10 characters + ellipsis) per category, rotated `-40` degrees. Chart height SHALL be fixed at 350 pixels. Provider and output-mode legends SHALL be rendered below the chart as applicable. Categories SHALL be sorted lowest-cost-first by the selected mode representative, or by the mean of available text and JSON representatives in `Both` mode.

#### Scenario: Both mode renders paired cost bars
- **WHEN** `Both` is selected for `openai/gpt-5`
- **THEN** the category displays adjacent text and JSON cost bars where both modes have data

#### Scenario: Cost ranges are independent by mode
- **WHEN** text costs are $0.10, $0.20, and $0.50 and JSON costs are $0.12, $0.30, and $0.45
- **THEN** the text bar extends to $0.20 with a $0.10-$0.50 whisker and the JSON bar extends to $0.30 with a $0.12-$0.45 whisker

#### Scenario: Duplicate costs are deduped within each mode
- **WHEN** one mode has effort costs $0.10, $0.10, $0.10, $0.20, and $0.50
- **THEN** that mode's representative cost is $0.20 from deduped values [$0.10, $0.20, $0.50]

#### Scenario: Single mode sorts by its representative
- **WHEN** text mode is selected and categories have representative costs [$0.10, $0.20, $0.50, $0.80]
- **THEN** categories appear from left to right in ascending cost order

#### Scenario: Both mode sorts by mean representative cost
- **WHEN** two categories have text/JSON representative costs `[$0.10, $0.50]` and `[$0.20, $0.30]`
- **THEN** the second category appears first because its mean is $0.25 rather than $0.30

#### Scenario: Missing JSON cost preserves text category
- **WHEN** `Both` is selected and a category has text cost data but no JSON cost data
- **THEN** the text bar renders, the JSON bar slot is empty, and the category sorts using the text representative

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** both mode bars use the Anthropic palette color (#D97757) with their respective mode treatments

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are present
- **THEN** the chart height is always 350 pixels

### Requirement: CostValueChart ranks comparable per-trial cost and reliability

`CostValueChart` SHALL plot mean cost per complete trial against mean one-attempt success for complete campaign summaries and SHALL expose total campaign cost separately.

#### Scenario: Render a five-trial campaign

- **WHEN** a model campaign summary has five complete trials
- **THEN** its cost axis SHALL use mean cost per complete trial
- **AND** its value axis SHALL use mean one-attempt success
- **AND** the tooltip SHALL show total campaign cost and attempt counts

#### Scenario: Campaign cost is partial

- **WHEN** pricing data is incomplete
- **THEN** the point SHALL be identified as partial
- **AND** it SHALL be excluded from default cost ranking


### Requirement: CostValueChart y-axis ticks never use scientific notation

The y-axis tick formatter on the `CostValueChart` SHALL render every
tick value as a USD currency string with no scientific notation. Tick
value `0` SHALL render as `$0`. Tick values smaller than `0.01` SHALL
render with up to four fraction digits (e.g. `$0.0052`). Non-finite
values (`NaN`, `Infinity`) SHALL render as `—`. The formatter SHALL be
shared by the chart's tooltip and the bar value labels.

#### Scenario: Zero tick renders as $0
- **WHEN** the y-axis includes the tick value `0`
- **THEN** the rendered tick label is `$0` and never contains `e+`, `e-`, or `E+`

#### Scenario: Sub-cent tick renders with enough precision
- **WHEN** a tick value is `0.00516`
- **THEN** the rendered tick label is `$0.0052` (or `$0.00516` if four fraction digits are kept), never `$5.2e-3`

#### Scenario: Non-finite tick renders as em dash
- **WHEN** the y-axis domain would otherwise include `NaN` or `Infinity`
- **THEN** the rendered tick label is `—`

## MODIFIED Requirements

### Requirement: CostValueChart renders vertical range-whisker bar chart
The `CostValueChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = provider/base-model group, Y-axis = total cost in USD). For a single output-mode selection, each category SHALL show that mode's median sorted, deduped effort total cost from zero using `summary.total_cost_usd`, with a neutral range whisker from the lowest to highest effort cost in that mode. When `Both` is selected, each category SHALL show adjacent text and JSON bars with independently calculated medians and range whiskers. The Y-axis domain SHALL start at 0 and include the highest displayed effort cost. Bars SHALL be color-coded by provider using the `getProviderColor()` palette and SHALL use the shared output-mode visual treatments. X-axis tick labels SHALL display one provider brand icon and the full base model name per category without ellipsis or text truncation, rotated `-40` degrees. Chart height SHALL be fixed at 350 pixels. Provider and output-mode legends SHALL be rendered below the chart as applicable. Categories SHALL be sorted highest-cost-first by the selected mode representative, or by the mean of available text and JSON representatives in `Both` mode.

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
- **THEN** categories appear from left to right in order $0.80, $0.50, $0.20, $0.10

#### Scenario: Both mode sorts by mean representative cost
- **WHEN** two categories have text/JSON representative costs `[$0.10, $0.50]` and `[$0.20, $0.30]`
- **THEN** the first category appears first because its mean is $0.30 rather than $0.25

#### Scenario: Missing JSON cost preserves text category
- **WHEN** `Both` is selected and a category has text cost data but no JSON cost data
- **THEN** the text bar renders, the JSON bar slot is empty, and the category sorts using the text representative

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** both mode bars use the Anthropic palette color (#D97757) with their respective mode treatments

#### Scenario: Full label renders for long base model
- **WHEN** a cost chart category is `google/gemini-3.1-flash-lite-preview`
- **THEN** the X-axis tick shows `gemini-3.1-flash-lite-preview` in full without ellipsis

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are present
- **THEN** the chart height is always 350 pixels

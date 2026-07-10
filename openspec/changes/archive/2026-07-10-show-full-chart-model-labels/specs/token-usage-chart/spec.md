## MODIFIED Requirements

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

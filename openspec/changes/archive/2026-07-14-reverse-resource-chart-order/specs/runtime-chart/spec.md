## MODIFIED Requirements

### Requirement: RuntimeBarChart renders vertical range-whisker bar chart ranking models by speed
The `RuntimeBarChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = provider/base-model group, Y-axis = total API time in seconds). For a single output-mode selection, each category SHALL show that mode's median sorted, deduped effort API time from zero with a neutral range whisker from the fastest to slowest effort in that mode. When `Both` is selected, each category SHALL show adjacent text and JSON bars with independently calculated medians and range whiskers. The Y-axis domain SHALL start at 0 and include the slowest displayed effort API time. Bars SHALL be color-coded by provider using the `getProviderColor()` palette and SHALL use the shared output-mode visual treatments. X-axis tick labels SHALL display one provider brand icon and the full base model name per category without ellipsis or text truncation, rotated `-40` degrees. Chart height SHALL be fixed at 350 pixels. Provider and output-mode legends SHALL be rendered below the chart as applicable. Categories SHALL be sorted highest-API-time-first by the selected mode representative, or by the mean of available text and JSON representatives in `Both` mode.

#### Scenario: Both mode renders paired API-time bars
- **WHEN** `Both` is selected for `openai/gpt-5`
- **THEN** the category displays adjacent text and JSON API-time bars where both modes have data

#### Scenario: API-time ranges are independent by mode
- **WHEN** text API times are 45s, 70s, and 110s and JSON API times are 35s, 55s, and 80s
- **THEN** the text bar extends to 70s with a 45s-110s whisker and the JSON bar extends to 55s with a 35s-80s whisker

#### Scenario: Duplicate API times are deduped within each mode
- **WHEN** one mode has API times 45s, 45s, 45s, 70s, and 110s
- **THEN** that mode's representative API time is 70s from deduped values [45s, 70s, 110s]

#### Scenario: Single mode sorts by its representative
- **WHEN** text mode is selected and model categories have representative API times [5000, 12000, 3000, 8000]
- **THEN** categories appear from left to right in order 12000, 8000, 5000, 3000

#### Scenario: Both mode sorts by mean representative time
- **WHEN** two categories have text/JSON representative API times `[40s, 60s]` and `[45s, 50s]`
- **THEN** the first category appears first because its mean is 50s rather than 47.5s

#### Scenario: Missing JSON time preserves text category
- **WHEN** `Both` is selected and a category has text API-time data but no JSON API-time data
- **THEN** the text bar renders, the JSON bar slot is empty, and the category sorts using the text representative

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** both mode bars use the Anthropic palette color (#D97757) with their respective mode treatments

#### Scenario: Full label renders for long base model
- **WHEN** an API-time chart category is `google/gemini-3.1-flash-lite-preview`
- **THEN** the X-axis tick shows `gemini-3.1-flash-lite-preview` in full without ellipsis

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are present
- **THEN** the chart height is always 350 pixels

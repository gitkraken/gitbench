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
Hovering or keyboard-focusing a runtime bar SHALL display one category-level tooltip with the provider/base-model group name. The tooltip SHALL separate available efforts into `Text` and `JSON` sections according to the selected output mode. Each section SHALL show its own representative median API time and each effort's total API time and average per-fixture API time. When `Both` is selected and a mode has no API-time data for the group, that mode's section SHALL show `No data`.

#### Scenario: Either sibling opens the shared tooltip
- **WHEN** a user hovers either the text or JSON runtime bar in a paired category
- **THEN** one tooltip appears for the provider/base-model group with separate mode sections

#### Scenario: Tooltip shows average per-fixture API time by mode
- **WHEN** average fixture API time exists for efforts in both modes
- **THEN** each mode section shows the average API time beside the corresponding effort

#### Scenario: Tooltip identifies each mode representative
- **WHEN** text and JSON mode summaries have different median API times
- **THEN** the tooltip displays the representative median independently in each mode section

#### Scenario: Tooltip shows unavailable mode
- **WHEN** `Both` is selected and the group has text API-time data but no JSON API-time data
- **THEN** the tooltip's JSON section reads `No data`

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

### Requirement: RuntimeBarChart ranks models by mean per-trial API time

`RuntimeBarChart` SHALL rank comparable model configurations by mean API time per complete trial for the selected campaign and SHALL expose total campaign API time and trial variability as secondary detail.

#### Scenario: Render campaigns with different trial counts

- **WHEN** model summaries contain different planned trial counts
- **THEN** bar magnitude SHALL use mean API time per complete trial
- **AND** the tooltip SHALL show completed trials, total API time, and campaign completeness

#### Scenario: Preserve reasoning-effort range meaning

- **WHEN** a bar aggregates multiple reasoning efforts
- **THEN** its existing range-whisker encoding SHALL continue to represent reasoning-effort range
- **AND** repeated-trial variability SHALL use separately labeled detail

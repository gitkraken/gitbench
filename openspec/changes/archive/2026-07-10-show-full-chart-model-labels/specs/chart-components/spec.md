## MODIFIED Requirements

### Requirement: Overview grouped metric charts use vertical range-whisker bars
Overview grouped metric bar charts SHALL use a shared vertical chart language for pass rate, cost, API time, and token usage. Each chart SHALL place provider/base-model groups on the X-axis and the metric value on the Y-axis. For a single output-mode selection, each provider/base-model category SHALL render one provider-colored bar whose value is the median of the deduped effort values for that mode, with a neutral range whisker spanning that mode's minimum and maximum effort values. When `Both` is selected, each category SHALL render adjacent `Text` and `JSON` bars, and each bar SHALL use an independently computed median and range whisker from only that output mode's efforts. Text bars SHALL use the solid provider color. JSON bars SHALL use the same provider color with reduced fill opacity and a visible outline. Range whiskers SHALL NOT be described as error bars in user-facing copy or specs.

#### Scenario: Single mode shows one representative bar
- **WHEN** a grouped metric row in `Text` mode has deduped effort values `[72, 81, 85]`, `minValue=72`, and `maxValue=85`
- **THEN** one solid text bar extends from 0 to 81 and its range whisker spans 72 to 85

#### Scenario: Both mode shows independent sibling bars
- **WHEN** a model group has text effort values `[72, 81, 85]` and JSON effort values `[76, 88, 91]` while `Both` is selected
- **THEN** the category shows a text bar at 81 with a 72-85 whisker and an adjacent JSON bar at 88 with a 76-91 whisker

#### Scenario: Modes are not combined for the representative
- **WHEN** text effort values are `[10, 20]` and JSON effort values are `[80, 90]`
- **THEN** the text representative is 15 and the JSON representative is 85
- **AND** no displayed representative is calculated from the combined values `[10, 20, 80, 90]`

#### Scenario: Duplicate values do not overweight each mode median
- **WHEN** one output mode has effort values `[10, 10, 10, 20, 50]`
- **THEN** that mode's representative value is computed from deduped values `[10, 20, 50]`, so its bar extends from 0 to 20 and its whisker spans 10 to 50

#### Scenario: Numeric axis starts at zero
- **WHEN** any grouped metric chart renders
- **THEN** its numeric Y-axis lower bound is 0

#### Scenario: Diagonal group labels are reused for pairs
- **WHEN** a grouped metric chart renders paired text and JSON bars
- **THEN** both bars share one diagonal provider-icon label with `-40` degree rotation and the full base model name

#### Scenario: Dense group labels remain full length
- **WHEN** a grouped metric chart renders many selected provider/base-model groups with names longer than 20 characters
- **THEN** the X-axis labels remain full length without ellipsis or text truncation
- **AND** the chart provides enough label space or horizontal overflow so the labels are not clipped by their tick containers

#### Scenario: Single-effort mode remains visible
- **WHEN** one mode summary has equal minimum, maximum, and representative values
- **THEN** that mode's bar remains visible from 0 to the representative value and its range whisker may collapse or be omitted

#### Scenario: Missing sibling mode preserves the category
- **WHEN** `Both` is selected and a provider/base-model group has text data but no JSON data
- **THEN** the text bar renders in its normal sibling position, the JSON slot remains empty, and the model category remains on the chart

#### Scenario: Both mode includes a style legend
- **WHEN** a grouped metric chart renders with `Both` selected
- **THEN** a mode legend identifies the solid treatment as `Text` and the translucent outlined treatment as `JSON`

### Requirement: PassRateBarChart renders vertical range-whisker bar chart
The `PassRateBarChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = provider/base-model group, Y-axis = pass rate percentage). For a single output-mode selection, each category SHALL show that mode's median deduped effort pass rate from zero with a neutral range whisker from its lowest to highest effort pass rate. When `Both` is selected, each category SHALL show adjacent text and JSON bars with independently calculated medians and range whiskers. The Y-axis domain SHALL start at 0 and SHALL use 100 as the pass-rate ceiling. Bars SHALL be color-coded by provider using the `getProviderColor()` palette and SHALL use the shared output-mode visual treatments. X-axis tick labels SHALL be rotated diagonally (`-40` degrees) with a custom tick renderer that displays a provider brand icon (via `ProviderIcon`) and the full base model name without ellipsis or text truncation. The component SHALL accept optional `benchmarkName` and `selectedBenchmark` props. When `benchmarkName` is provided, pass rates SHALL be computed from `matrix[model][benchmarkName].pass_at_k` (per-benchmark), otherwise from `model_summaries[model].pass_at_k` (global). The tooltip footnote SHALL reflect the data source by showing the fixture count for the benchmark when filtered, or "204 fixtures" for global. Chart height SHALL be fixed at 350 pixels. A provider legend SHALL be rendered below the chart card showing colored dots for each unique provider present.

#### Scenario: Both mode renders paired pass-rate bars
- **WHEN** `Both` is selected for model groups `['anthropic/claude-opus-4.7', 'openai/gpt-oss-120b']`
- **THEN** each model category displays adjacent text and JSON pass-rate bars where those modes are available

#### Scenario: Effort ranges are independent by mode
- **WHEN** `openai/gpt-5` has text pass rates 72%, 81%, and 85% and JSON pass rates 76%, 88%, and 91%
- **THEN** the text bar extends to 81% with a 72%-85% whisker and the JSON bar extends to 88% with a 76%-91% whisker

#### Scenario: Single-mode rendering remains one bar
- **WHEN** the output-mode selection is `JSON`
- **THEN** each displayed model category contains one JSON bar and no reserved text bar

#### Scenario: Bars sorted by visible representative score
- **WHEN** a single output mode is selected and grouped models have representative pass rates 90%, 75%, and 82%
- **THEN** categories appear ordered by 90%, 82%, then 75%

#### Scenario: Both mode sorts by mean representative score
- **WHEN** `Both` is selected and two groups have text/JSON representatives `[90%, 70%]` and `[78%, 76%]`
- **THEN** the first group sorts ahead of the second because their mean representative scores are 80% and 77%

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** both of its mode bars use the Anthropic palette color (#D97757) with their respective mode treatments

#### Scenario: Colors reflect provider for fallback providers
- **WHEN** a model group has provider `unknown-provider`
- **THEN** its mode bars use a deterministic `hsl(hue, 55%, 48%)` provider color

#### Scenario: Diagonal labels show provider icon and full base model
- **WHEN** a model group is `openai/gpt-oss-120b`
- **THEN** its shared X-axis tick shows the OpenAI icon and `gpt-oss-120b` in full, rotated `-40` degrees

#### Scenario: Long model names remain full length
- **WHEN** a model group is `google/gemini-3.1-flash-lite-preview`
- **THEN** its shared X-axis tick shows `gemini-3.1-flash-lite-preview` in full without ellipsis

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are selected in single or both mode
- **THEN** the chart height is always 350 pixels

#### Scenario: Provider and mode legends appear below the chart
- **WHEN** the chart shows multiple providers with `Both` selected
- **THEN** the provider legend identifies provider colors and the mode legend identifies text and JSON bar treatments

#### Scenario: Either sibling triggers one separated tooltip
- **WHEN** a user hovers or keyboard-focuses either bar in a paired pass-rate category
- **THEN** one tooltip appears for the provider/base-model group with separate `Text` and `JSON` effort lists and a representative median for each available mode

#### Scenario: Missing mode is explicit in tooltip
- **WHEN** `Both` is selected and a category has text pass-rate data but no JSON pass-rate data
- **THEN** the shared tooltip shows the text effort list and a JSON section labeled `No data`

#### Scenario: Per-benchmark pass rates used when benchmarkName provided
- **WHEN** `PassRateBarChart` receives `benchmarkName="blame_forensics"`
- **THEN** both mode summaries use pass rates from `matrix[model]["blame_forensics"].pass_at_k` and the tooltip footnote shows that benchmark's fixture count

#### Scenario: Global pass rates used when benchmarkName absent
- **WHEN** `PassRateBarChart` renders without a `benchmarkName` prop
- **THEN** mode summaries use `model_summaries[model].pass_at_k` and the tooltip footnote reads "% of 204 fixtures passed"

### Requirement: RuntimeBarChart renders vertical range-whisker bar chart ranking models by speed
The `RuntimeBarChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = provider/base-model group, Y-axis = total API time in seconds). Each solid bar SHALL represent one selected provider/base-model group's median deduped effort API time from zero. A neutral range whisker SHALL visualize the range from the fastest effort API time to the slowest effort API time in that group. The median deduped effort API time SHALL be the representative value used for sorting and bar prominence. The Y-axis domain SHALL start at 0 and include the slowest displayed effort API time. Bars SHALL be color-coded by provider using the `getProviderColor()` palette. X-axis tick labels SHALL display the provider brand icon (via `ProviderIcon`) and the full base model name without ellipsis or text truncation, rotated `-40` degrees. The component SHALL accept a `data` prop containing the full dataset and an optional selected group list for filtering. Chart height SHALL be fixed at 350 pixels. A provider legend SHALL be rendered below the chart card showing colored dots for each unique provider present. Model groups SHALL be sorted fastest-first by their median deduped effort API time.

#### Scenario: Bars render for selected model groups
- **WHEN** `RuntimeBarChart` receives selected groups `['anthropic/claude-opus-4.7', 'openai/gpt-oss-120b']`
- **THEN** two vertical grouped bars are displayed with API-time range whiskers for the selected base models

#### Scenario: Fastest median grouped model appears first
- **WHEN** model groups have median effort API times [5000, 12000, 3000, 8000]
- **THEN** bars appear from left to right in order: 3000, 5000, 8000, 12000

#### Scenario: Effort API-time range shown
- **WHEN** `openai/gpt-5` has effort API times 45s, 70s, and 110s
- **THEN** the `openai/gpt-5` solid bar extends from 0s to 70s and its range whisker spans 45s-110s

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** its bar is rendered in the Anthropic palette color (#D97757)

#### Scenario: Colors reflect provider for fallback providers
- **WHEN** a model group has provider `unknown-provider`
- **THEN** its bar is rendered in a deterministic `hsl(hue, 55%, 48%)` color

#### Scenario: Diagonal labels show provider icon and full base model
- **WHEN** a model group is `openai/gpt-oss-120b`
- **THEN** its X-axis tick shows the OpenAI icon and `gpt-oss-120b` in full, rotated `-40` degrees

#### Scenario: Long model names remain full length
- **WHEN** a base model name exceeds 20 characters
- **THEN** the displayed label remains full length without ellipsis

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are present
- **THEN** the chart height is always 350 pixels

#### Scenario: Provider legend appears below the chart
- **WHEN** the chart shows model groups from multiple providers
- **THEN** a horizontal legend with colored dots and provider names appears below the chart card

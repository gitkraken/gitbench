## MODIFIED Requirements

### Requirement: ModelSelector provides independent multi-select for models and reasoning levels
The `ModelSelector` React component SHALL render a multi-select interface listing provider/base-model groups for Overview chart selection. Each entry SHALL represent one base model group and SHALL include the effort levels available in that group as contextual detail. Selecting a group SHALL select that provider/base-model group for Overview charts; it SHALL NOT expose independent checkboxes for each effort level in Overview mode. The component SHALL expose selected group IDs via an `onChange` callback and accept an `initialSelected` prop for pre-selection.

#### Scenario: All base model groups are listed
- **WHEN** `ModelSelector` renders with a dataset containing `openai/gpt-5:low`, `openai/gpt-5:high`, and `anthropic/claude-sonnet:medium`
- **THEN** two selectable entries appear: `openai/gpt-5` and `anthropic/claude-sonnet`

#### Scenario: Group selection selects all efforts for chart grouping
- **WHEN** a user checks `openai/gpt-5`
- **THEN** the selected value contains the `openai/gpt-5` group ID and grouped Overview charts include the low and high effort values for that base model

#### Scenario: onChange fires with selected group list
- **WHEN** a user toggles group selections
- **THEN** the `onChange` callback receives the complete array of currently selected group IDs

#### Scenario: Quick-select shortcuts are sticky at top of dropdown
- **WHEN** `ModelSelector` dropdown is open and the model list is scrolled
- **THEN** "Select all" and "Clear" controls remain visible at the top of the dropdown, above the scrollable list

#### Scenario: Quick-select shortcuts are always clickable
- **WHEN** `ModelSelector` dropdown is open with many model groups visible
- **THEN** "Select all" and "Clear" controls are always reachable without scrolling

#### Scenario: Pass-rate badges remain readable on hover and selection
- **WHEN** a model group row is hovered or selected (keyboard or mouse) and displays a colored pass-rate range badge
- **THEN** the badge text SHALL remain clearly readable against the row's hover/selection background

### Requirement: PassRateBarChart renders horizontal bar chart
The `PassRateBarChart` React component SHALL render a Recharts vertical bar chart (bars go up, X-axis = provider/base-model group, Y-axis = pass rate percentage). Each bar SHALL represent one selected provider/base-model group and SHALL visualize the range from the lowest effort pass rate to the highest effort pass rate in that group. The highest effort pass rate SHALL be the representative value used for sorting and bar prominence. Bars SHALL be color-coded by provider using the `getProviderColor()` palette. X-axis tick labels SHALL be rotated diagonally (-40°) with a custom tick renderer that displays a provider brand icon (via `ProviderIcon`) and the truncated base model name (max ~10 characters + ellipsis). The component SHALL accept a `data` prop containing the full dataset and a selected group list. Chart height SHALL be fixed at 350 pixels. A provider legend SHALL be rendered below the chart card showing colored dots for each unique provider present.

#### Scenario: Bars render for selected model groups
- **WHEN** `PassRateBarChart` receives selected groups `['anthropic/claude-opus-4.7', 'openai/gpt-oss-120b']`
- **THEN** two vertical grouped bars are displayed with pass-rate ranges for the selected base models

#### Scenario: Effort range shown for a group
- **WHEN** `openai/gpt-5` has effort pass rates 72%, 81%, and 85%
- **THEN** the `openai/gpt-5` bar visualizes the range 72%-85% and uses 85% as the representative value

#### Scenario: Bars sorted by highest score
- **WHEN** grouped models have highest effort pass rates 90%, 75%, and 82%
- **THEN** bars appear ordered by 90%, 82%, then 75%

#### Scenario: Colors reflect provider
- **WHEN** a model group has provider `anthropic`
- **THEN** its bar is rendered in the Anthropic palette color (#D97757)

#### Scenario: Colors reflect provider for fallback providers
- **WHEN** a model group has provider `unknown-provider`
- **THEN** its bar is rendered in a deterministic `hsl(hue, 55%, 48%)` color

#### Scenario: Diagonal labels show provider icon and truncated base model
- **WHEN** a model group is `openai/gpt-oss-120b`
- **THEN** its X-axis tick shows the OpenAI icon and "gpt-oss-1…" (truncated), rotated -40°

#### Scenario: Long model names are truncated
- **WHEN** a base model name exceeds ~10 characters
- **THEN** the displayed label is truncated with an ellipsis

#### Scenario: Chart height is fixed at 350 pixels
- **WHEN** 5, 12, or 30 model groups are selected
- **THEN** the chart height is always 350 pixels

#### Scenario: Tick labels are offset below the axis line
- **WHEN** the chart renders with any model group count
- **THEN** the X-axis tick labels appear below the horizontal axis line, not centered on it

#### Scenario: Provider legend appears below the chart
- **WHEN** the chart shows model groups from multiple providers
- **THEN** a horizontal legend with colored dots and provider names appears below the chart card

### Requirement: Overview chart components share model selection
Overview chart components in the shared chart-components capability SHALL update their rendered data when any Overview `ModelSelector` changes the selected provider/base-model group set. The selected group set SHALL be the complete array from the latest model selection change, and each chart SHALL use that set for all model-dependent bars, columns, legends, and labels. Components that still render effort-level data SHALL expand selected groups to their child model+effort names internally.

#### Scenario: Model Summary updates from another selector
- **WHEN** a user changes the selected model groups in the Benchmark Matrix selector
- **THEN** the Model Summary chart updates its bars to match the same selected group set

#### Scenario: Benchmark Matrix updates from another selector
- **WHEN** a user changes the selected model groups in the Model Summary selector
- **THEN** the Benchmark Matrix updates its rendered model columns from the same selected group set

#### Scenario: Provider legend follows shared selection
- **WHEN** a shared group selection change removes all model groups for a provider from the Model Summary chart
- **THEN** that provider is removed from the Model Summary provider legend

#### Scenario: Stored model-level selection is migrated
- **WHEN** localStorage contains old model+effort names such as `openai/gpt-5:high`
- **THEN** Overview selection initializes with the corresponding `openai/gpt-5` group ID

#### Scenario: Unknown stored values are ignored
- **WHEN** localStorage contains values that are not known model names or group IDs
- **THEN** those values are ignored when initializing Overview selection

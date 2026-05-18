## MODIFIED Requirements

### Requirement: ModelSelector provides independent multi-select for models and reasoning levels
The `ModelSelector` React component SHALL render a multi-select interface listing all model+level combinations from the dataset. Each entry SHALL be independently selectable — selecting `gpt-4o#high` SHALL NOT automatically select `gpt-4o#low`. The component SHALL expose selected models via an `onChange` callback and accept an `initialSelected` prop for pre-selection.

#### Scenario: All model+level combos are listed
- **WHEN** `ModelSelector` renders with a dataset containing `gpt-4o#high`, `gpt-4o#medium`, `claude-sonnet`
- **THEN** all three entries appear as individually selectable checkboxes

#### Scenario: Independent selection
- **WHEN** a user checks `gpt-4o#high`
- **THEN** only `gpt-4o#high` is selected; `gpt-4o#medium` remains unchecked

#### Scenario: onChange fires with selected list
- **WHEN** a user toggles selections
- **THEN** the `onChange` callback receives the complete array of currently selected model names

#### Scenario: Quick-select shortcuts are sticky at top of dropdown
- **WHEN** `ModelSelector` dropdown is open and the model list is scrolled
- **THEN** "Select all" and "Clear" controls remain visible at the top of the dropdown, above the scrollable list

#### Scenario: Quick-select shortcuts are always clickable
- **WHEN** `ModelSelector` dropdown is open with many models visible
- **THEN** "Select all" and "Clear" controls are always reachable without scrolling

#### Scenario: Pass-rate badges remain readable on hover and selection
- **WHEN** a model row is hovered or selected (keyboard or mouse) and displays a colored pass-rate badge
- **THEN** the badge text SHALL remain clearly readable against the row's hover/selection background

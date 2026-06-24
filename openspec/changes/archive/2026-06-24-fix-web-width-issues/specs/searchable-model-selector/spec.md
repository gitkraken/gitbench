## ADDED Requirements

### Requirement: Compare page defaults to the top-two model groups by pass rate on cold load

When the Compare page (`/compare`) initializes its selected model
groups and no persisted selection exists in local storage, the
`ModelSelector` SHALL default to the two provider/base-model groups
with the highest mean pass rate across their visible output modes,
sorted descending. The default SHALL only apply on cold load (no
stored selection); a returning user's stored selection SHALL still
win.

#### Scenario: Cold load selects the top two by pass rate
- **WHEN** a user navigates to `/compare` with no stored `gitbench:compare-selection`
- **AND** the data has model groups with pass rates `[0.92, 0.88, 0.71, 0.55]`
- **THEN** the first two groups (pass rates `0.92` and `0.88`) are selected on first render

#### Scenario: Returning user keeps stored selection
- **WHEN** a user previously saved a selection (e.g. `[group_c, group_a]`)
- **AND** they navigate back to `/compare`
- **THEN** those two groups are pre-selected and the cold-load default does NOT override the stored selection

#### Scenario: Fewer than two groups available
- **WHEN** only one model group exists in the data
- **THEN** the cold-load default selects that single group
- **AND** the page surfaces its existing "Select at least two models to compare fixture reliability" copy

## ADDED Requirements

### Requirement: PassRateBarChart accepts optional initialData prop
The `PassRateBarChart` React component SHALL accept an optional `initialData` prop of type `GitBenchData | undefined`. When `initialData` is provided and no campaign override is active (no `?campaign=` query parameter), the component SHALL use `initialData` as its initial data state and SHALL NOT fetch from `/api/charts/pass-rate`. When `initialData` is absent or a campaign override is active, the component SHALL fetch from the report API client as before.

#### Scenario: Renders immediately from initialData
- **WHEN** `PassRateBarChart` receives `initialData` with model summaries and no campaign is selected
- **THEN** the chart renders from `initialData` on first hydration without showing "Loading..." and without making an API request

#### Scenario: Falls back to API when initialData absent
- **WHEN** `PassRateBarChart` receives no `initialData` prop
- **THEN** the component shows "Loading..." and fetches from `/api/charts/pass-rate` as before

#### Scenario: Falls back to API when campaign override active
- **WHEN** `PassRateBarChart` receives `initialData` but the URL contains `?campaign=<id>`
- **THEN** the component fetches from `/api/charts/pass-rate?campaign=<id>` to obtain campaign-specific data and metadata

#### Scenario: Benchmark detail page still fetches
- **WHEN** `PassRateBarChart` is rendered on a benchmark detail page with a `benchmarkName` prop and no `initialData`
- **THEN** the component fetches from `/api/charts/pass-rate?benchmark=<name>` as before
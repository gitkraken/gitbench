## Purpose

Report pages provide the page-level structure for the benchmark report, including grouped model listings, drill-down fixture galleries, comparison views, and supporting informational pages.
## Requirements
### Requirement: Dashboard includes overview charts
The Dashboard SHALL include React island charts: an overall pass rate bar chart, a pass-by-difficulty stacked bar chart, and an interactive benchmark × model heatmap. Charts SHALL be accompanied by a shared `ModelSelector` island.

#### Scenario: Pass rate bar chart renders
- **WHEN** the Dashboard loads and React hydrates
- **THEN** a horizontal bar chart displays pass rate per selected model

#### Scenario: Heatmap renders with model and benchmark axes
- **WHEN** the Dashboard loads and React hydrates
- **THEN** a heatmap displays benchmarks as rows, selected models as columns, with cells colored by pass rate

#### Scenario: Clicking a heatmap cell navigates
- **WHEN** a user clicks a cell in the heatmap
- **THEN** the browser navigates to the corresponding Benchmark Detail page

### Requirement: Model Detail page includes "Compare" button
The Model Detail page SHALL include a "Compare →" button that navigates to `/compare?with=<encoded-model-name>`, pre-selecting the current model.

#### Scenario: Compare button navigates to Compare page
- **WHEN** a user clicks "Compare →" on `/models/gpt-4o%23high`
- **THEN** the browser navigates to `/compare?with=gpt-4o%23high` with that model pre-selected

### Requirement: Model Detail page shows reasoning level comparison when applicable
When a base model has been run at multiple reasoning levels, the Model Detail page SHALL display a reasoning level comparison section showing the pass rate delta per benchmark between levels, sorted by delta magnitude.

#### Scenario: Reasoning comparison renders when multiple levels exist
- **WHEN** navigating to a model detail page for a base model with runs at `high`, `medium`, and `low`
- **THEN** a comparison table or chart shows per-benchmark pass rates for each reasoning level

#### Scenario: No reasoning comparison for single-level models
- **WHEN** navigating to a model detail page for a model with only one reasoning level
- **THEN** no reasoning comparison section is displayed

### Requirement: Benchmark Detail page shows leaderboard and per-fixture comparison
The Benchmark Detail page (`benchmarks/[name].astro`) SHALL render the benchmark description, a model leaderboard bar chart (React island), a per-fixture comparison table showing pass/fail and similarity for each selected model, and a tag breakdown chart.

#### Scenario: Leaderboard shows all selected models
- **WHEN** navigating to `/benchmarks/commit_messages`
- **THEN** a bar chart displays pass rate for each selected model on this benchmark

#### Scenario: Per-fixture table shows cross-model results
- **WHEN** navigating to `/benchmarks/commit_messages`
- **THEN** a table displays each fixture in the benchmark with columns for each selected model's pass/fail and similarity

#### Scenario: Clicking a fixture row navigates
- **WHEN** a user clicks a fixture row in the comparison table
- **THEN** the browser navigates to `/fixtures/<fixture-id>`

### Requirement: Fixture Detail page shows full prompt, expected, and all model outputs
The Fixture Detail page (`fixtures/[fixture].astro`) SHALL render the fixture metadata (id, description, purpose, difficulty, tags), the full prompt text in a monospace block, the full expected text in a monospace block, and all model outputs as static `ModelOutputCard` components showing model name, pass/fail badge, similarity score, and full output text. Each block SHALL include a copy-to-clipboard button.

#### Scenario: Full prompt is displayed in monospace
- **WHEN** navigating to `/fixtures/f001`
- **THEN** the complete prompt text is displayed in a monospace block with a copy button

#### Scenario: All model outputs are displayed
- **WHEN** navigating to `/fixtures/f001`
- **THEN** a card is rendered for each model that ran this fixture, showing the model name, similarity, pass/fail, and full output

#### Scenario: Copy button copies text to clipboard
- **WHEN** a user clicks the copy button on the prompt block
- **THEN** the full prompt text is copied to the system clipboard

### Requirement: Explore page provides tag-based fixture search
The Explore page (`explore.astro`) SHALL render a tag cloud showing all tags with fixture counts, and a React island for filter bar and filtered results. Selecting tags or difficulty levels SHALL filter the fixture list to show matching fixtures with per-model pass/fail sparkline bars.

#### Scenario: Tag cloud displays all tags
- **WHEN** navigating to `/explore`
- **THEN** all tags from the dataset are displayed with fixture counts

#### Scenario: Clicking a tag filters results
- **WHEN** a user clicks a tag in the tag cloud
- **THEN** the filtered results list shows only fixtures matching that tag

#### Scenario: Multiple filters combine with AND logic
- **WHEN** a user selects tag "rename" and difficulty "medium"
- **THEN** only fixtures matching BOTH criteria are displayed

### Requirement: Compare page enables multi-model analysis
The Compare page (`compare.astro`) SHALL be a React island component that provides: a multi-select model picker at the top, an overall pass rate comparison bar chart, a per-benchmark grouped comparison chart, a head-to-head scatter plot for two chosen models, an agreement matrix for the same two models, and a per-fixture detail table across all selected models.

#### Scenario: Model selection updates all comparison sections
- **WHEN** a user adds or removes models in the Compare page selector
- **THEN** all comparison sections (overall, by benchmark, head-to-head, per-fixture) update to reflect the new selection

#### Scenario: Head-to-head scatter plot renders per-fixture dots
- **WHEN** two models are selected for head-to-head comparison
- **THEN** a scatter plot displays one dot per fixture, with X = model A similarity, Y = model B similarity

#### Scenario: Agreement matrix shows pass/fail overlap
- **WHEN** two models are selected for head-to-head comparison
- **THEN** a 2×2 matrix shows counts of: both pass, both fail, A-only pass, B-only pass

#### Scenario: Pre-selection from query parameter
- **WHEN** navigating to `/compare?with=gpt-4o%23high`
- **THEN** `gpt-4o#high` is pre-selected in the model picker

### Requirement: History page shows run history and time series
The History page (`history.astro`) SHALL render a static run log table showing timestamp, model, pass rate, suite version, and delta from previous run. It SHALL include a React island time series chart showing pass rate over time per selected model. Expanding a run row SHALL show the specific fixtures that regressed or improved compared to the previous run of the same model.

#### Scenario: Run log table is rendered statically
- **WHEN** navigating to `/history`
- **THEN** a table displays all runs sorted by timestamp descending, without requiring JavaScript

#### Scenario: Time series chart shows pass rate over calendar time
- **WHEN** the History page loads and React hydrates
- **THEN** a line chart displays pass rate over time for each selected model

#### Scenario: Expanding a run row shows fixture deltas
- **WHEN** a user clicks to expand a run row
- **THEN** the expanded area lists fixtures whose pass status or similarity changed significantly from the previous run

### Requirement: Models index page groups by provider and base model
The Models index page (`/models`) SHALL render models grouped by provider, then by base model within each provider. Each provider section SHALL display the provider brand icon and provider name as a header. Within each provider section, base models SHALL be displayed as cards containing sub-cards for each reasoning level. Each level sub-card SHALL show: the level name, pass rate percentage (color-coded), and total cost in USD. Clicking a level sub-card SHALL navigate to `/models/<provider>/<base-model>/<level>/`.

#### Scenario: Models grouped by provider
- **WHEN** the Models page renders with models from anthropic and openai
- **THEN** two provider sections appear: "Anthropic" (with its icon) and "OpenAI" (with its icon)

#### Scenario: Reasoning levels as sub-cards under base model
- **WHEN** anthropic/claude-opus-4.7 has runs at low, medium, high, xhigh, and max
- **THEN** five level sub-cards appear inside the claude-opus-4.7 card, each showing its pass rate and total cost

#### Scenario: Clicking a level sub-card navigates to drill-down
- **WHEN** a user clicks the "low" sub-card under claude-opus-4.7
- **THEN** the browser navigates to `/models/anthropic/claude-opus-4.7/low/`

### Requirement: Base model overview page shows level comparison
The base model overview page (`/models/[provider]/[model]/`) SHALL display the provider icon, provider name, and base model name as a header. Below, it SHALL render reasoning level cards (same layout as the sub-cards on the index page) showing pass rate and total cost for each level. Each card SHALL link to the level's fixture gallery page.

#### Scenario: Level cards displayed for base model
- **WHEN** navigating to `/models/anthropic/claude-opus-4.7/`
- **THEN** cards for low, medium, high, xhigh, and max are displayed with pass rates and costs

#### Scenario: Header shows provider and base model
- **WHEN** navigating to `/models/anthropic/claude-opus-4.7/`
- **THEN** the page heading includes the Anthropic icon and "Anthropic / claude-opus-4.7"

### Requirement: Model level drill-down page shows fixture gallery
The model level page (`/models/[provider]/[model]/[level]/`) SHALL display: the full model identity (provider icon, base model, level), a reasoning level tab bar linking to sibling levels of the same base model, a summary stats area (pass rate, total cost, total tokens), a "Compare" button linking to `/compare?with=<encoded-full-model-name>`, and the existing fixture gallery with filter controls (benchmark, difficulty, tag) matching the current individual model page behavior.

#### Scenario: Tabs link to sibling levels
- **WHEN** viewing `/models/anthropic/claude-opus-4.7/low/`
- **THEN** a tab bar shows [low] [medium] [high] [xhigh] [max] with "low" visually active; clicking "high" navigates to `/models/anthropic/claude-opus-4.7/high/`

#### Scenario: Fixture gallery filters work
- **WHEN** user selects benchmark "git_grep" in the filter bar
- **THEN** only fixture cards for git_grep remain visible

#### Scenario: Compare button navigates correctly
- **WHEN** user clicks "Compare" on the page for `anthropic/claude-opus-4.7:low`
- **THEN** the browser navigates to `/compare?with=anthropic%2Fclaude-opus-4.7%3Alow`

### Requirement: Model summary card shows total cost not average cost
Any card displaying model cost data SHALL show `total_cost_usd` (total cost of the full evaluation run), not `avg_cost_usd` (average cost per fixture). Cost SHALL be formatted in USD with appropriate precision for the magnitude.

#### Scenario: Card shows total cost
- **WHEN** a model summary card renders and has `total_cost_usd=0.526615`
- **THEN** the card displays "Cost: $0.527" (or similar precision)

#### Scenario: Card handles missing cost data
- **WHEN** a model has no cost data (`total_cost_usd=null`)
- **THEN** no cost information is displayed on the card


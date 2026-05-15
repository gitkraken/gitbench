## ADDED Requirements

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

## REMOVED Requirements

### Requirement: Dashboard page displays model summary cards
**Reason**: Model summary cards are moving to the `/models` page with a grouped layout. The Overview page now shows only chart-based visualizations (bar chart, heatmap, scatter plot).
**Migration**: Navigate to `/models` to see the grouped model summary cards.

### Requirement: Model Detail page shows model statistics and fixture gallery
**Reason**: The flat `/models/[model]` route is replaced by nested `/models/[provider]/[model]/[level]/`. Functionality is preserved and enhanced with sibling level tabs.
**Migration**: Old URLs like `/models/anthropic~claude-opus-4.7~low` are replaced by `/models/anthropic/claude-opus-4.7/low/`.

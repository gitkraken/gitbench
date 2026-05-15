## MODIFIED Requirements

### Requirement: CostValueChart renders quadrant scatter plot
The `CostValueChart` React component SHALL render a Recharts ScatterChart with total cost of a full run (X-axis, USD) and pass rate percentage (Y-axis). Each point SHALL represent one model. Two ReferenceLines SHALL be drawn at the median X and median Y values to divide the chart into four quadrants. The X-axis SHALL be labeled "Total cost per full run (USD)" and SHALL use `summary.total_cost_usd` from model summaries.

#### Scenario: One dot per model
- **WHEN** `CostValueChart` renders with 5 models
- **THEN** 5 dots appear on the scatter plot

#### Scenario: Reference lines at median values
- **WHEN** model costs are [0.10, 0.20, 0.50, 0.80, 1.00] and pass rates are [60, 75, 80, 85, 92]
- **THEN** vertical reference line at X=0.50 and horizontal reference line at Y=80

#### Scenario: Upper-left quadrant is cheap and good
- **WHEN** a model has cost below the median AND pass rate above the median
- **THEN** its dot appears in the upper-left quadrant

#### Scenario: Bottom-right quadrant is expensive and bad
- **WHEN** a model has cost above the median AND pass rate below the median
- **THEN** its dot appears in the bottom-right quadrant

### Requirement: CostValueChart shows tooltips on hover
Hovering over a dot SHALL display a tooltip with the model name, pass rate percentage, and total cost formatted as USD (e.g., "$0.5270").

#### Scenario: Tooltip on hover
- **WHEN** a user hovers over a model dot
- **THEN** a tooltip appears showing model name, pass rate, and total cost in USD format

### Requirement: CostValueChart dots navigate to model detail
Clicking a dot SHALL navigate the browser to `/models/<provider>/<base-model>/<level>/`.

#### Scenario: Click navigates to model detail
- **WHEN** a user clicks on the dot for model "anthropic/claude-opus-4.7:low"
- **THEN** the browser navigates to `/models/anthropic/claude-opus-4.7/low/`

### Requirement: CostValueChart handles models without cost data
Models with no cost data (all `cost_usd` values are null) SHALL NOT appear on the chart. If ALL models lack cost data, the component SHALL display a message: "No pricing data available."

#### Scenario: Model without cost is excluded
- **WHEN** one model has all null costs and others have valid costs
- **THEN** only the models with valid costs appear as dots

#### Scenario: All models lack cost data
- **WHEN** every model has null cost data
- **THEN** the chart area displays "No pricing data available"

### Requirement: CostValueChart is placed on Models overview page
The `CostValueChart` component SHALL be rendered on `/` (the Overview/Home page) after the benchmark matrix section, inside a section labeled "Cost vs Quality". It SHALL be loaded with `client:load`.

#### Scenario: Chart on overview page
- **WHEN** navigating to `/`
- **THEN** a "Cost vs Quality" section with the quadrant scatter plot is visible below the benchmark heatmap

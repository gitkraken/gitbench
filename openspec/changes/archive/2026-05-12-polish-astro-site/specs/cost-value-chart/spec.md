## ADDED Requirements

### Requirement: CostValueChart renders quadrant scatter plot
The `CostValueChart` React component SHALL render a Recharts ScatterChart with average cost per fixture (X-axis, USD) and pass rate percentage (Y-axis). Each point SHALL represent one model. Two ReferenceLines SHALL be drawn at the median X and median Y values to divide the chart into four quadrants.

#### Scenario: One dot per model
- **WHEN** `CostValueChart` renders with 5 models
- **THEN** 5 dots appear on the scatter plot

#### Scenario: Reference lines at median values
- **WHEN** model costs are [0.01, 0.02, 0.05, 0.08, 0.10] and pass rates are [60, 75, 80, 85, 92]
- **THEN** vertical reference line at X=0.05 and horizontal reference line at Y=80

#### Scenario: Upper-left quadrant is cheap and good
- **WHEN** a model has cost below the median AND pass rate above the median
- **THEN** its dot appears in the upper-left quadrant

#### Scenario: Bottom-right quadrant is expensive and bad
- **WHEN** a model has cost above the median AND pass rate below the median
- **THEN** its dot appears in the bottom-right quadrant

### Requirement: CostValueChart shows tooltips on hover
Hovering over a dot SHALL display a tooltip with the model name, pass rate percentage, and average cost formatted as USD (e.g., "$0.0008").

#### Scenario: Tooltip on hover
- **WHEN** a user hovers over a model dot
- **THEN** a tooltip appears showing model name, pass rate, and cost in USD format

### Requirement: CostValueChart dots navigate to model detail
Clicking a dot SHALL navigate the browser to `/models/<encoded-model-name>`.

#### Scenario: Click navigates to model detail
- **WHEN** a user clicks on the dot for model "openai/gpt-oss-20b"
- **THEN** the browser navigates to `/models/openai%2Fgpt-oss-20b`

### Requirement: CostValueChart handles models without cost data
Models with no cost data (all `cost_usd` values are null) SHALL NOT appear on the chart. If ALL models lack cost data, the component SHALL display a message: "No pricing data available."

#### Scenario: Model without cost is excluded
- **WHEN** one model has all null costs and others have valid costs
- **THEN** only the models with valid costs appear as dots

#### Scenario: All models lack cost data
- **WHEN** every model has null cost data
- **THEN** the chart area displays "No pricing data available"

### Requirement: CostValueChart is placed on Models overview page
The `CostValueChart` component SHALL be rendered on `/models` (the models overview page) after the model grid cards, inside a section labeled "Cost vs Quality". It SHALL be loaded with `client:load`.

#### Scenario: Chart on models overview
- **WHEN** navigating to `/models`
- **THEN** a "Cost vs Quality" section with the quadrant scatter plot is visible below the model cards

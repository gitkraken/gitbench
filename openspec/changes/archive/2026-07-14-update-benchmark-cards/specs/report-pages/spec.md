## ADDED Requirements

### Requirement: Benchmarks index cards summarize eligible model scores
The Benchmarks index page (`/benchmarks`) SHALL render one card per benchmark with the benchmark name, best eligible model score, worst eligible model score, and average eligible model score. The average score badge SHALL appear beside the benchmark title. The best and worst score badges SHALL appear together in a separate statistics row below the title. The cards SHALL omit fixture count.

For each benchmark, the page SHALL calculate one eligible score per provider/base-model identity. Before model aggregation, a JSON-schema effort/output-mode variant SHALL be excluded when its fixture-derived pass percentage is `0` and every fixture result for that variant and benchmark has a structured-output error. The model's fixture-derived pass percentage SHALL then be computed from all remaining effort-level and output-mode results by grouping them by `fixture_id`, calculating each fixture's pass rate across those attempts, and averaging the fixture pass rates. A model with no remaining fixture results SHALL be ineligible.

When exactly one eligible model has the best or worst score, the card SHALL show that base model's user-facing label and the score. When multiple eligible models share the best or worst score, the card SHALL show the tied model count and the score instead of selecting an arbitrary model name. Average score SHALL be calculated as the arithmetic mean of the eligible base-model scores.

#### Scenario: Card shows best worst and average
- **WHEN** the Benchmarks index renders a benchmark with eligible scores for multiple models
- **THEN** the benchmark card shows the average eligible score beside the benchmark title
- **AND** the card shows best and worst eligible scores together below the title
- **AND** the card does not show fixture count

#### Scenario: Scores use fixture pass percentage
- **WHEN** a model has a benchmark matrix `pass_at_k` value of `1`
- **AND** only one of four benchmark fixture results passed for that model
- **THEN** the model's benchmark card score is `25.0%`
- **AND** the card does not treat the model score as `100.0%`

#### Scenario: Effort levels are aggregated before ranking
- **WHEN** one base model's low-effort variant passes every fixture
- **AND** the same base model's high-effort variant fails every fixture
- **THEN** that base model has one combined score of `50.0%`
- **AND** the low-effort variant does not independently qualify the base model as a `100.0%` performer

#### Scenario: Unique best and worst show model labels
- **WHEN** exactly one eligible model has the highest score for a benchmark
- **AND** exactly one eligible model has the lowest score for the benchmark
- **THEN** the card shows the best model label with its score
- **AND** the card shows the worst model label with its score

#### Scenario: Tied best or worst shows model count
- **WHEN** multiple eligible models share the highest score for a benchmark
- **THEN** the card shows the count of tied best models with the best score instead of a model label
- **AND** each provider/base-model identity contributes at most one score
- **WHEN** multiple eligible models share the lowest score for the benchmark
- **THEN** the card shows the count of tied worst models with the worst score instead of a model label

#### Scenario: Unsupported JSON zero is excluded
- **WHEN** a JSON-schema model has a fixture-derived pass percentage equal to `0`
- **AND** every fixture result for that model and benchmark has a structured-output error
- **THEN** that score is excluded from best, worst, and average card calculations

#### Scenario: Valid zero score remains eligible
- **WHEN** a JSON-schema model has a fixture-derived pass percentage equal to `0`
- **AND** at least one fixture result for that model and benchmark does not have a structured-output error
- **THEN** that score remains eligible for best, worst, and average card calculations

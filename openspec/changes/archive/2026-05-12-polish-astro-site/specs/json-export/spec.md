## MODIFIED Requirements

### Requirement: render_json exports aggregated data to JSON file
The `render.py` module SHALL provide a `render_json(data, output_path)` function that writes the aggregated data dict (from `aggregate_runs()`) as a formatted JSON file. The output SHALL include model summaries with cost aggregates (`total_cost_usd`, `avg_cost_usd`), benchmark summaries, the results matrix, per-fixture results with full model outputs (not truncated), fixture metadata (purpose, difficulty, tags, prompt, expected), cost data (`cost_usd`), and run history. The `"unknown"` model SHALL NOT appear in the output.

#### Scenario: render_json writes valid JSON
- **WHEN** `render_json(data, "web/public/results.json")` is called
- **THEN** `web/public/results.json` contains valid JSON with top-level keys for `models`, `benchmarks`, `fixtures`, `matrix`, `model_summaries`, `runs_meta`

#### Scenario: Full model outputs are included
- **WHEN** a fixture result has a model output longer than 200 characters
- **THEN** the full output is included in `results.json` (not truncated)

#### Scenario: Fixture metadata is included
- **WHEN** a fixture has purpose, difficulty, and tags
- **THEN** those fields appear in the fixture entry in `results.json`

#### Scenario: Cost data is included
- **WHEN** a fixture result has a valid `cost_usd`
- **THEN** the fixture entry in `results.json` includes `"cost_usd"`

#### Scenario: Unknown model is excluded
- **WHEN** the aggregated data contains an `"unknown"` model
- **THEN** it does not appear in the `models`, `model_summaries`, `matrix`, `fixtures`, or `runs_meta` sections of the output

## ADDED Requirements

### Requirement: aggregate_runs filters out the "unknown" model
The `aggregate_runs()` function SHALL, after building all data structures, remove any entry for model name `"unknown"` from: `model_list`, `model_summaries`, `matrix`, `fixtures`, and `runs_meta`. This filtering SHALL happen as the final step before returning the result dict.

#### Scenario: unknown model removed from all collections
- **WHEN** `aggregate_runs()` processes runs that include a model named `"unknown"`
- **THEN** the returned dict contains no references to `"unknown"` in models, summaries, matrix, fixtures, or runs_meta

#### Scenario: Runs for other models are unaffected
- **WHEN** `aggregate_runs()` filters out `"unknown"`
- **THEN** data for all other models remains intact and correctly computed

### Requirement: aggregate_runs computes model-level cost aggregates
The `aggregate_runs()` function SHALL compute per-model `total_cost_usd` and `avg_cost_usd` and store them in `model_summaries[model]`. `total_cost_usd` SHALL be the sum of all `cost_usd` values for that model's fixtures. `avg_cost_usd` SHALL be the mean across fixtures with valid (non-null) cost data.

#### Scenario: Cost aggregates computed
- **WHEN** a model has fixtures with costs [0.001, 0.002, null, 0.003]
- **THEN** `total_cost_usd` is `0.006` and `avg_cost_usd` is `0.002` (nulls excluded)

#### Scenario: Model with no cost data
- **WHEN** a model has no fixtures with valid cost data
- **THEN** both `total_cost_usd` and `avg_cost_usd` are `null`

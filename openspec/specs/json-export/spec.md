## Purpose

JSON export defines the generated report data shape used by the web app and report APIs.
## Requirements
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

### Requirement: JSON output includes fixture-level prompt and expected text
The JSON output SHALL include the full prompt and expected text for each fixture so the Astro Fixture Detail page can render them without accessing raw fixture YAML files.

#### Scenario: Fixture prompt is in JSON
- **WHEN** `results.json` is generated
- **THEN** each fixture entry includes a `prompt` field with the full prompt text

#### Scenario: Fixture expected is in JSON
- **WHEN** `results.json` is generated
- **THEN** each fixture entry includes an `expected` field with the full expected text

### Requirement: JSON output includes fixture descriptions
The JSON output SHALL include the `description` field from each fixture for display in fixture cards and detail pages.

#### Scenario: Fixture description is in JSON
- **WHEN** `results.json` is generated
- **THEN** each fixture entry includes a `description` field

### Requirement: JSON output preserves base model grouping and reasoning levels
The JSON output SHALL preserve the relationship between base models and reasoning levels. Each model entry SHALL include `name` (full name with level), `baseModel` (name without `#level`), and `reasoningLevel` (the level string or null).

#### Scenario: Model entry has parsed fields
- **WHEN** a model is `gpt-4o#high`
- **THEN** the model entry has `name: "gpt-4o#high"`, `baseModel: "gpt-4o"`, `reasoningLevel: "high"`

#### Scenario: Model without reasoning level has null
- **WHEN** a model is `claude-sonnet` (no `#` suffix)
- **THEN** the model entry has `name: "claude-sonnet"`, `baseModel: "claude-sonnet"`, `reasoningLevel: null`

### Requirement: CLI provides gitbench report command
The CLI SHALL provide a `gitbench report` command that aggregates legacy run results from `gitbench-results/`, ingests campaign artifacts from campaign directories containing `campaign.json`, validates configured result-safety publication requirements, and writes compatibility JSON to `web/public/results.json`. The command SHALL NOT run Astro build, dev-server, preview, or browser-opening workflows.

#### Scenario: report command publishes compatibility JSON
- **WHEN** `gitbench report` completes successfully
- **THEN** `web/public/results.json` contains the aggregated report JSON
- **AND** the command prints guidance for running web module commands when a user wants to build or view the report

#### Scenario: deprecated web flags do not run web workflows
- **WHEN** `gitbench report --open`, `gitbench report --dev`, or `gitbench report --no-build` is executed
- **THEN** the command prints a deprecation warning for the flag
- **AND** it does not run Astro build, dev-server, preview, or browser-opening behavior
- **AND** it still publishes compatibility JSON when valid report inputs are present

#### Scenario: report command ingests campaign artifacts
- **WHEN** `gitbench report` scans a result directory containing `campaign.json` and raw campaign attempt envelopes
- **THEN** the generated report JSON SHALL include campaign metadata, trials, exact raw-attempt references, fixture aggregates, and campaign summaries
- **AND** it SHALL NOT require a separate manual campaign export step

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

### Requirement: JSON output includes fixture API duration
The JSON output SHALL include fixture-level `api_duration_ms` in each aggregated fixture result when the source score contains API timing data. The field SHALL represent successful API call latency in milliseconds and SHALL remain distinct from wall-clock `duration_ms`.

#### Scenario: Fixture API duration is in JSON
- **WHEN** `results.json` is generated from a score with `api_duration_ms=350.2`
- **THEN** the fixture result entry includes `"api_duration_ms": 350.2`

#### Scenario: Missing fixture API duration remains null-compatible
- **WHEN** `results.json` is generated from a score without `api_duration_ms`
- **THEN** the fixture result entry does not substitute `duration_ms` for API time

### Requirement: JSON runtime summaries represent API time
The `"model_runtimes"` object in JSON output SHALL represent API-time aggregates computed from `api_duration_ms`, while keeping the existing summary shape of `total_ms`, `avg_ms`, `min_ms`, `max_ms`, and `fixture_count`.

#### Scenario: model_runtimes uses API duration
- **WHEN** a model has fixture scores with `api_duration_ms` values [20.0, 30.0] and `duration_ms` values [100.0, 100.0]
- **THEN** `model_runtimes[model].total_ms` is `50.0`
- **AND** it is not `200.0`

### Requirement: JSON export preserves output mode
The aggregated report JSON SHALL include `output_mode` for every model variant, run metadata entry, benchmark summary, and fixture result. Historical result payloads that omit `output_mode` SHALL be treated as `text`.

#### Scenario: Text mode default for historical runs
- **WHEN** `aggregate_runs()` reads a historical run envelope without `output_mode`
- **THEN** the aggregated JSON represents that run as `output_mode: "text"`

#### Scenario: Structured run remains separate
- **WHEN** `aggregate_runs()` reads a text run and a JSON-schema run for the same model and benchmark
- **THEN** the aggregated JSON preserves both result variants without merging their fixture counts or pass rates

### Requirement: JSON export includes structured-output result metadata
Fixture results in aggregated JSON SHALL include structured-output metadata when available, including raw structured output, parsed payload, and structured-output error details. Parsed payloads SHALL be included only for structured responses that parsed as strict JSON and validated against the fixture contract. Invalid structured responses SHALL be represented through raw structured output and structured-output error fields rather than invalid or non-finite parsed payload values.

#### Scenario: Valid structured result exported
- **WHEN** a structured fixture result has a parsed payload
- **THEN** the aggregated fixture result includes the parsed structured payload and canonical `model_output`

#### Scenario: Invalid structured result exported
- **WHEN** a structured fixture result has a structured-output error
- **THEN** the aggregated fixture result includes the structured-output error
- **AND** the aggregated fixture result includes the raw structured output where available
- **AND** the aggregated fixture result does not include the invalid response as `parsed_payload`

#### Scenario: Invalid structured result keeps report JSON valid
- **WHEN** a structured fixture result failed because the raw response was invalid JSON or failed schema validation
- **THEN** the aggregated fixture result represents the raw model response as a string
- **AND** `results.json` remains valid standard JSON

### Requirement: JSON export emits strict standard JSON
Generated report JSON artifacts SHALL be valid standard JSON that can be parsed by browser-compatible `JSON.parse` implementations. Report JSON serialization MUST NOT emit bare `NaN`, `Infinity`, or `-Infinity` constants.

#### Scenario: Non-finite value cannot be serialized
- **WHEN** report generation attempts to serialize aggregate data containing a non-finite numeric value
- **THEN** report generation fails with a clear serialization error
- **AND** the generated report JSON artifact does not contain bare non-finite JSON constants

#### Scenario: Browser parser can read generated report
- **WHEN** `render_json(data, "web/public/results.json")` completes successfully
- **THEN** the written file can be parsed by a browser-compatible JSON parser

### Requirement: JSON export exposes output-mode-aware model grouping
The aggregated JSON SHALL preserve provider/base-model/reasoning grouping while exposing output-mode variants for each effort that has text or JSON-schema results.

#### Scenario: Base model group contains mode variants
- **WHEN** a base model has `high` reasoning results in both text and JSON-schema modes
- **THEN** the corresponding base model group exposes both variants for the `high` effort
- **AND** each variant has its own pass rate and total cost

### Requirement: JSON export represents campaigns and attempts

The JSON export SHALL include campaign metadata, trial summaries, fixture reliability aggregates, explicit metric numerators and denominators, resource summaries, and references or records for raw attempts.

#### Scenario: Export a repeated campaign

- **WHEN** a five-trial campaign is exported
- **THEN** the export SHALL identify all five planned trials and their completion states
- **AND** fixture aggregates SHALL include passing and valid attempt counts
- **AND** raw attempts SHALL retain exact campaign and trial identities

### Requirement: JSON export imports historical results as legacy campaigns

The export pipeline SHALL interpret pre-campaign result artifacts as one-trial legacy campaigns without inventing repeated-trial evidence.

#### Scenario: Import a historical artifact

- **WHEN** an artifact from the previous report schema is loaded
- **THEN** it SHALL produce a one-trial campaign marked `legacy`
- **AND** repeated-trial variability fields SHALL be absent or explicitly unavailable

### Requirement: New exports use unambiguous metric names

New campaign exports SHALL use `mean_success_rate` and explicitly named `pass_any_at_n` fields and SHALL NOT use `pass_at_k` to represent ordinary pass rate.

#### Scenario: Read campaign summary metrics

- **WHEN** a consumer reads a campaign model summary
- **THEN** it SHALL be able to distinguish one-attempt mean success from passing at least once in multiple attempts

### Requirement: Campaign JSON export uses unambiguous metrics
Campaign JSON export SHALL use `mean_success_rate`, `pass_any_at_n`, `planned_trials`, `completed_trials`, `valid_attempts`, `passing_attempts`, and `excluded_attempts` for campaign metrics. Campaign export SHALL NOT use `pass_at_k` as the headline campaign metric.

#### Scenario: Repeated campaign export
- **WHEN** a campaign with five planned trials is exported
- **THEN** the campaign JSON SHALL identify all five trials and their completion state
- **AND** fixture summaries SHALL expose passing and valid attempt counts
- **AND** model and benchmark summaries SHALL expose `mean_success_rate`

#### Scenario: Legacy artifact remains readable
- **WHEN** `gitbench report` ingests a historical one-shot result artifact
- **THEN** the legacy aggregate fields SHALL remain readable
- **AND** the report SHALL NOT infer repeated-trial stability from that artifact

### Requirement: Campaign JSON export preserves exact attempt identity
Every raw campaign attempt record or reference in JSON export SHALL include campaign ID, trial index, model ID, reasoning effort, output mode, benchmark, and fixture ID.

#### Scenario: Exact identity exported
- **WHEN** a raw attempt is exported for a JSON-schema high-reasoning model run
- **THEN** its exported identity SHALL include `campaign_id`, `trial_index`, `model_id`, `reasoning_effort`, `output_mode`, `benchmark`, and `fixture_id`

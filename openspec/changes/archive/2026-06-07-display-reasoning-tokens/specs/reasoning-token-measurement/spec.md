## ADDED Requirements

### Requirement: Reasoning tokens flow into stored data

The `render.py` module SHALL include `reasoning_tokens` from each score in both the aggregated JSON output and the SQLite database. The `build-db.mjs` script SHALL include `reasoning_tokens` when inserting fixture results. The SQLite `fixture_results` table SHALL have a `reasoning_tokens INTEGER` column.

#### Scenario: JSON output preserves reasoning tokens
- **WHEN** a score has `reasoning_tokens: 150`
- **THEN** the JSON fixture entry includes `"reasoning_tokens": 150`

#### Scenario: DB writer stores reasoning tokens
- **WHEN** `write_sqlite_report_db()` processes a result with `reasoning_tokens: 150`
- **THEN** the `fixture_results` row has `reasoning_tokens = 150`

#### Scenario: build-db.mjs stores reasoning tokens
- **WHEN** `build-db.mjs` processes a result with `reasoning_tokens: 150`
- **THEN** the INSERT includes `reasoning_tokens: 150`

#### Scenario: Missing reasoning tokens stored as NULL
- **WHEN** a score does not include a `reasoning_tokens` key
- **THEN** the stored value is `NULL`

## ADDED Requirements

### Requirement: Token summaries include reasoning tokens

The model token summaries query in `node-sqlite-report-store.ts` SHALL include `COALESCE(SUM(reasoning_tokens), 0) AS reasoning_tokens` alongside the existing `input_tokens`, `output_tokens`, and `total_tokens` aggregations. The `ModelTokenSummary` type SHALL include a `reasoning_tokens: number` field.

#### Scenario: Reasoning tokens aggregated per model
- **WHEN** a model has 3 fixture results with reasoning_tokens [50, null, 100]
- **THEN** the model's token summary has `reasoning_tokens: 150`

#### Scenario: Model with no reasoning data
- **WHEN** a model has no fixture results with non-null reasoning_tokens
- **THEN** the model's token summary has `reasoning_tokens: 0`

## ADDED Requirements

### Requirement: OpenRouter cost is extracted from API response
The `OpenAIAdapter.generate()` method SHALL extract the `cost` field from the OpenRouter API response's `usage` object and include it in the returned usage dict under the key `"cost"`. The `cost` value SHALL be a float representing USD. When the `cost` field is absent or None (e.g., for non-OpenRouter providers), the returned usage dict SHALL omit the `"cost"` key or set it to None.

#### Scenario: OpenRouter response includes cost
- **WHEN** `generate()` receives a response where `response.usage.cost` is `7.68e-06`
- **THEN** the returned dict's `usage` has `"cost": 7.68e-06`

#### Scenario: Non-OpenRouter response has no cost
- **WHEN** `generate()` receives a response where `response.usage` lacks a `cost` attribute
- **THEN** the returned dict's `usage` has `"cost": null` or the key is absent

### Requirement: Cost is stored on Score dataclass
The `BenchmarkRunner._run_fixture()` method SHALL map `usage.get("cost")` onto `score.cost_usd` when usage is present and the cost key exists. The `cost_usd` field SHALL be a float or None.

#### Scenario: Cost mapped from usage to Score
- **WHEN** `_run_fixture()` processes a fixture and `usage` contains `{"cost": 0.0000125, ...}`
- **THEN** `score.cost_usd` is set to `0.0000125`

#### Scenario: Cost absent from usage on error
- **WHEN** `_run_fixture()` catches an exception and creates an error Score
- **THEN** `score.cost_usd` remains None

### Requirement: Cost appears in per-fixture aggregated JSON
The `aggregate_runs()` function in `render.py` SHALL include `cost_usd` in each fixture entry of the `fixtures` dict. When a score has `cost_usd`, it SHALL be copied as `"cost_usd": <value>`. When a score has no `cost_usd`, the field SHALL be omitted or set to `null`.

#### Scenario: Fixture with cost in aggregated output
- **WHEN** `aggregate_runs()` processes a score with `cost_usd=0.00000768`
- **THEN** the fixture dict includes `"cost_usd": 0.00000768`

#### Scenario: Fixture without cost in aggregated output
- **WHEN** `aggregate_runs()` processes a score where `cost_usd` is None
- **THEN** the fixture dict either omits `cost_usd` or has `"cost_usd": null`

### Requirement: model_summaries includes cost aggregates
The `aggregate_runs()` function SHALL compute and store per-model cost aggregates in `model_summaries`: `total_cost_usd` (sum of all fixture costs), `avg_cost_usd` (mean cost per fixture with valid cost data). These SHALL only include fixtures where `cost_usd` is not None.

#### Scenario: Model summary has cost aggregates
- **WHEN** a model has 3 fixtures with costs 0.01, 0.02, 0.03
- **THEN** `model_summaries[model]` has `total_cost_usd: 0.06` and `avg_cost_usd: 0.02`

#### Scenario: Model with no cost data has null aggregates
- **WHEN** a model has no fixtures with valid `cost_usd`
- **THEN** `model_summaries[model]` has `total_cost_usd: null` and `avg_cost_usd: null`

### Requirement: TypeScript FixtureResult includes cost_usd
The `FixtureResult` interface in `web/src/lib/types.ts` SHALL include `cost_usd: number | null` so TypeScript consumers can access pricing data with proper typing.

#### Scenario: FixtureResult type has cost_usd field
- **WHEN** reading `types.ts`
- **THEN** `FixtureResult` includes `cost_usd: number | null`

### Requirement: TypeScript ModelSummary includes cost aggregates
The `ModelSummary` interface in `web/src/lib/types.ts` SHALL include `total_cost_usd: number | null` and `avg_cost_usd: number | null`.

#### Scenario: ModelSummary type has cost fields
- **WHEN** reading `types.ts`
- **THEN** `ModelSummary` includes `total_cost_usd: number | null` and `avg_cost_usd: number | null`

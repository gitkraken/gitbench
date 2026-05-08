## ADDED Requirements

### Requirement: Score exposes reasoning level
The `Score` dataclass and its `to_dict()`/`from_dict()` methods SHALL include an optional `reasoning_level` field populated from the adapter's reasoning level.

#### Scenario: Score with reasoning level
- **WHEN** a fixture is scored during a run where the adapter has reasoning level `"high"`
- **THEN** `Score.to_dict()` SHALL include `"reasoning_level": "high"`

#### Scenario: Score without reasoning level
- **WHEN** a fixture is scored during a run where the adapter has no reasoning level
- **THEN** `Score.to_dict()` SHALL NOT include the `"reasoning_level"` key

### Requirement: CSV exports include reasoning_level column
All CSV export formats SHALL include a `reasoning_level` column populated from the `Score`, or empty string when absent.

#### Scenario: Per-fixture CSV includes reasoning level
- **WHEN** `export_csv()` processes scores that include `"reasoning_level": "low"`
- **THEN** each row in the CSV SHALL have `reasoning_level` set to `"low"`

#### Scenario: Benchmark-level CSV includes reasoning level
- **WHEN** `export_artificialanalysis()` processes scores that include `"reasoning_level": "high"`
- **THEN** each row in the CSV SHALL have `reasoning_level` set to `"high"`

#### Scenario: CSV with no reasoning level
- **WHEN** scores do not include `reasoning_level`
- **THEN** the CSV column SHALL be an empty string

### Requirement: HTML report displays reasoning level
The HTML report SHALL extract and display the reasoning level from the run's model name.

#### Scenario: Report with model that has reasoning level
- **WHEN** an HTML report renders a run with model `"o3-mini#high"`
- **THEN** the report SHALL display `"high"` as the reasoning level

#### Scenario: Report with model that has no reasoning level
- **WHEN** an HTML report renders a run with model `"o3-mini"`
- **THEN** the report SHALL display "—" or equivalent placeholder

### Requirement: Full model name distinguishes runs naturally
Since the model name includes the reasoning level, runs at different levels SHALL be naturally distinct without special deduplication logic.

#### Scenario: Same base model, different levels are separate runs
- **WHEN** two run envelopes have model names `"o3-mini#low"` and `"o3-mini#high"`
- **THEN** existing deduplication logic SHALL treat them as distinct runs (model names differ)

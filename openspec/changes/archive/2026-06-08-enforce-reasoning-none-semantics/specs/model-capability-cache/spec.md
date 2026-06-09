## MODIFIED Requirements

### Requirement: Effort matrix is shipped data file
The system SHALL ship a comprehensive effort matrix at `gitbench/data/effort_matrix.json` mapping model identifiers to arrays of valid effort level strings. The matrix SHALL be the authoritative static source for which effort levels are valid for each model and SHALL include only levels supported by current provider documentation or verified provider behavior.

#### Scenario: Matrix covers known models
- **WHEN** the matrix is loaded
- **THEN** it SHALL provide valid effort levels for all models listed in the project's `.gitbench.json` profiles that use an effort suffix

#### Scenario: Matrix includes max where supported
- **WHEN** a model is known to support the `max` effort level (e.g., `openai/gpt-5`)
- **THEN** the matrix SHALL include `max` in the valid levels for that model

#### Scenario: Matrix excludes max by default
- **WHEN** a model is not known to support `max`
- **THEN** the matrix SHALL NOT include `max` as a valid level for that model

#### Scenario: Matrix excludes undocumented DeepSeek V4 efforts
- **WHEN** current provider documentation lists only `high` and `xhigh` for DeepSeek V4 Flash or DeepSeek V4 Pro
- **THEN** the matrix SHALL list only `high` and `xhigh` for those models and SHALL reject `none`, `minimal`, `low`, and `medium`

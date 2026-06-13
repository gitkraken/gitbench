## MODIFIED Requirements

### Requirement: Explicit concurrency groups override inference
GitBench SHALL allow config-defined concurrency groups to override inferred capacity groups. Override matching SHALL apply to the base model ID after effort stripping. Groups MAY also specify a minimum inter-request interval.

#### Scenario: Explicit group collapses matching models
- **WHEN** config defines a group with key `openrouter:anthropic/claude` matching `anthropic/claude-*`
- **THEN** `anthropic/claude-opus-4.7:max` and `anthropic/claude-sonnet-4.7:high` both use `openrouter:anthropic/claude`

#### Scenario: Explicit group limit is used
- **WHEN** a matched explicit group has `max_concurrent_requests` set to 1
- **THEN** GitBench uses 1 as the request budget for that capacity group

#### Scenario: Explicit group interval overrides global default
- **WHEN** a matched explicit group has `min_request_interval_ms` set to 2000
- **THEN** GitBench enforces a 2000ms minimum interval between requests in that capacity group, regardless of the global `concurrency.min_request_interval_ms` setting

#### Scenario: Explicit group without interval uses global default
- **WHEN** a matched explicit group does not specify `min_request_interval_ms` but the global `concurrency.min_request_interval_ms` is 500
- **THEN** GitBench enforces a 500ms minimum interval for that capacity group

#### Scenario: Explicit groups do not match effort suffixes
- **WHEN** config defines a group matching `anthropic/claude-opus-*`
- **THEN** the group matches `anthropic/claude-opus-4.7:max` based on base model ID `anthropic/claude-opus-4.7`

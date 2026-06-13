## Purpose

Capacity-aware concurrency prevents GitBench runs from exceeding upstream model request limits by coordinating global and per-capacity-group request budgets while preserving deterministic output.
## Requirements
### Requirement: Model API calls are gated by request budgets
GitBench SHALL gate each real model API network attempt through a global request budget and a capacity-group request budget immediately before invoking the provider. Adapter retries SHALL reacquire these budgets instead of holding permits while waiting or bypassing capacity coordination.

#### Scenario: Global request budget limits simultaneous calls
- **WHEN** a run schedules work for multiple models and fixtures with a global maximum of 2 concurrent requests
- **THEN** no more than 2 model API attempts are in progress at the same time

#### Scenario: Capacity group request budget limits simultaneous calls
- **WHEN** two scheduled attempts target models in the same capacity group with `max_concurrent_requests` set to 1
- **THEN** the second model API attempt waits until the first model API attempt releases the group permit

#### Scenario: Independent groups may run concurrently
- **WHEN** two scheduled attempts target models in different capacity groups and the global request budget has available permits
- **THEN** both model API attempts may run at the same time

#### Scenario: Retry attempts reacquire request budgets
- **WHEN** a provider attempt fails with a retryable error and the adapter schedules another attempt
- **THEN** the retry waits for and reacquires the applicable global and capacity-group budgets before calling the provider again

#### Scenario: Retry waits do not retain permits
- **WHEN** an adapter is waiting for exponential backoff or a capacity-group cooldown
- **THEN** it holds neither a global request permit nor a capacity-group request permit

### Requirement: Capacity grouping ignores GitBench effort
GitBench SHALL derive capacity groups from the base model ID after removing any GitBench effort suffix.

#### Scenario: Effort variants share capacity group
- **WHEN** a profile contains `openai/gpt-5.4-mini:low` and `openai/gpt-5.4-mini:max`
- **THEN** both run targets use the same capacity group

#### Scenario: Effort remains in result identity
- **WHEN** a run target `anthropic/claude-opus-4.7:max` completes
- **THEN** result metadata and progress labels still identify the run target with effort `max`

### Requirement: OpenRouter groups are inferred from upstream model family
For OpenRouter profiles, GitBench SHALL infer capacity groups from the configured model string's upstream provider and model family after effort stripping.

#### Scenario: Anthropic Opus versions share a group
- **WHEN** an OpenRouter profile contains `anthropic/claude-opus-4.7:max` and `anthropic/claude-opus-4.8:max`
- **THEN** both run targets use the capacity group `openrouter:anthropic/claude-opus`

#### Scenario: Anthropic model families are separate
- **WHEN** an OpenRouter profile contains `anthropic/claude-opus-4.7:max` and `anthropic/claude-sonnet-4.7:max`
- **THEN** the Opus target uses `openrouter:anthropic/claude-opus` and the Sonnet target uses `openrouter:anthropic/claude-sonnet`

#### Scenario: OpenAI GPT variants share inferred family
- **WHEN** an OpenRouter profile contains `openai/gpt-5.4-mini:high` and `openai/gpt-5.4-nano:xhigh`
- **THEN** both run targets use the capacity group `openrouter:openai/gpt-5`

#### Scenario: Unknown OpenRouter family falls back to base model ID
- **WHEN** an OpenRouter model ID does not match a known family inference rule
- **THEN** GitBench uses `openrouter:<base-model-id>` as the inferred capacity group

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

### Requirement: Scheduling preserves deterministic output
GitBench SHALL preserve existing output structure and deterministic ordering even when scheduled work completes out of order.

#### Scenario: Model output order follows config order
- **WHEN** model runs complete in a different order than they were configured
- **THEN** stdout JSON, JSON output files, and JSONL records preserve configured model order

#### Scenario: Fixture output order follows fixture order
- **WHEN** fixtures complete in a different order than they were loaded
- **THEN** each benchmark result lists scores in fixture order

### Requirement: Rate limits establish shared capacity-group cooldowns
GitBench SHALL maintain a thread-safe `blocked_until` value for each capacity group. A provider HTTP 429 SHALL extend the affected group's cooldown before the failing call schedules a retry.

#### Scenario: Retry-After establishes group cooldown
- **WHEN** an attempt in capacity group `openrouter:model-a` receives HTTP 429 with `Retry-After: 30`
- **THEN** new attempts for `openrouter:model-a` wait at least 30 seconds before invoking the provider

#### Scenario: Missing Retry-After uses fallback cooldown
- **WHEN** an attempt receives HTTP 429 without a valid `Retry-After`
- **THEN** GitBench applies the configured fallback cooldown, defaulting to 30 seconds

#### Scenario: Cooldown is extended but not shortened
- **WHEN** a capacity group is blocked for another 20 seconds and a subsequent in-flight attempt reports a 45-second cooldown
- **THEN** the group's `blocked_until` is extended to the later deadline

#### Scenario: Shorter rate-limit response does not reduce cooldown
- **WHEN** a capacity group is blocked for another 45 seconds and a subsequent in-flight attempt reports a 10-second cooldown
- **THEN** the existing later `blocked_until` deadline remains in effect

#### Scenario: Unrelated groups remain available
- **WHEN** capacity group A is cooling down after HTTP 429
- **THEN** capacity group B may continue acquiring request budgets and invoking its provider

#### Scenario: Effort variants observe one cooldown
- **WHEN** `nvidia/nemotron-3-nano-30b-a3b:low` triggers a cooldown
- **THEN** attempts for other effort variants of `nvidia/nemotron-3-nano-30b-a3b` wait on the same capacity-group cooldown

### Requirement: Cooldown wake-ups preserve request pacing
GitBench SHALL combine cooldown enforcement with existing capacity limits and minimum request intervals so waiting callers do not create an immediate unbounded burst when a cooldown expires.

#### Scenario: Group concurrency still applies after cooldown
- **WHEN** multiple attempts are waiting for a capacity group with `max_concurrent_requests: 1`
- **THEN** only one attempt enters the provider when the cooldown expires

#### Scenario: Minimum interval still applies after cooldown
- **WHEN** a capacity group has a configured minimum request interval and multiple attempts resume after a cooldown
- **THEN** consecutive provider attempts continue to respect that minimum interval


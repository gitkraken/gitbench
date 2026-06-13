## MODIFIED Requirements

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

## ADDED Requirements

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

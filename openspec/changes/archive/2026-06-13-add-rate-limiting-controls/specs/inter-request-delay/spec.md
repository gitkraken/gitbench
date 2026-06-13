## ADDED Requirements

### Requirement: Configurable inter-request delay
The system SHALL support a configurable minimum interval between consecutive requests within a capacity group, enforced at the semaphore acquire level.

#### Scenario: Default delay is zero
- **WHEN** no `min_request_interval_ms` is configured globally or per-group
- **THEN** requests within a capacity group fire with no enforced inter-request delay (current behavior preserved)

#### Scenario: Global delay applies to all groups
- **WHEN** `concurrency.min_request_interval_ms` is set to 500 and no per-group override exists
- **THEN** every capacity group enforces at least 500ms between the release of one permit and the acquisition of the next

#### Scenario: Per-group delay overrides global
- **WHEN** a concurrency group entry specifies `min_request_interval_ms: 2000` while the global default is 500
- **THEN** that group enforces a 2000ms minimum interval, superseding the global default

#### Scenario: Delay is measured from permit release
- **WHEN** a permit is released at time T and the next acquire occurs at time T + 300ms with `min_request_interval_ms` set to 500
- **THEN** the acquire call sleeps for the remaining 200ms before returning the permit

#### Scenario: Delay does not block other groups
- **WHEN** group A is sleeping during its inter-request delay
- **THEN** group B (with available permits and no delay) may acquire and proceed immediately

#### Scenario: Zero delay disables rate limiting
- **WHEN** `min_request_interval_ms` is explicitly set to 0 for a group
- **THEN** no sleep occurs on acquire for that group

### Requirement: Rate-limited semaphore preserves concurrency semantics
The system SHALL enforce the inter-request delay without changing the existing concurrency limit behavior.

#### Scenario: Concurrent permit limit still enforced
- **WHEN** a capacity group has `max_concurrent_requests: 2` and `min_request_interval_ms: 1000`
- **THEN** at most 2 requests run concurrently, and each acquire after release enforces the 1000ms interval

#### Scenario: Single-permit group serializes with delay
- **WHEN** a capacity group has `max_concurrent_requests: 1` and `min_request_interval_ms: 500`
- **THEN** requests execute one at a time with at least 500ms between the end of one and the start of the next

### Requirement: Retry-After header is respected on 429 responses
The system SHALL read the HTTP `Retry-After` header from 429 rate-limit responses in OpenAI-compatible adapters and use it as a floor for retry delay.

#### Scenario: Retry-After used when larger than exponential backoff
- **WHEN** a 429 response includes `Retry-After: 30` and the current exponential backoff is 4 seconds
- **THEN** the retry delay is 30 seconds

#### Scenario: Exponential backoff used when larger than Retry-After
- **WHEN** a 429 response includes `Retry-After: 2` and the current exponential backoff is 8 seconds
- **THEN** the retry delay is 8 seconds

#### Scenario: Exponential backoff used when Retry-After is missing
- **WHEN** a 429 response does not include a `Retry-After` header
- **THEN** the retry delay falls back to the existing exponential backoff formula

#### Scenario: Non-429 errors unaffected
- **WHEN** a retryable error is not a rate-limit error (e.g., timeout, connection error)
- **THEN** the existing exponential backoff is used unchanged

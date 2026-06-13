## 1. Rate-Limited Semaphore

- [x] 1.1 Create `RateLimitedBoundedSemaphore` class in `gitbench/harness/capacity.py` — wraps `threading.BoundedSemaphore`, tracks last release time, sleeps on acquire when interval not met
- [x] 1.2 Update `RequestBudgetCoordinator.__init__` to accept `group_intervals: dict[str, float]` and construct rate-limited semaphores per group
- [x] 1.3 Update `RequestBudgetCoordinator._group_semaphore` to use `RateLimitedBoundedSemaphore` instead of raw `BoundedSemaphore`

## 2. Config Parsing

- [x] 2.1 Parse `concurrency.min_request_interval_ms` as a global default in `derive_capacity_info` or a new helper
- [x] 2.2 Merge per-group `min_request_interval_ms` from explicit concurrency groups into the group intervals dict
- [x] 2.3 Update `describe_request_budgets` to log interval settings alongside concurrency limits

## 3. Retry-After Header Support

- [x] 3.1 Add `_extract_retry_after(exception) -> float` helper in `gitbench/harness/model.py` to read `Retry-After` from `openai.RateLimitError.response.headers`
- [x] 3.2 Integrate `_extract_retry_after` result into the delay calculation in `OpenAIAdapter.generate()`: `delay = max(backoff, retry_after)`

## 4. Tests

- [x] 4.1 Unit tests for `RateLimitedBoundedSemaphore`: zero delay, nonzero delay, concurrent permit limit preserved, delay doesn't block other semaphores
- [x] 4.2 Unit tests for `min_request_interval_ms` config parsing: global default, per-group override, explicit zero overrides global, missing interval uses global
- [x] 4.3 Unit tests for `_extract_retry_after`: header present with integer, header present with float, header missing, malformed header
- [x] 4.4 Integration test verifying delay is enforced between sequential fixtures within a capacity group

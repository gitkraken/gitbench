## 1. Shared Selection State

- [x] 1.1 Add a shared Overview model selection helper or hook that initializes from loaded models, sanitizes stored model names, reads/writes `gitbench-model-selection`, listens for `model-selection-changed`, and exposes selected models plus a setter
- [x] 1.2 Ensure externally received `model-selection-changed` events update local chart state without rebroadcasting the same event in a loop
- [x] 1.3 Preserve empty selection as a valid user choice from "Clear all"

## 2. Selector Contract

- [x] 2.1 Update `ModelSelector` so external selection changes notify its parent via `onChange` or convert it to a controlled component used by the shared hook
- [x] 2.2 Ignore malformed `model-selection-changed` event details and clean up event listeners on unmount
- [x] 2.3 Preserve existing dropdown behavior: search, individual toggles, Select all, Clear all, pass-rate badges, localStorage persistence, and event dispatch

## 3. Overview Chart Integration

- [x] 3.1 Wire `PassRateBarChart` to the shared selected model state so bars and provider legend update when any Overview selector changes
- [x] 3.2 Wire `BenchmarkHeatmap` to the shared selected model state so model columns update when any Overview selector changes
- [x] 3.3 Wire `CostValueChart` to the shared selected model state while continuing to exclude selected models without cost data
- [x] 3.4 Wire `RuntimeBarChart` to the shared selected model state while continuing to exclude selected models without runtime data
- [x] 3.5 Wire `TokenUsageChart` to the shared selected model state

## 4. Empty-State Behavior

- [x] 4.1 Keep the `CostValueChart` ModelSelector visible when no selected models have pricing data
- [x] 4.2 Keep the `RuntimeBarChart` ModelSelector visible when no selected models have runtime data
- [x] 4.3 Keep the `TokenUsageChart` ModelSelector visible when selected models have no token data

## 5. Verification

- [x] 5.1 Add or update component tests for cross-selector synchronization where feasible
- [x] 5.2 Manually verify on `/` that changing any chart's ModelSelector updates Model Summary, Cost per Full Run, Runtime, Token Usage, and Benchmark Matrix
- [x] 5.3 Manually verify Select all, Clear all, search filtering, localStorage persistence, and no-data states still work
- [x] 5.4 Run the relevant frontend checks or test suite for `gitbench/web`

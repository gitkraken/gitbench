## Why

GitBench currently validates reasoning effort levels against a hardcoded matrix that covers only 9 OpenAI models. All other models (Google, Anthropic, DeepSeek, etc.) pass through silently — potentially wasting tokens on configurations where the requested effort level is silently mapped by OpenRouter to a lower value, or isn't supported at all. This undermines benchmark reliability and inflates costs.

## What Changes

- **Gate all configured model+effort combos** at `run` startup — any invalid combination fails the entire run before any API calls are made
- **Query the OpenRouter API** (`/api/v1/models?supported_parameters=reasoning`) to know which models support reasoning at all, cached aggressively (~7 days)
- **Ship a comprehensive effort matrix** (`gitbench/data/effort_matrix.json`) covering known model→valid-effort mappings, replacing the 9-entry `_MODEL_MATRIX` in `reasoning.py`
- **Remove the silent pass-through** for unknown models — if a model has an effort level configured but isn't in the capability data, the run fails with a clear diagnostic
- **Integrate validation into `run` startup** (not a separate command) — validation is the gate, not an optional check

## Capabilities

### New Capabilities
- `model-capability-cache`: Cached model capabilities from the OpenRouter models API, refreshed on a configurable TTL, used by the validation gate

### Modified Capabilities
- `reasoning-level-config`: Add strict validation requirements — every model+effort combo MUST be verified before benchmarks execute; unknown or invalid combos SHALL cause the run to abort with a diagnostic message

## Impact

- `gitbench/harness/reasoning.py` — simplified; validation logic moves to new module
- `gitbench/data/effort_matrix.json` — new data file shipped in code
- `gitbench/harness/capabilities.py` — new module: cache management, API fetch, validation
- `gitbench/cli.py` — replaces `validate_model_list()` call with new strict gate
- `tests/test_reasoning.py` — expanded with validation gate scenarios
- `tests/test_capabilities.py` — new test file

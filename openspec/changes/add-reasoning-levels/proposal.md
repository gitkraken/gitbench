## Why

LLM providers (OpenAI, Anthropic, etc.) now expose configurable reasoning effort controls (e.g., `reasoning_effort` for o-series models) that trade latency/cost for answer quality. GitBench currently has no mechanism to benchmark these levels, making it impossible to measure how increased reasoning effort improves Git task performance.

## What Changes

- Allow reasoning level to be specified as part of the model name using `#` delimiter (e.g., `o3-mini#high`, `gpt-4o#medium`)
- Parse model name in each adapter to separate the base model name from the reasoning level
- Forward reasoning level to provider APIs (OpenAI `reasoning_effort`, future providers)
- Track the full model name (including reasoning level) in results, making runs at different levels naturally distinct
- Display reasoning level from the model name in HTML reports and CSV exports

## Capabilities

### New Capabilities
- `reasoning-level-config`: Model name `#` syntax for specifying reasoning level
- `reasoning-level-forwarding`: Adapter-level parsing and forwarding to provider APIs
- `reasoning-level-tracking`: Per-result reasoning level extraction from model name for reporting

### Modified Capabilities
<!-- None -->

## Impact

- **Model layer**: `gitbench/harness/model.py` — `OpenAIAdapter` and `OllamaAdapter` parse `model#level` syntax from model name
- **Runner**: `gitbench/harness/runner.py` — pass the base model name and reasoning level separately to adapter
- **CLI**: No new flags needed — existing `--model` already accepts arbitrary strings
- **Config**: No schema changes — existing `models` lists accept `model#level` names
- **Types**: `gitbench/harness/types.py` — add optional `reasoning_level` to `Score` for CSV convenience
- **Export/Report**: `gitbench/export.py`, `gitbench/render.py` — extract and display reasoning level
- **Tests**: Tests for model name parsing, adapter forwarding, CSV/report display

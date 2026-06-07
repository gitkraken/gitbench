## 1. Create effort matrix data file

- [x] 1.1 Create `gitbench/data/` directory and `effort_matrix.json` covering all models in `.gitbench.json` with their valid effort levels
- [x] 1.2 Research and populate effort levels for each provider family: OpenAI, Anthropic, Google, DeepSeek, Qwen, Mistral, xAI, NVIDIA, MiniMax, Moonshot, Z.AI, Arcee, etc.
- [x] 1.3 Verify `max` effort inclusion: include for GPT-5 (confirmed), exclude for all others unless documented

## 2. Build capabilities module

- [x] 2.1 Create `gitbench/harness/capabilities.py` with cache path, TTL constant, and `fetch_model_capabilities()` function
- [x] 2.2 Implement `fetch_model_capabilities()` using `urllib` (stdlib, consistent with OllamaAdapter) to GET `/api/v1/models?supported_parameters=reasoning`
- [x] 2.3 Implement `load_cache()` and `save_cache()` for `~/.cache/gitbench/model-capabilities.json`
- [x] 2.4 Implement `load_effort_matrix()` to read the shipped `effort_matrix.json`
- [x] 2.5 Implement `resolve_capabilities()` that merges cache (reasoning support) + matrix (effort levels) → lookup dict
- [x] 2.6 Implement `validate_models()` that takes model list + profile configs and returns list of validation errors

## 3. Integrate validation gate into run command

- [x] 3.1 Replace `validate_model_list()` call in `cli.py` `run()` with new `validate_models()` from capabilities module
- [x] 3.2 Format validation errors as clear multi-line diagnostic output to stderr
- [x] 3.3 Add warning (not error) for Ollama models with effort suffixes
- [x] 3.4 Ensure mock models bypass validation

## 4. Simplify reasoning module

- [x] 4.1 Move `VALID_REASONING_LEVELS` constant to capabilities module or keep in reasoning.py as shared constant
- [x] 4.2 Remove `_MODEL_MATRIX` and `get_supported_levels()` from `reasoning.py`
- [x] 4.3 Update imports: capabilities module imports from reasoning.py for parse_model_reasoning
- [x] 4.4 Remove `validate_model_list()` from `reasoning.py` (replaced by capabilities.validate_models)

## 5. Tests

- [x] 5.1 Create `tests/test_capabilities.py` with tests for cache hit/miss/stale scenarios
- [x] 5.2 Test `resolve_capabilities()` with mocked cache and matrix data
- [x] 5.3 Test `validate_models()` with various valid/invalid configurations
- [x] 5.4 Update `tests/test_reasoning.py` to remove tests for removed functions, add tests for new flow
- [x] 5.5 Update `tests/test_cli.py` integration tests for new validation behavior
- [x] 5.6 Test end-to-end: valid config passes gate, invalid config aborts before API calls

## 6. Verify

- [x] 6.1 Run `gitbench run --all-models` with current `.gitbench.json` to verify all configured models pass validation
- [x] 6.2 Test with intentionally invalid config to verify gate failure and error message quality
- [x] 6.3 Verify cache file is created and used on second run

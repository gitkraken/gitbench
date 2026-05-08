## 1. Model Name Parsing

- [x] 1.1 Add a shared `parse_model_name()` utility that splits `"model#level"` into `(base_model, reasoning_level)` tuple, handling no `#` case and multiple `#` case
- [x] 1.2 Add optional `reasoning_level` field to `Score` dataclass and `to_dict()`/`from_dict()` in `gitbench/harness/types.py`

## 2. Model Adapters

- [x] 2.1 Parse model name in `OpenAIAdapter.__init__()`, store base model + reasoning level separately in `gitbench/harness/model.py`
- [x] 2.2 Forward reasoning level as `reasoning_effort` in `OpenAIAdapter.generate()` in `gitbench/harness/model.py`
- [x] 2.3 Parse model name in `OllamaAdapter.__init__()`, store base model + reasoning level, and log debug message in `generate()` in `gitbench/harness/model.py`
- [x] 2.4 Preserve full original model name for display/reporting in each adapter in `gitbench/harness/model.py`

## 3. Runner Plumbing

- [x] 3.1 Expose adapter's reasoning level in `BenchmarkRunner` and populate it into each `Score` in `gitbench/harness/runner.py`

## 4. CLI Layer

- [x] 4.1 Ensure `MockModelClient` path handles model names with `#` suffix (mock case in `get_model_client()`) in `gitbench/cli.py`

## 5. Export Layer

- [x] 5.1 Add `reasoning_level` column to `export_csv()` in `gitbench/export.py`
- [x] 5.2 Add `reasoning_level` column to `export_artificialanalysis()` in `gitbench/export.py`

## 6. HTML Report

- [x] 6.1 Parse and display reasoning level from model name in HTML report metadata in `gitbench/render.py`
- [x] 6.2 Handle absent reasoning level with "—" placeholder in `gitbench/render.py`

## 7. Tests

- [x] 7.1 Add tests for `parse_model_name()` utility (bare name, with level, multiple #)
- [x] 7.2 Add tests for `OpenAIAdapter` model parsing and `reasoning_effort` forwarding in `tests/test_model.py`
- [x] 7.3 Add tests for `OllamaAdapter` model parsing and debug logging in `tests/test_model.py`
- [x] 7.4 Add tests for `BenchmarkRunner` reasoning level population into `Score` in `tests/test_runner.py`
- [x] 7.5 Add tests for CSV export reasoning_level column in `tests/test_export.py`
- [x] 7.6 Add tests for HTML report reasoning level display in `tests/test_render.py`

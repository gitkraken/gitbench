## 1. Structured Output Validation

- [x] 1.1 Add a shared strict structured JSON parse helper that rejects `NaN`, `Infinity`, `-Infinity`, and parsed non-finite numeric values.
- [x] 1.2 Add local JSON Schema validation for structured-output contracts before canonicalization.
- [x] 1.3 Update OpenAI-compatible, Ollama, and mock model clients to use the shared strict parse helper for structured responses.
- [x] 1.4 Update the benchmark runner so parse/schema failures become fixture quality failures with `parsed_payload=null`, `raw_structured_output` preserved, `structured_error` populated, and `model_output` set to the raw provider output.

## 2. Report Artifact Safety

- [x] 2.1 Update `render_json` and any report JSON writers to reject non-finite values instead of serializing bare `Infinity`, `-Infinity`, or `NaN`.
- [x] 2.2 Ensure aggregation and SQLite report generation store invalid structured responses as raw output plus structured error, not as parsed payload JSON.
- [x] 2.3 Regenerate or repair the affected local report artifacts so `gitbench/web/public/results.json` is valid standard JSON again.

## 3. Web Fixture Display

- [x] 3.1 Update `ModelOutputCard` to display `Invalid JSON. Output: <raw structured output>` for structured parse failures.
- [x] 3.2 Update `ModelOutputCard` to display `Invalid structured output. Output: <raw structured output>` for structured schema failures.
- [x] 3.3 Ensure copy behavior exposes the raw model output for invalid structured responses.

## 4. Tests and Verification

- [x] 4.1 Add Python tests for strict parsing of invalid constants and oversized numeric literals that become non-finite values.
- [x] 4.2 Add Python runner tests proving schema-invalid structured responses fail as quality failures and preserve raw output.
- [x] 4.3 Add render/export tests proving generated report JSON is parseable by a browser-compatible JSON parser and never emits bare non-finite constants.
- [x] 4.4 Add web component or report-store tests for invalid structured-output display fields.
- [x] 4.5 Run the relevant Python tests and web tests with `pnpm` for the web app.

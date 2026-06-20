## Context

Structured-output runs currently parse provider responses with Python's standard `json.loads()`. That parser accepts non-standard constants and can decode very large JSON numeric literals into non-finite floats. When those values are retained in `parsed_payload`, Python's default JSON writer can serialize them as bare `Infinity`, `-Infinity`, or `NaN`.

The web app reads `gitbench/web/public/results.json` during Astro page generation through `loadDataSync()`. Browser-compatible JSON parsers reject those bare constants, so a single invalid structured result can break the home page before fixture-level rendering can display the underlying model output.

The existing structured-output spec already says responses must parse and validate before scoring, and invalid structured responses should be fixture failures. The implementation needs to make that boundary strict and ensure report artifacts remain parseable transport JSON.

## Goals / Non-Goals

**Goals:**

- Treat invalid or out-of-contract structured responses as quality failures, not operational failures.
- Strictly parse structured response JSON before schema validation and canonicalization.
- Validate parsed structured payloads against the fixture's JSON Schema contract before canonicalization.
- Preserve the model's raw invalid structured output as a string for debugging and display.
- Keep `results.json`, SQLite report data, and API payloads browser-parseable.
- Show a clear fixture-detail error that includes the raw model output.

**Non-Goals:**

- Do not repair, coerce, or scrub invalid model JSON into a valid structured payload.
- Do not hide the raw invalid model response from fixture detail pages when publication safety allows output display.
- Do not change scoring semantics for valid structured payloads.
- Do not introduce a new report data source for the Astro home page.

## Decisions

### Use a strict structured JSON parser helper

Add a shared helper for structured response parsing in the Python harness. It should reject `NaN`, `Infinity`, and `-Infinity` using `parse_constant`, and it should reject any parsed tree containing non-finite numeric values.

Rationale: Python's standard decoder is more permissive than browser JSON parsers. Centralizing this behavior keeps OpenAI-compatible, Ollama, and mock adapters aligned.

Alternative considered: only make `render_json(..., allow_nan=False)` fail. That catches invalid artifacts late, but it does not classify the fixture correctly or preserve the raw model output with a useful structured error.

### Validate against the fixture contract before canonicalization

After strict JSON parsing, validate the payload against the fixture JSON Schema contract. Only validated payloads should be assigned to `parsed_payload` and canonicalized into scorer text.

Rationale: The observed raw output was syntactically a JSON number, but the fixture expected an object with a `commit` field. Even if parsing succeeds, schema validation must decide whether the structured response is usable.

Alternative considered: rely on canonicalization to fail when the primary path is missing. That is weaker, produces less precise errors, and can turn invalid objects into empty canonical text.

### Store invalid structured responses as raw output plus error, not parsed payload

For parse or schema failures, store:

- `model_output`: the raw provider output string, so fixture cards and copy actions show what the model returned.
- `raw_structured_output`: the same raw provider output string.
- `structured_error`: a clear parse or schema validation message.
- `parsed_payload`: absent/null.

Rationale: The raw output is the evidence. `parsed_payload` represents a successfully parsed and validated structured payload, so retaining invalid or non-finite values there is misleading and can break report serialization.

Alternative considered: keep the invalid parsed Python value for debugging. That recreates the `Infinity` artifact failure and makes report consumers handle Python-specific JSON extensions.

### Make report JSON serialization strict

Report JSON writers should use strict JSON serialization guardrails that reject non-finite values rather than emitting `Infinity`, `-Infinity`, or `NaN`. The report build should fail if invalid numeric values leak past structured-output validation.

Rationale: The web app cannot gracefully render fixture-level errors if the top-level report artifact cannot be parsed. Strict serialization provides a final safety net.

Alternative considered: serialize non-finite values as strings globally. That would scrub/coerce data and could silently hide invalid pipeline states outside structured-output fields.

### Display structured-output errors from valid report data

Fixture output cards should render structured-output parse/schema errors using the stored `structured_error` and `raw_structured_output`. Parse failures should use wording like `Invalid JSON. Output: <raw output>`; schema failures can use `Invalid structured output. Output: <raw output>`.

Rationale: The UI can only be graceful after the report artifact loads. Once invalid structured responses are represented as valid report data, the fixture detail view can show the exact raw output without crashing the app.

Alternative considered: have `loadDataSync()` catch invalid `results.json` and display an app-wide fallback. That may be useful later, but it does not satisfy the requirement to show the failing fixture output and does not fix generated report artifacts.

## Risks / Trade-offs

- Existing historical artifacts may already contain bare non-finite JSON constants -> Regenerate or doctor affected report artifacts after the parser/export fixes; strict report generation should prevent recurrence.
- Adding schema validation without an external dependency may only support the local schema subset -> Implement validation for the schema constructs GitBench emits today, or add a small dependency deliberately if subset validation becomes brittle.
- Provider APIs may claim schema-enforced output but still return invalid payloads through OpenRouter or adapter differences -> Treat provider enforcement as advisory and always validate locally.
- Raw invalid output could contain sensitive or unsafe content -> Continue applying existing result-safety publication gating before public display.

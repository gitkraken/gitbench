## Context

GitBench currently validates reasoning effort levels using a hardcoded `_MODEL_MATRIX` dict in `gitbench/harness/reasoning.py` covering 9 OpenAI models. All other models pass through silently. When an unsupported effort level is sent through OpenRouter, the provider silently maps it to the nearest supported level — there is no error, but the benchmark data is inaccurate and tokens are wasted.

The OpenRouter `/api/v1/models` endpoint returns a `supported_parameters` list per model that includes `reasoning` when the model supports it (183 out of 341 models). However, it does NOT expose which specific effort values are valid. The official OpenRouter `ReasoningEffort` enum is `[xhigh, high, medium, low, minimal, none]` — `max` is not in the schema but is known to work on some models (e.g., GPT-5).

## Goals / Non-Goals

**Goals:**
- Validate every model+effort combination before any benchmark executes
- Fail the entire run with a clear diagnostic if ANY model+effort pair is invalid
- Cache model capabilities aggressively so validation is fast on subsequent runs
- Cover all models in the user's config, not just OpenAI models

**Non-Goals:**
- Validating provider-specific parameters beyond reasoning effort
- Validating models for non-OpenRouter providers (Ollama, direct OpenAI)
- A separate CLI command — validation lives in the `run` flow
- Runtime validation during benchmark execution

## Decisions

### Decision 1: Two-source validation (API + shipped matrix)

**Choice:** Merge data from two sources:
1. Live API: `/api/v1/models?supported_parameters=reasoning` → set of reasoning-capable model IDs
2. Shipped data file: `gitbench/data/effort_matrix.json` → per-model valid effort levels

**Rationale:** The API reliably tells us whether reasoning is supported (free, no auth needed). The effort levels per model are not queryable, so we ship them. This gives us the highest accuracy without the unreliability and cost of probe requests.

**Alternatives considered:**
- *Probe requests*: Fire a tiny request with the candidate effort level and check if it errors. Rejected because OpenRouter silently maps invalid efforts (no error), making probes unreliable.
- *Pure API-only*: Can only validate binary reasoning support, not which effort levels work. Insufficient for strict validation.
- *Pure matrix-only*: Would work but misses new models and doesn't catch reasoning→non-reasoning mismatches.

### Decision 2: Cache with 7-day TTL, stored in user home

**Choice:** Cache the API response at `~/.cache/gitbench/model-capabilities.json` with a `fetched_at` timestamp. If cached data is fresher than 7 days, skip the API call. Cache is per-user.

**Rationale:** Model capabilities change infrequently. 7 days balances freshness with API call avoidance. User home avoids polluting the project directory. The shipped matrix provides model→effort mappings that don't need API refreshing.

### Decision 3: Strict gate with no opt-out by default

**Choice:** If validation fails, the run exits with exit code 1 and a detailed error message listing every invalid combination. There is no `--skip-validation` flag in scope.

**Rationale:** The user explicitly requested a hard gate. A bypass flag could be added later if needed, but the default should be strict.

### Decision 4: Validate at `run` startup, not a separate command

**Choice:** Validation runs automatically when `gitbench run` starts, after model collection but before any API calls.

**Rationale:** The user explicitly requested integration into `run`. This ensures no way to accidentally skip validation.

### Decision 5: Separate `capabilities.py` module

**Choice:** Create `gitbench/harness/capabilities.py` as a new module handling cache management, API fetching, and the validation gate. Simplify `reasoning.py` to just parsing and constants.

**Rationale:** Keeps concerns separated. Capability resolution is distinct from model name parsing and adapter-specific forwarding. The new module is the single source of truth for "what capabilities does this model have."

### Decision 6: `effort_matrix.json` as shipped data file

**Choice:** Store the model→effort mapping in `gitbench/data/effort_matrix.json` (a JSON file shipped in the package), not in Python code.

**Rationale:** Easier to update independently of code changes. JSON is human-readable and diffable in version control. The file can be the basis for automated updates from OpenRouter documentation.

## Risks / Trade-offs

**[R] Stale matrix** — New models ship with different effort support before we update the matrix.
→ Mitigation: Unknown models without effort configuration pass through (they have no claim to validate). Unknown models WITH effort fail with "not in capability database — may need matrix update." This is the desired strict behavior.

**[R] Cache invalidation** — If model capabilities change within 7 days, stale cache could let invalid configs through.
→ Mitigation: The cache only provides the set of reasoning-capable models. The effort matrix (shipped in code) is the authoritative source for effort levels. A stale cache would only cause false negatives (rejecting valid models as unsupported), not false positives. A `--refresh-capabilities` flag could be added later.

**[R] Multiple API keys** — The API listing doesn't need auth, but validation only covers OpenRouter. Direct OpenAI/Ollama models aren't validated.
→ Mitigation: This is acceptable. The primary use case is OpenRouter multi-model configs. Ollama silently ignores effort levels anyway.

**[R] `effort_matrix.json` grows large** — 183 reasoning-capable models with effort levels per model.
→ Mitigation: JSON file is ~10KB. Effort levels are only stored for models actually used in configs (50-60 entries), not all 183.

## Open Questions

- Should we add a `--refresh-capabilities` flag to force API re-fetch? (deferred to future)

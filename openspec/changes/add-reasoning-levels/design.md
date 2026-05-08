## Context

GitBench runs LLM-powered Git benchmarks. LLM providers now expose reasoning effort controls (e.g., OpenAI `reasoning_effort` for o-series models). Rather than adding new config fields or CLI flags, reasoning level is embedded in the model name itself using a `#` delimiter — the same model listed with different levels becomes naturally distinct in config, results, and reports.

**Current state:**
- `ModelInterface.generate()` accepts `**kwargs` — unused by the runner today
- Profiles list model names as plain strings (e.g., `"o3-mini"`)
- `BenchmarkResult` has no reasoning metadata
- CSV exports and HTML reports have no reasoning-level column/display

## Goals / Non-Goals

**Goals:**
- Parse `model#level` syntax from model names (e.g., `o3-mini#high`)
- Separate base model name from reasoning level in each adapter
- Forward reasoning level to provider APIs via adapter-specific parameters
- Track reasoning level in `Score` for reporting convenience
- Display reasoning level in CSV exports and HTML reports
- Work with existing config, CLI, and profile machinery with zero schema changes

**Non-Goals:**
- Validating that a given reasoning level is supported by a specific model
- Ollama reasoning support (no native reasoning parameter)
- Changing fixture YAML schema
- Adding `reasoning_level` to config profiles or CLI flags

## Decisions

### Decision 1: Reasoning level embedded in model name using `#` delimiter

**Rationale:** The model name is already a free-form string flowing through config, CLI, runner, adapter, and results. Embedding the level there requires zero schema changes, zero new CLI flags, and naturally makes runs at different levels distinct (the model name in results includes the level). A user simply lists `o3-mini`, `o3-mini#medium`, `o3-mini#high` in their profile's models list.

**Alternatives considered:**
- Separate config field + CLI flag — rejected per user preference; adds config/CLI complexity
- `:` delimiter — rejected because Ollama model tags use `:` (e.g., `llama3.1:8b`)
- `@` or `+` delimiter — `#` is the most conventional for parameter-like suffixes and least likely to appear in real model names

### Decision 2: Adapter parses the model name, not the runner

**Rationale:** Each adapter already owns model name interpretation. The adapter strips the `#level` suffix, uses the base name for API calls, and forwards the reasoning level as a provider-specific parameter. The runner passes the full model name through unchanged.

**Alternatives considered:**
- Centralized parsing in runner — rejected, violates adapter pattern and would require passing parsed parts separately
- Global utility function — would work but adapter-level parsing keeps the concern local to where it's consumed

### Decision 3: Full model name stored in envelope, parsed level exposed in Score

**Rationale:** The envelope stores the full model name (e.g., `o3-mini#high`) as-is — this is the natural key and already makes runs at different levels distinct. The `Score` dataclass additionally exposes a parsed `reasoning_level` field so CSV exports can include it without re-parsing.

**Alternatives considered:**
- Only store full model name and re-parse everywhere — rejected, duplicative and error-prone
- Store both parsed and raw in envelope — rejected, envelope already has the raw model name

### Decision 4: The `#` suffix is entirely optional

**Rationale:** Backward compatibility. Existing configs and model names without `#` are treated as having no reasoning level.

## Risks / Trade-offs

- **[Risk] A model name legitimately containing `#`** → Mitigation: extremely rare in practice; no known model uses `#` in its identifier
- **[Risk] Ollama has no reasoning support** → Mitigation: OllamaAdapter logs a debug message and ignores the level
- **[Trade-off] No validation of reasoning level values** → Accepted: provider API is the gate

## Why

The structured-output schema system is misleading models. The `exact_match` scoring type maps to a `command` template with key `command` and description "The git command to execute," but `exact_match` is used across benchmarks that expect commit messages, email addresses, filenames, counts, and other non-command outputs. For example, `blame_forensics/f002` expects the commit message "Refactor HTTP module" but the schema tells the model to output a git command, so the model produces `{command: "git show 790ba4b"}` instead of `{commit_message: "Refactor HTTP module"}`.

The root cause is an architectural conflation: **scoring type** (how to compare output) is used to determine **output shape** (what the model should produce), but these are orthogonal concerns. `exact_match` is a scoring strategy that says "compare strings exactly" — it says nothing about what the string represents.

Additionally, state-assertion benchmarks (`git_clean`, `tag_management`, `worktree_usage`, `submodule_usage`) all fall through to a `command_list` (array) schema even though most fixtures expect a single command, not a list.

## What Changes

- Replace the template-function + tuple architecture with a **named schema registry** — each schema is a `StructuredOutputContract` looked up by a unique string name (e.g., `"commit_message"`, `"command"`, `"count"`)
- Replace `BENCHMARK_TEMPLATE_OVERRIDES` (tuples of implementation functions) with `BENCHMARK_DEFAULT_SCHEMAS` (simple `{benchmark_name: schema_name}` mapping)
- Replace `SCORING_TYPE_TEMPLATES` with `SCORING_TYPE_FALLBACKS` (simple `{scoring_type: schema_name}` mapping) — only for scoring types with natural output shapes
- Add `output_schema` field to fixture YAML — an optional string referencing a named schema, taking precedence over benchmark defaults and scoring-type fallbacks
- Make `exact_match` **error** if no resolution is found (no silent fallback to `command`)
- Rename the `commit_message` schema key from `"commit"` to `"commit_message"` for semantic clarity
- Split `command` (single) vs `command_list` (multiple) as benchmark defaults for state-assertion benchmarks
- Add 9 new domain-specific schemas: `email`, `filename`, `file_content`, `file_list`, `file_status`, `commit_message_list`, `yes_no`, `line_numbers`, `version_number`
- Add per-fixture `output_schema` overrides to ~28 fixtures in heterogeneous benchmarks and multi-command state-assertion fixtures
- Remove all old template functions, `BENCHMARK_TEMPLATE_OVERRIDES`, `STATE_ASSERTION_BENCHMARKS`, and `SCORING_TYPE_TEMPLATES`

## Capabilities

### Modified Capabilities

- `fixture-structured-output`: The schema resolution architecture changes from tuple-based templates to a named registry with benchmark-level defaults and fixture-level overrides. The `commit_message` schema key renames from `commit` to `commit_message`. `exact_match` scoring no longer silently falls back to `command` — it errors without explicit configuration. State-assertion benchmarks default to `command` (single) instead of `command_list` (array).

## Impact

- **`gitbench/structured_output.py`**: Major rewrite — schema registry, benchmark defaults, scoring-type fallbacks, new resolution flow, removal of template functions and old mappings
- **`gitbench/harness/types.py`**: `Fixture` dataclass gains `output_schema: str | None = None` field
- **`gitbench/harness/loader.py`**: Parse `output_schema` from fixture YAML
- **`gitbench/fixture_structured_validator.py`**: Update to use new resolution flow
- **`gitbench/harness/runner.py`**: No changes needed (already calls `contract_for_benchmark_fixture`)
- **`gitbench/harness/model.py`**: No changes needed (already accepts `StructuredOutputContract`)
- **Fixture YAML files** (~28 files): Add `output_schema` field to heterogeneous benchmark fixtures and multi-command state-assertion fixtures
- **Backward compatibility**: No fixture YAML changes required for homogeneous benchmarks — benchmark defaults handle them. The `commit_message` key rename is a breaking change for any stored results that reference the old key, but structured output is parsed at runtime so this only affects live model responses.
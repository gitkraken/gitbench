## Context

GitBench's structured-output system sends JSON schemas to model APIs (OpenAI-compatible `response_format` or Ollama `format`) to constrain model responses. The schema includes a key name and description that semantically guide the model's output.

The current architecture derives the schema from the fixture's **scoring type** via `SCORING_TYPE_TEMPLATES`:

```python
"exact_match": (command_template, "command", "string"),
```

This maps `exact_match` → `{command: "The git command to execute"}`. But `exact_match` is used by benchmarks expecting commit messages, emails, filenames, counts, file content, and other non-command answers. The model sees the `command` key and description, overrides its prompt instructions, and outputs a git command instead of the expected answer.

Additionally:
- State-assertion benchmarks fall through to `command_list` (array schema) even when most fixtures expect a single command
- The `commit_message` schema uses key `"commit"` which is ambiguous (could mean hash, message, or identifier)
- The `BENCHMARK_TEMPLATE_OVERRIDES` dict stores tuples of `(template_fn, primary_path, canonicalize)` — implementation details that shouldn't be in a configuration mapping

The fixture YAML already has an optional `structured_output` field (a full `StructuredOutputContract` dict), but it's never used in practice. The `Fixture` dataclass supports it but no fixture YAML declares it.

## Goals / Non-Goals

**Goals:**
- Create a named schema registry where each schema is a `StructuredOutputContract` looked up by a unique string
- Set benchmark-level default schemas as simple `{benchmark: schema_name}` mappings
- Add fixture-level `output_schema` field (a string referencing a named schema) for per-fixture overrides
- Make `exact_match` error loudly when no schema can be resolved (no silent misleading fallback)
- Rename `commit_message` schema key from `"commit"` to `"commit_message"`
- Default state-assertion benchmarks to `command` (single) instead of `command_list` (array)
- Add domain-specific schemas for heterogeneous benchmark fixtures
- Keep semantic separation between `resolved_content` (conflict resolution) and `file_content` (raw file content from history)

**Non-Goals:**
- Changing scoring logic, scoring types, or how scores are computed
- Changing how model adapters send schemas to providers
- Changing the fixture YAML structure beyond adding the optional `output_schema` field
- Changing the canonicalization strategies themselves (only which strategy each schema uses)
- Supporting user-defined custom schemas at runtime (the registry is code-defined)

## Decisions

### Named schema registry replaces template functions

**Decision:** A `SCHEMA_REGISTRY: dict[str, StructuredOutputContract]` where each entry is a complete contract (schema dict, primary_path, canonicalize, display_label). Looked up by string name.

**Rationale:** The current system spreads schema definition across template functions, scoring-type tuples, and benchmark override tuples — three places to look to understand one schema. A registry centralizes all schemas in one place, and benchmark/fixture configuration becomes simple string references.

**Alternative considered:** Keep template functions but change the mappings. Rejected because it keeps implementation details (function references, primary_path strings, canonicalize strings) in what should be configuration.

### Benchmark defaults as `{benchmark: schema_name}`

**Decision:** `BENCHMARK_DEFAULT_SCHEMAS: dict[str, str]` — just benchmark name to schema name. No tuples, no function references.

**Rationale:** This is declarative configuration, not implementation. Adding a new benchmark default is one line: `"new_benchmark": "commit_message"`. The schema definition lives in the registry.

### `output_schema` field in fixture YAML

**Decision:** Fixtures get an optional `output_schema: str` field containing a schema name from the registry. The loader parses it and stores it on the `Fixture` dataclass.

```yaml
id: f001
output_schema: email
# ...rest of fixture
```

**Rationale:** Simple string reference is easy to author, easy to validate, and keeps the schema definition in one place (the registry). The existing `structured_output` field (full contract dict) is kept for backward compatibility but `output_schema` is preferred.

**Alternative considered:** Keep using `structured_output` with inline schema dicts. Rejected because it duplicates schema definitions across fixtures and is harder to maintain.

### `exact_match` errors without resolution

**Decision:** When a fixture uses `exact_match` scoring and has no `output_schema` override and its benchmark has no default, the resolution raises a clear configuration error.

**Rationale:** `exact_match` is the only scoring type with no natural output shape — it could be anything. Silently falling back to `command` is the original bug. Erroring forces explicit configuration, which is the correct behavior for a polymorphic scoring type.

**Alternative considered:** Add a generic `answer` schema as fallback. Rejected per user direction — generic keys don't provide semantic guidance for structured output tokenization.

### Resolution precedence

```
1. fixture.output_schema (string) → SCHEMA_REGISTRY lookup
2. BENCHMARK_DEFAULT_SCHEMAS[benchmark_name] → SCHEMA_REGISTRY lookup
3. SCORING_TYPE_FALLBACKS[scoring_type] → SCHEMA_REGISTRY lookup
   (only for scoring types with natural shapes; exact_match excluded)
4. Error: "No schema resolution for fixture {id}"
```

### Key rename: `commit` → `commit_message`

**Decision:** The `commit_message` schema changes its JSON key from `"commit"` to `"commit_message"`.

**Rationale:** `"commit"` is ambiguous — it could mean a commit hash, a commit message, or a commit identifier. `"commit_message"` is unambiguous and directly matches what the prompt asks for. This was the specific issue observed: models seeing `{command: "..."}` output commands instead of commit messages. With the key being `commit_message`, the model has no ambiguity.

**Note:** The `bisect_commit` schema keeps key `"commit"` — in that context, "commit" means "the commit identifier" (hash or subject), not specifically a commit message.

### `resolved_content` vs `file_content` separation

**Decision:** Two distinct schemas:
- `resolved_content` — key: `resolved_content`, description: "The resolved file content" — for cherry_pick, merge_conflicts, rebase (conflict resolution)
- `file_content` — key: `content`, description: "The file content" — for git_show/f005 (reading file content from history)

**Rationale:** A model seeing `{resolved_content: "..."}` knows it's resolving a conflict. A model seeing `{content: "..."}` knows it's just reporting file content. Different mental models, different token guidance. Both currently canonicalize as strings, but the semantic distinction matters for model behavior.

### `command` vs `command_list` as benchmark defaults

**Decision:** State-assertion benchmarks (`git_clean`, `tag_management`, `worktree_usage`, `submodule_usage`) default to `command` (single string). Fixtures that expect multiple commands get per-fixture `output_schema: command_list` overrides.

**Rationale:** Most state-assertion fixtures expect a single command. The `command_list` array schema forces the model to output `["git clean -f"]` instead of `"git clean -f"`, which is unnecessary cognitive overhead and can confuse the canonicalization.

Multi-command fixtures identified:
- `worktree_usage`: f002 (2 commands), f007 (2 commands), f008 (4 commands)
- `submodule_usage`: f002 (2 commands), f003 (3 commands), f005 (3 commands), f007 (2 commands)

### Phased implementation

**Decision:** Three phases, each independently validatable.

**Rationale:** Phase 1 (schema registry + benchmark defaults) fixes the highest-impact issues with zero fixture YAML changes, providing a clean validation checkpoint. Phase 2 (per-fixture overrides) adds the long tail of heterogeneous fixes. Phase 3 (cleanup) removes dead code and runs full validation.

## Schema Registry (Complete)

| Name | Key | Type | Canonicalize | Description |
|------|-----|------|-------------|-------------|
| `commit_message` | `commit_message` | string | string | "The commit message of the identified commit" |
| `commit_message_list` | `commit_message_list` | array[str] | lines | "The list of commit messages" |
| `bisect_commit` | `commit` | string | string | "The commit hash or subject of the bad commit" |
| `commit_selection` | `commits` | array[str] | lines | "The commit hashes or subjects to select for squashing" |
| `hash` | `hash` | string | string | "The commit hash" |
| `command` | `command` | string | string | "The git command to execute" |
| `command_list` | `commands` | array[str] | command_lines | "The git commands to execute, one per element" |
| `stash_ref` | `stash` | string | stash_ref | "The stash reference (e.g. stash@{0})" |
| `reflog_ref` | `ref` | string | string | "The reflog reference" |
| `resolved_content` | `resolved_content` | string | file_block | "The resolved file content" |
| `file_content` | `content` | string | string | "The file content" |
| `filename` | `filename` | string | string | "The file name" |
| `file_list` | `files` | array[str] | lines | "The matching file names" |
| `file_status` | `status_code` | string | string | "The git status code (A, M, R, D, etc.)" |
| `branch_list` | `branches_to_delete` | array[str] | lines | "Branch names to delete" |
| `string_list` | `items` | array[str] | lines | "The list of matching items" |
| `count` | `count` | integer | numeric_string | "The numeric count" |
| `email` | `email` | string | string | "The email address" |
| `yes_no` | `found` | string | string | "Whether the search found matches (yes or no)" |
| `line_numbers` | `line_numbers` | string | string | "The line numbers where the pattern appears, comma-separated" |
| `version_number` | `version_number` | string | string | "The version number found" |

## Benchmark Default Mapping

| Benchmark | Default Schema | Was (old architecture) |
|-----------|---------------|----------------------|
| `blame_forensics` | `commit_message` | `command` (via exact_match → command_template) |
| `commit_messages` | `commit_message` | `commit` (key rename) |
| `git_clean` | `command` | `command_list` (via state_assertion fallback) |
| `tag_management` | `command` | `command_list` (via state_assertion fallback) |
| `worktree_usage` | `command` | `command_list` (via state_assertion fallback) |
| `submodule_usage` | `command` | `command_list` (via state_assertion fallback) |
| `cherry_pick` | `resolved_content` | `resolved_content` (unchanged) |
| `merge_conflicts` | `resolved_content` | `resolved_content` (unchanged) |
| `rebase` | `resolved_content` | `resolved_content` (unchanged) |
| `branch_cleanup` | `branch_list` | `branch_list` (unchanged) |
| `stash_recovery` | `stash_ref` | `stash_ref` (via scoring type) |
| `reflog` | `reflog_ref` | `reflog_ref` (via scoring type) |
| `git_bisect` | `bisect_commit` | `bisect_commit` (via scoring type) |
| `commit_squash` | `commit_selection` | `commit_selection` (via scoring type) |
| `git_show` | *(none)* | `command` (via exact_match) — now requires per-fixture |
| `git_grep` | *(none)* | mixed — now requires per-fixture |
| `git_log_format` | *(none)* | mixed — now requires per-fixture |

## Per-Fixture Overrides (Phase 2)

### git_show

| Fixture | output_schema | Why |
|---------|--------------|-----|
| f001 | `email` | "What is the author email?" |
| f002 | `filename` | "Which file was modified?" |
| f003 | `commit_message` | "What is the commit message?" |
| f004 | `email` | "What is the tagger email?" |
| f005 | `file_content` | "What was the content of doc.txt?" |
| f006 | `count` | "How many files were changed?" |
| f007 | `email` | "What is the author email?" |
| f008 | *(auto: hash)* | commit_hash_by_subject scoring type |
| f009 | `count` | "How many parent commits?" |
| f010 | `file_status` | "What is the status code?" (R) |
| f011 | `filename` | "Which file was changed?" |
| f012 | `count` | "How many files were added?" |

### git_grep

| Fixture | output_schema | Why |
|---------|--------------|-----|
| f001 | `file_list` | "Which files contain X?" (override string_list fallback) |
| f002 | *(auto: count)* | numeric_exact scoring type |
| f003 | *(auto: count)* | numeric_exact scoring type |
| f004 | `line_numbers` | "On which line numbers?" → "1,2,3" |
| f005 | *(auto: count)* | numeric_exact scoring type |
| f006 | `yes_no` | "Did the search find anything?" → "no" |
| f007 | *(auto: count)* | numeric_exact scoring type |
| f008 | `count` | "How many matches in src/?" → "2" |
| f009 | `version_number` | "What version number?" → "2.0" (string, not int) |
| f010 | `count` | "How many whole word matches?" → "2" |
| f011 | *(auto: count)* | numeric_exact scoring type |
| f012 | `file_list` | "Which files have counts?" (override string_list fallback) |

### git_log_format

| Fixture | output_schema | Why |
|---------|--------------|-----|
| f001 | `count` | "How many commits have 'Fix'?" → "2" |
| f002 | `commit_message_list` | "List commit messages with 'Add'" (override string_list) |
| f003 | `commit_message_list` | "Which commits by Alice?" (override string_list) |
| f004 | `count` | "How many commits by Alice?" → "3" |
| f005 | `commit_message_list` | "List commits in date range" → 2 messages |
| f006 | `count` | "How many commits in date range?" → "3" |
| f007 | *(auto: hash)* | commit_hash_by_subject scoring type |
| f008 | `count` | "How many commits total?" → "7" |
| f009 | `count` | "How many merge commits?" → "1" |
| f010 | *(auto: count)* | numeric_exact scoring type |
| f011 | `filename` | "Which file had most changes?" → "large.txt" |
| f012 | `count` | "How many insertions?" → "8" |

### State-assertion benchmarks (command_list overrides)

| Benchmark | Fixture | output_schema | Commands |
|-----------|---------|--------------|----------|
| `worktree_usage` | f002 | `command_list` | 2 commands |
| `worktree_usage` | f007 | `command_list` | 2 commands |
| `worktree_usage` | f008 | `command_list` | 4 commands |
| `submodule_usage` | f002 | `command_list` | 2 commands |
| `submodule_usage` | f003 | `command_list` | 3 commands |
| `submodule_usage` | f005 | `command_list` | 3 commands |
| `submodule_usage` | f007 | `command_list` | 2 commands |

## Scoring Type Fallbacks

| Scoring Type | Schema Name | Has natural shape? |
|-------------|-------------|-------------------|
| `numeric_exact` | `count` | Yes |
| `commit_hash_by_subject` | `hash` | Yes |
| `unordered_line_set` | `string_list` | Yes |
| `command_equivalence` | `command_list` | Yes |
| `stash_recovery` | `stash_ref` | Yes |
| `reflog_recovery` | `reflog_ref` | Yes |
| `bisect_regression` | `bisect_commit` | Yes |
| `commit_selection` | `commit_selection` | Yes |
| `llm_judge` | `commit_message` | Yes |
| `similarity` | `commit_message` | Yes |
| `state_assertions` | `command_list` | Yes |
| `exact_match` | *(none)* | **No — errors without explicit configuration** |
| `json_semantic_equal` | *(none)* | **No — requires per-fixture configuration** |

## Risks / Trade-offs

- **Risk: `commit_message` key rename breaks stored results** → **Mitigation:** Structured output is parsed at runtime from model responses, not from stored results. Old results with `parsed_payload: {commit: "..."}` are historical artifacts and won't be re-parsed. The rename only affects live model responses going forward.

- **Risk: Heterogeneous benchmarks have no default, so new fixtures without `output_schema` will error** → **Mitigation:** This is intentional. The error message will guide fixture authors to add `output_schema`. Better to error than to silently mislead models.

- **Risk: `version_number` schema is used by only one fixture (git_grep/f009)** → **Mitigation:** Acceptable — the schema is domain-specific and semantically correct. The registry can have single-use schemas; the alternative (generic key) is worse for model guidance.

- **Trade-off: `exact_match` no longer has a fallback** → This means every `exact_match` fixture must have either a benchmark default or a per-fixture `output_schema`. This is more work but prevents the original class of bug. The error message makes the fix obvious.

- **Trade-off: ~28 fixture YAML files need edits** → Acceptable for correctness. Homogeneous benchmarks need zero changes (Phase 1 handles them via benchmark defaults).
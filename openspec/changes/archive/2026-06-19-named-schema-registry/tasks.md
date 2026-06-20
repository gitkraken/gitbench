## Phase 1: Core Architecture + Homogeneous Benchmarks

- [x] 1.1 Create `SCHEMA_REGISTRY: dict[str, StructuredOutputContract]` in `gitbench/structured_output.py` with all base schemas (existing schemas as named entries, with `commit_message` key renamed from `commit` to `commit_message`)
- [x] 1.2 Create `BENCHMARK_DEFAULT_SCHEMAS: dict[str, str]` mapping all 14 homogeneous benchmarks to schema names
- [x] 1.3 Create `SCORING_TYPE_FALLBACKS: dict[str, str]` mapping scoring types with natural shapes to schema names (excluding `exact_match`)
- [x] 1.4 Add `output_schema: str | None = None` field to `Fixture` dataclass in `gitbench/harness/types.py`
- [x] 1.5 Update `Fixture.to_dict()` and `Fixture.from_dict()` to round-trip `output_schema`
- [x] 1.6 Update `FixtureLoader` in `gitbench/harness/loader.py` to parse `output_schema` from YAML
- [x] 1.7 Rewrite `contract_for_benchmark_fixture()` to use new resolution: `fixture.output_schema` → `BENCHMARK_DEFAULT_SCHEMAS` → `SCORING_TYPE_FALLBACKS` → error
- [x] 1.8 Update `gitbench/fixture_structured_validator.py` to use new resolution flow
- [x] 1.9 Validate: run `fixture_structured_validator` across all fixtures — all 14 homogeneous benchmarks should pass; the 3 heterogeneous benchmarks should show errors (expected, fixed in Phase 2)

## Phase 2: Per-Fixture Overrides + New Schemas

- [x] 2.1 Add new schemas to `SCHEMA_REGISTRY`: `email`, `filename`, `file_content` (key=`content`), `file_list` (key=`files`), `file_status`, `commit_message_list`, `yes_no` (key=`found`), `line_numbers`, `version_number`
- [x] 2.2 Add `output_schema: email` to `git_show` f001, f004, f007
- [x] 2.3 Add `output_schema: filename` to `git_show` f002, f011
- [x] 2.4 Add `output_schema: commit_message` to `git_show` f003
- [x] 2.5 Add `output_schema: file_content` to `git_show` f005
- [x] 2.6 Add `output_schema: count` to `git_show` f006, f009, f012
- [x] 2.7 Add `output_schema: file_status` to `git_show` f010
- [x] 2.8 Add `output_schema: file_list` to `git_grep` f001, f012
- [x] 2.9 Add `output_schema: line_numbers` to `git_grep` f004
- [x] 2.10 Add `output_schema: yes_no` to `git_grep` f006
- [x] 2.11 Add `output_schema: count` to `git_grep` f008, f010
- [x] 2.12 Add `output_schema: version_number` to `git_grep` f009
- [x] 2.13 Add `output_schema: count` to `git_log_format` f001, f004, f006, f008, f009, f012
- [x] 2.14 Add `output_schema: commit_message_list` to `git_log_format` f002, f003, f005
- [x] 2.15 Add `output_schema: filename` to `git_log_format` f011
- [x] 2.16 Add `output_schema: command_list` to `worktree_usage` f002, f007, f008
- [x] 2.17 Add `output_schema: command_list` to `submodule_usage` f002, f003, f005, f007
- [x] 2.18 Validate: run `fixture_structured_validator` across all fixtures — all should pass with zero issues

## Phase 3: Cleanup + Full Validation

- [x] 3.1 Remove all old template functions (`commit_message_template`, `command_template`, `numeric_template`, `hash_template`, `stash_ref_template`, `reflog_ref_template`, `bisect_commit_template`, `resolved_content_template`, `json_object_template`, `command_list_template`, `branch_list_template`, `commit_selection_template`, `string_list_template`, `_json_schema_object`)
- [x] 3.2 Remove `SCORING_TYPE_TEMPLATES` (replaced by `SCORING_TYPE_FALLBACKS`)
- [x] 3.3 Remove `BENCHMARK_TEMPLATE_OVERRIDES` (replaced by `BENCHMARK_DEFAULT_SCHEMAS`)
- [x] 3.4 Remove `STATE_ASSERTION_BENCHMARKS` (subsumed by benchmark defaults + scoring fallbacks)
- [x] 3.5 Remove old `resolve_contract_for_fixture()` function
- [x] 3.6 Remove old `contract_for_benchmark_fixture()` implementation (replaced in Phase 1)
- [x] 3.7 Run full test suite: `pytest tests/ -v`
- [x] 3.8 Run `fixture_structured_validator` across all fixtures one final time — verify zero issues
- [x] 3.9 Verify no fixture falls through to error — every fixture resolves to a named schema
- [x] 3.10 Spot-check: verify `blame_forensics/f002` resolves to `commit_message` schema with key `commit_message`, not `command`
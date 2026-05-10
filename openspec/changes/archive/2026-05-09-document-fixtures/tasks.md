## 1. Data model changes

- [x] 1.1 Add `purpose`, `difficulty`, `tags` fields to `Fixture` dataclass in `gitbench/harness/types.py` with defaults (`""`, `""`, `[]`)
- [x] 1.2 Update `Fixture.to_dict()` and `Fixture.from_dict()` to round-trip the new fields

## 2. Loader changes

- [x] 2.1 Update `FixtureLoader` in `gitbench/harness/loader.py` to parse `purpose`, `difficulty`, `tags` from YAML
- [x] 2.2 Add soft validation: emit `logging.warning` when a fixture is missing any metadata field
- [x] 2.3 Validate `difficulty` is one of the allowed enum values; warn and default to `""` if invalid

## 3. Results output

- [x] 3.1 Include fixture metadata (`purpose`, `difficulty`, `tags`) in `Score` serialization in JSON results output
- [x] 3.2 Ensure metadata does NOT leak into the model prompt — only `prompt` field is sent

## 4. Backfill fixture metadata

- [x] 4.1 Backfill `blame_forensics` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.2 Backfill `branch_cleanup` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.3 Backfill `cherry_pick` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.4 Backfill `commit_messages` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.5 Backfill `commit_squash` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.6 Backfill `git_bisect` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.7 Backfill `git_clean` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.8 Backfill `git_grep` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.9 Backfill `git_log_format` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.10 Backfill `git_show` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.11 Backfill `merge_conflicts` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.12 Backfill `rebase` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.13 Backfill `reflog` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.14 Backfill `stash_recovery` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.15 Backfill `submodule_usage` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.16 Backfill `tag_management` fixtures (f001–f012) with purpose, difficulty, tags
- [x] 4.17 Backfill `worktree_usage` fixtures (f001–f012) with purpose, difficulty, tags

## 5. Documentation

- [x] 5.1 Update `CONTRIBUTING.md` with fixture metadata authoring guide: field definitions, difficulty rubric with examples, tips for writing good purpose statements
- [x] 5.2 Update fixture schema YAML example in README.md to show new optional fields

## 6. Verification

- [x] 6.1 Run existing tests to confirm no regressions: `pytest tests/ -v`
- [x] 6.2 Manually run a benchmark with verbose output to verify metadata appears in results: `gitbench run --benchmark commit_messages --model mock --verbose`
- [x] 6.3 Run all benchmarks with mock model to verify all 204 fixtures load and score: `gitbench run --all --model mock`
- [x] 6.4 Verify no metadata appears in model prompts by inspecting mock output

## 1. Benchmark Git Environment Helper

- [x] 1.1 Add a reusable helper in `gitbench.utils.git` that returns a benchmark Git subprocess environment with `commit.gpgsign=false` and `tag.gpgSign=false`.
- [x] 1.2 Ensure the helper appends to existing `GIT_CONFIG_COUNT` entries instead of replacing unrelated Git config entries.
- [x] 1.3 Ensure deterministic `FixtureGenerationContext` values and optional caller-provided environment values are preserved when the helper applies signing overrides.

## 2. Runtime Integration

- [x] 2.1 Update `GitExecutor` to use the benchmark Git environment for fixture setup commands.
- [x] 2.2 Update `git_clean`, `submodule_usage`, `tag_management`, and `worktree_usage` model-command execution paths to use the benchmark Git environment while preserving required variables such as `GIT_ALLOW_PROTOCOL`.
- [x] 2.3 Search for additional benchmark paths that create commits or tags outside `GitExecutor` and wire the helper where needed.
- [x] 2.4 Leave existing fixture-level signing-disable commands in place unless removing them is clearly harmless and covered by tests.

## 3. Regression Coverage

- [x] 3.1 Add unit coverage for the environment helper, including append behavior with pre-existing `GIT_CONFIG_COUNT` entries.
- [x] 3.2 Add fixture setup coverage that simulates globally enabled `commit.gpgsign` and verifies normal and nested setup commits succeed without signing.
- [x] 3.3 Add stateful benchmark coverage that simulates globally enabled `tag.gpgSign` and verifies an annotated tag command executes without requiring a signing key.
- [x] 3.4 Add stateful benchmark coverage that simulates globally enabled `commit.gpgsign` and verifies a model-executed commit command succeeds without signing.
- [x] 3.5 Add or retain coverage proving unrelated Git configuration, especially `init.defaultBranch=main`, remains available.

## 4. Validation

- [x] 4.1 Run the focused Python tests for Git execution and affected stateful benchmarks.
- [x] 4.2 Run the broader relevant test subset to confirm benchmark setup, scoring, and fixture self-check behavior were not regressed.
- [x] 4.3 Run OpenSpec validation for `disable-git-signing-for-benchmarks`.

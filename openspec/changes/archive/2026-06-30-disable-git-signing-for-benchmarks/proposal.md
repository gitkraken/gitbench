## Why

Users can have global Git signing enabled through `commit.gpgsign=true` or `tag.gpgSign=true`. GitBench fixture setup and stateful benchmark scoring run temporary Git repositories that should not depend on a user's signing keys, so signing failures currently turn benchmark infrastructure into invalid model-quality signal.

## What Changes

- Ensure benchmark Git commands run with signing disabled for commits and tags by default.
- Apply the unsigned Git environment to fixture repository setup and to benchmark paths that execute model-provided Git commands during scoring.
- Preserve unrelated user and system Git configuration, such as default branch naming and protocol settings, instead of replacing the global config wholesale.
- Add regression coverage that simulates globally enabled commit and tag signing and verifies benchmark setup/scoring remain unsigned.

## Capabilities

### New Capabilities
- `benchmark-git-environment`: Defines the isolated Git environment required for benchmark fixture setup and stateful model-command execution.

### Modified Capabilities

None.

## Impact

- Affected code: `gitbench/utils/git.py`, stateful command benchmarks that execute model output, and related tests.
- Affected behavior: temporary benchmark repositories and model-executed benchmark Git commands ignore global commit/tag signing requirements.
- No CLI flags, result schemas, dependencies, or stored report formats change.

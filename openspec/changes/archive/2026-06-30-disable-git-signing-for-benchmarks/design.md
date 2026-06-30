## Context

GitBench builds temporary repositories from fixture setup commands and, for state-assertion benchmarks, executes model-provided Git commands against those repositories before scoring. These subprocesses currently inherit the user's Git configuration, so global `commit.gpgsign=true` or `tag.gpgSign=true` can force signing inside benchmark repos that do not have working signing keys.

Two fixtures already contain local signing workarounds, but the failure mode is broader than those fixtures. Most fixture setups create commits, and tag-management scoring can execute a correct annotated-tag command that fails only because the user's global tag signing is enabled.

## Goals / Non-Goals

**Goals:**

- Disable commit and tag signing for benchmark Git operations by default.
- Apply the behavior to fixture setup and to benchmark paths that execute model-provided commands.
- Preserve unrelated Git configuration so existing assumptions such as default branch naming continue to work.
- Keep the behavior internal to benchmark execution, with no new user-facing CLI option.
- Add tests that reproduce globally enabled signing and prove benchmark execution remains unsigned.

**Non-Goals:**

- Do not remove all user/global Git configuration from benchmark subprocesses.
- Do not change fixture prompts, expected answers, scoring contracts, result schemas, or report output.
- Do not add real signing support to benchmark fixtures.
- Do not require authors to add `git config commit.gpgsign false` or `git config tag.gpgSign false` to individual fixtures.

## Decisions

### Centralize benchmark Git environment construction

Add a helper in `gitbench.utils.git` that returns an environment dict for benchmark Git subprocesses. The helper should copy a caller-provided base environment, defaulting to `os.environ`, and append Git config entries:

- `commit.gpgsign=false`
- `tag.gpgSign=false`

The helper should use Git's `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_<n>` / `GIT_CONFIG_VALUE_<n>` mechanism and append after any existing entries so the benchmark's unsigned values take precedence.

Alternative considered: write local repo config immediately after every `git init`. That misses nested repositories created inside one fixture shell command and puts the burden on setup ordering.

Alternative considered: set `GIT_CONFIG_GLOBAL=/dev/null`. That is broader than needed and can remove benign settings used by the suite, such as system-level `init.defaultBranch=main`.

### Use the helper from setup and stateful command execution

`GitExecutor` should initialize its subprocess environment through the helper. If a `FixtureGenerationContext` is supplied, its deterministic author, committer, date, locale, and timezone values should be layered into the same environment before appending the signing overrides.

Benchmarks that execute normalized model command output should also use the helper. The initial target set is the stateful command benchmarks that currently build an ad hoc environment for execution:

- `git_clean`
- `submodule_usage`
- `tag_management`
- `worktree_usage`

Where these paths need additional variables such as `GIT_ALLOW_PROTOCOL`, those values should be merged before adding the signing overrides.

Alternative considered: only update `GitExecutor`. That fixes fixture setup but still leaves scoring-time false negatives when a correct model answer creates an annotated tag or commit under a signed global config.

### Keep read-only Git subprocesses unchanged unless needed

Read-only subprocesses used for context generation and assertions do not trigger signing and do not need to use the new helper as part of this change. This keeps the change focused on commands that can create signed objects.

Alternative considered: route every Git subprocess through the helper immediately. That is more uniform, but it increases the diff and risk without solving additional signing failures.

## Risks / Trade-offs

- [Risk] Existing `GIT_CONFIG_COUNT` entries are overwritten accidentally. -> Append to any existing count rather than replacing it, and cover the append behavior with a unit test.
- [Risk] A benchmark path that creates commits/tags outside `GitExecutor` or the four stateful command executors is missed. -> Search for model-command execution and commit/tag creation paths during implementation; add tests around the known failure surfaces.
- [Risk] Disabling tag signing changes a fixture intentionally testing signed tags. -> Existing fixtures simulate signed-tag awareness with annotated tags because no key is configured; real signing remains out of scope.
- [Risk] The helper masks a user's desire to test signed Git behavior locally. -> GitBench benchmark runs should be reproducible model evaluations, so unsigned fixture execution is the default contract.

## Migration Plan

Implement the helper, wire it into setup and stateful command execution, and add regression tests. Existing fixture-level signing-disable commands may remain harmlessly redundant; removing them is optional cleanup, not required for this change.

Rollback is straightforward: revert the helper usage and tests. No persisted data or user configuration is migrated.

## Open Questions

None.

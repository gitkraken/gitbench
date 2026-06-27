## Why

The June 25 fixture assessment identified real prompt/scorer mismatches, but it is now stale input evidence rather than current truth. This change captures the decisions from the follow-up review so fixture prompts, expected answers, and scorers agree before new campaign results are interpreted as model-quality signal.

## What Changes

- Fix `git_log_format/f005` so date-range filtering is scored as an unordered set of matching commit messages.
- Fix `submodule_usage/f005` so it verifies a correctly added, committed submodule state without requiring an unstated commit message.
- Add a `resolved_file_blocks` scorer for multi-file resolved-content answers.
- Migrate only the known multi-file conflict fixtures in this change:
  - `merge_conflicts/f010`, `cherry_pick/f010`, `rebase/f010`
  - `merge_conflicts/f012`, `cherry_pick/f012`, `rebase/f012`
- Clarify ambiguous single-file conflict prompts such as the `f005` conflict fixtures, but keep their current single-file scorer for now.
- Add shared strict command-answer normalization for stateful command execution and `command_equivalence`: accept plain command text or one whole-answer fenced code block, and reject prose extraction.
- Standardize all `commit_squash` prompts and expected values around selected commit subject lines, one per line.
- Update `commit_selection` scoring so hash-only answers fail once fixtures request subject lines, while bullet markers and legacy comma-separated subject lists remain tolerated.
- Add scorer capability metadata used by fixture self-checks so generic checks understand effective scoring behavior, including benchmark-local scorers.
- Keep campaign reruns out of scope; validation for this change is local tests only.
- Do not update `docs/benchmark-fixture-assessment.md`; it remains a historical assessment snapshot.

## Capabilities

### New Capabilities
- `scorer-capability-metadata`: Advertises effective scorer behavior for fixture self-checks and related tooling.

### Modified Capabilities
- `fixture-scoring-robustness`: Add multi-file resolved-content scoring, strict command wrapper normalization, and deterministic commit-selection subject scoring.
- `fixture-calibration`: Correct the agreed fixture prompt/scoring mismatches and require local validation for the changed suite behavior.
- `fixture-structured-output`: Add a named structured-output shape for multi-file resolved-content answers where needed.

## Impact

- Fixture YAML under `fixtures/git_log_format`, `fixtures/submodule_usage`, `fixtures/merge_conflicts`, `fixtures/cherry_pick`, `fixtures/rebase`, and `fixtures/commit_squash`.
- Scoring code in `gitbench/harness/scorer.py` and benchmark-specific scoring in `gitbench/benchmarks/commit_squash.py`.
- Command execution paths in `gitbench/benchmarks/git_clean.py`, `gitbench/benchmarks/tag_management.py`, `gitbench/benchmarks/worktree_usage.py`, and `gitbench/benchmarks/submodule_usage.py`.
- Fixture self-check code in `gitbench/fixture_self_check.py` plus a shared scoring metadata module.
- Structured-output schema registry in `gitbench/structured_output.py`.
- Local tests covering scorer behavior, fixture self-check behavior, command normalization, and affected expected-answer paths.

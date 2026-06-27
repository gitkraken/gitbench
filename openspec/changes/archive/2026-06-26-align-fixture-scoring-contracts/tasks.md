## 1. Scorer And Normalizer Foundations

- [x] 1.1 Add `resolved_file_blocks` scorer with explicit `scoring.expected_files`, strict file-content comparison, order-insensitive filename matching, default extra-file rejection, and `allow_extra_files` support.
- [x] 1.2 Add parser tests for accepted headings, reordered files, per-file fences, missing files, extra files, trailing whitespace, final newline differences, indentation changes, and malformed scorer config.
- [x] 1.3 Add a shared command-answer normalizer that accepts plain command text or one whole-answer fenced block and rejects prose extraction.
- [x] 1.4 Wire the shared command normalizer into `command_equivalence`.
- [x] 1.5 Wire the shared command normalizer into stateful command execution for `git_clean`, `tag_management`, `worktree_usage`, and `submodule_usage`.
- [x] 1.6 Add command normalization tests for whole-answer fences, prose rejection, invalid command syntax, stateful execution, and command equivalence.

## 2. Fixture Contract Updates

- [x] 2.1 Change `git_log_format/f005` to order-insensitive line-set scoring while keeping the date-range filtering prompt focused on matching commits.
- [x] 2.2 Change `submodule_usage/f005` assertions to verify a properly added and committed submodule state without depending on a specific commit message.
- [x] 2.3 Migrate `merge_conflicts/f010`, `cherry_pick/f010`, and `rebase/f010` to `resolved_file_blocks` with explicit `expected_files`.
- [x] 2.4 Update `merge_conflicts/f012`, `cherry_pick/f012`, and `rebase/f012` prompts to ask for both `app.py` and `requirements.txt`, then migrate them to `resolved_file_blocks`.
- [x] 2.5 Clarify ambiguous single-file conflict `f005` prompts while leaving their existing scorer in place.
- [x] 2.6 Standardize all `commit_squash` prompts to request selected commit subject lines, one per line.
- [x] 2.7 Migrate all `commit_squash.expected` values to newline-separated subject lines.

## 3. Commit Selection Behavior

- [x] 3.1 Update commit-selection parsing to treat newline-separated subject lines as canonical expected values while preserving legacy comma-separated subject parsing.
- [x] 3.2 Keep bullet markers accepted around selected subject lines.
- [x] 3.3 Reject hash-only commit-squash answers when the fixture requests subject lines.
- [x] 3.4 Update commit-squash tests, including the existing hash-only passing test, to reflect the subject-line output contract.

## 4. Scorer Capability Metadata And Self-Checks

- [x] 4.1 Add shared scorer capability metadata with lookup by `(benchmark_name, scoring.type)` and fallback by `scoring.type`.
- [x] 4.2 Move self-check decisions onto capability metadata for order sensitivity, dynamic lookup keys, and selection parsing.
- [x] 4.3 Keep `benchmark_name` optional in this change, but update suite-level validation/test paths to pass it where available.
- [x] 4.4 Add tests showing no false warning for branch-cleanup set scoring, reflog dynamic lookup keys, git-bisect dynamic/subject behavior, and generic exact-match multiline warnings.

## 5. Structured Output

- [x] 5.1 Add a named structured-output schema for multi-file resolved-content answers.
- [x] 5.2 Add canonicalization and validation tests showing multi-file payloads preserve filenames and contents for `resolved_file_blocks`.
- [x] 5.3 Verify existing single `resolved_content` structured-output behavior remains unchanged.

## 6. Local Verification

- [x] 6.1 Run the focused local tests for scorer behavior, command normalization, commit-squash behavior, fixture self-checks, structured output, and affected benchmark fixtures.
- [x] 6.2 Run the broader local test set agreed for fixture changes, excluding campaign execution.
- [x] 6.3 Confirm `docs/benchmark-fixture-assessment.md` remains unchanged and is only referenced as stale source evidence.

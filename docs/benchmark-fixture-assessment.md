# Benchmark Fixture Suite Assessment

Date: 2026-06-25

## Scope

This assessment covers every YAML benchmark fixture under `fixtures/`.

- Total fixtures: 204
- Benchmark groups: 17
- Fixtures per group: 12
- Active OpenSpec changes during assessment: none

## Evidence Used

- `openspec list --json`: no active changes.
- Fixture inventory: all 17 benchmark directories contain 12 YAML fixtures.
- Structured-output validation: 204 fixtures with contracts, 0 missing contracts, 0 issues.
- Runtime setup pass: 204 fixture repos set up successfully, 0 setup failures.
- Expected-answer runtime pass: 179 non-judge fixtures passed when scored with their expected answer, 12 `llm_judge` fixtures skipped, 13 expected-answer failures were dynamic target fixtures where `expected` stores a stable subject while the scorer requires a live hash or reflog selector.
- Existing low-pass audit source: `web/data/gitbench.db`, 14 stored attempts per fixture.
- Targeted tests: `tests/test_loader.py`, `tests/test_fixture_self_check.py`, `tests/test_structured_output.py`, and `tests/test_benchmarks.py` yielded 323 passing tests and 1 failure in `TestCommitMessagesBenchmark.test_score_method_works`. The failure is a mock/test compatibility issue with judge evidence, not an observed fixture YAML defect.

## Rating Key

- `Keep`: fixture is valid and valuable as-is.
- `Review`: fixture is valuable, but prompt wording, scorer tolerance, accepted alternatives, or observed pass rate should be reviewed.
- `Fix`: likely fixture/scoring defect before using failures as model-quality signal.
- Value is rated `High`, `Medium`, or `Low` relative to this suite.

## Suite-Level Findings

1. The fixture corpus is structurally healthy. Loading, metadata, setup, and structured-output round-tripping all passed across the full suite.
2. The main validity risks are not YAML shape. They are prompt/scorer alignment issues:
   - exact text scoring for conflict-resolution code blocks,
   - multi-file answer formatting,
   - command fixtures where fenced code blocks are executed literally,
   - prompts that imply one answer policy but do not state it.
3. The highest-priority fixture defects are:
   - `git_log_format/f005`: prompt does not specify order, but expected answer requires oldest-first order.
   - `submodule_usage/f005`: prompt asks to commit but does not specify the commit message, while assertions require `Add lib submodule`.
   - `merge_conflicts/f010`, `cherry_pick/f010`, and `rebase/f010`: high-value multi-file fixtures, but exact text formatting drives zero-pass behavior despite many semantically close outputs.
   - `merge_conflicts/f012`, `cherry_pick/f012`, and `rebase/f012`: prompts discuss two conflicted files but expected output only scores the primary file, causing avoidable ambiguity.
4. The cheap self-check currently reports false positives for benchmark-local scorers:
   - branch-cleanup fixtures are set-scored locally despite `exact_match` in YAML,
   - `git_bisect` and `reflog` fixtures use stable expected subjects with dynamic hash/selector scoring,
   - `commit_squash/f001` mentions hashes in the prompt but uses commit-selection scoring.
   The self-check should become scorer-aware before its warnings are treated as fixture defects.
5. The suite has strong value coverage. It spans commit-message generation, history forensics, grep/log/show interpretation, conflict resolution, bisect, reflog, stash, cleanup, submodules, tags, and worktrees. The weaker-value items are mostly trivial baselines, which are still useful for sanity checks.

## Global Next Steps

1. Fix the concrete fixture defects first: `git_log_format/f005`, `submodule_usage/f005`, and the multi-file conflict fixtures listed above.
2. Add scorer/executor normalization for common answer wrappers:
   - strip one wrapping fenced code block before command execution,
   - normalize code-block/file-block answers for exact conflict fixtures,
   - consider a semantic multi-file resolved-content scorer.
3. Make self-check scorer-aware so dynamic hash/reflog/bisect and branch-cleanup fixtures do not produce false warnings.
4. Re-run a campaign after fixture/scorer fixes and regenerate the low-pass audit against the new suite version.
5. Use post-fix pass-rate bands only after known fixture defects are removed; current low pass rate is a triage signal, not proof of difficulty.

## Fixture Assessments

### `blame_forensics`

Overall assessment: high-value benchmark. The fixtures test real blame/log reasoning with concrete bug classes. Exact-match to commit subject is mostly appropriate because the prompt asks for one commit message. Low-pass items should be reviewed for ambiguity in causal attribution, not retired.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 79% | Keep / High | SQL-injection regression is clear and valuable. | Keep. |
| `f002` | 86% | Keep / High | Missing error handling regression is clear. | Keep. |
| `f003` | 79% | Keep / High | Hardcoded secret introduction is a useful security-forensics case. | Keep. |
| `f004` | 93% | Keep / High | Race-condition removal is clear and well calibrated. | Keep. |
| `f005` | 29% | Review / High | Variable rename/reversion is valuable, but failures suggest causal attribution is debatable from the context. | Clarify why the later partial revert is the introducing commit, or keep as intentionally hard-medium. |
| `f006` | 57% | Keep / High | Off-by-one history is valid and tests nuanced blame reasoning. | Keep and monitor after next campaign. |
| `f007` | 100% | Keep / Medium | Integer truncation case is valid but currently easy. | Keep as baseline. |
| `f008` | 86% | Keep / High | Path traversal regression is clear and valuable. | Keep. |
| `f009` | 71% | Keep / High | Resource leak regression is clear. | Keep. |
| `f010` | 50% | Keep / High | Broken import case is validated by a self-check command and is valuable. | Keep; use as medium/hard calibration input. |
| `f011` | 79% | Keep / High | Access-control comparator change is precise and useful. | Keep. |
| `f012` | 93% | Keep / High | Null-check removal is clear. | Keep. |

### `branch_cleanup`

Overall assessment: valid and useful. The benchmark-local scorer correctly treats branch lists as sets, so self-check warnings about multi-line `exact_match` are false positives. The lower-pass `none` fixtures reveal model confusion around `main` appearing in merged output.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 64% | Keep / High | Single merged branch case is valid. | Keep. |
| `f002` | 71% | Keep / High | Multiple merged branch case is valid; order-insensitive scorer handles output order. | Keep. |
| `f003` | 43% | Review / Medium | `none` edge case is valuable but models may count `main`. | Consider prompt note: ignore `main` itself. |
| `f004` | 79% | Keep / High | Mixed merged/unmerged feature branches are valuable. | Keep. |
| `f005` | 93% | Keep / Medium | Hotfix branch cleanup is clear. | Keep. |
| `f006` | 93% | Keep / High | Mixed naming conventions are useful. | Keep. |
| `f007` | 100% | Keep / High | Nested branch topology is valuable despite high pass rate. | Keep. |
| `f008` | 100% | Keep / Medium | All-branches-merged case is valid. | Keep. |
| `f009` | 50% | Review / Medium | All-unmerged edge case is valuable but likely needs stronger `none` wording. | Clarify that only non-main merged branches should be listed. |
| `f010` | 79% | Keep / Medium | Release-branch cleanup is valid. | Keep. |
| `f011` | 71% | Keep / Low | Main-only repo is a trivial baseline. | Keep as sanity check. |
| `f012` | 100% | Keep / High | Large mixed branch set is valid. | Keep. |

### `cherry_pick`

Overall assessment: valuable but the exact-output conflict fixtures need calibration. Many low-pass outputs are semantically close but fail due to formatting or ambiguous policy. Multi-file fixtures are worth keeping after scorer/prompt fixes.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 29% | Review / High | Single-line conflict expects a combined result without explicitly stating the merge policy. | State the desired policy, or accept multiple semantically valid resolutions. |
| `f002` | 79% | Keep / Medium | Version conflict is clear enough. | Keep. |
| `f003` | 86% | Keep / Medium | Status conflict is clear. | Keep. |
| `f004` | 43% | Review / High | Contact conflict has no explicit preference policy, and expected output chooses one side. | Clarify preference policy. |
| `f005` | 7% | Fix / High | "Most useful changes" is subjective; expected answer ignores plausible merged alternatives. | Rewrite prompt with explicit chosen behavior or use a semantic code scorer. |
| `f006` | 71% | Keep / High | Config merge tests combining independent values. | Keep, but monitor for ambiguity. |
| `f007` | 93% | Keep / High | Multi-setting preference case is well calibrated. | Keep. |
| `f008` | 93% | Keep / High | Partial-conflict case is clear. | Keep. |
| `f009` | 93% | Keep / High | Three-way author conflict has clear current/incoming framing. | Keep. |
| `f010` | 0% | Fix / High | High-value multi-file fixture, but exact file-prefix/blank-line formatting is too brittle. | Add multi-file normalization or structured file-block scoring. |
| `f011` | 71% | Keep / High | JSON conflict is valid. | Keep; consider JSON semantic scorer if future failures are formatting-only. |
| `f012` | 21% | Review / High | Prompt discusses `requirements.txt` but expected output only scores `app.py`; models often answer broader task. | Either score both files or remove unscored file details from the prompt. |

### `commit_messages`

Overall assessment: high-value commit-message benchmark. The 12 fixtures cover common diff shapes and use `llm_judge`, which is the right fit for semantic message quality. The one targeted test failure is a stale/mock issue in the test, not fixture content.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 100% | Keep / Low | Single-file add is a trivial baseline. | Keep. |
| `f002` | 100% | Keep / Medium | Multiple new files test useful summarization. | Keep. |
| `f003` | 93% | Keep / Medium | Rename operation is valuable. | Keep. |
| `f004` | 93% | Keep / Medium | Deletion operation is valuable. | Keep. |
| `f005` | 86% | Keep / Medium | Single-file modification is valid. | Keep. |
| `f006` | 86% | Keep / High | Replacement-style change is valuable. | Keep. |
| `f007` | 100% | Keep / Medium | Subdirectory component add is valid. | Keep. |
| `f008` | 93% | Keep / High | Executable-bit change is a useful metadata case. | Keep. |
| `f009` | 93% | Keep / High | Bug-fix semantic message is valuable. | Keep. |
| `f010` | 86% | Keep / High | Multi-file refactor is valuable. | Keep. |
| `f011` | 86% | Keep / Medium | Config change is valid. | Keep. |
| `f012` | 100% | Keep / Medium | Docs-only change is valid. | Keep. |

### `commit_squash`

Overall assessment: valid and valuable. The custom `commit_selection` scorer is a good fit because it accepts commit messages or hashes and rejects clearly extra selected commits. Lower-pass fixtures look like meaningful difficulty rather than setup defects.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 93% | Keep / High | Basic WIP pair is well calibrated. | Keep. |
| `f002` | 100% | Keep / High | Fixup commit identification is clear. | Keep. |
| `f003` | 71% | Keep / High | Consecutive WIP updates are valuable. | Keep. |
| `f004` | 93% | Keep / High | Incremental feature construction is clear. | Keep. |
| `f005` | 50% | Review / High | Experimental sequence is valuable but borderline low-pass. | Review wording after next campaign; do not change unless failures show ambiguity. |
| `f006` | 71% | Keep / Medium | Documentation WIP selection is useful. | Keep. |
| `f007` | 86% | Keep / High | Test-file WIP sequence is valid. | Keep. |
| `f008` | 64% | Keep / High | Config WIP sequence is valid. | Keep. |
| `f009` | 57% | Review / High | Logic plus style-fix selection is valuable but may be borderline subjective. | Review failed outputs for whether style fix should be included. |
| `f010` | 79% | Keep / High | Debug WIP commits are clear. | Keep. |
| `f011` | 71% | Keep / High | Selective feature-1-only squashing is valuable. | Keep. |
| `f012` | 79% | Keep / High | Multi-WIP selection is valid. | Keep. |

### `git_bisect`

Overall assessment: structurally valid. All fixtures set up real histories and the custom scorer accepts either live hash prefix or subject. Value is high for regression identification, although the provided test-result table makes many cases easy for current models.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 100% | Keep / Medium | Bad-at-HEAD baseline is valid. | Keep. |
| `f002` | 93% | Keep / High | Mid-history config regression is valuable. | Keep. |
| `f003` | 100% | Keep / Medium | Feature-disable regression is valid. | Keep. |
| `f004` | 86% | Keep / High | TODO/removal regression is useful. | Keep. |
| `f005` | 93% | Keep / Medium | Setup regression is valid. | Keep. |
| `f006` | 100% | Keep / Medium | Port regression is valid but easy. | Keep. |
| `f007` | 93% | Keep / High | Environment switch regression is useful. | Keep. |
| `f008` | 100% | Keep / High | Validation removal is valuable despite high pass rate. | Keep. |
| `f009` | 100% | Keep / High | Import replacement regression is valid. | Keep. |
| `f010` | 100% | Keep / High | Debug-mode regression is valuable. | Keep. |
| `f011` | 79% | Keep / High | Color/config regression is better calibrated. | Keep. |
| `f012` | 93% | Keep / High | Production switch regression is valid. | Keep. |

### `git_clean`

Overall assessment: high-value stateful command benchmark. The low-pass fixtures are mostly subtle but valid command knowledge. A shared executor improvement should strip fenced command blocks before execution.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 93% | Keep / Low | Basic untracked file removal is a useful baseline. | Keep. |
| `f002` | 100% | Keep / Medium | Dry-run behavior is valid. | Keep. |
| `f003` | 79% | Keep / Medium | Directory removal is valid. | Keep. |
| `f004` | 36% | Keep / High | Ignored-files-only cleanup is subtle and valuable. | Keep; strip command fences globally. |
| `f005` | 43% | Keep / High | Untracked and ignored files but not directories is a valuable distinction. | Keep. |
| `f006` | 86% | Keep / Medium | Path-scoped cleanup is valid. | Keep. |
| `f007` | 71% | Keep / High | Exclusion option is useful. | Keep. |
| `f008` | 93% | Keep / Medium | Force directory cleanup is valid. | Keep. |
| `f009` | 93% | Keep / Medium | Directory-scoped cleanup is valid. | Keep. |
| `f010` | 100% | Keep / Medium | Dry-run with directories is valid. | Keep. |
| `f011` | 50% | Keep / High | Ignored directories are a calibrated hard edge. | Keep. |
| `f012` | 57% | Keep / High | Scoped untracked plus ignored cleanup is valuable. | Keep. |

### `git_grep`

Overall assessment: valid and useful. Sentinel-driven grep setup works. `f006` intentionally returns empty grep output, so empty context is not a setup defect. Numeric context-line fixtures are good calibration cases.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 100% | Keep / Medium | Filename extraction is valid. | Keep. |
| `f002` | 86% | Keep / Medium | Commit-message grep count is valid. | Keep. |
| `f003` | 93% | Keep / High | Regex/function-count case is valid. | Keep. |
| `f004` | 100% | Keep / Medium | Line-number extraction is valid. | Keep. |
| `f005` | 93% | Keep / Medium | Case-insensitive count is valid. | Keep. |
| `f006` | 71% | Review / Medium | Empty-output no-match case is valid but implicit. | Consider adding "empty output means no matches" if this is not meant to test inference. |
| `f007` | 43% | Keep / High | Context-line counting is validated by self-check and well calibrated. | Keep. |
| `f008` | 86% | Keep / Medium | Directory-limited function count is valid. | Keep. |
| `f009` | 100% | Keep / Medium | Branch-target grep is valid. | Keep. |
| `f010` | 93% | Keep / Medium | Whole-word matching is valid. | Keep. |
| `f011` | 64% | Keep / High | Multi-pattern count is useful. | Keep. |
| `f012` | 100% | Keep / Medium | Per-file count interpretation is valid. | Keep. |

### `git_log_format`

Overall assessment: mostly valid. `f005` is the clear defect because output order is not specified but exact scoring requires one order. Dynamic hash scoring for `f007` is appropriate.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 100% | Keep / Medium | Count by message grep is valid. | Keep. |
| `f002` | 93% | Keep / Medium | Add-message listing uses order-insensitive scoring. | Keep. |
| `f003` | 93% | Keep / Medium | Author filtering uses order-insensitive scoring. | Keep. |
| `f004` | 79% | Keep / Medium | Author count is valid. | Keep. |
| `f005` | 50% | Fix / High | Date-range list requires oldest-first order without saying so; default `git log` order is newest-first. | Specify order or switch to unordered-line-set. |
| `f006` | 71% | Keep / High | Date-range count is valid. | Keep. |
| `f007` | 93% | Keep / High | Short-hash lookup uses dynamic scoring correctly. | Keep. |
| `f008` | 93% | Keep / Medium | Commit count is valid. | Keep. |
| `f009` | 93% | Keep / Medium | Merge-count fixture is valid. | Keep. |
| `f010` | 100% | Keep / High | Multiple merge commits count is valid. | Keep. |
| `f011` | 100% | Keep / Medium | Stat largest-file extraction is valid. | Keep. |
| `f012` | 100% | Keep / Medium | Stat insertion count is valid. | Keep. |

### `git_show`

Overall assessment: valuable inspection benchmark. Most fixtures are strong. `f002` is low-pass because the context contains adjacent commits and models often answer the latest shown commit rather than the requested subject; this may be acceptable difficulty or may warrant narrower context.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 93% | Keep / Low | Latest author email is a baseline. | Keep. |
| `f002` | 36% | Review / High | Targeted commit file extraction is valuable but distractor context causes many wrong answers. | Consider narrowing context or emphasizing the requested commit subject. |
| `f003` | 100% | Keep / Medium | Lightweight tag target message is valid. | Keep. |
| `f004` | 100% | Keep / High | Annotated tagger metadata is valuable. | Keep. |
| `f005` | 79% | Keep / High | File-at-revision content is valid. | Keep. |
| `f006` | 100% | Keep / Medium | Changed-file count is valid. | Keep. |
| `f007` | 100% | Keep / Low | Latest author email with explicit format is easy baseline. | Keep. |
| `f008` | 100% | Keep / High | Full hash extraction uses dynamic scoring correctly. | Keep. |
| `f009` | 100% | Keep / Medium | Merge parent count is valid. | Keep. |
| `f010` | 100% | Keep / Medium | Rename status code extraction is valid. | Keep. |
| `f011` | 100% | Keep / Medium | Binary file stat extraction is valid. | Keep. |
| `f012` | 93% | Keep / Medium | Added-file count is valid. | Keep. |

### `merge_conflicts`

Overall assessment: high-value but scorer/prompt calibration is the main weakness. Exact content scoring is appropriate for some single-file cases but brittle for code blocks and multi-file answers.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 36% | Review / High | Expected combines both branch edits, but prompt does not state that policy. | Clarify merge policy or accept multiple valid resolutions. |
| `f002` | 93% | Keep / Medium | Version conflict is well calibrated. | Keep. |
| `f003` | 79% | Keep / Medium | Status conflict is valid. | Keep. |
| `f004` | 86% | Keep / High | Contact multi-line conflict is valuable and currently calibrated. | Keep. |
| `f005` | 43% | Fix / High | "Most useful changes" is subjective and expected answer is one debatable policy. | State exact desired behavior or score semantic properties. |
| `f006` | 64% | Keep / High | YAML config merge is valuable. | Keep; monitor ambiguity. |
| `f007` | 71% | Keep / High | Three-way config policy is valuable. | Keep. |
| `f008` | 86% | Keep / High | Partial-conflict scenario is valuable. | Keep. |
| `f009` | 93% | Keep / High | Three-way author conflict is calibrated. | Keep. |
| `f010` | 0% | Fix / High | Multi-file answer format is too brittle for exact scoring. | Add file-block normalization or structured multi-file scorer. |
| `f011` | 79% | Keep / High | JSON conflict is valid. | Keep; consider JSON semantic scorer later. |
| `f012` | 7% | Review / High | Prompt discusses two files, but expected scores only `app.py`. | Either score both files or remove `requirements.txt` from the prompt. |

### `rebase`

Overall assessment: valuable and mostly clearer than merge/cherry-pick because several prompts specify current-branch policy. The same exact-output and multi-file issues remain.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 43% | Review / High | Expected combines edits but prompt does not state that resolution policy. | Clarify policy or accept multiple valid resolutions. |
| `f002` | 100% | Keep / Medium | Version conflict explicitly keeps current branch. | Keep. |
| `f003` | 100% | Keep / Medium | Status conflict explicitly keeps current branch. | Keep. |
| `f004` | 79% | Keep / High | Contact conflict is valid. | Keep. |
| `f005` | 14% | Fix / High | "Most useful changes" is subjective and expected differs from merge/cherry-pick analogs. | State explicit policy or use semantic scorer. |
| `f006` | 64% | Keep / High | YAML config merge is valuable. | Keep. |
| `f007` | 79% | Keep / High | Three-way config policy is valid. | Keep. |
| `f008` | 79% | Keep / High | Project-title conflict is valid. | Keep. |
| `f009` | 100% | Keep / High | Current-branch author policy is explicit. | Keep. |
| `f010` | 0% | Fix / High | Multi-file exact formatting causes zero-pass behavior. | Add file-block normalization or structured multi-file scorer. |
| `f011` | 93% | Keep / High | JSON conflict is valid. | Keep. |
| `f012` | 0% | Review / High | Prompt discusses two files, but expected scores only `app.py`. | Either score both files or remove `requirements.txt` from the prompt. |

### `reflog`

Overall assessment: high-value recovery benchmark. Dynamic `reflog_recovery` scoring is appropriate; self-check hash warnings are false positives because stable expected subjects resolve to live hashes/selectors at score time.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 79% | Keep / High | Soft-reset recovery is valid. | Keep. |
| `f002` | 93% | Keep / High | Hard-reset recovery is valid. | Keep. |
| `f003` | 79% | Keep / High | Amend original-hash recovery is valuable. | Keep. |
| `f004` | 79% | Keep / High | Deleted feature branch recovery is valuable. | Keep. |
| `f005` | 93% | Keep / High | Pre-squash rebase recovery is valuable. | Keep. |
| `f006` | 86% | Keep / High | Detached-HEAD recovery is valid. | Keep. |
| `f007` | 93% | Keep / High | Multiple reset recovery is valuable. | Keep. |
| `f008` | 71% | Keep / High | Incorrect rebase recovery is valuable. | Keep. |
| `f009` | 86% | Keep / High | Cherry-pick then reset recovery is valid. | Keep. |
| `f010` | 79% | Keep / High | Orphaned commit recovery is valid; message acceptance is intentional. | Keep. |
| `f011` | 86% | Keep / High | Multi-branch expert case is valuable. | Keep. |
| `f012` | 64% | Keep / High | Hard reset then checkout is useful and calibrated. | Keep. |

### `stash_recovery`

Overall assessment: valid and well calibrated. The custom stash-ref scorer avoids string-similarity false positives between adjacent stash references.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 100% | Keep / Low | Single stash is a trivial baseline. | Keep. |
| `f002` | 100% | Keep / Medium | Older stash lookup is valid. | Keep. |
| `f003` | 93% | Keep / Medium | Branch reference lookup is valid. | Keep. |
| `f004` | 100% | Keep / Medium | Pre-merge stash timing is valid. | Keep. |
| `f005` | 100% | Keep / High | Stash-pop failure recovery is valuable. | Keep. |
| `f006` | 93% | Keep / Medium | Multi-file stash lookup is valid. | Keep. |
| `f007` | 100% | Keep / Medium | Older index selection is valid. | Keep. |
| `f008` | 93% | Keep / High | Untracked-file stash is valuable. | Keep. |
| `f009` | 100% | Keep / High | Apply vs pop distinction is valuable. | Keep. |
| `f010` | 93% | Keep / Medium | Subdirectory stash context is valid. | Keep. |
| `f011` | 93% | Keep / High | Stash after rebase is valuable. | Keep. |
| `f012` | 93% | Keep / Medium | Branch-name message parsing is valid. | Keep. |

### `submodule_usage`

Overall assessment: high-value stateful command benchmark. Most fixtures are valid; `f005` has a concrete prompt/assertion mismatch around the required commit message. Fenced command output should be stripped globally before execution.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 79% | Keep / High | Basic add-submodule command is valid. | Keep. |
| `f002` | 79% | Keep / High | Init/update workflow is valid. | Keep. |
| `f003` | 36% | Keep / High | Complete removal is subtle and valuable. | Keep; strip command fences globally. |
| `f004` | 71% | Keep / Medium | Status command is valid. | Keep. |
| `f005` | 14% | Fix / High | Assertion requires commit message `Add lib submodule`, but prompt does not specify it. | Specify commit message in prompt or remove message-specific assertion. |
| `f006` | 79% | Keep / Medium | Listing command uses command-equivalence scoring. | Keep. |
| `f007` | 93% | Keep / High | Multiple submodule add is valid. | Keep. |
| `f008` | 57% | Keep / High | Deinit without removal is valuable. | Keep. |
| `f009` | 79% | Keep / High | URL sync workflow is valid. | Keep. |
| `f010` | 86% | Keep / High | Remote update workflow is valid. | Keep. |
| `f011` | 100% | Keep / Low | `.gitmodules` inspection is easy but useful baseline. | Keep. |
| `f012` | 86% | Keep / High | Branch-tracking submodule add is valid. | Keep. |

### `tag_management`

Overall assessment: valid stateful command benchmark. Lower-pass fixtures are largely meaningful Git-tag subtleties rather than fixture defects.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 86% | Keep / Low | Lightweight tag baseline is valid. | Keep. |
| `f002` | 93% | Keep / Medium | Annotated tag creation is valid. | Keep. |
| `f003` | 79% | Keep / Medium | Tag deletion is valid. | Keep. |
| `f004` | 93% | Keep / Low | Tag listing baseline is valid. | Keep. |
| `f005` | 100% | Keep / Medium | Pattern filtering is valid. | Keep. |
| `f006` | 79% | Keep / High | Tagging an older commit is valuable. | Keep. |
| `f007` | 79% | Keep / Medium | Tag inspection is valid. | Keep. |
| `f008` | 57% | Keep / High | Rename-via-create/delete is valuable and state-scored. | Keep. |
| `f009` | 71% | Keep / Medium | Simulated signed tag wording is acceptable. | Keep. |
| `f010` | 79% | Keep / High | Push tag to remote is valid. | Keep. |
| `f011` | 57% | Keep / High | Fetching remote tags is valid and useful. | Keep. |
| `f012` | 100% | Keep / Medium | Version-sort listing is valid. | Keep. |

### `worktree_usage`

Overall assessment: high-value stateful command benchmark. `f005` failures include invalid long-option guesses, so low pass is meaningful. `f008` is valid but should benefit from global command-fence stripping.

| Fixture | Rate | Status | Assessment | Next step |
| --- | ---: | --- | --- | --- |
| `f001` | 79% | Keep / High | Existing-branch worktree creation is valid. | Keep. |
| `f002` | 86% | Keep / High | Worktree edit/commit workflow is valuable. | Keep. |
| `f003` | 79% | Keep / Medium | Worktree removal is valid. | Keep. |
| `f004` | 86% | Keep / Medium | Worktree listing uses command-equivalence scoring. | Keep. |
| `f005` | 21% | Keep / High | New-branch worktree creation is valuable; common failures are invalid Git syntax. | Keep. |
| `f006` | 79% | Keep / High | Detached worktree is valuable. | Keep. |
| `f007` | 86% | Keep / High | Multiple worktrees are valid. | Keep. |
| `f008` | 29% | Review / High | End-to-end worktree commit is valuable; fenced/multi-command output likely suppresses otherwise valid answers. | Strip command fences before execution and rerun audit. |
| `f009` | 79% | Keep / High | Broken worktree prune/repair is valid. | Keep. |
| `f010` | 71% | Keep / Medium | Worktree lock command is valid. | Keep. |
| `f011` | 79% | Keep / Medium | Worktree unlock command is valid. | Keep. |
| `f012` | 86% | Keep / High | Tag-based worktree is valid. | Keep. |

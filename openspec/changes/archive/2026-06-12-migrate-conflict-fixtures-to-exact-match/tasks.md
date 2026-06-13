## 1. Scorer: fence normalization

- [x] 1.1 Add a `_strip_wrapping_fence(text) -> str` helper in `gitbench/harness/scorer.py` that removes a single wrapping triple-backtick fence (with optional language tag on the opening line) and surrounding whitespace; returns input unchanged when no complete wrapping fence is present
- [x] 1.2 Apply the helper in the `exact_match` branch of `Scorer.score()` when `fixture.scoring.get("strip_fences")` is true, before the existing `.strip()` comparison

## 2. Fixture migration

- [x] 2.1 Migrate `fixtures/cherry_pick/` f001–f008, f010–f012 to `scoring: {type: exact_match, strip_fences: true}`; add `order_matters: true` where expected is multi-line; drop `threshold`
- [x] 2.2 Migrate `fixtures/merge_conflicts/` f001–f008, f010–f012 the same way
- [x] 2.3 Migrate `fixtures/rebase/` f001, f004–f008, f010–f012 the same way
- [x] 2.4 Migrate `fixtures/git_grep/f001.yaml` to `scoring: {type: unordered_line_set}`; drop `threshold`

## 3. Structured-output alignment

- [x] 3.1 Add `cherry_pick` and `rebase` entries to `BENCHMARK_TEMPLATE_OVERRIDES` in `gitbench/structured_output.py` using `resolved_content_template` / `file_block`, matching the existing `merge_conflicts` entry, so `json_schema` mode does not fall back to the command-shaped template that `exact_match` maps to
- [x] 3.2 Run the fixture self-check (`fixture_self_check`) over the migrated benchmarks and resolve any flagged issues

## 4. Tests

- [x] 4.1 Unit tests for `_strip_wrapping_fence`: bare fence, fence with language tag, no fence, unterminated fence, fence with internal backticks in content
- [x] 4.2 Scorer tests: exact_match with `strip_fences` passes fenced-correct output and fails unfenced-wrong output; without the flag, fenced output fails
- [x] 4.3 Regression test encoding the original false positive: `'Hello, Planet!'` against expected `'Hello, Planet!!!'` must fail under the migrated scoring
- [x] 4.4 Verify `git_grep/f001` passes with reordered lines and fails with extra filenames under `unordered_line_set` defaults
- [x] 4.5 Run the full test suite and a mock-model benchmark run for the four affected benchmarks in both output modes

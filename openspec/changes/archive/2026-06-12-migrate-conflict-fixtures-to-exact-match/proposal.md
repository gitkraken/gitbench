## Why

32 fixtures across `cherry_pick` (11), `merge_conflicts` (11), `rebase` (9), and `git_grep` (1) use `similarity` (SequenceMatcher) scoring even though each has a single deterministic correct answer — the resolved file content or an exact filename list. Fuzzy matching produces verified false positives: on `cherry_pick/f001` and `rebase/f001`, the wrong resolution `Hello, Planet!` scores 0.933 against expected `Hello, Planet!!!` and **passes** the 0.9 threshold, crediting a model that completely failed the merge (kept one side, dropped the incoming change). The whole point of those fixtures is combining both sides, and character-level similarity cannot see the difference.

## What Changes

- Migrate 31 conflict-resolution fixtures (`cherry_pick` f001–f008/f010–f012, `merge_conflicts` f001–f008/f010–f012, `rebase` f001/f004–f008/f010–f012) from `scoring.type: similarity` to `scoring.type: exact_match`
- Migrate `git_grep/f001` from `similarity` to `unordered_line_set`, consistent with the other line-list git_grep fixtures
- Add an opt-in `strip_fences: true` scoring option to the `exact_match` path that removes a single wrapping markdown code fence (with optional language tag) before comparison, so a model that wraps correct file content in ``` fences is not failed on formatting alone
- Set `order_matters: true` on migrated multi-line fixtures (required by the fixture self-check rule for multi-line exact_match)
- Remove now-unused `threshold` keys from migrated fixtures
- No changes to fixture prompts, setup, or expected values

## Capabilities

### Modified Capabilities

- `fixture-scoring-robustness`: `exact_match` gains optional code-fence normalization; conflict-resolution and filename-list fixtures move from fuzzy to deterministic scoring

## Impact

- `fixtures/cherry_pick/*.yaml`, `fixtures/merge_conflicts/*.yaml`, `fixtures/rebase/*.yaml`, `fixtures/git_grep/f001.yaml` — scoring blocks updated
- `gitbench/harness/scorer.py` — `exact_match` branch gains fence normalization
- `gitbench/structured_output.py` — `SCORING_TYPE_TEMPLATES` maps `exact_match` to `command_template`; verify `BENCHMARK_TEMPLATE_OVERRIDES` / `STATE_ASSERTION_BENCHMARKS` keep `cherry_pick`, `merge_conflicts`, `rebase` on file-content templates in `json_schema` output mode (merge_conflicts already overrides to `resolved_content_template`)
- `tests/test_scorer.py` — new cases for fence normalization and migrated scoring
- **Pass rates will drop** for these benchmarks — that is the intent, but historical result comparability breaks; results produced before/after this change should not be charted together

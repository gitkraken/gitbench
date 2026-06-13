## Why

Whether the LLM judge scores a fixture is currently decided by three scattered, implicit conditions: the hardcoded `JUDGE_REQUIRED_BENCHMARKS = {"commit_messages"}` allowlist in `gitbench/config.py:18`, per-benchmark scorer injection in `runner.py:140`, and the scorer's `similarity`-branch guard `judge_client is not None and diff is not None` (`scorer.py:624`). The intent is invisible in the fixture files — `commit_messages` fixtures say `type: similarity`, identical to the fuzzy-matched fixtures in four other benchmarks that do NOT get a judge. Adding a second judge-scored benchmark today requires touching config, runner wiring, and possibly the scorer, and the `diff is not None` coupling means any benchmark whose `get_diff()` returns content would silently engage commit-message judging on its similarity fixtures.

## What Changes

- Add an explicit `llm_judge` scoring type to the `Scorer`; the judge fires if and only if a fixture declares `scoring.type: llm_judge`
- Migrate the 12 `commit_messages` fixtures from `scoring.type: similarity` to `scoring.type: llm_judge` (thresholds preserved)
- Derive judge-required benchmarks by scanning loaded fixtures for `llm_judge` scoring instead of the hardcoded `JUDGE_REQUIRED_BENCHMARKS` set; CLI preflight validation ("judge profile required") keeps working unchanged
- Runner constructs one judge-aware `Scorer` when a judge is configured, removing the per-benchmark `benchmark._scorer = Scorer(judge_client=...)` injection
- The `similarity` scoring branch reverts to pure SequenceMatcher — no judge code path remains in it
- Fallback semantics preserved exactly: when all judge models fail, score via SequenceMatcher and set `error: judge_failed: ...`
- Register `llm_judge` in `structured_output.py`'s `SCORING_TYPE_TEMPLATES` (commit-message template) so `json_schema` output mode keeps working

## Capabilities

### Modified Capabilities

- `llm-judge-scoring`: judge gating moves from benchmark allowlist + diff-presence heuristic to an explicit per-fixture scoring type; scorer/runner/CLI wiring simplified accordingly

## Impact

- `gitbench/harness/scorer.py` — new `llm_judge` branch; `similarity` branch loses judge logic
- `gitbench/harness/runner.py` — drop `_judge_benchmarks` set and per-benchmark scorer swap
- `gitbench/config.py` — remove `JUDGE_REQUIRED_BENCHMARKS`; add fixture-driven discovery helper
- `gitbench/cli.py` — preflight validation reads discovered judge benchmarks
- `fixtures/commit_messages/*.yaml` — `type: similarity` → `type: llm_judge`
- `gitbench/structured_output.py` — `llm_judge` template mapping (existing `commit_messages` benchmark override already covers it; mapping added for completeness)
- Tests: `tests/test_scorer.py`, `tests/test_judge.py`, `tests/test_cli.py`, `tests/test_integration.py`
- No score-value changes for commit_messages — same judge, same prompt, same fallback; only the routing is explicit

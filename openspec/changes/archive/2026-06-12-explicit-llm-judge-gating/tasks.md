## 1. Scorer

- [x] 1.1 Add an `llm_judge` branch to `Scorer.score()` in `gitbench/harness/scorer.py`: call `self._judge_client.evaluate_commit_message(diff or "", model_output, prompt=prompt or fixture.prompt)`, apply threshold, preserve the SequenceMatcher fallback with `error: judge_failed: ...` when the judge raises
- [x] 1.2 Make the `llm_judge` branch return a scoring error (`Scoring error: llm_judge requires a judge client`) when `self._judge_client` is None
- [x] 1.3 Remove all judge logic from the `similarity` branch — pure SequenceMatcher again

## 2. Discovery and wiring

- [x] 2.1 Replace `JUDGE_REQUIRED_BENCHMARKS` in `gitbench/config.py` with a `discover_judge_benchmarks(benchmarks: list[str]) -> set[str]` helper that loads each benchmark's fixtures and returns those containing any `scoring.type: llm_judge` fixture
- [x] 2.2 Update CLI preflight in `gitbench/cli.py` to use the discovery helper; keep the all-mock-models exemption and the existing error message
- [x] 2.3 Simplify `gitbench/harness/runner.py`: drop `_judge_benchmarks` and the per-benchmark `benchmark._scorer = Scorer(judge_client=...)` swap; construct one judge-aware `Scorer` at init when a judge is configured and use it everywhere

## 3. Fixtures and structured output

- [x] 3.1 Migrate `fixtures/commit_messages/` f001–f012 from `scoring.type: similarity` to `scoring.type: llm_judge`, keeping thresholds
- [x] 3.2 Add `"llm_judge": (commit_message_template, "commit", "string")` to `SCORING_TYPE_TEMPLATES` in `gitbench/structured_output.py`
- [x] 3.3 Check `fixture_self_check.py`, `fixture_audit.py`, and `fixture_structured_validator.py` for similarity-type assumptions that should also recognize `llm_judge`

## 4. Tests

- [x] 4.1 Scorer tests: `llm_judge` type routes to judge; judge failure falls back to SequenceMatcher with `judge_failed` error; missing judge client yields a scoring error; `similarity` type never calls the judge even when one is configured
- [x] 4.2 Discovery tests: benchmark with llm_judge fixtures is detected; benchmark without is not; CLI preflight errors when a judge benchmark is requested without a judge profile (and not when models are all mock)
- [x] 4.3 Update existing judge tests in `tests/test_judge.py` / `tests/test_cli.py` / `tests/test_integration.py` that reference `JUDGE_REQUIRED_BENCHMARKS` or rely on similarity-type judge routing
- [x] 4.4 Integration: mock-judge run of `commit_messages` in both output modes produces scores identical in shape to before (similarity field, threshold pass/fail, fallback error format)

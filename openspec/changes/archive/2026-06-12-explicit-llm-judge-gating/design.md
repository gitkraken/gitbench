## Context

The judge pipeline works (ensemble averaging, retries, SequenceMatcher fallback — see the `llm-judge-scoring` spec), but its gating is implicit. Three conditions must align for a judge call: the benchmark name is in `JUDGE_REQUIRED_BENCHMARKS` (config.py), the runner swapped in a judge-aware scorer for that benchmark (runner.py:140-141), and the fixture's scoring type is `similarity` with a non-None `diff` argument (scorer.py:624). Meanwhile `cherry_pick`, `merge_conflicts`, `rebase`, and `git_grep` fixtures also declare `type: similarity` and rely on never being given a judge — fragile, and unreadable from the fixture file alone.

The sibling change `migrate-conflict-fixtures-to-exact-match` moves those other similarity users to deterministic scoring. After both changes land, `similarity` remains only as the generic fuzzy fallback and `llm_judge` is the sole judge entry point.

## Goals / Non-Goals

**Goals:**
- A fixture's scoring behavior is fully determined by its own `scoring.type`
- Adding a future judge-scored benchmark requires only writing fixtures with `type: llm_judge`
- Preserve all existing judge behavior: ensemble averaging, per-client retries, fallback-to-SequenceMatcher with `judge_failed` error, threshold semantics, CLI preflight error when no judge profile is configured
- commit_messages scores are unchanged before/after (same judge prompt, same routing outcome)

**Non-Goals:**
- Generalizing the judge prompt beyond commit messages (`evaluate_commit_message` and `JUDGE_COMMIT_MESSAGE_PROMPT` stay as-is; per-fixture judge prompts are a future change layered on this one)
- Extending judge scoring to any new benchmark
- Changing judge profile configuration (`judge.profile` in gitbench.json) or ensemble/retry behavior

## Decisions

### Decision 1: New scoring type, not a fixture-level boolean flag

**Chosen**: `scoring.type: llm_judge` as a first-class scoring type with its own `Scorer.score()` branch.

**Rationale**: Scoring type is already the single dispatch axis in `Scorer.score()` and in `structured_output.py` template derivation. A separate `use_judge: true` flag on similarity fixtures would create a second axis and keep the similarity branch polluted with judge logic.

**Alternatives considered**:
- `scoring.judge: true` modifier on `similarity` → two dispatch axes, similarity branch stays complex
- Keep benchmark allowlist but make it config-file-driven → still invisible at the fixture level, still a parallel source of truth

### Decision 2: Derive judge-required benchmarks from fixtures

**Chosen**: Replace the `JUDGE_REQUIRED_BENCHMARKS` constant with a helper that loads fixture scoring types per benchmark (via `FixtureLoader`) and reports which requested benchmarks contain any `llm_judge` fixture. CLI preflight uses this for its "judge profile required" error; the mock-models exemption stays.

**Rationale**: One source of truth. The constant can silently drift from fixture reality; deriving it cannot. Fixture loading is already cheap and happens at CLI startup for other validation.

**Alternatives considered**:
- Keep the constant, assert it matches fixtures at startup → two sources of truth plus a checker; more code than deriving
- Drop preflight validation and fail at scoring time → wastes a full benchmark run before surfacing a config error; fallback would silently produce SequenceMatcher scores

### Decision 3: One judge-aware Scorer, dispatch by type

**Chosen**: Runner builds a single `Scorer(judge_client=...)` when a judge is configured and uses it for all benchmarks; the `llm_judge` branch raises a scoring error if reached without a judge client (CLI preflight makes this unreachable in real runs; mock runs keep their existing exemption path).

**Rationale**: The per-benchmark `benchmark._scorer = Scorer(judge_client=...)` swap exists only because gating lived at the benchmark level. With gating in the scoring type, the swap — and reaching into a private attribute from the runner — disappears.

### Decision 4: `llm_judge` branch keeps the diff/prompt plumbing

**Chosen**: The branch calls `judge_client.evaluate_commit_message(diff, model_output, prompt=prompt or fixture.prompt)` with the same arguments the similarity branch passes today; `diff=None` is passed as an empty string rather than being a gate.

**Rationale**: The diff is judge *input*, not a routing condition. Conflating "we have a diff" with "use the judge" was the original coupling this change removes.

## Risks / Trade-offs

- **Risk**: Fixture-driven discovery adds a fixture load at CLI preflight → **Mitigation**: fixtures are small YAML files already parsed during runs; cache the loaded set so the runner reuses it
- **Risk**: External fixture sets (forks, custom suites) using `type: similarity` for commit_messages would silently lose judge scoring → **Mitigation**: the in-repo fixtures migrate in this change; release notes flag the rename, and an unknown-type error catches typos like `llm-judge`
- **Risk**: `structured_output.py` falls back to a warning + no contract for unknown scoring types; missing the `llm_judge` mapping would degrade `json_schema` mode → **Mitigation**: explicit task adds the `SCORING_TYPE_TEMPLATES` entry; the `commit_messages` entry in `BENCHMARK_TEMPLATE_OVERRIDES` already provides a second layer of coverage
- **Risk**: Doctor/rerun paths that reconstruct scorers might bypass the new branch → **Mitigation**: doctor reruns flow through the same runner scoring path; integration test covers a doctored judge fixture

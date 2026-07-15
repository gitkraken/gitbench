## Context

The Benchmarks index (`web/src/pages/benchmarks/index.astro`) currently computes card content inline. Each card links to a benchmark detail page, shows the benchmark name, a `Best: <percent>%` badge, and a fixture count. The page has access to the full static report artifact through `loadDataSync()`, including `models`, `matrix`, and fixture-level results.

JSON-schema runs that do not support structured output can appear in the report as real benchmark cells with `pass_at_k: 0`, `total: 12`, and fixture-level `structured_error` values. These are different from valid JSON-schema attempts that parse successfully but still score 0%.

## Goals / Non-Goals

**Goals:**

- Replace fixture count on Benchmarks index cards with best, worst, and average eligible model scores.
- Show the model label for unique best or worst scores.
- Show a distinct model count instead of a model label when best or worst scores are tied.
- Exclude only strict unsupported JSON-schema zero-score cells from card calculations.
- Derive one score per provider/base-model identity from the percentage of benchmark fixtures passed across its eligible effort levels and output modes, not from benchmark matrix `pass_at_k`.
- Keep the calculation deterministic and testable.

**Non-Goals:**

- Change Benchmark Detail page charts, selectors, or per-fixture comparison behavior.
- Change report artifact generation, database schema, or APIs.
- Hide valid 0% JSON-schema results that parsed and were scored normally.
- Add user-configurable filtering to the Benchmarks index.

## Decisions

### Compute card summaries in a helper

Create a small report-summary helper rather than keeping the logic inline in the Astro template. The helper should accept `GitBenchData` and a benchmark name, then return:

- eligible score count
- best score and either a single model label or tied-model count
- worst score and either a single model label or tied-model count
- average eligible model score

Rationale: the strict exclusion rule is easy to regress if embedded in presentation markup. A helper can be covered with focused unit tests using small synthetic report artifacts.

Alternative considered: keep all logic inside `benchmarks/index.astro`. This is less code up front but makes the unsupported-JSON distinction hard to test.

### Derive model benchmark scores from fixture outcomes

Each provider/base-model identity should receive one benchmark score. First discard any strictly unsupported JSON-schema variant. Then combine the remaining fixture results from all effort levels and output modes for that base model, group them by `fixture_id`, compute each fixture's pass rate across those attempts, and average the fixture pass rates. A single 100% effort variant therefore cannot make the base model 100% when its other effort variants fail fixtures.

Rationale: benchmark cards should describe how much of the benchmark a model solved. Matrix `pass_at_k` can encode pass-at-k semantics that are too generous, while ranking effort variants independently over-represents models with more configured variants.

### Define unsupported JSON exclusion from fixture evidence

Exclude a model/output-mode benchmark score only when all of these are true:

- the model entry is JSON-schema mode
- the fixture-derived benchmark score is exactly `0`
- every fixture result for that model and benchmark has a non-empty `structured_error`

Rationale: this matches the observed unsupported structured-output pattern without dropping valid JSON-schema attempts that scored 0% after successful parsing/scoring.

Alternative considered: exclude every JSON-schema cell with `pass_at_k === 0`. That would hide legitimate worst performers and inflate average scores.

### Keep model labels user-facing

Card labels should avoid storage-only suffixes such as `__json_schema`. If a JSON-schema variant is the unique best or worst, the label should identify the same model/effort in a user-facing way and may include a compact output-mode marker such as `JSON` if needed to disambiguate from text mode.

Rationale: other report pages treat `__json_schema` as storage detail, not visible model identity.

Alternative considered: render raw matrix keys directly. That is simpler but leaks implementation details into the card UI.

### Aggregate by provider/base-model identity before ranking

Multiple effort levels and output-mode variants for the same provider/base-model should be aggregated into one score before best, worst, ties, or average are calculated. For example, `openai/gpt-a:low` and `openai/gpt-a:high` contribute fixture attempts to one `openai/gpt-a` score.

Rationale: the card label says `models`; treating effort-level cells as separate scores inflates ties and weights the overall average toward models with more configured efforts.

### Average over eligible fixture-derived model scores

Average score should be the arithmetic mean of eligible base-model scores, displayed as a one-decimal percentage. Missing fixture results and strict unsupported JSON variants should not contribute to a model score or the model-level denominator.

Rationale: the card is summarizing model performance spread for the benchmark, not fixture count or trial count.

### Place average beside the benchmark title

The average score badge should appear inline beside the benchmark title. Best and worst badges should remain grouped in a separate statistics row below the title.

Rationale: the average is the quickest benchmark-level difficulty signal, while best and worst describe the model-performance range and read naturally as a pair.

## Risks / Trade-offs

- Strict unsupported detection depends on fixture-level `structured_error` presence → Mitigation: write tests covering unsupported JSON, valid 0% JSON, text 0%, and missing-cell cases.
- Cards may become visually dense with long model names → Mitigation: use compact typography/truncation/title text and tied-count fallback when many models share a score.
- Best scores often tie across many models → Mitigation: count display is intentional and avoids arbitrary winner selection.
- If every cell for a benchmark is excluded or missing, summary values may be unavailable → Mitigation: render a clear empty state such as `No eligible scores` rather than showing misleading `0%`.

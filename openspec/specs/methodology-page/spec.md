## Purpose

The methodology page provides a static explanation of GitBench's benchmarking approach, metrics, and methodology for site visitors.
## Requirements
### Requirement: Methodology page exists at /methodology
The site SHALL have a route at `/methodology` that renders a static content page explaining how GitBench works. The page SHALL use the standard `Layout` component with title "Methodology". The content SHALL be hardcoded prose in the Astro template — no data loading or React islands needed.

#### Scenario: Methodology page is accessible
- **WHEN** navigating to `/methodology`
- **THEN** a page with the sidebar, header "Methodology", and explanatory content is rendered

#### Scenario: Methodology page is linked from sidebar
- **WHEN** viewing any page
- **THEN** the sidebar contains a "Methodology" link

### Requirement: Methodology explains benchmark design
The Methodology page SHALL explain: what a benchmark fixture is (prompt → model → output → score), how fixtures are designed (YAML files with setup, prompt, expected, scoring config), and the current benchmark categories (the ~17 git task domains).

#### Scenario: Benchmark design section is present
- **WHEN** viewing the Methodology page
- **THEN** there is a section describing how fixtures and benchmarks work

### Requirement: Methodology explains similarity scoring
The Methodology page SHALL explain how similarity scoring works: the comparison algorithm (e.g., sequence matcher, fuzzy matching), the threshold for pass/fail determination, and what similarity percentages mean in practice (e.g., 100% = exact match, 85% = mostly correct with minor differences).

#### Scenario: Scoring section is present
- **WHEN** viewing the Methodology page
- **THEN** there is a section explaining similarity scoring and pass thresholds

### Requirement: Methodology explains pass@k metric
The Methodology page SHALL explain the `pass_at_k` metric: it is the proportion of fixtures passed, computed as `passed / total` per benchmark and overall. The page SHALL note that `k` represents the number of runs considered (usually 1 for single-run evaluations).

#### Scenario: pass@k section is present
- **WHEN** viewing the Methodology page
- **THEN** there is a section explaining the pass@k metric formula and interpretation

### Requirement: Methodology explains model selection and run metadata
The Methodology page SHALL explain: how models are selected for benchmarking, what `profile`, `git_sha`, and `benchmark_suite_version` mean in run metadata, and that models are called via OpenRouter (or local Ollama).

#### Scenario: Run metadata section is present
- **WHEN** viewing the Methodology page
- **THEN** there is a section explaining run metadata fields

### Requirement: Methodology page supports tooltip triggers
The Methodology page SHALL use the `.has-tooltip` class on key technical terms and section headers that benefit from contextual explanation. Tooltips SHALL provide quick definitions for terms like "SequenceMatcher", "pass@k", "OpenRouter", and "Ollama" without requiring the reader to search elsewhere. The tooltip content SHALL be concise (1-2 sentences per term).

#### Scenario: Technical terms have tooltips
- **WHEN** viewing the Methodology page
- **THEN** key technical terms (e.g., "SequenceMatcher", "OpenRouter", "benchmark suite") have `.has-tooltip` spans with explanatory text

#### Scenario: Tooltips supplement but do not replace existing prose
- **WHEN** reading the Methodology page
- **THEN** the existing detailed explanations remain intact, with tooltips providing quick-reference definitions on hover

### Requirement: Methodology acknowledges limitations
The Methodology page SHALL include a "Limitations" section acknowledging: this only measures output correctness (not speed, UX, or multi-turn reasoning), results vary by run, similarity scoring is an approximation of correctness, and only open-weight models available through OpenRouter are tested.

#### Scenario: Limitations section is present
- **WHEN** viewing the Methodology page
- **THEN** there is a section listing known limitations of the benchmark

### Requirement: Methodology explains benchmark reliability metrics

The methodology page SHALL explain that model generation can be non-deterministic, describe evaluation runs and complete trial rounds, define mean one-attempt success and `pass_any_at_n`, explain stable-pass/flaky/stable-fail classifications, and state all denominator and exclusion rules. The page MAY define "campaign" as the internal stored identity for repeated evaluation runs, but it SHALL prefer reader-facing terms such as "evaluation run" and "trial round" for the primary explanation.

#### Scenario: Reader interprets mean success

- **WHEN** a reader views a model with 80% mean success over five trials
- **THEN** the methodology SHALL explain that this is the proportion of valid attempts that passed
- **AND** it SHALL not describe it as the probability of passing at least once in five attempts

#### Scenario: Reader interprets excluded failures

- **WHEN** an attempt is absent because of provider, fixture-identity, or judge failure
- **THEN** the methodology SHALL explain that the evaluation run is incomplete
- **AND** the failure is not silently counted as model-quality failure

#### Scenario: Reader views a legacy campaign

- **WHEN** a report contains a one-trial legacy campaign
- **THEN** the methodology SHALL explain that fixture stability cannot be inferred from it
- **AND** it SHALL make clear that "campaign" is the stored evaluation identity, not an end-user selection workflow

### Requirement: Methodology explains remaining sources of variance

The methodology page SHALL describe deterministic fixture inputs, target-provider routing evidence, LLM-judge caching and provenance, structured-output validation, and the limits of reproducibility.

#### Scenario: Reader assesses reproducibility

- **WHEN** a reader reviews the methodology
- **THEN** it SHALL avoid claiming that hosted model evaluations are deterministic
- **AND** it SHALL identify which inputs are fixed and which external factors can still vary

### Requirement: Methodology distinguishes resource normalizations

The methodology page SHALL distinguish mean per-trial cost, tokens, and API time from total evaluation-run consumption and from wall-clock duration. When campaign terminology appears in this section, it SHALL be used only to identify the stored internal evaluation unit behind those totals.

#### Scenario: Reader compares evaluation run costs

- **WHEN** two evaluation runs have different trial counts
- **THEN** the methodology SHALL explain why ranking charts use mean cost per complete trial
- **AND** why total run cost remains operationally relevant


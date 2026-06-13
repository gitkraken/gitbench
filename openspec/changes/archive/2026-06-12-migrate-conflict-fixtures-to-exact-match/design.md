## Context

The `Scorer.score()` `similarity` branch (gitbench/harness/scorer.py) compares model output to `fixture.expected` with `difflib.SequenceMatcher` against a per-fixture threshold. Conflict-resolution fixtures use threshold 0.9, but for short expected values a wrong answer can share >90% of characters with the right one: `SequenceMatcher('Hello, Planet!', 'Hello, Planet!!!') = 0.933`. These fixtures prompt "Provide ONLY the resolved file content" and have exactly one correct resolution, so fuzzy scoring adds noise without tolerance the benchmark actually needs.

Two adjacent systems care about scoring type:
- `gitbench/structured_output.py` derives JSON-schema contracts from scoring type (`SCORING_TYPE_TEMPLATES`) with per-benchmark overrides (`BENCHMARK_TEMPLATE_OVERRIDES`); `merge_conflicts` already overrides to `resolved_content_template` with `file_block` canonicalization
- `gitbench/fixture_self_check.py` requires multi-line `exact_match` fixtures to declare `scoring.order_matters: true`

## Goals / Non-Goals

**Goals:**
- Wrong conflict resolutions never pass; correct resolutions always pass
- Tolerate formatting noise that doesn't change content (wrapping code fence, leading/trailing whitespace)
- Keep prompts, setup, and expected values unchanged — only scoring blocks move
- Keep the `similarity` scorer intact for `commit_messages` (until the judge-gating refactor lands)

**Non-Goals:**
- Extending the LLM judge to these benchmarks (deterministic ground truth doesn't need a judge; see the `explicit-llm-judge-gating` change for judge work)
- Whitespace-insensitive *content* comparison (internal whitespace in a resolved file is part of the answer)
- Re-calibrating difficulty ratings or adding new fixtures
- Migrating `rebase` f002/f003/f009 (already `exact_match`) or `merge_conflicts`/`cherry_pick` f009 (already `exact_match`)

## Decisions

### Decision 1: exact_match, not LLM judge

**Chosen**: Migrate to `exact_match` with normalization rather than extending judge scoring to these benchmarks.

**Rationale**: Every migrated fixture has one correct answer fully determined by the prompt. A judge adds API cost, latency, ensemble calls, and nondeterminism to recover a verdict that string equality gives for free. The judge earns its cost only for open-ended outputs (commit messages).

**Alternatives considered**:
- LLM judge → cost and noise for zero accuracy gain over equality
- Raise similarity threshold to 0.95+ → still gameable for short strings; `'Hello, Planet!'` vs `'Hello, Planet!!!'` is 0.933 and other near-misses can exceed 0.95
- Per-fixture thresholds tuned to the nearest wrong answer → fragile, unverifiable, breaks when fixtures change

### Decision 2: Opt-in `strip_fences` flag, not a global exact_match behavior change

**Chosen**: `scoring.strip_fences: true` on migrated fixtures; the exact_match scorer strips one wrapping triple-backtick fence (optional language tag) plus surrounding whitespace before comparison.

**Rationale**: 40+ existing exact_match fixtures across `blame_forensics`, `branch_cleanup`, `git_show`, etc. expect short command/value answers where silently changing comparison semantics risks unnoticed behavior shifts. Opt-in keeps the change scoped to fixtures that asked for it.

**Alternatives considered**:
- Always strip fences in exact_match → defensible (stripping only makes scoring more lenient to formatting) but changes behavior of every existing fixture in one PR; can be promoted to default later as its own decision
- Normalize in the runner before scoring → would affect every scorer including state assertions; too broad

### Decision 3: git_grep f001 → unordered_line_set

**Chosen**: `unordered_line_set` rather than `exact_match`.

**Rationale**: The prompt says "Output ONLY the filenames, one per line" — a line-set answer. Other git_grep fixtures already use `unordered_line_set`/`exact_match`/`numeric_exact`; this removes the last fuzzy fixture in that benchmark and tolerates line-order differences, which are irrelevant to correctness.

### Decision 4: `order_matters: true` on multi-line fixtures

**Chosen**: Set the flag during migration rather than exempting these fixtures from the self-check.

**Rationale**: `fixture_self_check.py` flags multi-line exact_match fixtures without `order_matters`. For resolved file content, line order genuinely matters, so the flag is accurate, not boilerplate.

## Risks / Trade-offs

- **Risk**: Pass rates drop sharply on these three benchmarks, breaking comparability with previously published results → **Mitigation**: this is the correctness fix working as intended; call it out in release notes/blog draft and avoid mixing pre/post results in one chart
- **Risk**: Models that produce a correct resolution with a trailing comment ("Here is the resolved file: ...") now fail where similarity gave partial credit → **Mitigation**: intentional — the prompts say "ONLY the file content" and reasoning checks already penalize commentary; fence stripping covers the most common benign wrapper
- **Risk**: `json_schema` output mode derives templates from scoring type, and `exact_match` maps to `command_template` (a command answer shape) which is wrong for file content → **Mitigation**: extend `BENCHMARK_TEMPLATE_OVERRIDES` so `cherry_pick` and `rebase` use `resolved_content_template`/`file_block` like `merge_conflicts` already does; covered by an explicit task
- **Risk**: An expected value with a subtle trailing-newline mismatch fails a correct answer → **Mitigation**: exact_match already compares `.strip()`-ed values; multi-line expected values in fixtures end with a single newline which strip handles

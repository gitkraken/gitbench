## Context

`docs/benchmark-fixture-assessment.md` is a useful June 25 snapshot, but it is stale and not authoritative for this change. The current source of truth is the fixture review discussion captured in this change: fix only the agreed prompt/scorer contract issues, avoid broad fixture recalibration, and validate locally.

Current behavior has several mismatch classes:

- `git_log_format/f005` asks for date-range filtering but exact-matches one ordering.
- `submodule_usage/f005` asks the model to commit but asserts an unstated commit message.
- Multi-file conflict fixtures require exact file-heading punctuation even when the resolved file contents are correct.
- `f012` conflict fixtures describe two files but currently ask for and score only `app.py`.
- Command benchmarks execute or compare fenced command answers literally.
- `commit_squash` allows hash-or-message answers even though deterministic commit subject lines are clearer and easier to audit.
- Fixture self-checks reason from raw YAML scoring fields, while some benchmarks use effective scorer behavior that differs from those fields.

## Goals / Non-Goals

**Goals:**
- Align prompt text, expected values, and scorer behavior for the agreed fixture set.
- Add a `resolved_file_blocks` scorer for explicit file-to-content answers.
- Keep the new scorer opt-in and migrate only known multi-file conflict fixtures in this change.
- Normalize strict whole-answer command fences for command answers without extracting commands from prose.
- Standardize `commit_squash` around commit subject lines.
- Make self-checks scorer-aware through shared scoring capability metadata.
- Keep validation to local tests.

**Non-Goals:**
- Running or publishing a new campaign.
- Rewriting `docs/benchmark-fixture-assessment.md`.
- Migrating single-file conflict fixtures to `resolved_file_blocks`.
- Making `benchmark_name` required for self-check callers.
- Changing `git_bisect` or `reflog` dynamic hash/selector behavior.
- Loosening conflict content correctness into semantic or LLM-judge scoring.

## Decisions

### Decision 1: Use `unordered_line_set` for `git_log_format/f005`

The fixture tests date-range filtering, not ordering. The expected answer should accept February and March commit subjects in either order and reject missing or extra subjects.

Alternative considered: change expected to default `git log` newest-first order and state that order in the prompt. Rejected because it broadens the skill under test.

### Decision 2: Score `submodule_usage/f005` by committed repository state

The fixture should verify that the submodule exists, `.gitmodules` exists in the committed state, and the final state reflects committed submodule changes. It should not require `Add lib submodule` or exactly one commit.

The implementation should prefer tree/state assertions over commit-message assertions. If existing state assertions cannot express the needed checks cleanly, extend assertion types rather than using another message proxy.

### Decision 3: Introduce `resolved_file_blocks`

`resolved_file_blocks` uses explicit `scoring.expected_files` as the correctness oracle. `fixture.expected` remains a human/display/backcompat string.

The scorer:
- Parses model output into file blocks keyed by filename.
- Ignores file order.
- Rejects missing files.
- Rejects extra files by default.
- Allows extra files only when `allow_extra_files: true`.
- Accepts bounded filename headings: optional markdown heading markers, optional `---`, optional backticks, filename, optional colon.
- Accepts one wrapping fence around each file content.
- Normalizes line endings, trailing whitespace, and final newline differences.
- Preserves indentation and interior blank lines.
- Fails closed when `expected_files` is missing or malformed.

This scorer supports single-file answers, but this change migrates only multi-file fixtures.

### Decision 4: Keep exact single-file conflict scoring for now

Ambiguous single-file `f005` conflict prompts should be clarified now because “most useful changes” does not define a deterministic oracle. Their scorer migration is deferred to `migrate-single-file-conflict-scoring`.

### Decision 5: Ask for and score both files in `f012`

The `f012` fixtures should request both `app.py` and `requirements.txt` with filename-prefixed blocks. Scoring only `app.py` contradicts the fixture purpose and hides dependency-aware resolution behavior.

### Decision 6: Strict command fence normalization is shared

A shared helper should normalize model command answers for both stateful command execution and `command_equivalence`.

Accepted forms:
- Plain command text, one command per line.
- One whole-answer fenced code block containing only commands.

Rejected forms:
- Prose before or after a fenced block.
- Extracting commands from explanatory paragraphs.
- Per-command fenced blocks in this change.

### Decision 7: Standardize `commit_squash` on subject lines

All `commit_squash` prompts should ask for selected commit subject lines, one per line. Fixture expected values should migrate from comma-separated subjects to newline-separated subjects. The scorer can tolerate bullets and legacy comma-separated model output, but hash-only answers should fail when the prompt requests subject lines.

### Decision 8: Add effective scoring capability metadata

Fixture self-checks should consume shared scoring capability metadata instead of relying on raw `scoring.type` alone. Capability lookup should use `(benchmark_name, scoring.type)` first, then fall back to `scoring.type`. `benchmark_name` remains optional in this change for compatibility.

The metadata should describe effective behavior such as order sensitivity, dynamic expected values, stable lookup keys, and selection parsing. It should not become a pile of self-check-only benchmark exceptions.

## Risks / Trade-offs

- Newly passing historical `f010` outputs may include semantically wrong content if parsing is too permissive -> keep parsing bounded and compare file contents strictly.
- Command fence normalization can hide instruction drift if it extracts commands from prose -> accept only whole-answer fences and pure command text.
- `commit_selection` hash rejection can reduce pass rates -> this is intended after the prompt contract is deterministic; local tests should update the previous hash-only pass test.
- Self-check capability metadata can drift from actual scorer behavior -> co-locate tests with scorer behavior and add capability tests for known benchmark-local cases.
- Suite results become incomparable with previous campaigns -> campaign reruns are out of scope and will be handled separately after implementation.

## Migration Plan

1. Add scorer and normalizer behavior with tests.
2. Update only the agreed fixtures.
3. Add scoring capability metadata and self-check tests.
4. Run local tests for scorer, benchmarks, structured output, fixture self-checks, and affected expected-answer paths.
5. Leave campaign reruns and assessment regeneration to a later/manual step.

## Open Questions

- Exact state assertion shape for “submodule was committed” should be selected during implementation based on the existing assertion API.
- The structured-output schema shape for multi-file resolved content should use the smallest schema that preserves filename-to-content structure.

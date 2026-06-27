## Context

The scoring-contract cleanup adds `resolved_file_blocks` but intentionally migrates only multi-file fixtures. Single-file conflict fixtures are calibration-sensitive: a parser or prompt tweak may create newly passing or failing outputs that look plausible but alter benchmark meaning.

## Goals / Non-Goals

**Goals:**
- Decide from evidence whether single-file conflict fixtures should migrate to file-aware scoring.
- Replay stored attempts before and after candidate migrations.
- Manually inspect changed outcomes before accepting migrations.
- Keep only migrations with clear correctness evidence.

**Non-Goals:**
- Adding new conflict fixtures.
- Running a full external campaign.
- Using an LLM judge for deterministic conflict fixtures.
- Changing multi-file conflict behavior already covered by `align-fixture-scoring-contracts`.

## Decisions

### Decision 1: Evidence before migration

Each candidate single-file fixture must have expected-answer self-checks and before/after stored-attempt replay before migration. Newly passing outputs require manual semantic inspection.

### Decision 2: Use the existing file-block scorer where it fits

If a single-file answer has a clear filename and resolved content contract, prefer `resolved_file_blocks` over inventing a second parser. If no filename is requested, either keep exact scoring or update the prompt explicitly before migration.

### Decision 3: Treat changed outcomes as calibration decisions

The output of this proposal is not just code changes; it is a documented decision for each migrated or non-migrated fixture.

## Risks / Trade-offs

- Parser tolerance could convert wrong answers into passes -> manually inspect all newly passing stored attempts.
- Prompt changes could make results less comparable -> document affected fixtures and require suite version handling in implementation.
- Replay tooling may expose legacy result-shape inconsistencies -> keep replay local and use representative stored attempts if full coverage is not practical.

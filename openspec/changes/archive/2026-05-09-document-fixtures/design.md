## Context

GitBench fixtures are YAML files with fields: `id`, `description`, `setup`, `prompt`, `expected`, `scoring`. The `description` field is a short one-liner. When benchmark results are consumed — by researchers, maintainers, or automated analysis — there's no way to understand what a fixture is actually testing or why a model might have struggled with it. The existing `description` is too terse for this purpose.

The fixture pipeline is: YAML file → `FixtureLoader` → `Fixture` dataclass → benchmark runs → `Score` → `BenchmarkResult` → JSON output.

The project has 17 benchmark categories with 12 fixtures each = 204 fixtures.

## Goals / Non-Goals

**Goals:**
- Add optional `purpose`, `difficulty`, and `tags` fields to fixture YAML
- Parse them in the loader and store in the `Fixture` dataclass
- Include them in JSON results output so consumers can interpret scores
- Backfill all 204 existing fixtures with meaningful metadata
- Update CONTRIBUTING.md with authoring guidance

**Non-Goals:**
- Changing scoring, prompts, expected answers, or benchmark behavior
- Changing the CLI or HTML report
- Adding metadata to the model prompt (models don't see this)
- Requiring these fields — they are optional, fixtures without them load fine
- Translating metadata to other languages

## Decisions

### Field names and types

| Field | Type | Purpose |
|-------|------|---------|
| `purpose` | `str` | 1-3 sentences explaining what Git skill this tests and why it matters |
| `difficulty` | `str` (enum) | One of: `trivial`, `easy`, `medium`, `hard`, `expert` |
| `tags` | `list[str]` | Searchable keywords (e.g., `["conflict-resolution", "rebase", "three-way-merge"]`) |

**Rationale:** `purpose` is freeform prose for human readers; `difficulty` is a controlled vocabulary so results can be stratified by difficulty; `tags` enables filtering and grouping across benchmarks. All three are optional to maintain backward compatibility.

**Alternative considered:** A single rich `description` field with structured sub-fields. Rejected because it would require parsing and break the existing `description` contract for anyone already reading it.

### Where metadata appears in output

Metadata is added to the `Score` object (or a parallel structure) in the JSON results. It is *not* added to the HTML report in this change (separate follow-up).

**Rationale:** JSON output is the primary programmatic interface. Adding to HTML requires template changes and is a separate concern.

**Alternative considered:** Embedding metadata in the `BenchmarkResult` at the benchmark level. Rejected because metadata is fixture-level, not benchmark-level — two fixtures in the same benchmark can have different purposes and difficulties.

### Backfill strategy

Backfill all 204 fixtures in one pass by categorizing:
- `trivial`: Single command, no conflicts or edge cases
- `easy`: Simple multi-step, straightforward
- `medium`: Requires understanding of Git concepts or multi-branch workflows
- `hard`: Complex scenarios, conflict resolution, edge cases
- `expert`: Rare Git operations, subtle behavior, or multi-repo scenarios

**Rationale:** A single author doing all backfills ensures consistency. Letting contributors backfill piecemeal would create uneven quality.

### Validation approach

The loader emits a `logging.warning()` when a fixture is missing any of the new metadata fields. This is informational, not a hard error — fixtures load fine without it.

**Rationale:** Soft validation encourages authors to include metadata without breaking existing fixtures or requiring immediate migration.

## Risks / Trade-offs

- **Risk:** Inconsistent difficulty ratings across benchmarks → **Mitigation:** Single author backfills with consistent rubric; difficulty documented in CONTRIBUTING.md
- **Risk:** Field proliferation — adding 3 fields now, more later → **Mitigation:** `tags` is extensible without schema changes; difficulty is a fixed enum
- **Risk:** JSON output size increase → **Mitigation:** Metadata is small (~200 bytes per fixture). For 204 fixtures that's ~40KB additional. Acceptable.
- **Trade-off:** Making purpose/difficulty subjective. What's "medium" to one person may be "easy" to another. Acceptable — the goal is relative ordering, not absolute calibration.

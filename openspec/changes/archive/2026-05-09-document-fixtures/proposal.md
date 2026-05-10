## Why

Fixture descriptions are currently one-liners like "Single file added" or "Create a lightweight tag on HEAD." Consumers of benchmark results — researchers comparing models, maintainers triaging failures, users interpreting scores — have no way to understand *what skill a fixture is probing*, *why it was included*, or *what its difficulty level is*. Without this context, a pass/fail on a fixture is just a data point with no meaning. This change adds structured metadata to every fixture so results are self-describing and actionable.

## What Changes

- Add three new optional fields to each fixture YAML: `purpose`, `difficulty`, and `tags`
- Update the `Fixture` dataclass and loader to support these new fields
- Backfill descriptive metadata (purpose, difficulty, tags) into all ~204 existing fixtures across all 17 benchmark categories
- Include fixture metadata in JSON results output so consumers see it alongside scores
- Add validation to the loader so new fixtures prompt authors to include the fields
- Update CONTRIBUTING.md with guidance on writing good fixture metadata

## Capabilities

### New Capabilities

- `fixture-metadata`: Rich descriptive metadata for benchmark fixtures including purpose (what skill is tested and why it matters), difficulty level, and searchable tags. This metadata flows through the load → score → result pipeline so consumers can filter, group, and interpret results.

### Modified Capabilities

<!-- None — this is purely additive metadata. Existing scoring, loading, and benchmark behavior is unchanged. -->

## Impact

- **Fixture YAML files** (`fixtures/*/f*.yaml`): All ~204 files gain new fields (`purpose`, `difficulty`, `tags`)
- **`gitbench/harness/types.py`**: `Fixture` dataclass gains three new optional fields
- **`gitbench/harness/loader.py`**: `FixtureLoader` parses new fields, with soft validation warnings
- **JSON results output**: Score objects optionally include fixture metadata for consumer context
- **`CONTRIBUTING.md`**: New section on writing fixture metadata
- **Backward compatibility**: All new fields are optional — old fixtures load without changes, old result consumers ignore unknown fields

# GitBench

A benchmark suite for evaluating language models' Git competency. GitBench runs synthetic Git scenarios against models and scores their responses against known-good solutions.

## Requirements

- Python 3.10+
- Git CLI installed and available in `PATH`

## Installation

```bash
pip install -e .
```

Or with a dedicated virtual environment:

```bash
# Create the virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate

# Install the package in editable mode
pip install -e .
```

## Quick Start

```bash
# List available benchmarks
gitbench list

# Run all benchmarks with the mock model (no API key needed)
gitbench run --all --model mock

# Run with a real model
gitbench run --all --model gpt-4o

# Run with a reasoning level
gitbench run --all --model o3-mini#high

# Run with Ollama locally
gitbench run --all --model llama3.1:8b --provider ollama
```

## Configuration

Model profiles can be defined in `gitbench.json` (searched in `./gitbench.json`, `./.gitbench.json`, `~/.gitbench.json`):

```json
{
  "models": {
    "openai-gpt4o": {
      "models": ["gpt-4o", "gpt-4o-mini"],
      "provider": "openai",
      "api_key_env": "OPENAI_API_KEY"
    },
    "ollama-local": {
      "models": ["llama3.1:8b", "qwen2.5-coder:7b"],
      "provider": "ollama",
      "base_url": "http://localhost:11434"
    }
  },
  "outputs": {
    "json": "runs/latest.json"
  }
}
```

Store API keys in a local `.env` file or in your shell environment, then reference
the variable name from each profile with `api_key_env`. GitBench loads `.env`
without overriding variables already exported by your shell.

```dotenv
OPENAI_API_KEY=
OPENROUTER_API_KEY=
```

Do not put literal API keys in `gitbench.json`; persisted `api_key` fields are
rejected so secrets stay out of configuration files.

Then run with profiles:

```bash
gitbench run --all --profile openai-gpt4o
gitbench run --all --all-profiles              # all profiles sequentially
gitbench run --all --all-models                # flattened, can run concurrently
```

List configured profiles:

```bash
gitbench profiles
```

### Result safety configuration

Result safety is optional. To enable it, reference a model profile containing
exactly one model:

```json
{
  "models": {
    "openrouter-result-safety": {
      "model": "openai/gpt-5.4-mini:none",
      "base_url": "https://openrouter.ai/api/v1",
      "api_key_env": "OPENROUTER_API_KEY"
    }
  },
  "result_safety": {
    "profile": "openrouter-result-safety"
  }
}
```

The selected provider receives stored model-generated fields and retained
diagnostic strings, not explicit fixture prompts or expected answers. GitBench
reviews each score before normal serialization, fails closed on reviewer or
response errors, and writes only a fixed application-owned redaction marker to
public artifacts. A configured profile with zero or multiple models is
rejected.

The repository config includes `openrouter-result-safety-example` as a
single-model example but does not enable `result_safety`; select and verify the
reviewer model before adding the section.

## Running Benchmarks

### Full CLI reference

```
gitbench run [OPTIONS]
```

Key options:

| Option | Description |
| ------ | ----------- |
| `--all`, `-a` | Run all benchmarks against all models (shortcut) |
| `--all-benchmarks` | Run all available benchmarks |
| `--benchmark`, `-b` | Run a specific benchmark by name |
| `--model`, `-m` | Model to use. `mock` for testing, Ollama model names, or OpenAI-compatible model IDs |
| `--profile`, `-p` | Model profile from gitbench.json |
| `--all-profiles` | Run against all profiles defined in config |
| `--all-models` | Run against all models across all profiles (flattened) |
| `--provider` | Explicit provider type: `ollama` or `openai` (auto-detected from base_url if omitted) |
| `--base-url` | API base URL. Defaults to `http://localhost:11434` for Ollama |
| `--verbose`, `-v` | Print detailed per-fixture results |
| `--timeout`, `-t` | Timeout in seconds per model attempt |
| `--retry-count`, `-r` | Retry attempts on failure (default: 3) |
| `--model-workers` | Number of models to run concurrently (default: 1) |
| `--fixture-workers` | Number of fixtures to run concurrently within a benchmark (default: 1) |
| `--judge` | Enable LLM judge scoring (overrides config benchmarks list) |
| `--judge-profile` | Override the judge model profile from config |

### Output options

| Option | Description |
| ------ | ----------- |
| `--json-output` | Single JSON file for results (default: `gitbench-results/{timestamp}/results-v{version}.json`) |
| `--output-dir`, `-d` | Write per-run auto-named JSON files to a directory |
| `--jsonl`, `-j` | Append run results as a JSON line to a file (useful for accumulating runs) |
| `--export`, `-e` | Export format(s): `csv`, `json`, `artificialanalysis` (repeatable) |
| `--export-path` | Path for export file (auto-named from model + timestamp if omitted) |

### Examples

```bash
# Run a specific benchmark with verbose output
gitbench run --benchmark commit_messages --model mock --verbose

# Run all benchmarks with Ollama, 4 concurrent fixtures
gitbench run --all --model llama3.1:8b --provider ollama --fixture-workers 4

# Run with profile, export results
gitbench run --all --profile openai-gpt4o --export csv --export artificialanalysis

# Accumulate runs in a JSONL file
gitbench run --all --model gpt-4o --jsonl runs/history.jsonl

# Run two models concurrently
gitbench run --all --all-models --model-workers 2
```

### Model reasoning levels

Models can be suffixed with `#level` or `:level` to control reasoning effort:

```bash
gitbench run --all --model o3-mini#high
gitbench run --all --model gpt-4o#minimal
gitbench run --all --model anthropic/claude-opus-4.7:max
```

Valid levels: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max` (model-dependent).
The harness validates the combination before any calls are made, failing fast on invalid pairings.
A final colon segment is treated as effort only when it matches one of these values, so model IDs
such as `llama3.1:8b` keep their tag as part of the base model name.

### LLM Judge Scoring

GitBench uses a secondary LLM ("judge") to evaluate free-text outputs semantically
rather than relying on character-level similarity. The `commit_messages` benchmark
**requires** a judge — it will not run without one.

**Judge model group** — create a dedicated model profile for your judge models
in `gitbench.json`. These should be cheap, fast models:

```json
{
  "models": {
    "my-judge-models": {
      "models": ["granite-4.1-8b", "ling-2.6-flash"],
      "provider": "openai",
      "base_url": "https://openrouter.ai/api/v1",
      "api_key_env": "OPENROUTER_API_KEY"
    }
  }
}
```

**Configuration** — add a `judge` section referencing the judge model group:

```json
{
  "judge": {
    "profile": "my-judge-models"
  }
}
```

- `profile` (required): Name of a model profile to use as the judge model group.
  **Every model in the profile is called** and their scores are averaged.
  The judge automatically applies to all judge-required benchmarks (`commit_messages`).

**CLI usage**:

```bash
# Judge auto-enabled for commit_messages when config has a judge section
gitbench run --benchmark commit_messages --model gpt-4o

# Explicitly enable/override
gitbench run --benchmark commit_messages --model gpt-4o --judge

# Override the judge profile
gitbench run --benchmark commit_messages --model gpt-4o --judge --judge-profile my-other-judge

# Mock model skips the judge requirement (for testing)
gitbench run --benchmark commit_messages --model mock
```

**How it works**:

1. Every model in the judge profile receives the git diff and the model's generated commit message.
2. Each returns a score between 0.0 and 1.0 rating message quality.
3. The **average** of all successful scores replaces the `SequenceMatcher` similarity score.
4. Each model adapter retries up to 5 times with `Retry-After` backoff on rate limits.
5. Failed models are excluded from the average.
6. If all models fail, the system falls back to `SequenceMatcher`
   and marks the result with a "judge_failed" error.
7. Running `commit_messages` without a `judge` section exits with an error
   (except with `--model mock` for testing).

**Judge prompt criteria**:
- Accuracy: Does the message describe the diff changes?
- Conciseness: Is the message well-structured?
- Convention: Does it follow conventional commit format?
- Intent: Does it capture the change's purpose and scope?

### Request concurrency budgets

`--model-workers` and `--fixture-workers` still control how much work GitBench schedules, but
model API calls are gated by request budgets. Configure a global limit, profile-level limit, or
explicit capacity groups in `gitbench.json`:

```json
{
  "concurrency": {
    "max_concurrent_requests": 4,
    "groups": [
      {
        "key": "openrouter:anthropic/claude-opus",
        "match": ["anthropic/claude-opus-*"],
        "max_concurrent_requests": 1
      }
    ]
  },
  "models": {
    "openrouter": {
      "models": [
        "anthropic/claude-opus-4.7:max",
        "anthropic/claude-opus-4.8:max"
      ],
      "provider": "openai",
      "base_url": "https://openrouter.ai/api/v1",
      "max_concurrent_requests": 2
    }
  }
}
```

OpenRouter profiles infer common upstream capacity groups after stripping effort suffixes:
Anthropic Opus/Sonnet/Haiku families, OpenAI GPT-5 families, and Google Gemini 3 families.
Unknown OpenRouter model IDs fall back to `openrouter:<base-model-id>`. Explicit group matches
run against the base model ID, so `anthropic/claude-opus-4.7:max` matches
`anthropic/claude-opus-*`.

## Result doctoring

Transient failures (rate limits, timeouts, server errors) can be repaired without re-running the entire suite:

```bash
# Preview what would be repaired
gitbench doctor results.json --dry-run

# Repair a single result file
gitbench doctor results.json

# Repair result files in every timestamped directory under gitbench-results/
gitbench doctor --latest

# Use a longer timeout for slow repair reruns
gitbench doctor --latest --timeout 180
```

The `doctor` command identifies failures caused by known transient error patterns (HTTP 429, 500/502/503/504, timeouts, rate limits) and re-runs only those fixtures against the original models.

## Result safety doctoring

When `result_safety.profile` is configured, new runs are reviewed before JSON,
JSONL, CSV, stdout, or aggregate output is written. Historical files can be
reviewed separately:

```bash
# Classify one artifact without changing it
gitbench safety-doctor results.json --dry-run

# Sanitize one artifact
gitbench safety-doctor results.json

# Sweep JSON files in every timestamped directory under gitbench-results/
gitbench safety-doctor --latest --dry-run
gitbench safety-doctor --latest
```

Flagged generated content and non-empty retained `error` or
`structured_error` diagnostics are replaced with
`[Redacted - Reason: Inappropriate NSFW content]`; scoring, token, cost,
timing, and benchmark summaries are preserved. Before an existing file
with redactions is replaced atomically, its complete unsanitized original is
written to the mirrored, collision-safe `gitbench-results-nsfw/` tree.

`gitbench-results-nsfw/` is gitignored but is not encrypted. It can contain
explicit content, so local access control, retention, and deletion are the
operator's responsibility. Clean artifacts do not create backups. A failed
classification or required backup leaves the source artifact unchanged.

## Report generation

After running benchmarks, generate a static report site:

```bash
gitbench report
```

This aggregates results from `gitbench-results/`, generates `web/public/results.json`, builds the Astro site to `web/dist/`, and starts a preview server.

When result safety is configured, report generation validates every raw or
aggregate input before writing report JSON or SQLite data. Missing, stale, or
modified safety metadata is rejected with the artifact path and a direction to
run `gitbench safety-doctor`. Report validation never calls the reviewer model.

```bash
gitbench report --open       # build and open in browser
gitbench report --dev        # start dev server with hot reload
gitbench report --no-build   # only generate results.json (skip build)
gitbench report -d my-results/ --open   # use custom input dir
```

## Export formats

Results can be exported to structured formats for external analysis:

| Format | Description |
| ------ | ----------- |
| `csv` | One row per fixture result (benchmark, fixture_id, model, passed, similarity, error, etc.) |
| `json` | Complete formatted run envelope |
| `artificialanalysis` | One row per benchmark (model, benchmark, score, total, passed) — compatible with artificialanalysis.com |

```bash
gitbench run --all --model gpt-4o --export csv --export artificialanalysis
```

## Result versioning

Saved run envelopes include two version fields:

| Field | Meaning |
| ----- | ------- |
| `schema_version` / `version` | Integer output schema version for result readers |
| `benchmark_suite_version` | `0.x` suite version tied to benchmark and fixture coverage |

During the pre-1.0 period, bump `benchmark_suite_version` whenever fixtures, benchmark definitions, prompts, expected answers, or scoring rules change in a way that affects comparability. Use `0.x` minor bumps for added or behavior-changing benchmark coverage, and patch bumps for corrections that keep the same intended coverage.

Generated default artifact filenames include the benchmark suite version, and report rendering sorts accumulated runs by `benchmark_suite_version` first, then timestamp.

## Benchmarks

GitBench includes 17 benchmark categories:

| Benchmark         | Description                                                            | Fixtures | Scoring       |
| ----------------- | ---------------------------------------------------------------------- | -------- | ------------- |
| `blame_forensics` | Trace which commit introduced a bug using git blame/log                | 12       | exact_match   |
| `branch_cleanup`  | Identify branches to delete (fully merged into main)                   | 12       | exact_match   |
| `cherry_pick`     | Apply specific commits from one branch to another, resolving conflicts | 12       | similarity    |
| `commit_messages` | Given a diff, generate a meaningful commit message                     | 12       | similarity    |
| `commit_squash`   | Squash multiple commits into a single coherent commit                  | 12       | commit_selection |
| `git_bisect`      | Identify the commit that introduced a bug via automated bisect         | 12       | dynamic hash   |
| `git_clean`       | Safely remove untracked files and directories                          | 12       | state_assertions |
| `git_grep`        | Search repository content with git grep                                | 12       | exact_match/similarity/numeric_exact |
| `git_log_format`  | Format git log output for targeted history inspection                  | 12       | exact_match/unordered_line_set/dynamic hash |
| `git_show`        | Inspect commits, tags, and file state with git show                    | 12       | exact_match/dynamic hash |
| `merge_conflicts` | Resolve merge conflicts producing the correct final tree               | 12       | similarity    |
| `rebase`          | Clean up commit history before PR (squash, reorder, amend)             | 12       | similarity    |
| `reflog`          | Restore lost commits or fix detached HEAD state                        | 12       | similarity    |
| `stash_recovery`  | Recover stashed changes or resolve stash pop conflicts                 | 12       | similarity    |
| `submodule_usage` | Manage git submodules for external dependencies                        | 12       | state_assertions |
| `tag_management`  | Create, inspect, move, and delete tags                                 | 12       | state_assertions |
| `worktree_usage`  | Use git worktrees for parallel development                             | 12       | state_assertions |

Each benchmark has 12 fixtures — 204 total — for meaningful pass@1 scoring.

### Scoring Types

| Type | Description |
| ---- | ----------- |
| `similarity` | Text similarity via `difflib.SequenceMatcher`. Default threshold: 0.5 |
| `exact_match` | Exact string comparison after stripping whitespace |
| `unordered_line_set` | Compare newline-delimited answers as a set when order is not part of the task |
| `numeric_exact` | Compare count/integer answers while tolerating whitespace and optional one-number prose |
| `json_semantic_equal` | Compare parsed JSON values so whitespace and property order do not matter |
| `command_equivalence` | Tokenized command comparison against fixture-declared accepted alternatives |
| `state_assertions` | Execute model output as git commands, then verify repo state via assertions (file_exists, dir_exists, file_content, branch_exists, git_config, git_output) |
| `structured` | Parse model output as key-value fields, score each independently (exact_match or similarity per field) |
| `commit_selection` | Verify that the model selects specific expected commits (used by commit_squash) |
| `commit_hash_by_subject` | Derive the full or short commit hash from a stable commit subject in the fixture repo |
| `dynamic_hash` | Match against a git hash that varies per run (used by git_bisect and legacy fixtures) |

Use `command_equivalence` for read-only fixtures that ask for a Git command and
where multiple command spellings are semantically equivalent:

```yaml
scoring:
  type: command_equivalence
  accepted:
    - git submodule
    - git submodule status
```

Multi-command alternatives are supported as ordered command sequences:

```yaml
scoring:
  type: command_equivalence
  accepted:
    - - git submodule init
      - git submodule update
    - - git submodule update --init
```

## Output Format

### Envelope

Every run produces an envelope wrapping benchmark results with metadata:

```json
{
  "version": 1,
  "schema_version": 1,
  "benchmark_suite_version": "0.1.0",
  "timestamp": "2025-01-15T10:30:00+00:00",
  "git_sha": "abc1234",
  "model": "gpt-4o",
  "profile": "openai-gpt4o",
  "summary": {
    "total_benchmarks": 17,
    "total_fixtures": 204,
    "total_passed": 120,
    "overall_pass_at_k": 0.5882
  },
  "results": [ ... ]
}
```

### Single benchmark

When running `--benchmark <name>`, output is a single benchmark result:

```json
{
  "benchmark": "commit_messages",
  "total": 12,
  "passed": 3,
  "pass_at_k": 0.25,
  "scores": [
    {
      "fixture_id": "f001",
      "passed": true,
      "similarity": 0.72,
      "model_output": "Add greeting file",
      "error": null
    }
  ],
  "errors": 0
}
```

### Multi-model / multi-profile output

When running `--all-models` or `--all-profiles`, results are nested:

```json
{
  "benchmark_suite_version": "0.1.0",
  "summary": {
    "total_models": 2,
    "total_fixtures": 408,
    "total_passed": 220,
    "overall_pass_at_k": 0.5392
  },
  "models": [
    { "model": "gpt-4o", "summary": {...}, "results": [...] },
    { "model": "gpt-4o-mini", "summary": {...}, "results": [...] }
  ]
}
```

### All benchmarks combined

When running `--all`, output is a combined JSON with a summary and per-benchmark results:

```json
{
  "summary": {
    "total_benchmarks": 17,
    "total_fixtures": 204,
    "total_passed": 15,
    "overall_pass_at_k": 0.25
  },
  "results": [
    {
      "benchmark": "commit_messages",
      "total": 12,
      "passed": 3,
      "pass_at_k": 0.25,
      "scores": [...],
      "errors": 0
    },
    ...
  ]
}
```

| Field       | Type      | Description                                            |
| ----------- | --------- | ------------------------------------------------------ |
| `benchmark` | `string`  | Benchmark name                                         |
| `total`     | `integer` | Total number of fixtures                               |
| `passed`    | `integer` | Number of fixtures that passed                         |
| `pass_at_k` | `float`   | Fraction of fixtures with at least one passing attempt |
| `scores`    | `list`    | Per-fixture score objects                              |
| `errors`    | `integer` | Number of fixtures that produced an error              |

Each score object contains:

| Field          | Type             | Description                                   |
| -------------- | ---------------- | --------------------------------------------- |
| `fixture_id`   | `string`         | Fixture identifier                            |
| `passed`       | `boolean`        | Whether the model output passed the threshold |
| `similarity`   | `float`          | Text similarity score (0.0 – 1.0)             |
| `model_output` | `string`         | The model's generated output                  |
| `error`        | `string \| null` | Error message if processing failed            |
| `reasoning_level` | `string \| null` | Reasoning level used (e.g. `"high"`)        |
| `model`        | `string`         | Model name (present in multi-model output)    |

## Running Tests

```bash
pytest tests/
```

Run with verbose output:

```bash
pytest tests/ -v
```

Run only integration tests:

```bash
pytest tests/test_integration.py -v
```

Run specific test files:

```bash
pytest tests/test_cli.py -v
pytest tests/test_export.py -v
pytest tests/test_parallel_fixtures.py -v
pytest tests/test_result_doctoring.py -v
pytest tests/test_result_safety.py tests/test_result_safety_cli.py -v
```

## Adding Fixtures and Benchmarks

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full fixture authoring guide and step-by-step instructions for adding new benchmark categories.

**Quick fixture template:**

```yaml
id: "f013"
description: "My scenario"
purpose: "Tests ability to generate a commit message for a new file."
difficulty: easy
tags: [commit-message, add, basic]
setup:
  - "git init"
  - "git config user.email 'test@test.com'"
  - "git config user.name 'Test User'"
  - "echo 'content' > file.txt"
  - "git add file.txt"
prompt: "Your instruction to the model"
expected: "The correct output"
scoring:
  type: "similarity"
  threshold: 0.5
```

**Important gotchas:**

- **YAML colon values:** strings containing colons (e.g. `"Fix: login"`) must be single-quoted to prevent PyYAML from parsing them as mapping keys.
- **Rebase vs merge conflict polarity:** In merge conflicts, HEAD's changes appear above `=======`. In rebase conflicts, the polarity is reversed — upstream's changes appear _below_ `=======`.
- **GitExecutor exit codes:** `git merge` and `git rebase` exit with code 1 on conflicts. `GitExecutor.setup_repo()` handles this automatically — do not call `_run_command()` directly for merge/rebase commands in fixtures.
- **New benchmarks:** Drop a Python module inheriting from `Benchmark` in `gitbench/benchmarks/`. No registration or harness changes needed — auto-discovered via `importlib`.

## Project Structure

```
gitbench/
├── __init__.py
├── cli.py                  # Click-based CLI (run, doctoring, profiles, report)
├── config.py               # Configuration loader (gitbench.json profiles)
├── export.py               # CSV and artificialanalysis format exporters
├── render.py               # Result aggregation and JSON generation for reports
├── result_doctoring.py     # Selective repair of transient failures
├── result_safety.py        # Safety review, redaction, metadata, and backups
├── version.py              # Version constants (schema, suite, package)
├── harness/
│   ├── benchmark.py       # Benchmark abstract base class
│   ├── types.py           # Dataclasses: ModelMessage, Fixture, Score, BenchmarkResult
│   ├── model.py           # ModelInterface, OpenAIAdapter, OllamaAdapter, MockModelClient
│   ├── loader.py          # FixtureLoader: YAML loading and validation
│   ├── runner.py          # BenchmarkRunner: executes benchmarks with progress reporting
│   ├── scorer.py          # Scorer: similarity, command equivalence, state assertions, pass@k
│   └── reasoning.py       # Model reasoning level validation matrix
├── benchmarks/
│   ├── __init__.py        # Auto-discovery import (no registration needed)
│   ├── blame_forensics.py # Blame/forensics benchmark
│   ├── branch_cleanup.py  # Branch cleanup benchmark
│   ├── cherry_pick.py     # Cherry-pick benchmark
│   ├── commit_messages.py # Commit message generation benchmark
│   ├── commit_squash.py   # Commit squash benchmark
│   ├── git_bisect.py      # Git bisect benchmark
│   ├── git_clean.py       # Git clean benchmark
│   ├── git_grep.py        # Git grep benchmark
│   ├── git_log_format.py  # Git log formatting benchmark
│   ├── git_show.py        # Git show benchmark
│   ├── merge_conflicts.py # Merge conflict resolution benchmark
│   ├── rebase.py          # Interactive rebase benchmark
│   ├── reflog.py          # Reflog/detached HEAD recovery benchmark
│   ├── stash_recovery.py  # Stash recovery benchmark
│   ├── submodule_usage.py # Submodule usage benchmark
│   ├── tag_management.py  # Tag management benchmark
│   └── worktree_usage.py  # Worktree usage benchmark
├── ui/
│   ├── __init__.py
│   ├── display.py         # RichProgressDisplay: live TUI with progress bars
│   └── format.py          # Duration, cost, and human-readable formatting
└── utils/
    └── git.py             # GitExecutor: sandboxed git repo management
fixtures/
├── blame_forensics/       # 12 YAML fixtures
├── branch_cleanup/        # 12 YAML fixtures
├── cherry_pick/           # 12 YAML fixtures
├── commit_messages/       # 12 YAML fixtures
├── commit_squash/         # 12 YAML fixtures
├── git_bisect/            # 12 YAML fixtures
├── git_clean/             # 12 YAML fixtures
├── git_grep/              # 12 YAML fixtures
├── git_log_format/        # 12 YAML fixtures
├── git_show/              # 12 YAML fixtures
├── merge_conflicts/       # 12 YAML fixtures
├── rebase/                # 12 YAML fixtures
├── reflog/                # 12 YAML fixtures
├── stash_recovery/        # 12 YAML fixtures
├── submodule_usage/       # 12 YAML fixtures
├── tag_management/        # 12 YAML fixtures
└── worktree_usage/        # 12 YAML fixtures
tests/
├── conftest.py            # Shared test fixtures
├── test_benchmarks.py     # Benchmark correctness tests
├── test_cli.py            # CLI integration tests
├── test_config.py         # Config loader tests
├── test_export.py         # Export format tests
├── test_format.py         # UI formatting tests
├── test_git.py            # GitExecutor tests
├── test_integration.py    # End-to-end integration tests
├── test_loader.py         # Fixture loader tests
├── test_model.py          # Model adapter tests
├── test_parallel_fixtures.py  # Parallel fixture execution tests
├── test_reasoning.py      # Reasoning level validation tests
├── test_render.py         # Render/aggregation tests
├── test_result_doctoring.py   # Doctor command tests
├── test_result_safety.py      # Result-safety unit tests
├── test_result_safety_cli.py  # Result-safety CLI and publication-gate tests
├── test_scorer.py         # Scoring logic tests
└── test_types.py          # Data type tests
```

## Architecture

- **CLI** (`gitbench/cli.py`): Click-based command group with `run`, `list`, `doctor`, `safety-doctor`, `profiles`, and `report` commands.
- **Configuration** (`gitbench/config.py`): Loads model profiles from `gitbench.json` and project `.env` files. Profiles define model lists, provider type, base URL, credential variable names via `api_key_env`, timeout, and retry settings.
- **Benchmark ABC** (`gitbench/harness/benchmark.py`): Abstract base class enforcing `run_setup()`, `load_fixtures()`, and `score()` interface. Drop a new Python module in `benchmarks/` to add a new benchmark category — auto-discovered via `importlib`.
- **Benchmark Runner** (`gitbench/harness/runner.py`): Orchestrates fixture execution against a model, supports concurrent fixtures, and reports progress via the `RunProgress` protocol.
- **Model adapters** (`gitbench/harness/model.py`): `ModelInterface` ABC with `OpenAIAdapter`, `OllamaAdapter`, and `MockModelClient` implementations. Models can specify a reasoning level with `model#level` syntax.
- **Reasoning validation** (`gitbench/harness/reasoning.py`): Validates model + reasoning level combinations before any API calls. Fails fast on invalid pairings.
- **Fixture loader** (`gitbench/harness/loader.py`): Parses and validates YAML fixtures. Supports single fixture per file (dict) or multiple (list).
- **Scorer** (`gitbench/harness/scorer.py`): Computes text similarity via `difflib.SequenceMatcher`, command equivalence, state assertions, structured field scoring, and `pass_at_k` across fixtures.
- **Git executor** (`gitbench/utils/git.py`): Manages sandboxed temporary git repositories for fixture isolation. Uses `_run_command_permissive` internally for `git merge` and `git rebase` which intentionally exit code 1 on conflicts.
- **Progress display** (`gitbench/ui/display.py`): Rich-based live TUI with progress bars, model panels, throughput stats, cost estimation, and final summary tables.
- **Export** (`gitbench/export.py`): Pluggable format registry. Ships with CSV (per-fixture) and artificialanalysis (per-benchmark) exporters.
- **Result doctoring** (`gitbench/result_doctoring.py`): Identifies transient failures (rate limits, timeouts, server errors) and re-runs only affected fixtures against the original models.
- **Result safety** (`gitbench/result_safety.py`): Reviews canonical generated-content bundles, applies deterministic redaction, records audit hashes, backs up affected originals, and validates publication inputs.
- **Report rendering** (`gitbench/render.py`): Aggregates run envelopes from directories or JSONL files, resolves model metadata, and produces `results.json` for the Astro report site.

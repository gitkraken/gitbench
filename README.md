# GitBench

A benchmark suite for evaluating language models' Git competency. GitBench runs synthetic Git scenarios against models and scores their responses against known-good solutions.

## Requirements

- Python 3.10+
- Git CLI installed and available in `PATH`

## Installation

```bash
pip install -e .
```

Or with the included virtual environment:

```bash
source .venv/bin/activate
```

## Running Benchmarks

### List available benchmarks

```bash
gitbench list
# or
python -m gitbench.cli list
```

### Run all benchmarks at once

```bash
gitbench run --all --model mock
# or
python -m gitbench.cli run --all --model mock
```

### Run a specific benchmark

```bash
gitbench run --benchmark commit_messages --model mock
```

With a real model (requires `OPENAI_API_KEY` environment variable):

```bash
OPENAI_API_KEY=sk-... gitbench run --benchmark commit_messages --model openai
```

### Verbose output

Add `--verbose` (or `-v`) to see per-fixture results including pass/fail and similarity scores:

```bash
gitbench run --all --model mock --verbose
```

### Output files

```bash
gitbench run --all --model mock
```

Each successful run writes results to:

| Artifact | Default path |
| -------- | ------------ |
| JSON results | `gitbench-results/<timestamp>/results-v<benchmark_suite_version>.json` |

Override the path on the CLI:

```bash
gitbench run --all --model mock --json-output results.json
```

You can also set defaults in `gitbench.json` or `.gitbench.json`:

```json
{
  "outputs": {
    "json": "runs/latest.json",
    "html": "runs/latest.html"
  }
}
```

### Generate a report

After running benchmarks, generate a static report site:

```bash
gitbench report
```

This aggregates results from `gitbench-results/`, generates `web/public/results.json`, builds the Astro site to `web/dist/`, and starts a preview server.

```bash
gitbench report --open    # build and open in browser
gitbench report --dev     # start dev server with hot reload
gitbench report --no-build  # only generate results.json (skip build)
```

### Result versioning

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
| `git_grep`        | Search repository content with git grep                                | 12       | exact_match/similarity |
| `git_log_format`  | Format git log output for targeted history inspection                  | 12       | exact_match    |
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
| `command_equivalence` | Tokenized command comparison against fixture-declared accepted alternatives |
| `state_assertions` | Execute model output as git commands, then verify repo state via assertions (file_exists, dir_exists, file_content, branch_exists, git_config, git_output) |
| `structured` | Parse model output as key-value fields, score each independently (exact_match or similarity per field) |
| `commit_selection` | Verify that the model selects specific expected commits (used by commit_squash) |
| `dynamic_hash` | Match against a git hash that varies per run (used by git_bisect, git_show) |

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

### Adding New Fixtures

Fixtures live in `fixtures/<benchmark>/`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full fixture authoring guide, including YAML gotchas, setup command tips, and validation.

Quick start:

```yaml
id: "f013"
description: "My scenario"
purpose: "Tests ability to generate a commit message for a new file. Evaluates basic diff comprehension."
difficulty: easy
tags:
  - commit-message
  - add
  - basic
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

**YAML gotcha:** values containing colons (e.g., `"Fix: login"`) must use single quotes, or PyYAML will parse them as mapping keys.

### Adding a New Benchmark Category

See [CONTRIBUTING.md](CONTRIBUTING.md#adding-a-new-benchmark) for the step-by-step guide. The short version: drop a Python module inheriting from `Benchmark` in `gitbench/benchmarks/`. No registration or harness changes needed — auto-discovered via `importlib`.

**Important gotcha — rebase vs merge conflict polarity:** In merge conflicts, HEAD's changes appear above `=======`. In rebase conflicts, the polarity is reversed — upstream's changes appear _below_ `=======`. When writing rebase fixtures, describe the correct branch context in the prompt.

**Important gotcha — GitExecutor exit codes:** `git merge` and `git rebase` exit with code 1 on conflicts. `GitExecutor.setup_repo()` handles this automatically — do not call `_run_command()` directly for merge/rebase commands in fixtures.

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

## Project Structure

```
gitbench/
├── __init__.py
├── cli.py                  # Click-based CLI (run, list)
├── harness/
│   ├── types.py           # Dataclasses: ModelMessage, Fixture, Score, BenchmarkResult
│   ├── model.py           # ModelInterface, OpenAIAdapter, MockModelClient
│   ├── loader.py          # FixtureLoader: YAML loading and validation
│   └── scorer.py          # Scorer: similarity, command equivalence, state assertions, pass@k
├── benchmarks/
│   ├── __init__.py       # Benchmark abstract base class
│   ├── blame_forensics.py # Blame/forensics benchmark
│   ├── branch_cleanup.py # Branch cleanup benchmark
│   ├── cherry_pick.py    # Cherry-pick benchmark
│   ├── commit_messages.py # Commit message generation benchmark
│   ├── commit_squash.py  # Commit squash benchmark
│   ├── git_bisect.py     # Git bisect benchmark
│   ├── git_clean.py      # Git clean benchmark
│   ├── git_grep.py       # Git grep benchmark
│   ├── git_log_format.py # Git log formatting benchmark
│   ├── git_show.py       # Git show benchmark
│   ├── merge_conflicts.py # Merge conflict resolution benchmark
│   ├── rebase.py         # Interactive rebase benchmark
│   ├── reflog.py         # Reflog/detached HEAD recovery benchmark
│   ├── stash_recovery.py # Stash recovery benchmark
│   ├── submodule_usage.py # Submodule usage benchmark
│   ├── tag_management.py # Tag management benchmark
│   └── worktree_usage.py # Worktree usage benchmark
└── utils/
    └── git.py            # GitExecutor: sandboxed git repo management
fixtures/
├── blame_forensics/     # 12 YAML fixtures for blame/forensics benchmark
├── branch_cleanup/      # 12 YAML fixtures for branch cleanup benchmark
├── cherry_pick/         # 12 YAML fixtures for cherry-pick benchmark
├── commit_messages/     # 12 YAML fixtures for commit message benchmark
├── commit_squash/       # 12 YAML fixtures for commit squash benchmark
├── git_bisect/          # 12 YAML fixtures for git bisect benchmark
├── git_clean/           # 12 YAML fixtures for git clean benchmark
├── git_grep/            # 12 YAML fixtures for git grep benchmark
├── git_log_format/      # 12 YAML fixtures for git log formatting benchmark
├── git_show/            # 12 YAML fixtures for git show benchmark
├── merge_conflicts/     # 12 YAML fixtures for merge conflict benchmark
├── rebase/              # 12 YAML fixtures for rebase benchmark
├── reflog/              # 12 YAML fixtures for reflog benchmark
├── stash_recovery/      # 12 YAML fixtures for stash recovery benchmark
├── submodule_usage/     # 12 YAML fixtures for submodule usage benchmark
├── tag_management/      # 12 YAML fixtures for tag management benchmark
└── worktree_usage/      # 12 YAML fixtures for worktree usage benchmark
tests/                    # Unit and integration tests
```

## Architecture

- **Benchmark ABC** (`gitbench/benchmarks/__init__.py`): Abstract base class enforcing `load_fixtures()` and `score()` interface. Drop a new Python module in `benchmarks/` to add a new benchmark category. See [CONTRIBUTING.md](CONTRIBUTING.md#adding-a-new-benchmark) for the full guide.
- **Model adapters** (`gitbench/harness/model.py`): `ModelInterface` ABC with `OpenAIAdapter` and `MockModelClient` implementations. Add a new adapter for model-specific needs.
- **Fixture loader** (`gitbench/harness/loader.py`): Parses and validates YAML fixtures. Supports single fixture per file (dict) or multiple (list).
- **Scorer** (`gitbench/harness/scorer.py`): Computes text similarity via `difflib.SequenceMatcher` and `pass_at_k` across fixtures.
- **Git executor** (`gitbench/utils/git.py`): Manages sandboxed temporary git repositories for fixture isolation. Uses `_run_command_permissive` internally for `git merge` and `git rebase` which intentionally exit code 1 on conflicts.

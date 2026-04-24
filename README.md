# GitBench

A benchmark harness for evaluating LLM-generated git commit messages.

GitBench runs fixtures — each fixture sets up a git repository with staged changes, asks a model to generate a commit message, and scores the model's response against an expected message using text similarity.

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

### Run the commit message benchmark

With the mock model (no API key needed):

```bash
gitbench run --benchmark commit_messages --model mock
# or
python -m gitbench.cli run --benchmark commit_messages --model mock
```

With a real model (requires `OPENAI_API_KEY` environment variable):

```bash
OPENAI_API_KEY=sk-... gitbench run --benchmark commit_messages --model openai
```

### Verbose output

Add `--verbose` (or `-v`) to see per-fixture results including pass/fail and similarity scores:

```bash
gitbench run --benchmark commit_messages --model mock --verbose
```

### Output to a file

```bash
gitbench run --benchmark commit_messages --model mock --output results.json
```

## Output Format

The CLI outputs JSON to stdout (or writes to a file with `--output`). The format is:

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

| Field | Type | Description |
|-------|------|-------------|
| `benchmark` | `string` | Benchmark name |
| `total` | `integer` | Total number of fixtures |
| `passed` | `integer` | Number of fixtures that passed |
| `pass_at_k` | `float` | Fraction of fixtures with at least one passing attempt |
| `scores` | `list` | Per-fixture score objects |
| `errors` | `integer` | Number of fixtures that produced an error |

Each score object contains:

| Field | Type | Description |
|-------|------|-------------|
| `fixture_id` | `string` | Fixture identifier |
| `passed` | `boolean` | Whether the model output passed the threshold |
| `similarity` | `float` | Text similarity score (0.0 – 1.0) |
| `model_output` | `string` | The model's generated commit message |
| `error` | `string \| null` | Error message if processing failed |

## Adding New Fixtures

Fixtures live in `fixtures/commit_messages/`. Each is a YAML file with this structure:

```yaml
id: "f013"                        # Unique identifier
description: "Merge conflict resolution"  # Human-readable description
setup:                             # Git commands to set up the repo state
  - "git init"
  - "git config user.email 'test@test.com'"
  - "git config user.name 'Test User'"
  - "echo 'resolved' > conflict.txt"
  - "git add conflict.txt"
prompt: "Generate a concise commit message (max 50 characters)..."
expected: "Resolve merge conflict"  # Expected model output for scoring
scoring:
  type: "similarity"              # Scoring algorithm
  threshold: 0.5                  # Minimum similarity to pass (0.0 – 1.0)
```

### Setup command tips

- Use absolute paths with `printf` for multi-line content:
  ```yaml
  setup:
    - "git init"
    - "git config user.email 'test@test.com'"
    - "git config user.name 'Test User'"
    - "printf 'line1\\nline2\\nline3' > file.txt"
    - "git add file.txt"
  ```
- All commands run in a sandboxed temporary git repository.
- The last setup command should leave changes staged (`git add`) so that `git diff --staged` produces the diff for the prompt.
- Use `chmod +x` for permission change tests:
  ```yaml
  setup:
    - "touch script.sh"
    - "chmod +x script.sh"
    - "git add script.sh"
  ```

### Fixture guidelines

1. **Unique IDs**: Use sequential IDs (`f013`, `f014`, ...) to avoid collisions.
2. **Diverse scenarios**: Cover different git operations (add, rename, delete, modify, chmod, etc.).
3. **Realistic prompts**: Keep prompts concise and focused on the commit message task.
4. **Realistic expected messages**: Use conventional commit format when appropriate (e.g., `feat:`, `fix:`, `docs:`).
5. **Set an appropriate threshold**: The default threshold is `0.5`, which is suitable for most cases. Lower it to make scoring more lenient, raise it to require near-exact matches.

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
│   └── scorer.py          # Scorer: similarity scoring and pass@k computation
├── benchmarks/
│   ├── __init__.py       # Benchmark abstract base class
│   └── commit_messages.py # CommitMessagesBenchmark implementation
└── utils/
    └── git.py            # GitExecutor: sandboxed git repo management
fixtures/
└── commit_messages/     # YAML fixtures for commit message benchmark
tests/                    # Unit and integration tests
```

## Architecture

- **Benchmark ABC** (`gitbench/benchmarks/__init__.py`): Abstract base class enforcing `load_fixtures()` and `score()` interface.
- **Model adapters** (`gitbench/harness/model.py`): `ModelInterface` ABC with `OpenAIAdapter` and `MockModelClient` implementations.
- **Fixture loader** (`gitbench/harness/loader.py`): Parses and validates YAML fixtures.
- **Scorer** (`gitbench/harness/scorer.py`): Computes text similarity via `difflib.SequenceMatcher` and `pass_at_k` across fixtures.
- **Git executor** (`gitbench/utils/git.py`): Manages sandboxed temporary git repositories for fixture isolation.

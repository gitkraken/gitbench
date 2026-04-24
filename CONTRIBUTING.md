# Contributing to GitBench

Thank you for your interest in contributing. This guide covers the two main ways to contribute: adding new fixtures to existing benchmarks, and adding new benchmark categories.

## Adding New Fixtures

### Fixture Structure

Fixtures live in `fixtures/<benchmark>/`. Each is a YAML file:

```yaml
id: "f013"
description: "What this fixture tests"
setup:
  - "git init"
  - "git config user.email 'test@test.com'"
  - "git config user.name 'Test User'"
  - "echo 'content' > file.txt"
  - "git add file.txt"
prompt: "Your instruction to the model"
expected: "The correct model output"
scoring:
  type: "similarity"
  threshold: 0.5
```

**Required fields:**
- `id` — unique identifier (use next sequential number: f013, f014, ...)
- `setup` — list of git commands to set up the repo state
- `prompt` — what to ask the model
- `expected` — correct answer for scoring

**Optional fields:**
- `description` — human-readable description
- `scoring.type` — scoring algorithm (`similarity` is the only one currently)
- `scoring.threshold` — minimum similarity to pass (0.0–1.0, default 0.5)

### Setup Command Tips

- Use `printf` for multi-line file content:
  ```yaml
  setup:
    - "printf 'line1\\nline2\\nline3' > file.txt"
  ```
- The last setup command should leave changes staged so `git diff --staged` works.
- All commands run in a sandboxed temporary git repository.
- Set git identity for each fixture to avoid warnings:
  ```yaml
  setup:
    - "git config user.email 'test@test.com'"
    - "git config user.name 'Test User'"
  ```

### Fixture Guidelines

1. **Unique IDs** — Use sequential IDs (`f013`, `f014`, ...) to avoid collisions.
2. **Diverse scenarios** — Cover different git operations and edge cases.
3. **Realistic prompts** — Keep prompts concise and focused.
4. **Realistic expected values** — Use conventional commit format when appropriate.
5. **Appropriate thresholds** — Default 0.5 works for most text. Lower for lenient scoring, raise for exact-match requirements.
6. **YAML gotcha** — Bare colons in strings (e.g., commit messages like "Fix: login") cause PyYAML to parse them as mapping keys. Use single quotes: `'Fix: login'` or explicit block scalars (`|`).

### Validating Fixtures

Run the test suite to catch fixture errors:

```bash
pytest tests/test_loader.py -v
```

Or test fixture loading directly:

```bash
python3 -c "from gitbench.harness.loader import FixtureLoader; l = FixtureLoader(); print(len(l.load_dir('fixtures/commit_messages')), 'fixtures loaded')"
```

---

## Adding a New Benchmark

Adding a new benchmark category takes three steps: create the module, create fixtures, and verify.

### Step 1: Create the Benchmark Module

Drop a new Python file in `gitbench/benchmarks/`. It must:

1. Inherit from `Benchmark` (`from gitbench.benchmarks import Benchmark`)
2. Define `name` and `description` class attributes
3. Implement `load_fixtures()` — returns list of `Fixture` objects
4. Implement `score()` — returns a `Score` object

```python
"""My benchmark for GitBench."""

from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor


class MyBenchmark(Benchmark):
    """Benchmark for evaluating X."""

    name = "my_benchmark"
    description = "Describe what this benchmarks"

    def __init__(self):
        self._loader = FixtureLoader()
        self._scorer = Scorer()

    def load_fixtures(self) -> list[Fixture]:
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "my_benchmark"
        return self._loader.load_dir(str(fixtures_dir))

    def score(self, fixture: Fixture, model_output: str) -> Score:
        return self._scorer.score(fixture, model_output)

    def setup_fixture(self, fixture: Fixture) -> tuple[GitExecutor, str]:
        executor = GitExecutor()
        repo_path = executor.setup_repo(f"fixture_{fixture.id}", fixture.setup)
        return executor, repo_path

    def get_diff(self, repo_path: str) -> str:
        # Return whatever git context the model needs
        # For commit_messages: git diff --staged
        # For merge conflicts: read conflicted files from filesystem
        # For git_bisect: git log --oneline + test output
        # For reflog: git reflog output
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--staged"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return result.stdout or result.stderr

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        return f"{fixture.prompt}\n\n{diff}"
```

**Auto-discovery:** The harness discovers benchmarks via `importlib` + `inspect.getmembers`. Drop the file in `benchmarks/` — no registration needed.

### Step 2: Create Fixtures

Create the directory and YAML fixtures:

```bash
mkdir -p fixtures/my_benchmark
```

Follow the structure from [Adding New Fixtures](#adding-new-fixtures) above. Use 10+ fixtures for meaningful pass@1 scoring (12 is the current standard).

### Step 3: Add Unit Tests

Add tests to `tests/test_benchmarks.py`:

```python
def test_mybenchmark_loads():
    from gitbench.benchmarks.my_benchmark import MyBenchmark

    benchmark = MyBenchmark()
    fixtures = benchmark.load_fixtures()
    assert len(fixtures) >= 10
    assert all(hasattr(f, 'id') for f in fixtures)

def test_mybenchmark_required_fields():
    fixtures = MyBenchmark().load_fixtures()
    for f in fixtures:
        assert f.id
        assert f.prompt
        assert f.expected
```

Run the test suite:

```bash
pytest tests/test_benchmarks.py -k "MyBenchmark" -v
```

---

## Conflict Marker Polarity: Rebase vs Merge

This is a common trap when writing `rebase` fixtures.

**In merge conflicts:** HEAD's changes appear above `=======`, the other branch's changes appear below.

```
<<<<<<< HEAD
content from main
=======
content from feature
>>>>>>> feature
```

**In rebase conflicts:** the polarity is reversed — the upstream's changes appear *below* `=======` (because in a rebase, the branch being rebased onto becomes the new HEAD).

```
<<<<<<< HEAD
content from feature (branch being rebased)
=======
content from main (upstream)
>>>>>>> main
```

When copying a `merge_conflicts` fixture to create a `rebase` fixture, the expected value may need to flip. For example, a merge conflict with expected `"Hello, Planet!!!"` may have the same expected value in rebase, but the *prompt* must describe the correct branch context.

**Rule:** In rebase conflicts, the content from the branch being rebased (the one you started on) appears above `=======`. The content from the branch being rebased onto (the target) appears below `=======`.

---

## GitExecutor: Non-Zero Exit Codes

`GitExecutor._run_command()` raises `RuntimeError` on any non-zero git exit code. Some git commands are expected to fail:

- `git merge` exits code 1 when there are conflicts
- `git rebase` exits code 1 when there are conflicts

If your benchmark needs to intentionally trigger a conflict state (and the fixture setup needs to run `git merge` or `git rebase`), the `GitExecutor.setup_repo()` method handles this — it uses `_run_command_permissive` internally for these commands. You don't need to call it directly; just pass the setup commands and the executor handles the exit code correctly.

If you need to run other commands that may exit non-zero, you can extend `GitExecutor` with a `_run_command_permissive` method following the same pattern.

---

## Scoring

Currently the only scoring type is `similarity` using Python's `difflib.SequenceMatcher`. It computes character-level similarity between the model's output and the expected value.

The threshold controls pass/fail:
- `0.5` — moderate similarity (suitable for commit messages, file content)
- `0.8+` — near-exact match (suitable for commit hashes, specific identifiers)
- Below `0.5` — lenient (accepts loosely related outputs)

Future milestones may add semantic scoring for cases where text similarity doesn't capture correctness (e.g., identifying a commit hash vs describing it in prose).

---

## Testing Your Changes

```bash
# Run the full test suite
pytest tests/ -v

# Run benchmark-specific tests
pytest tests/test_benchmarks.py -v

# Run a specific benchmark end-to-end
python -m gitbench.cli run --benchmark my_benchmark --model mock

# Run all benchmarks
python -m gitbench.cli run --all --model mock
```

---

## Style Conventions

- **Docstrings** — All public classes and methods have docstrings (NumPy format, as already established in the codebase).
- **Naming** — snake_case for Python identifiers.
- **Imports** — standard library first, then third-party, then project-local.
- **Fixtures** — single-quoted YAML strings for values containing colons or special characters.

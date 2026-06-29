# Contributing to GitBench

Thank you for your interest in contributing. This guide covers the two main ways to contribute: adding new fixtures to existing benchmarks, and adding new benchmark categories.

## Adding New Fixtures

### Fixture Structure

Fixtures live in `fixtures/<benchmark>/`. Each is a YAML file:

```yaml
id: "f013"
description: "What this fixture tests"
purpose: "Tests ability to generate a commit message for a new file. Evaluates basic diff comprehension and summarization."
difficulty: easy
tags:
  - commit-message
  - single-file
  - basic
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
- `description` — short human-readable description
- `purpose` — 1–3 sentence explanation of what skill is tested and why it matters
- `difficulty` — relative difficulty: `trivial`, `easy`, `medium`, `hard`, or `expert`
- `tags` — list of searchable keywords (e.g., `["commit-message", "basic"]`)
- `scoring.type` — scoring algorithm (`similarity`, `exact_match`, `command_equivalence`, `state_assertions`, or benchmark-specific types)
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
5. **Appropriate thresholds** — Default 0.5 works for loose text only. Use higher thresholds for conflict resolutions and exact or benchmark-specific scorers for identifiers, selections, hashes, and commands.
6. **YAML gotcha** — Bare colons in strings (e.g., commit messages like "Fix: login") cause PyYAML to parse them as mapping keys. Use single quotes: `'Fix: login'` or explicit block scalars (`|`).

### Fixture Metadata (Optional but Recommended)

Fixtures support three optional metadata fields that help consumers of benchmark results understand what each fixture tests and why it matters:

```yaml
purpose: "Tests ability to resolve a simple single-line merge conflict. Evaluates basic conflict marker comprehension and merge strategy selection."
difficulty: easy
tags:
  - merge-conflict
  - single-line
  - basic
  - resolution
```

**`purpose`** (string): 1–3 sentences explaining what Git skill this fixture tests and why it matters for evaluating model competency. Write for a researcher or user reading benchmark results — they should understand the scenario without needing to read the YAML setup.

**`difficulty`** (string, enum): One of:
- `trivial` — Single straightforward git command with no edge cases (e.g., "list all tags", "remove a single untracked file")
- `easy` — Simple multi-step operation with clear expected output (e.g., "add a submodule", "create a lightweight tag")
- `medium` — Requires understanding of Git concepts or multi-branch workflows (e.g., "resolve a multi-line merge conflict", "recover a commit via reflog after amend")
- `hard` — Complex scenarios, conflict resolution, or subtle Git behavior (e.g., "resolve three-way conflicts with multiple files", "find orphaned commits after mixed reset")
- `expert` — Rare Git operations, advanced workflows, or scenarios requiring deep Git internals knowledge (e.g., "multi-branch reflog analysis across rebases")

**`tags`** (list of strings): Searchable keywords describing the fixture's domain, operations, or concepts. Use lowercase, hyphen-separated terms. Examples: `["rebase", "conflict-resolution", "multi-file", "three-way"]`. Tags enable filtering and grouping across benchmark categories.

**Tips for writing good `purpose` statements:**
- Start with "Tests ability to..." or "Evaluates..."
- Mention the specific Git operation or concept being tested
- Explain why this scenario matters for real-world Git competency
- Keep it concise — 1–3 sentences is usually enough
- Example: "Tests ability to recover a commit from a deleted feature branch via reflog. Evaluates understanding of reflog-based recovery workflows, which are essential for disaster recovery in collaborative Git environments."

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

Use the narrowest scorer that matches the fixture's intended answer.

- `similarity` uses Python's `difflib.SequenceMatcher`. It is suitable for natural-language commit messages and file content where small wording differences are acceptable. Use higher thresholds, such as `0.9`, for conflict resolutions where incomplete output should fail.
- `exact_match` compares stripped strings exactly. Use it for literal answers such as commit subjects, email addresses, tag names, and exact command output.
- `unordered_line_set` compares non-empty output lines as a set. Use it when the prompt asks for all matching lines or commit messages and order is not part of the skill under test.
- `numeric_exact` compares numeric/count answers after trimming whitespace. Set `allow_prose: true` only when a single number embedded in prose should be accepted.
- `commit_hash_by_subject` derives the expected hash from repository state using `subject` and optional `hash_length: short`. Use it instead of storing static hashes or commit messages for hash-answer fixtures.
- `json_semantic_equal` parses JSON and compares the resulting value. Use it for structured conflict outputs where property order and whitespace should not matter.
- `command_equivalence` compares tokenized command lines against fixture-declared accepted alternatives. Use it for read-only prompts that ask the model to output a Git command.
- `state_assertions` executes model commands in the fixture repo and validates the resulting state. Use it for commands that mutate the repository.
- Benchmark-specific scorers, such as branch selection, commit selection, stash recovery, reflog recovery, and dynamic commit-hash scoring, should enforce the Git-specific correctness contract directly.

### Fixture Self-Checks

Run or extend `gitbench.fixture_self_check` when a fixture expectation can be checked
without a model run. Suite-level validation must call
`check_fixture(fixture, benchmark_name=Benchmark.name)` so self-checks use the
benchmark's effective scoring behavior. Use `check_fixture_generically(...)` only
for explicit fixture-only checks that intentionally ignore benchmark-local scorer
behavior. Current self-checks flag hash prompts with static non-hash expected
values, multi-line `exact_match` fixtures without `scoring.order_matters: true`,
and fixture-declared Git-derived expectations:

```yaml
scoring:
  type: numeric_exact
  self_check:
    command: git log --merges --format=%H
    transform: count_nonempty_lines
```

Use self-checks for counts, short hashes, and other values that can be derived from
the generated repository state.

### Command Equivalence

Use `command_equivalence` when multiple command spellings are semantically equivalent and the fixture asks for a command, not for command output or repo mutation.

```yaml
scoring:
  type: command_equivalence
  accepted:
    - git submodule
    - git submodule status
```

For ordered multi-command answers, list each accepted sequence:

```yaml
scoring:
  type: command_equivalence
  accepted:
    - - git submodule init
      - git submodule update
    - - git submodule update --init
```

Accepted alternatives must be semantically equivalent, not merely similar. Do not list a command that is broader, mutates extra state, omits required flags, or answers a different question just because it often appears near the right command.

### Selection Scoring

Fixtures that ask the model to select branches, commits, files, stash refs, or other Git identifiers should fail when the answer includes extra incorrect selections unless partial credit is explicitly intended and documented in the fixture. In cleanup and history-editing tasks, over-selection is usually dangerous: deleting an extra branch or squashing an unrelated commit is a real failure.

### State Assertions

Use `state_assertions` when the model must perform an operation and correctness is best proven by repository state. Prefer assertions over exact command text for mutating operations because several command sequences may legitimately reach the same state.

### Similarity Scoring

Similarity scoring is intentionally approximate. Keep it for prose and resolved file content where reasonable formatting variation is expected. Avoid low thresholds for multi-file conflict fixtures; broad similarity can let incomplete answers pass when only one returned file resembles the expected output.

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

# Generate a report after running benchmarks
gitbench report
```

## UI Development

The report UI is an Astro static site at top-level `web/`.

**Prerequisites:** Node.js >= 22.12.0

```bash
cd web
npm install
```

**Dev workflow:**

```bash
# Generate results.json from benchmark data
gitbench report

# Start Astro dev server with hot reload
cd web && npm run dev
```

**Tech stack:**
- [Astro](https://astro.build) — static site generation
- [React 19](https://react.dev) — interactive chart islands
- [shadcn/ui](https://ui.shadcn.com) — component primitives (Card, Badge, Button, Select, Command, Popover)
- [Tailwind CSS v4](https://tailwindcss.com) — utility-first CSS
- [Recharts](https://recharts.org) — chart components
- [Lucide](https://lucide.dev) — icons

**Adding shadcn components:**
```bash
cd web
npx shadcn@latest add <component-name>
```

Components are stored in `src/components/ui/` and imported via `@/components/ui/<name>`.

**Build:**
```bash
cd web && npm run build
# Output: dist/
```

---

## Style Conventions

- **Docstrings** — All public classes and methods have docstrings (NumPy format, as already established in the codebase).
- **Naming** — snake_case for Python identifiers.
- **Imports** — standard library first, then third-party, then project-local.
- **Fixtures** — single-quoted YAML strings for values containing colons or special characters.

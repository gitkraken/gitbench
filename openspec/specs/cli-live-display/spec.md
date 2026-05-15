## ADDED Requirements

### Requirement: RichProgressDisplay implements RunProgress protocol
The `RichProgressDisplay` class SHALL implement the `RunProgress` protocol (`model_started`, `benchmark_started`, `fixture_finished`, `benchmark_finished`, `model_finished`) and render a live Rich-based TUI display to stderr.

#### Scenario: Display initializes on construction
- **WHEN** `RichProgressDisplay(models, benchmarks, verbose=True/False)` is constructed
- **THEN** a Rich `Live` context manager SHALL be started with `screen=True` (alternate screen buffer) and `auto_refresh=False`
- **AND** the initial layout SHALL be rendered showing a header, per-model panels (all "pending"), and an empty comparison table

### Requirement: Live display uses alternate screen buffer
The live display SHALL use Rich's `screen=True` mode to render in the terminal's alternate screen buffer, so that when `close()` is called the display is swapped out cleanly without leaving artifacts in scrollback.

#### Scenario: Display swaps out on close
- **WHEN** `close()` is called after a benchmark run completes
- **THEN** `Live.stop()` SHALL be called, restoring the terminal to its pre-display state
- **AND** a final static summary table SHALL be printed to stdout using Rich's `Console` (no live refresh)

### Requirement: Header shows run metadata
The header section of the live display SHALL show an elapsed timer (updating on each refresh), model count, and benchmark count. When all models are done, the header SHALL change from "GitBench progress" to "GitBench complete".

#### Scenario: Header updates elapsed time
- **WHEN** the display refreshes during a run
- **THEN** the header SHALL show elapsed time in `XmXXs` format (e.g., "2m14s")
- **AND** the model and benchmark counts SHALL be shown (e.g., "2 models · 18 benchmarks")

### Requirement: Per-model panels show live progress
Each model SHALL have a bordered Rich `Panel` displaying: a progress bar (benchmarks completed / total), the current benchmark name, current fixture progress (e.g., "fixture 12/30"), pass rate percentage with raw counts (e.g., "67.3% (198/294)"), error count, accumulated input/output tokens with human-readable suffixes, and accumulated cost in USD. The panel SHALL be color-coded by status: cyan for running, green for done, yellow for error, dim for pending.

#### Scenario: Panel updates on fixture completion
- **WHEN** `fixture_finished(model, benchmark, passed=True)` is called
- **THEN** the model's panel SHALL increment its passed and total fixture counts
- **AND** the pass rate percentage SHALL recalculate and display with appropriate color (green ≥80%, yellow ≥50%, red <50%)

#### Scenario: Panel shows accumulated tokens and cost
- **WHEN** token data is available after fixture completion
- **THEN** the model's panel SHALL show input tokens with `⇣` prefix and human-readable suffix (e.g., "45.2K⇣")
- **AND** output tokens with `⇡` prefix and human-readable suffix (e.g., "12.8K⇡")
- **AND** cost in USD (e.g., "$0.042")

### Requirement: Comparison summary table fills in live
A comparison table SHALL render below the model panels showing one row per benchmark. For small model sets, columns SHALL be: benchmark name, then one column per model with its pass rate. For larger model sets, the table SHALL switch to aggregate columns showing completion count, best result, and result range. Rows for benchmarks not yet started SHALL show "..." in dim text. Rows for in-progress benchmarks SHALL show "running" in cyan. Completed rows SHALL show the pass rate with the same color thresholds as the model panels.

#### Scenario: Row fills in as benchmark completes
- **WHEN** `benchmark_finished(model, benchmark, errors=0)` is called
- **THEN** if all models have completed this benchmark, the row SHALL switch from "running" to the pass rate with color coding

#### Scenario: Multi-model run omits delta column
- **WHEN** multiple models are being run
- **THEN** the comparison table SHALL NOT include a delta column

#### Scenario: Large model set uses aggregate summary
- **WHEN** five or more models are being run
- **THEN** the comparison table SHALL use aggregate columns instead of one column per model

### Requirement: Verbose mode shows log panel and writes log file
When `--verbose` is passed, the live display SHALL include a fixed-height log panel (6 lines) at the bottom showing the most recent per-fixture results with timestamp, benchmark/fixture_id, PASS/FAIL status, and similarity score. On `close()`, the full verbose log SHALL be written to a timestamped file at `gitbench-logs/verbose-{timestamp}.log`, and the file path SHALL be printed to stderr.

#### Scenario: Log panel shows recent fixtures during run
- **WHEN** a fixture completes in verbose mode
- **THEN** a line like `[HH:MM:SS] bench/fixture_id: PASS  sim=0.87` SHALL appear in the log panel
- **AND** the log panel SHALL scroll to show only the most recent 6 lines

#### Scenario: Log file written on close
- **WHEN** `close()` is called after a verbose run
- **THEN** the full log buffer SHALL be written to `gitbench-logs/verbose-{timestamp}.log`
- **AND** stderr SHALL print "Verbose log written to: gitbench-logs/verbose-{timestamp}.log"

### Requirement: Non-TTY fallback for piped stderr
When stderr is not a TTY (piped or redirected), `RichProgressDisplay` SHALL skip the live display and instead render periodic plain-text progress summaries to stderr, using Rich's `Console` with `force_terminal=False`. The final summary table SHALL still be printed to stdout if stdout is a TTY.

#### Scenario: Plain-text output when stderr is piped
- **WHEN** `RichProgressDisplay` detects that stderr is not a TTY
- **THEN** `self.enabled` SHALL be `False`
- **AND** progress callbacks SHALL write plain-text status lines to stderr (e.g., "[model] benchmark: 12/30 fixtures, 67.3% pass rate")
- **AND** no ANSI escape codes or alternate screen buffer SHALL be used

### Requirement: Human-readable number formatting
The `gitbench/ui/format.py` module SHALL provide `human_readable(n, unit="")` that formats integers ≥1000 with K/M/B suffixes (e.g., `1234` → `"1.2K"`, `1234567` → `"1.2M"`). It SHALL also provide `human_readable_cost(n)` that formats floats as USD (e.g., `0.042` → `"$0.04"`, `1.23` → `"$1.23"`). It SHALL also provide `format_duration(seconds)` that formats as `"XmXXs"` or `"XXs"`.

#### Scenario: Token count formatted with suffix
- **WHEN** `human_readable(45123, unit="")` is called
- **THEN** the result SHALL be `"45.1K"`

#### Scenario: Large token count formatted as millions
- **WHEN** `human_readable(1234567, unit="")` is called
- **THEN** the result SHALL be `"1.2M"`

#### Scenario: Cost formatted as USD
- **WHEN** `human_readable_cost(0.042)` is called
- **THEN** the result SHALL be `"$0.04"`

### Requirement: No hand-rolled terminal code remains
After this change, the files `gitbench/ui/terminal.py`, `gitbench/ui/progress.py`, and `gitbench/ui/summary.py` SHALL be deleted. All terminal output SHALL be handled by Rich's `Console`, `Live`, `Table`, `Panel`, and `Layout` classes.

#### Scenario: Deleted modules are not importable
- **WHEN** importing from `gitbench.ui.terminal`, `gitbench.ui.progress`, or `gitbench.ui.summary`
- **THEN** an `ImportError` SHALL be raised

### Requirement: Rich dependency is declared
`rich>=13.0.0` SHALL be listed in `pyproject.toml` under `[project].dependencies`.

#### Scenario: Rich is installable as a dependency
- **WHEN** `pip install -e .` is run
- **THEN** Rich SHALL be installed automatically

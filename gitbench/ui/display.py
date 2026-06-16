"""Rich-based live progress display implementing the RunProgress protocol."""

import sys
from collections import deque
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from gitbench.harness.runner import RunProgress
from gitbench.ui.format import format_duration, human_readable, human_readable_cost


MIN_PANEL_WIDTH = 34
COMPACT_PANEL_WIDTH = 26
DENSE_PANEL_WIDTH = 16
FULL_PANEL_HEIGHT = 6
COMPACT_PANEL_HEIGHT = 5
DENSE_PANEL_HEIGHT = 3
SUMMARY_CHROME_HEIGHT = 4
MIN_SUMMARY_ROWS = 4
MIN_SUMMARY_VISIBLE_HEIGHT = SUMMARY_CHROME_HEIGHT + 1
HEADER_HEIGHT = 3
LOG_HEIGHT = 8


def _progress_bar(pct: float, width: int = 20) -> str:
    """Build a unicode-block progress bar string with Rich markup.

    Args:
        pct: Percentage complete (0-100).
        width: Total character width of the bar.

    Returns:
        Rich-markup string like ``"[green]████████░░░░░░░░[/] 40%"``.
    """
    filled = max(0, min(width, int(pct / 100 * width)))
    empty = width - filled
    if pct >= 100:
        colour = "green"
    else:
        colour = "cyan"
    return f"[{colour}]{'█' * filled}{'░' * empty}[/] {pct:.0f}%"


def _pass_rate_colour(pass_rate: float) -> str:
    """Return a Rich colour name for a pass rate threshold."""
    if pass_rate >= 0.8:
        return "green"
    elif pass_rate >= 0.5:
        return "yellow"
    else:
        return "red"


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


class RichProgressDisplay:
    """Render a Rich-based live progress display on stderr.

    Implements the :class:`RunProgress` protocol so it can be passed
    directly to :class:`BenchmarkRunner`.
    """

    def __init__(
        self,
        models: list[str],
        benchmarks: list[str],
        *,
        verbose: bool = False,
        refresh_interval: float = 1.0,
        campaign_id: str | None = None,
        trials: int | None = None,
        planned_attempts: int | None = None,
        publication_state: str | None = None,
    ) -> None:
        """Initialise the display.

        Args:
            models: Display names for each model being benchmarked.
            benchmarks: Names of benchmarks that will be run.
            verbose: If ``True``, show a scrolling log panel and write a
                log file on close.
            refresh_interval: Seconds between heartbeat repaints while the
                live display is active.
            campaign_id: Optional campaign identifier for repeated
                evaluation campaigns.
            trials: Number of planned trial rounds when running a campaign.
            planned_attempts: Total planned attempts across all trials.
            publication_state: Campaign publication state label.
        """
        self._models = models
        self._benchmarks = benchmarks
        self._verbose = verbose
        self._campaign_id = campaign_id
        self._trials = trials
        self._planned_attempts = planned_attempts
        self._publication_state = publication_state
        self._completed_attempts = 0
        self._failed_attempts = 0
        self._reused_attempts = 0
        self._new_attempts = 0
        self._quality_failed_attempts = 0
        self._infrastructure_failed_attempts = 0
        self._invalid_attempts = 0
        self._unscored_attempts = 0
        self._safety_blocked_attempts = 0
        self._lock = Lock()
        self._started_at = monotonic()
        self._refresh_interval = refresh_interval
        self._stop_refresh = Event()
        self._refresh_thread: Thread | None = None
        self._closed = False

        # TTY detection
        self.enabled = sys.stderr.isatty()

        # Per-model state
        self._rows: dict[str, dict] = {}
        for model in models:
            self._rows[model] = {
                "model": model,
                "status": "pending",
                "current_benchmark": "-",
                "benchmarks_done": 0,
                "benchmarks_total": len(benchmarks),
                "fixtures_done": 0,
                "fixtures_total": 0,
                "passed": 0,
                "errors": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            }

        # Per-model per-benchmark results for the comparison table
        self._bench_results: dict[str, dict[str, dict]] = {}
        for model in models:
            self._bench_results[model] = {}
            for bench in benchmarks:
                self._bench_results[model][bench] = {
                    "total": 0,
                    "passed": 0,
                    "errors": 0,
                    "done": False,
                }

        # Verbose log ring buffer
        self._log_lines: deque[str] = deque(maxlen=500)

        if self.enabled:
            try:
                self._console = Console(stderr=True)
                layout = self._build_layout()
                self._live = Live(
                    layout,
                    console=self._console,
                    screen=True,
                    auto_refresh=False,
                )
                self._live.start()
                self._start_periodic_refresh()
            except Exception:
                self.enabled = False
                self._console = Console(stderr=True, force_terminal=False)
                self._live = None
        else:
            self._console = Console(stderr=True, force_terminal=False)
            self._live = None

    # -- RunProgress protocol ------------------------------------------------

    def model_started(self, model: str) -> None:
        with self._lock:
            row = self._rows[model]
            if row["status"] == "pending":
                row["status"] = "queued"
            self._refresh()

    def benchmark_started(self, model: str, benchmark: str, total: int) -> None:
        with self._lock:
            row = self._rows[model]
            row["current_benchmark"] = benchmark
            row["status"] = "running"
            row["fixtures_total"] += total
            self._refresh()

    def fixture_finished(
        self,
        model: str,
        benchmark: str,
        passed: bool,
        *,
        fixture_id: str = "",
        similarity: float = 0.0,
    ) -> None:
        with self._lock:
            row = self._rows[model]
            row["current_benchmark"] = benchmark
            row["fixtures_done"] += 1
            if passed:
                row["passed"] += 1

            br = self._bench_results[model][benchmark]
            br["total"] += 1
            if passed:
                br["passed"] += 1

            if self._verbose and fixture_id:
                status = "PASS" if passed else "FAIL"
                ts = datetime.now().strftime("%H:%M:%S")
                line = (
                    f"[{ts}] {benchmark}/{fixture_id}: {status}  "
                    f"passed={passed}  similarity={similarity:.4f}"
                )
                self._log_lines.append(line)
                if not self.enabled:
                    self._console.print(line)

            self._refresh()

    def benchmark_finished(self, model: str, benchmark: str, errors: int) -> None:
        with self._lock:
            row = self._rows[model]
            row["current_benchmark"] = benchmark
            row["errors"] += errors
            row["benchmarks_done"] += 1
            if row["fixtures_done"] >= row["fixtures_total"]:
                row["status"] = "running"

            br = self._bench_results[model][benchmark]
            br["errors"] = errors
            br["done"] = True

            self._refresh()

    def model_finished(self, model: str, summary: dict) -> None:
        with self._lock:
            row = self._rows[model]
            if row["status"] in {"pending", "queued", "running", "error"}:
                row["status"] = "done"
            self._refresh()

    def campaign_attempt_completed(self, count: int = 1) -> None:
        """Increment the number of completed campaign attempts."""
        with self._lock:
            self._completed_attempts += count
            self._new_attempts += count
            self._refresh()

    def campaign_attempt_failed(self, count: int = 1) -> None:
        """Increment the number of failed campaign attempts."""
        with self._lock:
            self._failed_attempts += count
            self._completed_attempts += count
            self._new_attempts += count
            self._refresh()

    def campaign_attempt_reused(self, count: int = 1) -> None:
        """Increment the number of reused campaign attempts."""
        with self._lock:
            self._reused_attempts += count
            self._refresh()

    def campaign_attempt_recorded(
        self,
        status: str,
        *,
        safety_state: str | None = None,
        count: int = 1,
    ) -> None:
        """Record a completed campaign attempt with status-specific counters."""
        with self._lock:
            self._completed_attempts += count
            self._new_attempts += count
            if status == "valid_fail":
                self._quality_failed_attempts += count
            elif status == "infrastructure_failure":
                self._infrastructure_failed_attempts += count
            elif status in {"invalid_input", "hash_mismatch"}:
                self._invalid_attempts += count
            elif status == "unscored":
                self._unscored_attempts += count
            elif status == "safety_blocked" or safety_state == "blocked":
                self._safety_blocked_attempts += count
            if status != "valid_pass":
                self._failed_attempts += count
            self._refresh()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True

        self._stop_refresh.set()
        if self._refresh_thread is not None:
            self._refresh_thread.join(timeout=self._refresh_interval + 0.5)

        with self._lock:
            if self._live is not None:
                try:
                    self._live.stop()
                except Exception:
                    pass
                self._live = None
            self._restore_terminal()

        # Print final static summary to stdout (if TTY)
        if sys.stdout.isatty():
            try:
                table = self._render_summary_table(width=self._console.size.width)
                stdout_console = Console()
                stdout_console.print(table)
            except Exception:
                pass

        # Dump verbose log to file
        if self._verbose and self._log_lines:
            self._dump_verbose_log()

    def _restore_terminal(self) -> None:
        """Best-effort fallback for terminal state if Rich cleanup is incomplete."""
        if not sys.stderr.isatty():
            return
        try:
            # Show cursor, leave alternate screen, reset modes/styles, normal keypad.
            sys.stderr.write("\x1b[?25h\x1b[?1049l\x1b[?1l\x1b>\x1b[0m\r\n")
            sys.stderr.flush()
        except Exception:
            pass

    # -- refresh -------------------------------------------------------------

    def _refresh(self) -> None:
        if not self.enabled or self._live is None:
            try:
                self._render_fallback()
            except Exception:
                pass
            return
        try:
            layout = self._build_layout()
            self._live.update(layout, refresh=True)
        except Exception:
            pass

    def _start_periodic_refresh(self) -> None:
        if (
            not self.enabled
            or self._live is None
            or self._refresh_interval <= 0
            or self._refresh_thread is not None
        ):
            return

        self._refresh_thread = Thread(
            target=self._periodic_refresh_loop,
            name="gitbench-progress-refresh",
            daemon=True,
        )
        self._refresh_thread.start()

    def _periodic_refresh_loop(self) -> None:
        while not self._stop_refresh.wait(self._refresh_interval):
            with self._lock:
                if self._live is None:
                    return
                self._refresh()

    def _render_fallback(self) -> None:
        """Render plain-text progress lines when stderr is not a TTY."""
        for model, row in self._rows.items():
            if row["status"] in ("pending",):
                continue
            bench_pct = (
                f"{row['benchmarks_done']}/{row['benchmarks_total']}"
            )
            fix_pct = f"{row['fixtures_done']}/{row['fixtures_total']}"
            total = row["fixtures_total"]
            if total > 0:
                rate = f"{row['passed'] / total * 100:.1f}%"
            else:
                rate = "0%"
            self._console.print(
                f"[{row['status']}] {model}: {row['current_benchmark']}  "
                f"benchmarks {bench_pct}  fixtures {fix_pct}  "
                f"pass {rate} ({row['passed']}/{total})  "
                f"failures {row['errors']}"
            )

    # -- layout construction --------------------------------------------------

    def _terminal_size(self) -> tuple[int, int]:
        size = self._console.size
        return size.width, size.height

    def _panel_columns(self, width: int, model_count: int) -> int:
        if model_count <= 0:
            return 1
        target_width = MIN_PANEL_WIDTH
        if width < MIN_PANEL_WIDTH * min(model_count, 3):
            target_width = COMPACT_PANEL_WIDTH
        return _clamp(width // target_width, 1, model_count)

    def _active_benchmarks(self) -> set[str]:
        return {
            row["current_benchmark"]
            for row in self._rows.values()
            if row["status"] == "running" and row["current_benchmark"] != "-"
        }

    def _summary_limit(
        self,
        height: int,
        panel_rows: int,
        panel_height: int,
        *,
        log_height: int,
    ) -> int | None:
        available = height - HEADER_HEIGHT - log_height - (panel_rows * panel_height)
        if available < MIN_SUMMARY_VISIBLE_HEIGHT:
            return 0
        row_limit = available - SUMMARY_CHROME_HEIGHT
        if row_limit >= len(self._benchmarks):
            return None
        return max(1, row_limit)

    def _layout_plan(self, width: int, height: int) -> dict[str, int | bool | None]:
        columns = self._panel_columns(width, len(self._models))
        panel_rows = max(1, ceil(len(self._models) / columns))
        panel_width = width // columns if columns else width
        compact = panel_width < 38 or height < 30
        panel_height = COMPACT_PANEL_HEIGHT if compact else FULL_PANEL_HEIGHT
        log_height = LOG_HEIGHT if self._verbose and height >= 24 else 0

        summary_limit = self._summary_limit(
            height,
            panel_rows,
            panel_height,
            log_height=log_height,
        )
        if summary_limit == 0 and panel_height > DENSE_PANEL_HEIGHT:
            compact = True
            panel_height = DENSE_PANEL_HEIGHT
            summary_limit = self._summary_limit(
                height,
                panel_rows,
                panel_height,
                log_height=log_height,
            )

        if summary_limit == 0 and panel_rows * panel_height > height - HEADER_HEIGHT:
            columns = _clamp(width // DENSE_PANEL_WIDTH, 1, len(self._models))
            panel_rows = max(1, ceil(len(self._models) / columns))
            compact = True
            panel_height = DENSE_PANEL_HEIGHT
            summary_limit = self._summary_limit(
                height,
                panel_rows,
                panel_height,
                log_height=log_height,
            )

        return {
            "columns": columns,
            "panel_rows": panel_rows,
            "panel_height": panel_height,
            "compact": compact,
            "dense": panel_height == DENSE_PANEL_HEIGHT,
            "log_height": log_height,
            "summary_limit": summary_limit,
            "show_summary": summary_limit != 0,
        }

    def _build_layout(self) -> Layout:
        width, height = self._terminal_size()
        plan = self._layout_plan(width, height)
        columns = int(plan["columns"])
        panel_rows = int(plan["panel_rows"])
        panel_height = int(plan["panel_height"])
        compact = bool(plan["compact"])
        dense = bool(plan["dense"])
        summary_limit = plan["summary_limit"]
        log_height = int(plan["log_height"])
        show_summary = bool(plan["show_summary"])

        layout = Layout()
        layout.split_column(
            Layout(self._render_header(), name="header", size=HEADER_HEIGHT),
            Layout(name="main"),
            Layout(name="log", size=log_height, visible=self._verbose and log_height > 0),
        )

        main = layout["main"]
        main.split_column(
            Layout(name="panels", size=panel_rows * panel_height),
            Layout(name="summary", visible=show_summary),
        )

        panel_rows_layouts = []
        for row_index in range(panel_rows):
            row_models = self._models[
                row_index * columns : (row_index + 1) * columns
            ]
            row_layout = Layout(name=f"panel_row_{row_index}", size=panel_height)
            row_layout.split_row(
                *[
                    Layout(
                        self._render_model_panel(
                            model,
                            compact=compact,
                            dense=dense,
                        ),
                        name=f"model_{row_index}_{i}",
                        ratio=1,
                    )
                    for i, model in enumerate(row_models)
                ]
            )
            panel_rows_layouts.append(row_layout)
        if panel_rows_layouts:
            main["panels"].split_column(*panel_rows_layouts)

        if show_summary:
            main["summary"].update(
                self._render_summary_table(
                    limit=None if summary_limit is None else int(summary_limit),
                    width=width,
                )
            )

        if self._verbose:
            layout["log"].update(self._render_log_panel())

        return layout

    # -- header ---------------------------------------------------------------

    def _render_header(self) -> Panel:
        elapsed = format_duration(monotonic() - self._started_at)
        all_done = all(
            r["status"] in ("done", "error") for r in self._rows.values()
        )
        label = "GitBench complete" if all_done else "GitBench progress"
        text = (
            f"[bold]{label}[/] · {len(self._models)} model(s) · "
            f"{len(self._benchmarks)} benchmarks · elapsed {elapsed}"
        )
        if self._campaign_id:
            campaign_info = f"Campaign: {self._campaign_id}"
            if self._trials is not None:
                campaign_info += f" · {self._trials} trial(s)"
            if self._planned_attempts is not None:
                remaining = max(
                    0,
                    self._planned_attempts
                    - self._reused_attempts
                    - self._completed_attempts,
                )
                campaign_info += (
                    f" · planned {self._planned_attempts}"
                    f" · reused {self._reused_attempts}"
                    f" · new {self._new_attempts}"
                    f" · remaining {remaining}"
                )
            failure_parts = []
            if self._quality_failed_attempts:
                failure_parts.append(f"quality failed {self._quality_failed_attempts}")
            if self._infrastructure_failed_attempts:
                failure_parts.append(f"infra failed {self._infrastructure_failed_attempts}")
            if self._invalid_attempts:
                failure_parts.append(f"invalid {self._invalid_attempts}")
            if self._unscored_attempts:
                failure_parts.append(f"unscored {self._unscored_attempts}")
            if self._safety_blocked_attempts:
                failure_parts.append(f"safety blocked {self._safety_blocked_attempts}")
            if failure_parts:
                campaign_info += " · " + " · ".join(failure_parts)
            if self._publication_state:
                campaign_info += f" · {self._publication_state}"
            text += f"\n[cyan]{campaign_info}[/]"
        return Panel(text, style="bold blue")

    # -- model panels ---------------------------------------------------------

    def _render_model_panel(
        self,
        model: str,
        *,
        compact: bool = False,
        dense: bool = False,
    ) -> Panel:
        row = self._rows[model]
        total = row["fixtures_total"]

        # Status colour
        status_colours = {
            "pending": "dim",
            "queued": "yellow",
            "running": "cyan",
            "done": "green",
            "error": "red",
        }
        sc = status_colours.get(row["status"], "dim")

        # Progress bar
        if row["benchmarks_total"] > 0:
            b_pct = row["benchmarks_done"] / row["benchmarks_total"] * 100
        else:
            b_pct = 0.0
        bar_width = 10 if compact else 20
        bar = _progress_bar(b_pct, width=bar_width)

        # Pass rate
        if total > 0:
            pass_rate = row["passed"] / total
            rate_colour = _pass_rate_colour(pass_rate)
            rate_str = (
                f"[{rate_colour}]{pass_rate * 100:.1f}%[/] "
                f"({row['passed']}/{total})"
            )
        else:
            rate_str = "[dim]-[/]"

        # Current benchmark + fixture progress
        if row["status"] == "running" and row["fixtures_total"] > 0:
            current = (
                f"{row['current_benchmark']}  ·  "
                f"fixture {row['fixtures_done']}/{row['fixtures_total']}"
            )
        elif row["status"] == "done":
            current = f"{row['benchmarks_done']}/{row['benchmarks_total']} benchmarks"
        elif row["status"] == "pending":
            current = "[dim]waiting...[/]"
        else:
            current = row["current_benchmark"]
        if compact:
            if row["status"] == "running" and row["fixtures_total"] > 0:
                current = (
                    f"{self._abbreviate(row['current_benchmark'], 12)} "
                    f"{row['fixtures_done']}/{row['fixtures_total']}"
                )
            elif row["status"] == "done":
                current = f"{row['benchmarks_done']}/{row['benchmarks_total']} bench"
            elif row["status"] == "pending":
                current = "[dim]waiting[/]"

        # Tokens
        in_tok = human_readable(row["input_tokens"])
        out_tok = human_readable(row["output_tokens"])
        tokens_str = f"[dim]Tokens:[/] {in_tok}⇣  {out_tok}⇡"

        # Cost
        cost_str = f"[dim]Cost:[/] {human_readable_cost(row['cost_usd'])}"

        if dense:
            short_current = current.replace("  ·  ", " ")
            content = Text.from_markup(
                f"{rate_str}  ·  {short_current}  ·  {row['errors']} fail"
            )
        elif compact:
            content = Text.from_markup(
                f"{bar}  ·  {current}\n"
                f"{rate_str}  ·  {row['errors']} failures"
            )
        else:
            content = Text.from_markup(
                f"{bar}  ·  {current}\n"
                f"Pass: {rate_str}  ·  {row['errors']} failures\n"
                f"{tokens_str}  ·  {cost_str}"
            )

        title_model = self._abbreviate(model, 20 if dense else 28 if compact else 48)
        title = f"[bold {sc}]{title_model}[/]"
        if row["status"] == "done":
            title = f"[bold {sc}]✓ {title_model}[/]"
        elif row["status"] == "error":
            title = f"[bold {sc}]✗ {title_model}[/]"

        return Panel(content, title=title, border_style=sc)

    # -- summary table --------------------------------------------------------

    def _summary_benchmarks(self, limit: int | None) -> tuple[list[str], int]:
        if limit is None or limit >= len(self._benchmarks):
            return self._benchmarks, 0

        active = self._active_benchmarks()
        visible_limit = max(1, limit - 1)
        ordered = sorted(
            self._benchmarks,
            key=lambda bench: (bench not in active, self._benchmarks.index(bench)),
        )
        visible = ordered[:visible_limit]
        visible.sort(key=self._benchmarks.index)
        return visible, len(self._benchmarks) - len(visible)

    def _compact_summary(self, width: int | None) -> bool:
        if width is None:
            return False
        if len(self._models) > 4:
            return True
        full_width = 18 + (len(self._models) * 14)
        return len(self._models) > 2 and width < full_width

    def _abbreviate(self, value: str, max_len: int) -> str:
        if len(value) <= max_len:
            return value
        return value[: max(1, max_len - 1)] + "…"

    def _render_summary_table(
        self,
        *,
        limit: int | None = None,
        width: int | None = None,
    ) -> Table:
        if self._compact_summary(width):
            return self._render_compact_summary_table(limit=limit)

        table = Table(title="Live Summary", expand=True)
        table.add_column(
            "Benchmark",
            style="dim",
            no_wrap=True,
            max_width=22,
            overflow="ellipsis",
        )
        for model in self._models:
            table.add_column(
                model,
                justify="right",
                max_width=16,
                overflow="ellipsis",
                no_wrap=True,
            )

        visible_benchmarks, omitted = self._summary_benchmarks(limit)
        for bench in visible_benchmarks:
            row_values: list[str] = [bench]

            for model in self._models:
                br = self._bench_results[model].get(bench, {})
                if not br.get("done"):
                    # Is it running?
                    is_running = (
                        self._rows[model]["current_benchmark"] == bench
                        and self._rows[model]["status"] == "running"
                    )
                    if is_running:
                        row_values.append("[cyan]running[/]")
                    else:
                        row_values.append("[dim]...[/]")
                else:
                    total = br["total"]
                    passed = br["passed"]
                    rate = passed / total if total > 0 else 0.0
                    colour = _pass_rate_colour(rate)
                    row_values.append(
                        f"[{colour}]{rate:.1%}[/] [dim]({passed}/{total})[/]"
                    )

            table.add_row(*row_values)

        if omitted:
            omitted_row = [f"[dim]... {omitted} more[/]"]
            omitted_row.extend(["[dim]...[/]"] * len(self._models))
            table.add_row(*omitted_row)

        return table

    def _render_compact_summary_table(
        self,
        *,
        limit: int | None = None,
    ) -> Table:
        table = Table(title="Live Summary", expand=True, padding=(0, 1))
        table.add_column(
            "Benchmark",
            style="dim",
            no_wrap=True,
            max_width=20,
            overflow="ellipsis",
        )
        table.add_column("Done", justify="right", max_width=7, no_wrap=True)
        table.add_column(
            "Best",
            justify="right",
            max_width=16,
            overflow="ellipsis",
            no_wrap=True,
        )
        if len(self._models) >= 2:
            table.add_column("Range", justify="right", max_width=12, no_wrap=True)

        visible_benchmarks, omitted = self._summary_benchmarks(limit)
        for bench in visible_benchmarks:
            done_results: list[tuple[str, float]] = []
            running = False

            for model in self._models:
                br = self._bench_results[model].get(bench, {})
                if br.get("done"):
                    total = br["total"]
                    rate = br["passed"] / total if total > 0 else 0.0
                    done_results.append((model, rate))
                elif (
                    self._rows[model]["current_benchmark"] == bench
                    and self._rows[model]["status"] == "running"
                ):
                    running = True

            row_values = [bench, f"{len(done_results)}/{len(self._models)}"]
            if done_results:
                best_model, best_rate = max(done_results, key=lambda item: item[1])
                colour = _pass_rate_colour(best_rate)
                row_values.append(
                    f"[{colour}]{self._abbreviate(best_model, 8)} {best_rate:.0%}[/]"
                )
            elif running:
                row_values.append("[cyan]running[/]")
            else:
                row_values.append("[dim]...[/]")

            if len(self._models) >= 2:
                if len(done_results) >= 2:
                    rates = [rate for _, rate in done_results]
                    row_values.append(f"[dim]{min(rates):.0%}-{max(rates):.0%}[/]")
                else:
                    row_values.append("[dim]...[/]")

            table.add_row(*row_values)

        if omitted:
            omitted_row = [f"[dim]... {omitted} more[/]", "", ""]
            if len(self._models) >= 2:
                omitted_row.append("")
            table.add_row(*omitted_row)

        return table

    # -- log panel (verbose) --------------------------------------------------

    def _render_log_panel(self) -> Panel:
        if not self._log_lines:
            return Panel(
                Text.from_markup("[dim]No log entries yet[/]"),
                title="Verbose Log",
            )

        recent = list(self._log_lines)[-6:]
        content = "\n".join(recent)
        return Panel(content, title="Verbose Log", border_style="dim")

    # -- verbose log dump -----------------------------------------------------

    def _dump_verbose_log(self) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        log_dir = Path("gitbench-logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"verbose-{ts}.log"
        log_path.write_text("\n".join(self._log_lines) + "\n")
        self._console.print(f"Verbose log written to: {log_path}")

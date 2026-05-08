"""Colored summary table of benchmark results."""

import sys

from gitbench.ui.terminal import (
    BOLD,
    GREEN,
    RED,
    RESET,
    YELLOW,
    is_output_suppressed,
    should_use_colors,
)


class SummaryTable:
    """Render a colored summary table of benchmark results to stdout.

    Only renders when stdout is a TTY (colored output suppressed when piped).
    Uses ANSI escape codes when color is enabled, plain text otherwise.
    Color coding for pass@1: green >= 0.8, yellow >= 0.5, red < 0.5.
    """

    def __init__(self, results: list[dict], stream=None) -> None:
        """Initialise summary table with benchmark results.

        Args:
            results: List of BenchmarkResult dicts with benchmark, total,
                     passed, pass_at_k keys.
            stream: Output stream.  Defaults to sys.stdout.
        """
        self.stream = stream or sys.stdout
        self.results = results
        self.enabled = not is_output_suppressed(self.stream)
        self._color_enabled = should_use_colors(self.stream)

    def _color(self, text: str, color: str) -> str:
        if self._color_enabled:
            return f"{color}{text}{RESET}"
        return text

    def _bold(self, text: str) -> str:
        if self._color_enabled:
            return f"{BOLD}{text}{RESET}"
        return text

    @staticmethod
    def _pass_at_k_color(pass_at_k: float) -> str:
        if pass_at_k >= 0.8:
            return GREEN
        elif pass_at_k >= 0.5:
            return YELLOW
        else:
            return RED

    def render(self) -> str | None:
        """Render the summary table and write to stream.

        Returns:
            The table string, or None if stdout is not a TTY.
        """
        if not self.enabled:
            return None

        sorted_results = sorted(
            self.results, key=lambda r: r.get("benchmark", ""),
        )

        total_fixtures = sum(r.get("total", 0) for r in sorted_results)
        total_passed = sum(r.get("passed", 0) for r in sorted_results)
        overall_pass_at_k = (
            round(total_passed / total_fixtures, 4)
            if total_fixtures > 0 else 0.0
        )

        lines: list[str] = []

        header = f"{'Benchmark':<30} {'Pass@1':>8} {'Passed/Fail':>12}"
        lines.append(self._bold(header))
        lines.append("-" * 54)

        for r in sorted_results:
            benchmark = r.get("benchmark", "?")
            total = r.get("total", 0)
            passed = r.get("passed", 0)
            failed = total - passed
            pass_at_k = r.get("pass_at_k", 0.0)

            color = self._pass_at_k_color(pass_at_k)
            pass_at_k_colored = self._color(f"{pass_at_k:.1%}", color)
            passed_fail = f"{passed}/{failed}"

            lines.append(
                f"{benchmark:<30} {pass_at_k_colored:>8} {passed_fail:>12}",
            )

        lines.append("-" * 54)

        summary_color = self._pass_at_k_color(overall_pass_at_k)
        summary_pct = self._color(f"{overall_pass_at_k:.1%}", summary_color)
        total_str = f"{total_passed}/{total_fixtures}"

        lines.append(
            self._bold(
                f"{'TOTAL':<30} {summary_pct:>8} {total_str:>12}",
            ),
        )

        table = "\n".join(lines) + "\n"
        self.stream.write(table)
        self.stream.flush()
        return table

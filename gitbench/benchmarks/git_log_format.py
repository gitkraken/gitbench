"""Git log/formatting benchmark for GitBench."""

import logging
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)


class GitLogFormatBenchmark(Benchmark):
    """Benchmark for evaluating LLM git log querying and formatting reasoning.

    This benchmark sets up a repository with a known commit history and asks
    the model to answer questions about git log output (grep, author, date-range,
    oneline, merges, stat). Scored via default similarity scoring.
    """

    name = "git_log_format"
    description = "Query and interpret git log output with various formatting options"

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None) -> Score:
        """Score a git log answer against the expected value.

        Args:
            fixture: The fixture containing the expected answer.
            model_output: The answer provided by the model.
            repo_path: Optional path to the git repository (unused).

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def setup_fixture(self, fixture: Fixture) -> tuple[GitExecutor, str]:
        """Set up a git repository for a git log formatting scenario.

        Args:
            fixture: The fixture containing setup commands.

        Returns:
            A tuple of (GitExecutor, repo_path).
        """
        executor = GitExecutor()
        repo_path = executor.setup_repo(f"git_log_format_{fixture.id}", fixture.setup)
        logger.debug(f"Set up fixture {fixture.id} at {repo_path}")
        return executor, repo_path

    def get_diff(self, repo_path: str) -> str:
        """Get git log output in various formats for the repository.

        Returns git log with oneline, grep, author, date-range, merges, and stat
        views to give the model comprehensive commit history context.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Combined git log output for analysis.
        """
        commands = [
            (["git", "log", "--oneline", "--all"], "Git log (oneline)"),
            (["git", "log", "--format=%H %an %ae %ad %s", "--date=short", "--all"], "Git log (detailed)"),
            (["git", "log", "--merges", "--oneline", "--all"], "Git log (merges)"),
            (["git", "log", "--stat", "--all"], "Git log (stat)"),
        ]

        parts = []
        for cmd, label in commands:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            parts.append(f"{label}:\n{result.stdout}")

        return "\n".join(parts)

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and git log output.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git log output to include in the prompt.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\n{diff}"

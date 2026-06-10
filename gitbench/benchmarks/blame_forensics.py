"""Blame forensics benchmark for GitBench."""

import logging
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)


class BlameForensicsBenchmark(Benchmark):
    """Benchmark for evaluating LLM bug-introducing commit identification.

    This benchmark sets up a repository with a known commit history where
    a bug was introduced in a specific commit. The model must use git log
    and git blame analysis to identify the bug-introducing commit.
    Scored via exact_match comparison.
    """

    name = "blame_forensics"
    description = "Identify bug-introducing commits using git blame analysis"

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None, diff: str | None = None, prompt: str | None = None) -> Score:
        """Score a blame forensics answer against the expected value.

        Args:
            fixture: The fixture containing the expected commit message.
            model_output: The answer provided by the model.
            repo_path: Optional path to the git repository (unused).

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def get_diff(self, repo_path: str) -> str:
        """Get git log and blame output for the repository.

        Returns git log with oneline format and blame information
        to give the model context about commit history and line origins.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Combined git log and blame output for analysis.
        """
        parts = []

        # Git log with oneline format
        log_result = subprocess.run(
            ["git", "log", "--oneline", "--all"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        parts.append(f"Git log (oneline):\n{log_result.stdout}")

        files_result = subprocess.run(
            ["git", "ls-files"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        files = [line.strip() for line in files_result.stdout.splitlines() if line.strip()]
        for file_path in files:
            content_result = subprocess.run(
                ["git", "show", f"HEAD:{file_path}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            blame_result = subprocess.run(
                ["git", "blame", "--", file_path],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            parts.append(f"Current {file_path}:\n{content_result.stdout}")
            parts.append(f"Git blame for {file_path}:\n{blame_result.stdout}")

        return "\n".join(parts)

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and git output.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git log output to include in the prompt.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\n{diff}"

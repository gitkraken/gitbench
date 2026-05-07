"""Git show/inspect benchmark for GitBench."""

import logging
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)


class GitShowBenchmark(Benchmark):
    """Benchmark for evaluating LLM git show/inspect reasoning.

    This benchmark sets up a repository with known commits, tags, renames,
    and binary changes, then asks the model to inspect commit details, diffs,
    file state at revisions, and tag contents via git show. Scored via default
    similarity scoring.
    """

    name = "git_show"
    description = "Inspect commit details, diffs, tags, and file state using git show"

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None) -> Score:
        """Score a git show answer against the expected value.

        Args:
            fixture: The fixture containing the expected answer.
            model_output: The answer provided by the model.
            repo_path: Optional path to the git repository (unused).

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def setup_fixture(self, fixture: Fixture) -> tuple[GitExecutor, str]:
        """Set up a git repository for a git show scenario.

        Args:
            fixture: The fixture containing setup commands.

        Returns:
            A tuple of (GitExecutor, repo_path).
        """
        executor = GitExecutor()
        repo_path = executor.setup_repo(f"git_show_{fixture.id}", fixture.setup)
        logger.debug(f"Set up fixture {fixture.id} at {repo_path}")
        return executor, repo_path

    def get_diff(self, repo_path: str) -> str:
        """Get git show output for all commits and tags in the repository.

        Runs git show on all commits (--all) and all tags to give the model
        comprehensive inspection context.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Combined git show output for analysis.
        """
        parts = []

        # Show all commits
        result = subprocess.run(
            ["git", "show", "--stat", "--patch", "--all"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        parts.append(f"All commits:\n{result.stdout}")

        # Show all tags
        tags_result = subprocess.run(
            ["git", "tag", "-l"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        tags = [t.strip() for t in tags_result.stdout.strip().split("\n") if t.strip()]
        for tag in tags:
            tag_result = subprocess.run(
                ["git", "show", tag],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            parts.append(f"Tag '{tag}':\n{tag_result.stdout}")

        return "\n".join(parts)

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and git show output.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git show output to include in the prompt.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\n{diff}"

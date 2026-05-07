"""Merge conflict resolution benchmark for GitBench."""

import logging
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)


class MergeConflictsBenchmark(Benchmark):
    """Benchmark for evaluating merge conflict resolution.

    This benchmark sets up a real git repository with an unresolved
    merge conflict and asks the model to provide the correct resolved
    content for the conflicted file(s).
    """

    name = "merge_conflicts"
    description = "Resolve a merge conflict"

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None) -> Score:
        """Score a resolved file against the expected value.

        Args:
            fixture: The fixture containing the expected resolved content.
            model_output: The resolved file content produced by the model.

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def setup_fixture(self, fixture: Fixture) -> tuple[GitExecutor, str]:
        """Set up a git repository with an unresolved merge conflict.

        Args:
            fixture: The fixture containing setup commands.

        Returns:
            A tuple of (GitExecutor, repo_path).

        Raises:
            RuntimeError: If setup commands fail.
        """
        executor = GitExecutor()
        repo_path = executor.setup_repo(f"fixture_{fixture.id}", fixture.setup)
        logger.debug(f"Set up fixture {fixture.id} at {repo_path}")
        return executor, repo_path

    def get_diff(self, repo_path: str) -> str:
        """Get the content of files with merge conflict markers.

        Merge conflicts are not staged changes, so `git diff --staged`
        and `git diff HEAD` return nothing useful. Instead, we read
        the conflicted file(s) directly from the filesystem to capture
        the conflict markers (<<<<<<<, =======, >>>>>>>) so the model
        can see the full conflict state.

        Args:
            repo_path: Path to the git repository.

        Returns:
            The content of conflicted files with conflict markers included.
        """
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"git diff --name-only --diff-filter=U failed: {result.stderr}")
            return ""

        conflicted_files = result.stdout.strip().split("\n")
        if not conflicted_files or conflicted_files == [""]:
            logger.warning("No conflicted files found in repository")
            return ""

        output_parts = []
        for filename in conflicted_files:
            if not filename:
                continue
            file_path = Path(repo_path) / filename
            if file_path.exists():
                content = file_path.read_text()
                output_parts.append(f"--- {filename}\n{content}")

        return "\n\n".join(output_parts)

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and conflicted file content.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The conflicted file content to include in the prompt.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\nConflicted file content:\n{diff}"

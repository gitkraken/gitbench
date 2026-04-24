"""Git stash recovery benchmark for GitBench."""

import logging
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)


class StashRecoveryBenchmark(Benchmark):
    """Benchmark for evaluating git stash recovery reasoning.

    This benchmark sets up a real git repository with a scenario where
    changes have been stashed and asks the model to identify the correct
    stash entry to recover using git stash list output.
    """

    name = "stash_recovery"
    description = "Recover stashed changes using git stash list"

    def __init__(self):
        """Initialize the stash recovery benchmark."""
        self._loader = FixtureLoader()
        self._scorer = Scorer()

    def load_fixtures(self) -> list[Fixture]:
        """Load all git stash recovery fixtures.

        Returns:
            List of Fixture objects from the fixtures/stash_recovery directory.

        Raises:
            FileNotFoundError: If the fixtures directory doesn't exist.
        """
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "stash_recovery"
        logger.info(f"Loading fixtures from: {fixtures_dir}")

        fixtures = self._loader.load_dir(str(fixtures_dir))
        logger.info(f"Loaded {len(fixtures)} fixtures")
        return fixtures

    def score(self, fixture: Fixture, model_output: str) -> Score:
        """Score the model's recovery answer against the expected value.

        Args:
            fixture: The fixture containing the expected recovery answer.
            model_output: The stash reference or recovery instruction produced by the model.

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        return self._scorer.score(fixture, model_output)

    def setup_fixture(self, fixture: Fixture) -> tuple[GitExecutor, str]:
        """Set up a git repository for a stash recovery scenario.

        Args:
            fixture: The fixture containing setup commands.

        Returns:
            A tuple of (GitExecutor, repo_path).

        Raises:
            RuntimeError: If setup commands fail.
        """
        executor = GitExecutor()
        repo_path = executor.setup_repo(f"stash_recovery_{fixture.id}", fixture.setup)
        logger.debug(f"Set up fixture {fixture.id} at {repo_path}")
        return executor, repo_path

    def get_diff(self, repo_path: str) -> str:
        """Get git stash list output for the repository.

        Returns the stash list showing all stash entries, which gives
        the model the information needed to identify which stash contains
        the changes to recover.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Git stash list output showing all stash entries.
        """
        result = subprocess.run(
            ["git", "stash", "list"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"git stash list failed: {result.stderr}")
            return ""

        return result.stdout

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and git stash list output.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git stash list output to include in the prompt.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\nGit stash list:\n{diff}"

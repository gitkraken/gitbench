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

    def __init__(self):
        """Initialize the blame forensics benchmark."""
        self._loader = FixtureLoader()
        self._scorer = Scorer()

    def load_fixtures(self) -> list[Fixture]:
        """Load all blame forensics fixtures.

        Returns:
            List of Fixture objects from the fixtures/blame_forensics directory.
        """
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "blame_forensics"
        logger.info(f"Loading fixtures from: {fixtures_dir}")

        fixtures = self._loader.load_dir(str(fixtures_dir))
        logger.info(f"Loaded {len(fixtures)} fixtures")
        return fixtures

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None) -> Score:
        """Score a blame forensics answer against the expected value.

        Args:
            fixture: The fixture containing the expected commit message.
            model_output: The answer provided by the model.
            repo_path: Optional path to the git repository (unused).

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def setup_fixture(self, fixture: Fixture) -> tuple[GitExecutor, str]:
        """Set up a git repository for a blame forensics scenario.

        Args:
            fixture: The fixture containing setup commands.

        Returns:
            A tuple of (GitExecutor, repo_path).
        """
        executor = GitExecutor()
        repo_path = executor.setup_repo(f"blame_forensics_{fixture.id}", fixture.setup)
        logger.debug(f"Set up fixture {fixture.id} at {repo_path}")
        return executor, repo_path

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
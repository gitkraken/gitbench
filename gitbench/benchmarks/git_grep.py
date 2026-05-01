"""Git grep benchmark for GitBench."""

import logging
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)


class GitGrepBenchmark(Benchmark):
    """Benchmark for evaluating LLM git grep reasoning.

    This benchmark sets up a repository with known file content and asks
    the model to produce the correct git grep command or interpret grep
    output. Each fixture stores its grep command in a sentinel file
    (.grep_command) so get_diff() can execute the right invocation
    without hardcoded fixture logic.
    """

    name = "git_grep"
    description = "Search repository content using git grep"

    def __init__(self):
        """Initialize the git grep benchmark."""
        self._loader = FixtureLoader()
        self._scorer = Scorer()

    def load_fixtures(self) -> list[Fixture]:
        """Load all git grep fixtures.

        Returns:
            List of Fixture objects from the fixtures/git_grep directory.
        """
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "git_grep"
        logger.info(f"Loading fixtures from: {fixtures_dir}")

        fixtures = self._loader.load_dir(str(fixtures_dir))
        logger.info(f"Loaded {len(fixtures)} fixtures")
        return fixtures

    def setup_fixture(self, fixture: Fixture) -> tuple[GitExecutor, str]:
        """Set up a git repository for a git grep scenario.

        Args:
            fixture: The fixture containing setup commands.

        Returns:
            A tuple of (GitExecutor, repo_path).
        """
        executor = GitExecutor()
        repo_path = executor.setup_repo(f"git_grep_{fixture.id}", fixture.setup)
        logger.debug(f"Set up fixture {fixture.id} at {repo_path}")
        return executor, repo_path

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None) -> Score:
        """Score a git grep answer against the expected value.

        Args:
            fixture: The fixture containing the expected output.
            model_output: The grep output or command produced by the model.
            repo_path: Optional path to the git repository.

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def get_diff(self, repo_path: str) -> str:
        """Get git grep output for the repository.

        Reads the sentinel file .grep_command to determine which git grep
        invocation to run, then executes it and returns the output.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Git grep output for analysis.
        """
        sentinel = Path(repo_path) / ".grep_command"
        if not sentinel.exists():
            logger.warning(f"No .grep_command sentinel in {repo_path}")
            return ""

        grep_cmd = sentinel.read_text().strip()
        logger.debug(f"Executing grep command: {grep_cmd}")

        result = subprocess.run(
            grep_cmd,
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        output = result.stdout
        if result.stderr:
            logger.debug(f"Grep stderr: {result.stderr}")

        return output

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and grep output.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git grep output to include.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\n{diff}"

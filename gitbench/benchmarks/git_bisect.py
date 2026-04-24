"""Git bisect benchmark for GitBench."""

import logging
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)


class GitBisectBenchmark(Benchmark):
    """Benchmark for evaluating git bisect reasoning.

    This benchmark sets up a real git repository with a known bad commit
    in the history and asks the model to identify the bad commit hash.
    The model receives git log output and a test script that can identify
    which commits pass/fail the test.
    """

    name = "git_bisect"
    description = "Identify the bad commit in a git history via bisect"

    def __init__(self):
        """Initialize the git bisect benchmark."""
        self._loader = FixtureLoader()
        self._scorer = Scorer()

    def load_fixtures(self) -> list[Fixture]:
        """Load all git bisect fixtures.

        Returns:
            List of Fixture objects from the fixtures/git_bisect directory.

        Raises:
            FileNotFoundError: If the fixtures directory doesn't exist.
        """
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "git_bisect"
        logger.info(f"Loading fixtures from: {fixtures_dir}")

        fixtures = self._loader.load_dir(str(fixtures_dir))
        logger.info(f"Loaded {len(fixtures)} fixtures")
        return fixtures

    def score(self, fixture: Fixture, model_output: str) -> Score:
        """Score the model's identified bad commit against the expected value.

        Args:
            fixture: The fixture containing the expected bad commit.
            model_output: The bad commit hash or subject line produced by the model.

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        return self._scorer.score(fixture, model_output)

    def setup_fixture(self, fixture: Fixture) -> tuple[GitExecutor, str]:
        """Set up a git repository with a known bad commit in history.

        Args:
            fixture: The fixture containing setup commands.

        Returns:
            A tuple of (GitExecutor, repo_path).

        Raises:
            RuntimeError: If setup commands fail.
        """
        executor = GitExecutor()
        repo_path = executor.setup_repo(f"bisect_{fixture.id}", fixture.setup)
        logger.debug(f"Set up fixture {fixture.id} at {repo_path}")
        return executor, repo_path

    def get_diff(self, repo_path: str) -> str:
        """Get git log output and test results for the repository.

        Returns the commit log (newest first) along with the test script
        output showing which commits pass or fail the test. This gives
        the model the information needed to identify the bad commit.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Git log output and test script results.
        """
        parts = []

        # Get commit log (last 10 commits, newest first)
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if log_result.returncode != 0:
            logger.error(f"git log failed: {log_result.stderr}")
            return ""

        parts.append("Git commit history (newest first):")
        parts.append(log_result.stdout)

        # Get the test script path (fixture stores test_script as part of setup metadata)
        # We look for a test script in the repo root
        test_script = Path(repo_path) / "test.sh"
        if test_script.exists():
            parts.append("\nTest script output by commit:")
            # Run test script at current HEAD
            test_result = subprocess.run(
                ["bash", str(test_script)],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            status = "PASS" if test_result.returncode == 0 else "FAIL"
            parts.append(f"Current HEAD: {status} (exit code {test_result.returncode})")
            if test_result.stdout:
                parts.append(f"  stdout: {test_result.stdout.strip()}")
            if test_result.stderr:
                parts.append(f"  stderr: {test_result.stderr.strip()}")

        return "\n".join(parts)

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and git log/test output.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git log and test output to include in the prompt.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\n{diff}"
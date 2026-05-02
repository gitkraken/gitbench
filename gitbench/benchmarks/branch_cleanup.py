"""Branch cleanup benchmark for GitBench."""

import logging
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)


class BranchCleanupBenchmark(Benchmark):
    """Benchmark for evaluating LLM branch cleanup decisions.

    This benchmark provides a repository with multiple branches and asks
    the model to identify which branches should be deleted (fully merged
    into main). Scored via exact_match.
    """

    name = "branch_cleanup"
    description = "Identify branches to delete (fully merged into main)"

    def __init__(self):
        """Initialize the branch cleanup benchmark."""
        self._loader = FixtureLoader()
        self._scorer = Scorer()

    def load_fixtures(self) -> list[Fixture]:
        """Load all branch cleanup fixtures.

        Returns:
            List of Fixture objects from the fixtures/branch_cleanup directory.
        """
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "branch_cleanup"
        logger.info(f"Loading fixtures from: {fixtures_dir}")

        fixtures = self._loader.load_dir(str(fixtures_dir))
        logger.info(f"Loaded {len(fixtures)} fixtures")
        return fixtures

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None) -> Score:
        """Score a branch cleanup answer against the expected value.

        Args:
            fixture: The fixture containing the expected branch names.
            model_output: The branch names identified by the model.
            repo_path: Optional path to the git repository (unused for selection scoring).

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        if fixture.scoring.get("type") == "exact_match":
            return self._score_branch_selection(fixture, model_output, repo_path)

        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def _score_branch_selection(
        self,
        fixture: Fixture,
        model_output: str,
        repo_path: str | None = None,
    ) -> Score:
        """Score branch selection using set-based exact match.

        Parses both expected and model_output as newline-separated branch names,
        computes similarity as the fraction of expected branches found in model output,
        and returns detailed error listing missing and extra branches.

        Args:
            fixture: The fixture containing the expected branch names.
            model_output: The branch names identified by the model.
            repo_path: Optional path to the git repository (unused).

        Returns:
            A Score object with passed/failed status and set-based similarity.
        """
        expected_set = {
            line.strip() for line in fixture.expected.split("\n") if line.strip()
        }
        model_set = {
            line.strip() for line in model_output.split("\n") if line.strip()
        }

        matches = expected_set & model_set
        similarity = len(matches) / len(expected_set) if expected_set else 0.0
        threshold = fixture.scoring.get("threshold", 1.0)
        passed = similarity >= threshold

        missing = expected_set - model_set
        extra = model_set - expected_set

        error_parts = []
        if missing:
            error_parts.append(f"Missing: {sorted(missing)}")
        if extra:
            error_parts.append(f"Extra: {sorted(extra)}")
        error = "\n".join(error_parts) if error_parts else None

        return Score(
            fixture_id=fixture.id,
            passed=passed,
            similarity=round(similarity, 4),
            model_output=model_output,
            error=error,
        )

    def setup_fixture(self, fixture: Fixture) -> tuple[GitExecutor, str]:
        """Set up a git repository for a branch cleanup scenario.

        Args:
            fixture: The fixture containing setup commands.

        Returns:
            A tuple of (GitExecutor, repo_path).
        """
        executor = GitExecutor()
        repo_path = executor.setup_repo(f"branch_cleanup_{fixture.id}", fixture.setup)
        logger.debug(f"Set up fixture {fixture.id} at {repo_path}")
        return executor, repo_path

    def get_diff(self, repo_path: str) -> str:
        """Get the branch list for the repository.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Git branch output showing all branches with merge status,
            followed by branches merged into main.
        """
        lines = []

        # Show all branches with merge status
        result = subprocess.run(
            ["git", "branch", "-v"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            lines.append(result.stdout)

        # Show branches merged into main (explicit merge status context)
        merged_result = subprocess.run(
            ["git", "branch", "--merged", "main"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if merged_result.returncode == 0 and merged_result.stdout.strip():
            lines.append("\nMerged into main:\n")
            lines.append(merged_result.stdout)

        return "".join(lines)

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and branch list.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git branch output to include in the prompt.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\nBranches:\n{diff}"

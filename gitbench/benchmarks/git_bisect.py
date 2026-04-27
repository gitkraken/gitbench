"""Git bisect benchmark for GitBench."""

import logging
import re
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)

_HASH_RE = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)


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

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None) -> Score:
        """Score the model's identified bad commit against the expected value.

        Args:
            fixture: The fixture containing the expected bad commit.
            model_output: The bad commit hash or subject line produced by the model.

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        if fixture.scoring.get("type") == "bisect_regression":
            return self._score_bisect_regression(fixture, model_output, repo_path)
        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def _score_bisect_regression(
        self, fixture: Fixture, model_output: str, repo_path: str | None = None
    ) -> Score:
        """Score bisect answers against the live target commit.

        Fixture commit hashes are dynamic because real commits are created
        during setup. The fixture's expected value is the stable target subject;
        at score time we resolve it to the generated hash and accept either the
        subject or the generated hash/prefix.
        """
        if repo_path is None:
            return self._scorer.score(
                Fixture(
                    id=fixture.id,
                    description=fixture.description,
                    setup=fixture.setup,
                    prompt=fixture.prompt,
                    expected=fixture.expected,
                    scoring={
                        "type": "similarity",
                        "threshold": fixture.scoring.get("threshold", 0.5),
                    },
                ),
                model_output,
            )

        commits = self._commits(repo_path)
        target_hashes = {
            full_hash.lower()
            for full_hash, _, subject in commits
            if subject == fixture.expected
        }

        if not target_hashes:
            return Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output=model_output,
                error=f"Could not find target commit subject '{fixture.expected}'",
            )

        mentioned_hashes = [
            match.group(0).lower() for match in _HASH_RE.finditer(model_output)
        ]
        hash_match = any(
            target_hash.startswith(mentioned_hash)
            for target_hash in target_hashes
            for mentioned_hash in mentioned_hashes
        )
        subject_match = fixture.expected.lower() in model_output.lower()

        passed = hash_match or subject_match
        return Score(
            fixture_id=fixture.id,
            passed=passed,
            similarity=1.0 if passed else 0.0,
            model_output=model_output,
            error=None
            if passed
            else f"Expected target hash/prefix or subject '{fixture.expected}'",
        )

    def _commits(self, repo_path: str) -> list[tuple[str, str, str]]:
        """Return commits as (full_hash, short_hash, subject), newest first."""
        result = subprocess.run(
            ["git", "log", "--format=%H%x00%h%x00%s"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"git log failed: {result.stderr}")
            return []

        commits: list[tuple[str, str, str]] = []
        for line in result.stdout.splitlines():
            parts = line.split("\x00", maxsplit=2)
            if len(parts) == 3:
                commits.append((parts[0], parts[1], parts[2]))
        return commits

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

        commits = self._commits(repo_path)
        if not commits:
            return ""

        parts.append("Git commit history (newest first):")
        parts.extend(f"{short_hash} {subject}" for _, short_hash, subject in commits)

        test_script = Path(repo_path) / "test.sh"
        if test_script.exists():
            original_ref = self._current_ref(repo_path)
            parts.append("\nTest results by commit (oldest first):")

            try:
                for full_hash, short_hash, subject in reversed(commits):
                    checkout_result = subprocess.run(
                        [
                            "git",
                            "-c",
                            "advice.detachedHead=false",
                            "checkout",
                            "--quiet",
                            full_hash,
                        ],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                    )
                    if checkout_result.returncode != 0:
                        parts.append(
                            f"{short_hash} {subject}: ERROR checking out commit"
                        )
                        continue

                    test_result = subprocess.run(
                        ["bash", "test.sh"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                    )
                    status = "PASS" if test_result.returncode == 0 else "FAIL"
                    parts.append(
                        f"{short_hash} {subject}: {status} "
                        f"(exit code {test_result.returncode})"
                    )
            finally:
                subprocess.run(
                    ["git", "checkout", "--quiet", original_ref],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )

        return "\n".join(parts)

    def _current_ref(self, repo_path: str) -> str:
        """Return the current branch name when available, otherwise HEAD hash."""
        branch_result = subprocess.run(
            ["git", "symbolic-ref", "--short", "-q", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if branch_result.returncode == 0 and branch_result.stdout.strip():
            return branch_result.stdout.strip()

        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if hash_result.returncode == 0 and hash_result.stdout.strip():
            return hash_result.stdout.strip()

        return "HEAD"

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and git log/test output.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git log and test output to include in the prompt.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\n{diff}"

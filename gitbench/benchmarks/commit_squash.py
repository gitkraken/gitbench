"""Git commit squash benchmark for GitBench."""

import logging
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)


def _expected_commit_messages(expected: str) -> list[str]:
    """Parse the expected comma-separated commit messages for this benchmark."""
    return [item.strip() for item in expected.split(",") if item.strip()]


class CommitSquashBenchmark(Benchmark):
    """Benchmark for evaluating git commit squash reasoning.

    This benchmark sets up a real git repository with a commit history
    that contains commits that should be squashed for cleaner history,
    and asks the model to identify which commits to squash.
    """

    name = "commit_squash"
    description = "Identify commits to squash into a cleaner history"

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None, diff: str | None = None, prompt: str | None = None) -> Score:
        """Score the model's identified commits to squash against the expected value.

        Args:
            fixture: The fixture containing the expected commits to squash.
            model_output: The commits or commit hashes to squash produced by the model.

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        if fixture.scoring.get("type") == "commit_selection":
            return self._score_commit_selection(fixture, model_output, repo_path)

        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def _score_commit_selection(
        self,
        fixture: Fixture,
        model_output: str,
        repo_path: str | None = None,
    ) -> Score:
        """Score by detecting the expected commit messages in a free-form answer.

        Commit-squash answers are often verbose: strong answers include hashes,
        the target commit, and interactive-rebase instructions. Raw string
        similarity penalizes those useful details, so this scorer evaluates the
        actual selected commits listed in ``expected``.
        """
        expected_messages = _expected_commit_messages(fixture.expected)
        if not expected_messages:
            return Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output=model_output,
                error="No expected commit messages defined",
            )

        normalized_output = model_output.lower()
        hashes_by_message = self._commit_hashes_by_message(repo_path)
        found = [
            message
            for message in expected_messages
            if self._mentions_commit(message, hashes_by_message, normalized_output)
        ]
        extra = self._selected_extra_commits(
            model_output,
            expected_messages,
            hashes_by_message,
        )

        similarity = len(found) / len(expected_messages)
        threshold = fixture.scoring.get("threshold", 1.0)
        allow_extra = fixture.scoring.get("allow_extra", False)
        passed = similarity >= threshold and (allow_extra or not extra)
        missing = [message for message in expected_messages if message not in found]
        error_parts = []
        if missing:
            error_parts.append(f"Missing expected commit messages: {missing}")
        if extra:
            error_parts.append(f"Extra selected commit messages: {extra}")

        return Score(
            fixture_id=fixture.id,
            passed=passed,
            similarity=round(similarity, 4),
            model_output=model_output,
            error=None if passed else "; ".join(error_parts),
        )

    def _mentions_commit(
        self,
        message: str,
        hashes_by_message: dict[str, str],
        normalized_output: str,
    ) -> bool:
        """Return True when output mentions a commit by subject or hash."""
        if message.lower() in normalized_output:
            return True

        commit_hash = hashes_by_message.get(message)
        if not commit_hash:
            return False

        return commit_hash[:7] in normalized_output or commit_hash in normalized_output

    def _commit_hashes_by_message(self, repo_path: str | None) -> dict[str, str]:
        """Return full commit hashes keyed by subject for the fixture repo."""
        if repo_path is None:
            return {}

        result = subprocess.run(
            ["git", "log", "--format=%H%x00%s"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.debug(f"git log for commit selection scoring failed: {result.stderr}")
            return {}

        hashes_by_message = {}
        for line in result.stdout.splitlines():
            commit_hash, _, subject = line.partition("\0")
            if commit_hash and subject:
                hashes_by_message[subject] = commit_hash.lower()
        return hashes_by_message

    def _selected_extra_commits(
        self,
        model_output: str,
        expected_messages: list[str],
        hashes_by_message: dict[str, str],
    ) -> list[str]:
        """Find clearly selected non-expected commits in model output.

        Commit-selection answers can mention target/base commits as explanatory
        context. To avoid rejecting that useful context, this only treats bullet
        lines and comma-separated command-like lists as selected commits.
        """
        expected_set = {message.lower() for message in expected_messages}
        selected_regions = []
        for line in model_output.splitlines():
            stripped = line.strip()
            if stripped.startswith(("-", "*")) or "," in stripped:
                selected_regions.append(stripped.lower())

        extras = []
        for message, commit_hash in hashes_by_message.items():
            if message.lower() in expected_set:
                continue
            abbreviated_hash = commit_hash[:7]
            if any(
                message.lower() in region
                or commit_hash in region
                or abbreviated_hash in region
                for region in selected_regions
            ):
                extras.append(message)

        return extras

    def get_diff(self, repo_path: str) -> str:
        """Get git log output for the repository.

        Returns the commit log (newest first) showing the history
        that the model needs to analyze to identify commits to squash.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Git log output showing commit history.
        """
        # Get commit log (newest first)
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"git log failed: {result.stderr}")
            return ""

        return result.stdout

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and git log output.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git log output to include in the prompt.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\nGit commit history (newest first):\n{diff}"

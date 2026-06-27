"""Git commit squash benchmark for GitBench."""

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


def _expected_commit_messages(expected: str) -> list[str]:
    """Parse expected commit subject lines for this benchmark.

    New fixtures store one subject per line. Comma-separated expected values are
    still accepted for older fixtures during the migration window.
    """
    lines = [line.strip() for line in expected.splitlines() if line.strip()]
    if len(lines) > 1:
        return lines
    if len(lines) == 1 and "," not in lines[0]:
        return lines
    return [item.strip() for item in expected.split(",") if item.strip()]


def _selected_commit_messages(model_output: str) -> list[str]:
    """Parse selected subject lines from model output.

    The canonical answer is one subject per line. Bullet markers are tolerated,
    and a single comma-separated line remains accepted for older outputs.
    """
    lines = [
        _strip_selection_bullet(line)
        for line in model_output.splitlines()
        if line.strip()
    ]
    if len(lines) == 1 and "," in lines[0]:
        return [item.strip() for item in lines[0].split(",") if item.strip()]
    return lines


def _strip_selection_bullet(line: str) -> str:
    return re.sub(r"^\s*[-*]\s+", "", line.strip()).strip()


def _selection_key(value: str) -> str:
    return value.strip().lower()


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
        """Score by comparing selected subject lines to expected subjects.

        The deterministic contract is the selected subject lines from
        ``expected``. Hashes alone are not sufficient.
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

        selected_messages = _selected_commit_messages(model_output)
        selected_keys = {_selection_key(message) for message in selected_messages}
        hashes_by_message = self._commit_hashes_by_message(repo_path)
        found = [
            message
            for message in expected_messages
            if _selection_key(message) in selected_keys
        ]
        extra = self._selected_extra_commits(
            selected_messages,
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
        selected_messages: list[str],
        expected_messages: list[str],
        hashes_by_message: dict[str, str],
    ) -> list[str]:
        """Find selected non-expected commits in parsed answer lines."""
        expected_set = {_selection_key(message) for message in expected_messages}

        extras = []
        for selected in selected_messages:
            selected_key = _selection_key(selected)
            if selected_key in expected_set:
                continue
            extras.append(
                self._commit_display_for_selection(selected_key, selected, hashes_by_message)
            )

        return extras

    def _commit_display_for_selection(
        self,
        selected_key: str,
        selected: str,
        hashes_by_message: dict[str, str],
    ) -> str:
        for message, commit_hash in hashes_by_message.items():
            message_key = _selection_key(message)
            abbreviated_hash = commit_hash[:7]
            if (
                selected_key == message_key
                or message_key in selected_key
                or commit_hash in selected_key
                or abbreviated_hash in selected_key
            ):
                return message
        return selected.strip()

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

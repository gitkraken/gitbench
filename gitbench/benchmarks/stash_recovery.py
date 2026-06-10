"""Git stash recovery benchmark for GitBench."""

import logging
import re
import subprocess
from pathlib import Path

from gitbench.harness.benchmark import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)

_STASH_REF_RE = re.compile(r"stash@\{\d+\}")


class StashRecoveryBenchmark(Benchmark):
    """Benchmark for evaluating git stash recovery reasoning.

    This benchmark sets up a real git repository with a scenario where
    changes have been stashed and asks the model to identify the correct
    stash entry to recover using git stash list output.
    """

    name = "stash_recovery"
    description = "Recover stashed changes using git stash list"

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None, diff: str | None = None, prompt: str | None = None) -> Score:
        """Score the model's recovery answer against the expected value.

        Args:
            fixture: The fixture containing the expected recovery answer.
            model_output: The stash reference or recovery instruction produced by the model.
            repo_path: Optional path to the git repository (for state_assertions scoring).

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        if fixture.scoring.get("type") == "stash_recovery":
            return self._score_stash_recovery(fixture, model_output)
        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def _score_stash_recovery(self, fixture: Fixture, model_output: str) -> Score:
        """Score stash recovery answers by exact stash reference.

        Similarity scoring is too permissive for stash refs: stash@{0} and
        stash@{1} differ by one character but identify different entries.
        Accept a correct reference anywhere in a command, such as
        `git stash apply stash@{1}`.
        """
        expected = fixture.expected.strip()
        refs = _STASH_REF_RE.findall(model_output)
        passed = expected in refs or model_output.strip() == expected

        return Score(
            fixture_id=fixture.id,
            passed=passed,
            similarity=1.0 if passed else 0.0,
            model_output=model_output,
            error=None if passed else f"Expected stash reference '{expected}'",
        )

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
        list_result = subprocess.run(
            ["git", "stash", "list"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if list_result.returncode != 0:
            logger.error(f"git stash list failed: {list_result.stderr}")
            return ""

        parts = [list_result.stdout.rstrip()]
        refs = _STASH_REF_RE.findall(list_result.stdout)

        if refs:
            parts.append("\nStash details:")

        for ref in refs:
            show_result = subprocess.run(
                ["git", "stash", "show", "--patch", "--include-untracked", ref],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if show_result.returncode != 0:
                show_result = subprocess.run(
                    ["git", "stash", "show", "--patch", ref],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )

            parts.append(f"\n{ref}:")
            if show_result.returncode == 0 and show_result.stdout.strip():
                parts.append(show_result.stdout.rstrip())
            else:
                parts.append("(no patch details available)")

        return "\n".join(parts).strip() + "\n"

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and git stash list output.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git stash list output to include in the prompt.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\nGit stash list:\n{diff}"

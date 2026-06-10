"""Git show/inspect benchmark for GitBench."""

import logging
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)


class GitShowBenchmark(Benchmark):
    """Benchmark for evaluating LLM git show/inspect reasoning.

    This benchmark sets up a repository with known commits, tags, renames,
    and binary changes, then asks the model to inspect commit details, diffs,
    file state at revisions, and tag contents via git show. Scored via default
    similarity scoring.
    """

    name = "git_show"
    description = "Inspect commit details, diffs, tags, and file state using git show"

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None, diff: str | None = None, prompt: str | None = None) -> Score:
        """Score a git show answer against the expected value.

        Args:
            fixture: The fixture containing the expected answer.
            model_output: The answer provided by the model.
            repo_path: Optional path to the git repository (unused).

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def _score_commit_hash_by_subject(
        self,
        fixture: Fixture,
        model_output: str,
        repo_path: str | None,
    ) -> Score:
        """Score an answer against a commit's full hash resolved from the repo."""
        if repo_path is None:
            return Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output=model_output,
                error="repo_path required for commit_hash_by_subject scoring",
            )

        subject = fixture.scoring.get("subject")
        if not subject:
            return Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output=model_output,
                error="commit_hash_by_subject scoring requires subject",
            )

        result = subprocess.run(
            ["git", "log", "--format=%H%x00%s"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output=model_output,
                error=f"git log failed: {result.stderr.strip()}",
            )

        expected_hash = None
        for line in result.stdout.splitlines():
            commit_hash, _, commit_subject = line.partition("\0")
            if commit_subject == subject:
                expected_hash = commit_hash
                break

        if expected_hash is None:
            return Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output=model_output,
                error=f"Could not find commit with subject: {subject}",
            )

        match = model_output.strip() == expected_hash
        return Score(
            fixture_id=fixture.id,
            passed=match,
            similarity=1.0 if match else 0.0,
            model_output=model_output,
            error=None if match else f"Expected full hash {expected_hash}, got {model_output.strip()}",
        )

    def get_diff(self, repo_path: str) -> str:
        """Get git show output for all commits and tags in the repository.

        Runs git show on all commits (--all) and all tags to give the model
        comprehensive inspection context.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Combined git show output for analysis.
        """
        parts = []

        # Show all commits
        result = subprocess.run(
            ["git", "show", "--stat", "--patch", "--all"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        parts.append(f"All commits:\n{result.stdout}")

        # Show all tags
        tags_result = subprocess.run(
            ["git", "tag", "-l"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        tags = [t.strip() for t in tags_result.stdout.strip().split("\n") if t.strip()]
        for tag in tags:
            tag_result = subprocess.run(
                ["git", "show", tag],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            parts.append(f"Tag '{tag}':\n{tag_result.stdout}")

        return "\n".join(parts)

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and git show output.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git show output to include in the prompt.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\n{diff}"

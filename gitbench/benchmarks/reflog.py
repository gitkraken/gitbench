"""Git reflog benchmark for GitBench."""

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
_REFLOG_SELECTOR_RE = re.compile(r"\bHEAD@\{\d+\}")


class ReflogBenchmark(Benchmark):
    """Benchmark for evaluating git reflog reasoning.

    This benchmark sets up a real git repository with a scenario where
    commits have been lost (reset, rebase, amend) and asks the model
    to identify the correct commit state or recovery instruction using
    git reflog output.
    """

    name = "reflog"
    description = "Recover lost commits using git reflog"

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None) -> Score:
        """Score the model's recovery answer against the expected value.

        Args:
            fixture: The fixture containing the expected recovery answer.
            model_output: The commit hash or recovery instruction produced by the model.

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        if fixture.scoring.get("type") == "reflog_recovery":
            return self._score_reflog_recovery(fixture, model_output, repo_path)
        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def _score_reflog_recovery(
        self, fixture: Fixture, model_output: str, repo_path: str | None = None
    ) -> Score:
        """Score reflog answers against the dynamic commit hash in the repo.

        Reflog fixture commit hashes are intentionally not static: the setup
        creates real commits, so timestamps change the SHA. The stable fixture
        expected value is the target commit message; at score time we resolve
        that message to the live reflog hash and accept answers that identify
        the target hash or a HEAD@{n} selector pointing at that hash.
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

        entries = self._parse_reflog_entries(repo_path)
        target_hashes = {
            entry_hash
            for entry_hash, _, line in entries
            if fixture.expected in line
        }

        if not target_hashes:
            return Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output=model_output,
                error=f"Could not find target reflog entry for '{fixture.expected}'",
            )

        selector_to_hash = {selector: entry_hash for entry_hash, selector, _ in entries}
        mentioned_hashes = [
            m.group(0).lower() for m in _HASH_RE.finditer(model_output)
        ]
        mentioned_selectors = [
            m.group(0) for m in _REFLOG_SELECTOR_RE.finditer(model_output)
        ]

        hash_match = any(
            target_hash.startswith(mentioned_hash)
            for target_hash in target_hashes
            for mentioned_hash in mentioned_hashes
        )
        selector_match = any(
            selector_to_hash.get(selector) in target_hashes
            for selector in mentioned_selectors
        )
        message_match = (
            fixture.scoring.get("accept_message", False)
            and fixture.expected in model_output
        )

        passed = hash_match or selector_match or message_match
        error = None
        if not passed:
            error = (
                "Expected output to mention target hash prefix/full hash"
                f" or matching HEAD@{{n}} selector for '{fixture.expected}'"
            )

        return Score(
            fixture_id=fixture.id,
            passed=passed,
            similarity=1.0 if passed else 0.0,
            model_output=model_output,
            error=error,
        )

    def _parse_reflog_entries(self, repo_path: str) -> list[tuple[str, str, str]]:
        """Return reflog entries as (hash, selector, line)."""
        entries: list[tuple[str, str, str]] = []
        for line in self.get_diff(repo_path).splitlines():
            hash_match = _HASH_RE.match(line)
            selector_match = _REFLOG_SELECTOR_RE.search(line)
            if hash_match and selector_match:
                entries.append(
                    (hash_match.group(0).lower(), selector_match.group(0), line)
                )
        return entries

    def setup_fixture(self, fixture: Fixture) -> tuple[GitExecutor, str]:
        """Set up a git repository for a reflog recovery scenario.

        Args:
            fixture: The fixture containing setup commands.

        Returns:
            A tuple of (GitExecutor, repo_path).

        Raises:
            RuntimeError: If setup commands fail.
        """
        executor = GitExecutor()
        repo_path = executor.setup_repo(f"reflog_{fixture.id}", fixture.setup)
        logger.debug(f"Set up fixture {fixture.id} at {repo_path}")
        return executor, repo_path

    def get_diff(self, repo_path: str) -> str:
        """Get git reflog output for the repository.

        Returns the reflog showing all reference updates including
        commits that have been lost from the main history but are
        still reachable via reflog. This gives the model the information
        needed to identify the correct commit to recover.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Git reflog output showing commit history including lost commits.
        """
        result = subprocess.run(
            ["git", "reflog", "show", "--no-abbrev"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"git reflog show --no-abbrev failed: {result.stderr}")
            # Fall back to simple reflog
            result = subprocess.run(
                ["git", "reflog"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error(f"git reflog failed: {result.stderr}")
                return ""

        return result.stdout

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and git reflog output.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git reflog output to include in the prompt.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\nGit reflog:\n{diff}"

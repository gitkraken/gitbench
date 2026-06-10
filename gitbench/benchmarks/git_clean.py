"""Git clean benchmark for GitBench."""

import logging
import os
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import GitExecutor

logger = logging.getLogger(__name__)


class GitCleanBenchmark(Benchmark):
    """Benchmark for evaluating LLM git clean commands.

    This benchmark provides a repository with various untracked files,
    directories, and ignored files, then asks the model to produce the
    correct git clean command(s) for a given cleanup scenario.
    The model's output (commands) is executed in the repo, then state
    assertions are checked.
    """

    name = "git_clean"
    description = "Clean untracked and ignored files from a repository"

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None, diff: str | None = None, prompt: str | None = None) -> Score:
        """Score the fixture by executing model output then checking state.

        Args:
            fixture: The fixture with expected state assertions.
            model_output: The git commands output by the model.
            repo_path: Path to the git repository.

        Returns:
            A Score object based on state assertion results.
        """
        if repo_path is None:
            return Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output=model_output,
                error="repo_path required for state_assertions scoring",
            )

        # Execute the model's commands
        self.execute_model_output(repo_path, model_output, fixture)

        # Score based on state assertions
        return self._scorer.score(fixture, model_output, repo_path=repo_path)

    def execute_model_output(self, repo_path: str, model_output: str, fixture: Fixture) -> None:
        """Execute the model's output as shell commands.

        Runs each line as a command. Stops on first failure.

        Args:
            repo_path: Path to the git repository.
            model_output: The model's command output.
            fixture: The fixture being scored.
        """
        lines = [line.strip() for line in model_output.strip().split("\n") if line.strip()]

        for line in lines:
            logger.info(f"Executing: {line}")
            try:
                env = os.environ.copy()
                env["GIT_ALLOW_PROTOCOL"] = "file:git:ssh:https"
                result = subprocess.run(
                    line,
                    shell=True,
                    cwd=repo_path,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    logger.warning(
                        f"Command failed (exit {result.returncode}): {line}\n"
                        f"stderr: {result.stderr}"
                    )
                    # Stop on failure
                    return
                if result.stderr:
                    logger.debug(f"Command stderr: {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.error(f"Command timed out: {line}")
                return
            except Exception as e:
                logger.error(f"Command error: {line}: {e}")
                return

    def get_diff(self, repo_path: str) -> str:
        """Get the current status showing untracked and ignored files.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Git status output showing untracked/ignored files.
        """
        status_result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        # Show untracked files
        untracked_result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        # Show ignored files
        ignored_result = subprocess.run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        output = f"Status:\n{status_result.stdout or '(clean)'}\n"
        output += f"Untracked files:\n{untracked_result.stdout or '(none)'}\n"
        output += f"Ignored files:\n{ignored_result.stdout or '(none)'}"
        return output

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the prompt with the fixture prompt and repo status.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git status output to include.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\n{diff}"

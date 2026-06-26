"""Worktree usage benchmark for GitBench."""

import logging
import os
import subprocess
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import (
    CommandAnswerNormalizationError,
    Scorer,
    normalize_command_answer,
)
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import FixtureGenerationContext, GitExecutor

logger = logging.getLogger(__name__)


class WorktreeUsageBenchmark(Benchmark):
    """Benchmark for evaluating LLM git worktree management.

    This benchmark provides a repository and asks the model to perform
    git worktree operations (add, remove, prune, lock, unlock, list).
    The model's output (commands) is executed in the repo, then state
    assertions are checked.
    """

    name = "worktree_usage"
    description = "Manage git worktrees for parallel development"

    def __init__(self, fixtures_root=None) -> None:
        super().__init__(fixtures_root=fixtures_root)
        self._current_executor: GitExecutor | None = None

    def setup_fixture(
        self,
        fixture: Fixture,
        *,
        fixture_generation_context: FixtureGenerationContext | None = None,
    ) -> tuple[GitExecutor, str]:
        """Set up a git repository for a worktree usage scenario.

        Creates the repo and registers cleanup handlers.

        Args:
            fixture: The fixture containing setup commands.
            fixture_generation_context: Optional deterministic context for
                reproducible fixture generation.

        Returns:
            A tuple of (GitExecutor, repo_path).
        """
        executor = GitExecutor(
            fixture_generation_context=fixture_generation_context,
        )
        repo_path = executor.setup_repo(f"worktree_usage_{fixture.id}", fixture.setup)

        # Store executor reference so execute_model_output can use it for cleanup
        self._current_executor = executor

        # Register sibling directories for cleanup (bare remotes, temp clones)
        parent_dir = os.path.dirname(repo_path)
        for sibling_name in ["remote-bare", "remote", "clone"]:
            sibling_path = os.path.join(parent_dir, sibling_name)
            executor.register_cleanup(sibling_path)

        logger.debug(f"Set up fixture {fixture.id} at {repo_path}")
        return executor, repo_path

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None, diff: str | None = None, prompt: str | None = None) -> Score:
        """Score the fixture by executing model output then checking state.

        Args:
            fixture: The fixture with expected state assertions.
            model_output: The git commands output by the model.
            repo_path: Path to the git repository.

        Returns:
            A Score object based on state assertion results.
        """
        if fixture.scoring.get("type") == "command_equivalence":
            return self._scorer.score(fixture, model_output, repo_path=repo_path)

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

        Runs each line as a command. After executing, discovers created worktrees
        via 'git worktree list --porcelain' and registers them for cleanup.

        Args:
            repo_path: Path to the git repository.
            model_output: The model's command output.
            fixture: The fixture being scored.
        """
        try:
            lines = normalize_command_answer(model_output)
        except CommandAnswerNormalizationError as e:
            logger.warning(str(e))
            return

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

        # Discover worktrees created by the commands and register for cleanup
        self._discover_and_register_worktrees(repo_path)

    def _discover_and_register_worktrees(self, repo_path: str) -> None:
        """Discover worktrees via git worktree list --porcelain and register cleanup.

        Args:
            repo_path: Path to the git repository.
        """
        if self._current_executor is None:
            return

        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.warning(f"git worktree list failed: {result.stderr}")
                return

            # Parse porcelain output. Each worktree block starts with a line
            # containing the worktree path (absolute). Example:
            #   worktree /path/to/worktree
            #   branch refs/heads/main
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line.startswith("worktree "):
                    worktree_path = line[len("worktree ") :].strip()
                    # Skip the main worktree (the repo itself)
                    realpath = os.path.realpath(worktree_path)
                    repo_realpath = os.path.realpath(repo_path)
                    if realpath != repo_realpath:
                        logger.info(f"Discovering worktree: {worktree_path}")
                        self._current_executor.register_cleanup(worktree_path)
        except Exception as e:
            logger.error(f"Error discovering worktrees: {e}")

    def get_diff(self, repo_path: str) -> str:
        """Get the current worktree list output.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Git worktree list --porcelain output.
        """
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        except Exception as e:
            logger.error(f"Error getting worktree list: {e}")
        return "(no worktrees)"

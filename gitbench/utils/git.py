"""Git executor for sandboxed git command execution."""

import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FixtureGenerationContext:
    """Deterministic inputs used to make generated Git history reproducible.

    The same context (version, seed, author/committer identity, timestamp,
    timezone, and locale) must produce identical Git objects across campaign
    trials.
    """

    version: str = ""
    seed: int | None = None
    author_name: str = "GitBench Fixture Author"
    author_email: str = "fixture@gitbench.local"
    committer_name: str = "GitBench Fixture Committer"
    committer_email: str = "fixture@gitbench.local"
    date: str = "2020-01-01T00:00:00+0000"
    tz: str = "UTC"
    locale: str = "C.UTF-8"

    def git_env(self) -> dict[str, str]:
        """Return a copy of the current process environment with stable Git inputs."""
        env = os.environ.copy()
        env.update(
            {
                "GIT_AUTHOR_NAME": self.author_name,
                "GIT_AUTHOR_EMAIL": self.author_email,
                "GIT_COMMITTER_NAME": self.committer_name,
                "GIT_COMMITTER_EMAIL": self.committer_email,
                "GIT_AUTHOR_DATE": self.date,
                "GIT_COMMITTER_DATE": self.date,
                "TZ": self.tz,
                "LC_ALL": self.locale,
                "LANG": self.locale,
            }
        )
        return env


class GitExecutor:
    """Executes git commands in an isolated temporary directory."""

    def __init__(
        self,
        base_dir: str | None = None,
        fixture_generation_context: FixtureGenerationContext | None = None,
    ):
        """Initialize the git executor.

        Args:
            base_dir: Optional base directory for temp repos.
                     Defaults to system temp directory.
            fixture_generation_context: Optional deterministic context. When
                provided, all git commands run with stable author/committer
                identities, timestamps, timezone, and locale so repeated
                fixture generation produces the same Git object identities.

        Raises:
            RuntimeError: If git is not available in PATH.
        """
        self._base_dir = base_dir or tempfile.gettempdir()
        self._workspace_path: str | None = None
        self._repo_path: str | None = None
        self._cleanup_targets: list[str] = []
        self._created_branches: list[str] = []
        self._fixture_generation_context = fixture_generation_context
        self._env = (
            fixture_generation_context.git_env()
            if fixture_generation_context
            else os.environ.copy()
        )

        # Verify git is available
        git_path = shutil.which("git")
        if not git_path:
            raise RuntimeError(
                "git command not found in PATH. GitBench requires git to be installed."
            )
        self._git_path = git_path

    @property
    def repo_path(self) -> str | None:
        """Return the current repo path, or None if not set up."""
        return self._repo_path

    def setup_repo(self, name: str, commands: list[str]) -> str:
        """Create a temp repo and run setup commands.

        Args:
            name: Unique name for this repo (used as subdirectory name).
            commands: List of git/shell commands to run as setup.
                      Each command is run with cwd set to the repo directory.

        Returns:
            Absolute path to the created repository.

        Raises:
            RuntimeError: If a command fails (non-zero exit).
        """
        if self._workspace_path is not None:
            self.cleanup()

        workspace_dir = Path(tempfile.mkdtemp(prefix=f"{name}_", dir=self._base_dir))
        self._workspace_path = str(workspace_dir)
        repo_dir = workspace_dir / name
        repo_dir.mkdir(parents=True, exist_ok=True)
        self._repo_path = str(repo_dir)

        for command in commands:
            # Track branch creation commands
            is_branch, branch_name = self._is_branch_creation(command)
            if is_branch and branch_name:
                self._created_branches.append(branch_name)
                logger.debug(f"Tracking branch creation: {branch_name}")

            # git merge, rebase, and cherry-pick return exit code 1 when there are
            # conflicts, which is the expected outcome for conflict fixtures.
            if (
                command.startswith("git merge")
                or command.startswith("git rebase")
                or command.startswith("git cherry-pick")
            ):
                self._run_command_permissive(command)
            else:
                self._run_command(command)

        logger.debug(f"Repo setup complete: {self._repo_path}")
        return self._repo_path

    def _run_command(self, command: str) -> None:
        """Run a single command in the repo directory.

        Args:
            command: The command string to execute.

        Raises:
            RuntimeError: If the command returns non-zero exit.
        """
        result = subprocess.run(
            command,
            shell=True,
            cwd=self._repo_path,
            capture_output=True,
            text=True,
            env=self._env,
        )

        if result.returncode != 0:
            logger.error(
                f"Command failed: {command}\n"
                f"Exit code: {result.returncode}\n"
                f"stderr: {result.stderr}"
            )
            raise RuntimeError(
                f"Command failed in {self._repo_path}: {command}\n"
                f"stderr: {result.stderr}"
            )

        if result.stderr:
            logger.debug(f"Command stderr: {result.stderr}")

    def _run_command_permissive(self, command: str) -> None:
        """Run a single command that may return exit code 1 (e.g., git merge).

        Args:
            command: The command string to execute.

        Raises:
            RuntimeError: If the command returns non-zero AND non-1 exit.
        """
        result = subprocess.run(
            command,
            shell=True,
            cwd=self._repo_path,
            capture_output=True,
            text=True,
            env=self._env,
        )

        # git merge, rebase, and cherry-pick return 1 when there are conflicts (expected)
        if result.returncode not in (0, 1):
            logger.error(
                f"Command failed: {command}\n"
                f"Exit code: {result.returncode}\n"
                f"stderr: {result.stderr}"
            )
            raise RuntimeError(
                f"Command failed in {self._repo_path}: {command}\n"
                f"stderr: {result.stderr}"
            )

        if result.stderr:
            logger.debug(f"Command stderr: {result.stderr}")

    def _is_branch_creation(self, command: str) -> tuple[bool, str | None]:
        """Detect branch creation commands and extract the branch name.

        Args:
            command: The command string to parse.

        Returns:
            A tuple of (is_branch_creation, branch_name).
            branch_name is None if not a branch creation command.
        """
        tokens = command.split()

        # git checkout -b <branch>
        if (
            len(tokens) >= 4
            and tokens[0] == "git"
            and tokens[1] == "checkout"
            and tokens[2] == "-b"
        ):
            return (True, tokens[3])

        # git branch <name> (not -d, -D, --delete, -m, -M, -r, -l, etc.)
        if len(tokens) >= 3 and tokens[0] == "git" and tokens[1] == "branch":
            branch_name = tokens[2]
            # Skip flags that make this not a creation
            if branch_name.startswith("-"):
                return (False, None)
            return (True, branch_name)

        return (False, None)

    def register_cleanup(self, path: str) -> None:
        """Register an additional path for cleanup.

        Use for directories created outside the main repo (e.g., worktrees,
        bare repos for submodules).

        Args:
            path: Absolute path to clean up during cleanup().
        """
        self._cleanup_targets.append(path)

    def cleanup(self) -> None:
        """Remove the temporary repository directory tree and registered targets.

        Does nothing if no repo has been set up.
        """
        import shutil as shutil_cleanup

        # Delete tracked branches before removing the repo directory
        for branch_name in self._created_branches:
            if self._repo_path:
                result = subprocess.run(
                    ["git", "branch", "-D", branch_name],
                    cwd=self._repo_path,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    logger.debug(f"Deleted branch: {branch_name}")
                else:
                    logger.debug(
                        f"Branch {branch_name} already deleted or not found: "
                        f"{result.stderr.strip()}"
                    )

        # Clean up registered targets (worktrees, bare repos, etc.)
        for target in self._cleanup_targets:
            target_path = Path(target)
            if target_path.exists():
                shutil_cleanup.rmtree(target_path)
                logger.debug(f"Cleaned up target: {target}")

        # Clean up the main repo
        if self._repo_path:
            repo = Path(self._repo_path)
            if repo.exists():
                shutil_cleanup.rmtree(repo)
                logger.debug(f"Cleaned up repo: {self._repo_path}")
            self._repo_path = None

        if self._workspace_path:
            workspace = Path(self._workspace_path)
            if workspace.exists():
                shutil_cleanup.rmtree(workspace)
                logger.debug(f"Cleaned up workspace: {self._workspace_path}")
            self._workspace_path = None

        self._cleanup_targets.clear()
        self._created_branches = []

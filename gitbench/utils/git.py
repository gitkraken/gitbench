"""Git executor for sandboxed git command execution."""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class GitExecutor:
    """Executes git commands in an isolated temporary directory."""

    def __init__(self, base_dir: str | None = None):
        """Initialize the git executor.

        Args:
            base_dir: Optional base directory for temp repos.
                     Defaults to system temp directory.

        Raises:
            RuntimeError: If git is not available in PATH.
        """
        self._base_dir = base_dir or tempfile.gettempdir()
        self._repo_path: str | None = None

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
        repo_dir = Path(self._base_dir) / name
        repo_dir.mkdir(parents=True, exist_ok=True)
        self._repo_path = str(repo_dir)

        for command in commands:
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

    def cleanup(self) -> None:
        """Remove the temporary repository directory tree.

        Does nothing if no repo has been set up.
        """
        if self._repo_path:
            import shutil as shutil_cleanup

            repo = Path(self._repo_path)
            if repo.exists():
                shutil_cleanup.rmtree(repo)
                logger.debug(f"Cleaned up repo: {self._repo_path}")
            self._repo_path = None

"""Abstract base class for GitBench benchmarks."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.utils.git import FixtureGenerationContext, GitExecutor

logger = logging.getLogger(__name__)


class Benchmark(ABC):
    """Abstract base class for GitBench benchmarks.

    Subclasses must provide ``name``, ``description``, ``score()``, and
    ``get_diff()``.  ``load_fixtures()``, ``setup_fixture()``, and
    ``format_prompt()`` have defaults that work for most benchmarks.
    """

    name: str = ""
    description: str = ""

    def __init__(self, fixtures_root: Path | str | None = None) -> None:
        """Initialise the benchmark.

        Args:
            fixtures_root: Root directory for fixture YAML files.
                Defaults to ``<repo_root>/fixtures/``.
        """
        if fixtures_root is None:
            import gitbench
            fixtures_root = Path(gitbench.__file__).parent.parent / "fixtures"
        self._fixtures_root = Path(fixtures_root)
        self._loader = FixtureLoader()
        self._scorer = Scorer()

    def load_fixtures(self) -> list[Fixture]:
        """Load all fixtures for this benchmark.

        The default implementation loads every ``.yaml`` / ``.yml`` file
        from ``<fixtures_root>/<self.name>/``.

        Returns:
            List of Fixture objects.

        Raises:
            FileNotFoundError: If the fixtures directory does not exist.
        """
        logger.info("Loading fixtures from: %s", self._fixtures_root / self.name)
        fixtures = self._loader.load_dir(str(self._fixtures_root / self.name))
        logger.info("Loaded %d fixtures", len(fixtures))
        return fixtures

    @abstractmethod
    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None, diff: str | None = None, prompt: str | None = None) -> Score:
        """Score a model output against the expected value.

        Args:
            fixture: The fixture being scored.
            model_output: The string produced by the model.
            repo_path: Optional path to the git repository (required for
                state_assertions scoring).

        Returns:
            A Score object.
        """
        ...

    def setup_fixture(
        self,
        fixture: Fixture,
        *,
        fixture_generation_context: FixtureGenerationContext | None = None,
    ) -> tuple[GitExecutor, str]:
        """Set up a git repository for a single fixture.

        The default creates a new :class:`GitExecutor` and runs
        ``fixture.setup`` commands inside a temp repo named
        ``<self.name>_<fixture.id>``.  When ``fixture_generation_context``
        is supplied, Git commands use deterministic author/committer
        identities, timestamps, timezone, and locale so repeated setups
        produce identical Git object identities.

        Args:
            fixture: The fixture to set up.
            fixture_generation_context: Optional deterministic context for
                reproducible fixture generation.

        Returns:
            A tuple of (GitExecutor, repo_path).
        """
        executor = GitExecutor(
            fixture_generation_context=fixture_generation_context,
        )
        repo_path = executor.setup_repo(
            f"{self.name}_{fixture.id}", fixture.setup
        )
        return executor, repo_path

    @abstractmethod
    def get_diff(self, repo_path: str) -> str:
        """Return the git context the model needs to answer the prompt.

        Args:
            repo_path: Path to the git repository.

        Returns:
            A string with git command output (diff, log, status, etc.).
        """
        ...

    def format_prompt(self, fixture: Fixture, diff: str) -> str:
        """Format the full prompt sent to the model.

        The default joins the fixture prompt and the git context::

            {fixture.prompt}\
\
{diff}

        Benchmarks that want a label between the two can override.

        Args:
            fixture: The fixture containing the base prompt.
            diff: The git context string from ``get_diff()``.

        Returns:
            The formatted prompt string.
        """
        return f"{fixture.prompt}\n\n{diff}"

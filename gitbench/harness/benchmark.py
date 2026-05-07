"""Abstract base class for GitBench benchmarks."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score

logger = logging.getLogger(__name__)


class Benchmark(ABC):
    """Abstract base class for GitBench benchmarks.

    Subclasses must provide ``name``, ``description``, and ``score()``.
    ``load_fixtures()`` has a default that loads from
    ``<fixtures_root>/<self.name>/``.
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
    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None) -> Score:
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

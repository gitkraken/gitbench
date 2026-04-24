"""Benchmark base classes for GitBench."""

from abc import ABC, abstractmethod

from gitbench.harness.types import Fixture, Score


class Benchmark(ABC):
    """Abstract base class for GitBench benchmarks.

    All benchmarks must inherit from this class and implement
    the required methods.
    """

    # Class-level attributes for benchmark metadata
    name: str = ""
    description: str = ""

    @abstractmethod
    def load_fixtures(self) -> list[Fixture]:
        """Load all fixtures for this benchmark.

        Returns:
            List of Fixture objects for this benchmark.

        Raises:
            FileNotFoundError: If the fixtures directory doesn't exist.
            ValueError: If a fixture file is invalid.
        """
        pass

    @abstractmethod
    def score(self, fixture: Fixture, model_output: str) -> Score:
        """Score a model output against the expected value.

        Args:
            fixture: The fixture containing the expected output and scoring config.
            model_output: The string produced by the model.

        Returns:
            A Score object with passed/failed status and similarity value.
        """
        pass
"""Abstract base class for GitBench benchmarks."""

from abc import ABC, abstractmethod

from gitbench.harness.types import Fixture, Score


class Benchmark(ABC):
    """Abstract base class for GitBench benchmarks."""

    name: str = ""
    description: str = ""

    @abstractmethod
    def load_fixtures(self) -> list[Fixture]:
        pass

    @abstractmethod
    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None) -> Score:
        pass

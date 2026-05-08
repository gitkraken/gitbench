"""Benchmark runner — executes benchmarks against a model client."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Protocol

from gitbench.harness.benchmark import Benchmark
from gitbench.harness.model import ModelInterface
from gitbench.harness.types import BenchmarkResult, Fixture, ModelMessage, Score
from gitbench.version import BENCHMARK_SUITE_VERSION

logger = logging.getLogger(__name__)


class RunProgress(Protocol):
    """Progress sink used by :class:`BenchmarkRunner`."""

    def model_started(self, model: str) -> None: ...

    def benchmark_started(self, model: str, benchmark: str, total: int) -> None: ...

    def fixture_finished(self, model: str, benchmark: str, passed: bool, *, fixture_id: str = "", similarity: float = 0.0) -> None: ...

    def benchmark_finished(self, model: str, benchmark: str, errors: int) -> None: ...

    def model_finished(self, model: str, summary: dict) -> None: ...


class BenchmarkRunner:
    """Runs benchmark fixtures against a model and scores the output."""

    def __init__(
        self,
        registry: dict[str, type[Benchmark]],
        model_client: ModelInterface,
    ) -> None:
        """Initialise the runner.

        Args:
            registry: A mapping of benchmark name → class.
            model_client: The model adapter to call for generation.
        """
        self._registry = registry
        self._model_client = model_client

    def run_benchmark(
        self,
        benchmark_name: str,
        *,
        fixture_workers: int = 1,
        progress: RunProgress | None = None,
        progress_model_name: str | None = None,
    ) -> BenchmarkResult:
        """Run a single benchmark against the model.

        Args:
            benchmark_name: Name of the benchmark to run.
            fixture_workers: Number of worker threads for parallel fixture
                execution (1 = sequential).
            progress: Optional progress sink.
            progress_model_name: Model display name for progress callbacks
                (defaults to ``benchmark_name``).

        Returns:
            The benchmark result.

        Raises:
            ValueError: If the benchmark is not found.
        """
        if benchmark_name not in self._registry:
            available = list(self._registry.keys())
            raise ValueError(
                f"Unknown benchmark: {benchmark_name}. Available: {available}"
            )

        benchmark_class = self._registry[benchmark_name]
        benchmark = benchmark_class()
        model_name = progress_model_name or benchmark_name

        logger.debug("Loading fixtures for %s ...", benchmark_name)
        fixtures = benchmark.load_fixtures()
        logger.debug("Loaded %d fixtures", len(fixtures))

        if progress:
            progress.benchmark_started(model_name, benchmark_name, len(fixtures))

        if fixture_workers > 1 and len(fixtures) > 1:
            scores = self._run_fixtures_parallel(
                benchmark, fixtures, fixture_workers,
                progress=progress, model_name=model_name,
                benchmark_name=benchmark_name,
            )
        else:
            scores = self._run_fixtures_sequential(
                benchmark, fixtures,
                progress=progress, model_name=model_name,
                benchmark_name=benchmark_name,
            )

        total = len(fixtures)
        passed = sum(1 for s in scores if s.passed)
        pass_at_k = passed / total if total > 0 else 0.0
        errors = sum(1 for s in scores if s.error)

        if progress:
            progress.benchmark_finished(model_name, benchmark_name, errors)

        return BenchmarkResult(
            benchmark=benchmark_name,
            total=total,
            passed=passed,
            pass_at_k=round(pass_at_k, 4),
            scores=scores,
            errors=errors,
        )

    def run_all(
        self,
        benchmark_names: list[str],
        *,
        model_name: str = "",
        fixture_workers: int = 1,
        progress: RunProgress | None = None,
        progress_model_name: str | None = None,
    ) -> dict:
        """Run every named benchmark against the model.

        Args:
            benchmark_names: Benchmarks to run.
            fixture_workers: Passed through to ``run_benchmark``.
            progress: Optional progress sink.
            progress_model_name: Model display name for progress callbacks.

        Returns:
            A dict with keys ``model``, ``benchmark_suite_version``,
            ``summary``, and ``results``.
        """
        if progress:
            progress.model_started(progress_model_name or "model")

        results_list: list[dict] = []

        for bench_name in benchmark_names:
            if bench_name not in self._registry:
                results_list.append({
                    "benchmark": bench_name,
                    "error": f"Unknown benchmark '{bench_name}'",
                })
                continue

            try:
                result = self.run_benchmark(
                    bench_name,
                    fixture_workers=fixture_workers,
                    progress=progress,
                    progress_model_name=progress_model_name,
                )
                results_list.append(result.to_dict())
            except Exception as exc:
                logger.error(
                    "Benchmark '%s' failed: %s", bench_name, exc,
                )
                if progress:
                    progress.benchmark_finished(
                        progress_model_name or "model", bench_name, errors=1,
                    )
                results_list.append({"benchmark": bench_name, "error": str(exc)})

        total_fixtures = sum(r.get("total", 0) for r in results_list)
        total_passed = sum(r.get("passed", 0) for r in results_list)
        overall_pass_at_k = (
            round(total_passed / total_fixtures, 4)
            if total_fixtures > 0 else 0.0
        )

        model_result = {
            "model": model_name,
            "benchmark_suite_version": BENCHMARK_SUITE_VERSION,
            "summary": {
                "total_benchmarks": len(results_list),
                "total_fixtures": total_fixtures,
                "total_passed": total_passed,
                "overall_pass_at_k": overall_pass_at_k,
            },
            "results": results_list,
        }

        if progress:
            progress.model_finished(
                progress_model_name or "model", model_result["summary"],
            )

        return model_result

    # ------------------------------------------------------------------

    def _run_fixture(self, benchmark: Benchmark, fixture: Fixture) -> tuple[int, Score]:
        """Run a single fixture through the full lifecycle.

        Returns ``(fixture.id, score)``.  Never raises — errors are captured
        in the returned :class:`Score`.
        """
        executor = None
        try:
            executor, repo_path = benchmark.setup_fixture(fixture)
            diff = benchmark.get_diff(repo_path)
            prompt = benchmark.format_prompt(fixture, diff)

            messages = [ModelMessage(role="user", content=prompt)]
            response = self._model_client.generate(messages)

            if isinstance(response, dict):
                model_output = response.get("text", response.get("content", ""))
            else:
                model_output = str(response)

            score = benchmark.score(fixture, model_output, repo_path=repo_path)
            return fixture.id, score
        except Exception as exc:
            logger.error("Error processing fixture %s: %s", fixture.id, exc)
            return fixture.id, Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output="",
                error=str(exc),
            )
        finally:
            if executor is not None:
                executor.cleanup()

    def _run_fixtures_parallel(
        self,
        benchmark: Benchmark,
        fixtures: list[Fixture],
        workers: int,
        *,
        progress: RunProgress | None,
        model_name: str,
        benchmark_name: str,
    ) -> list[Score]:
        """Run fixtures in parallel, preserving fixture order in the output."""
        ordered_scores: list[Score | None] = [None] * len(fixtures)
        ordered_ids = [f.id for f in fixtures]

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {
                executor.submit(self._run_fixture, benchmark, f): i
                for i, f in enumerate(fixtures)
            }
            for future in as_completed(future_map):
                idx = future_map[future]
                fixture_id, score = future.result()
                ordered_scores[idx] = score
                if progress:
                    progress.fixture_finished(
                        model_name, benchmark_name, score.passed,
                        fixture_id=fixture_id,
                        similarity=score.similarity,
                    )

        fixture_index = {fid: i for i, fid in enumerate(ordered_ids)}
        return [
            ordered_scores[fixture_index[s.fixture_id]]
            for s in ordered_scores if s is not None
        ]

    def _run_fixtures_sequential(
        self,
        benchmark: Benchmark,
        fixtures: list[Fixture],
        *,
        progress: RunProgress | None,
        model_name: str,
        benchmark_name: str,
    ) -> list[Score]:
        """Run fixtures one at a time."""
        scores: list[Score] = []
        for fixture in fixtures:
            logger.debug("Processing fixture %s ...", fixture.id)
            _, score = self._run_fixture(benchmark, fixture)
            scores.append(score)
            if progress:
                progress.fixture_finished(
                    model_name, benchmark_name, score.passed,
                    fixture_id=fixture.id,
                    similarity=score.similarity,
                )
        return scores

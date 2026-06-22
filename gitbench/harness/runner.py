"""Benchmark runner — executes benchmarks against a model client."""

import logging
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Any, Protocol

from gitbench.harness.benchmark import Benchmark
from gitbench.harness.capacity import RequestAttemptGate, RequestBudgetCoordinator
from gitbench.harness.campaign import hash_text
from gitbench.harness.judge import JudgeClient
from gitbench.harness.model import (
    DEFAULT_MODEL_TIMEOUT,
    ModelInterface,
    ReasoningDisableError,
    RetriesExhaustedError,
)
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import BenchmarkResult, Fixture, ModelMessage, Score
from gitbench.structured_output import (
    StructuredOutputSchemaError,
    canonicalize,
    contract_for_benchmark_fixture,
    validate_structured_payload,
)
from gitbench.utils.git import FixtureGenerationContext
from gitbench.version import BENCHMARK_SUITE_VERSION

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_MODE = "both"


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
        *,
        request_budget: RequestBudgetCoordinator | None = None,
        capacity_key: str | None = None,
        output_mode: str = DEFAULT_OUTPUT_MODE,
        model_generate_kwargs: dict | None = None,
        judge_config: dict | None = None,
        model_timeout: int = DEFAULT_MODEL_TIMEOUT,
        attempt_gate: RequestAttemptGate | None = None,
    ) -> None:
        """Initialise the runner.

        Args:
            registry: A mapping of benchmark name → class.
            model_client: The model adapter to call for generation.
            output_mode: ``text``, ``json_schema``, or ``both`` (default).
            judge_config: Optional judge config dict with a ``profile`` key.
                When provided, a JudgeClient is created and a single
                judge-aware Scorer is used for all benchmarks;
                scoring-type dispatch alone decides whether the judge is called.
            model_timeout: Timeout in seconds for judge model clients
                (default: 240).
            attempt_gate: Optional request-attempt gate passed to judge
                model clients for capacity coordination.
        """
        self._registry = registry
        self._model_client = model_client
        self._request_budget = request_budget
        self._capacity_key = capacity_key
        self._output_mode = output_mode
        self._model_generate_kwargs = dict(model_generate_kwargs or {})
        self._judge_config = judge_config
        self._judge_client: JudgeClient | None = None
        self._model_timeout = model_timeout
        self._attempt_gate = attempt_gate

        if judge_config is not None:
            from gitbench.config import resolve_profile

            judge_profile = resolve_profile(judge_config["_config"], judge_config["profile"])
            judge_model_clients = self._create_judge_model_client(judge_profile)
            self._judge_client = JudgeClient(judge_model_clients)

        # Construct one judge-aware Scorer when a judge is configured;
        # scoring-type dispatch alone decides whether the judge is called.
        self._scorer = Scorer(judge_client=self._judge_client)

    def _create_judge_model_client(self, profile: dict):
        """Create model clients for every model in the judge profile.

        Each client is configured with ``retry_count=5`` for robust
        judge retries, the runner's resolved model timeout, and the
        attempt gate for capacity coordination.
        The JudgeClient will try them in order.
        """
        from gitbench.cli import get_model_client

        models = profile.get("models", [])
        if not models:
            raise ValueError("Judge profile has no models configured")

        clients = []
        for model in models:
            client = get_model_client(
                model,
                timeout=self._model_timeout,
                retry_count=5,
                base_url=profile.get("base_url"),
                api_key=profile.get("api_key"),
                provider=profile.get("provider"),
                attempt_gate=self._attempt_gate,
            )
            clients.append(client)
        return clients

    def run_benchmark(
        self,
        benchmark_name: str,
        *,
        fixture_workers: int = 1,
        selected_fixture_ids: list[str] | None = None,
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

        if selected_fixture_ids is not None:
            fixture_by_id = {fixture.id: fixture for fixture in fixtures}
            missing = [
                fixture_id
                for fixture_id in selected_fixture_ids
                if fixture_id not in fixture_by_id
            ]
            if missing:
                raise ValueError(
                    f"Unknown fixture id(s) for benchmark {benchmark_name}: "
                    f"{', '.join(missing)}"
                )
            fixtures = [fixture_by_id[fixture_id] for fixture_id in selected_fixture_ids]

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
            "output_mode": self._output_mode,
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

    def _provider_route_metadata(self) -> dict[str, Any]:
        """Return available provider-route metadata from the model client."""
        client = self._model_client
        metadata: dict[str, Any] = {
            "model_id": getattr(client, "model", None),
            "reasoning_level": getattr(client, "reasoning_level", None),
            "adapter": type(client).__name__,
        }
        base_url = getattr(client, "base_url", None) or getattr(client, "_base_url", None)
        if base_url:
            metadata["base_url"] = base_url
        return {k: v for k, v in metadata.items() if v is not None}

    def _normalized_request_config(
        self,
        *,
        output_mode: str,
        structured_output_contract: Any | None,
    ) -> dict[str, Any]:
        """Return normalized request configuration for provenance."""
        config: dict[str, Any] = {
            "output_mode": output_mode,
            "model_generate_kwargs": dict(self._model_generate_kwargs),
        }
        if structured_output_contract is not None:
            config["structured_output"] = {
                "benchmark": structured_output_contract.primary_path,
                "canonicalize": structured_output_contract.canonicalize,
            }
        return config

    def run_fixture_identity(
        self,
        benchmark_name: str,
        fixture_id: str,
        *,
        fixture_generation_context: FixtureGenerationContext | None = None,
        campaign_scoring_context: dict | None = None,
    ) -> Score:
        """Run one exact benchmark fixture and return its score."""
        if benchmark_name not in self._registry:
            available = list(self._registry.keys())
            raise ValueError(
                f"Unknown benchmark: {benchmark_name}. Available: {available}"
            )
        benchmark = self._registry[benchmark_name]()
        fixture_by_id = {fixture.id: fixture for fixture in benchmark.load_fixtures()}
        if fixture_id not in fixture_by_id:
            raise ValueError(
                f"Unknown fixture id for benchmark {benchmark_name}: {fixture_id}"
            )
        _fixture_id, score = self._run_fixture(
            benchmark,
            fixture_by_id[fixture_id],
            fixture_generation_context=fixture_generation_context,
            campaign_scoring_context=campaign_scoring_context,
        )
        return score

    def _run_fixture(
        self,
        benchmark: Benchmark,
        fixture: Fixture,
        *,
        fixture_generation_context: FixtureGenerationContext | None = None,
        campaign_scoring_context: dict | None = None,
    ) -> tuple[int, Score]:
        """Run a single fixture through the full lifecycle.

        Returns ``(fixture.id, score)``. Runtime errors, including reasoning
        violations after preflight, are captured in the returned
        :class:`Score`.
        """
        executor = None
        score = None
        t_start = time.perf_counter()
        benchmark_name = getattr(benchmark, "name", benchmark.__class__.__name__)
        output_mode = self._output_mode

        try:
            executor, repo_path = benchmark.setup_fixture(
                fixture,
                fixture_generation_context=fixture_generation_context,
            )
            diff = benchmark.get_diff(repo_path)
            prompt = benchmark.format_prompt(fixture, diff)

            messages = [ModelMessage(role="user", content=prompt)]

            generate_kwargs = dict(self._model_generate_kwargs)
            structured_output_contract = None
            if output_mode == "json_schema":
                structured_output_contract = contract_for_benchmark_fixture(
                    fixture, benchmark_name
                )
                if structured_output_contract is not None:
                    generate_kwargs["structured_output_contract"] = structured_output_contract
                else:
                    raise ValueError(
                        f"No structured-output contract for fixture "
                        f"{fixture.id} (benchmark {benchmark_name}, "
                        f"scoring type {fixture.scoring.get('type')})"
                    )

            response = self._model_client.generate(messages, **generate_kwargs)

            if isinstance(response, dict):
                model_output = response.get("text", response.get("content", ""))
                usage = response.get("usage")
                parsed_payload = response.get("parsed_payload")
                structured_error = response.get("structured_error")
                request_telemetry = response.get("request_telemetry")
            else:
                model_output = str(response)
                usage = None
                response = {}
                parsed_payload = None
                structured_error = None
                request_telemetry = None

            raw_structured_output = response.get("raw_structured_output")

            # Validate and canonicalize structured output before scoring.
            if (
                output_mode == "json_schema"
                and not structured_error
                and structured_output_contract is not None
            ):
                try:
                    validate_structured_payload(
                        parsed_payload,
                        structured_output_contract,
                    )
                    model_output = canonicalize(parsed_payload, structured_output_contract)
                except StructuredOutputSchemaError as exc:
                    structured_error = (
                        f"Structured output schema validation failed: {exc}"
                    )

            if structured_error:
                if not isinstance(raw_structured_output, str):
                    raw_structured_output = model_output
                model_output = raw_structured_output
                parsed_payload = None
                score = Score(
                    fixture_id=fixture.id,
                    passed=False,
                    similarity=0.0,
                    model_output=model_output,
                    error=structured_error,
                    reasoning_level=getattr(
                        self._model_client, "reasoning_level", None
                    ),
                    prompt=fixture.prompt,
                    expected=fixture.expected,
                    description=fixture.description,
                )
                # Attach structured-output fields
                score._parsed_payload = parsed_payload
                score._raw_structured_output = raw_structured_output
                score._structured_error = structured_error
                score._output_mode = output_mode
                score.provider_route_metadata = self._provider_route_metadata()
                score.request_config = self._normalized_request_config(
                    output_mode=output_mode,
                    structured_output_contract=structured_output_contract,
                )
                return fixture.id, score

            effective_campaign_context = campaign_scoring_context
            if effective_campaign_context is not None:
                effective_campaign_context = dict(effective_campaign_context)
                effective_campaign_context.setdefault(
                    "target_output_hash", hash_text(model_output)
                )

            scoring_type = fixture.scoring.get("type", "similarity")
            if scoring_type == "llm_judge":
                # llm_judge fixtures go through the judge-aware Scorer
                # with the same arguments and failure behavior as before.
                score = self._scorer.score(
                    fixture,
                    model_output,
                    repo_path=repo_path,
                    diff=diff,
                    prompt=fixture.prompt,
                    campaign_scoring_context=effective_campaign_context,
                )
            else:
                # Non-judge fixtures are evaluated through the benchmark's
                # own score() method so custom scorers and stateful command
                # execution run before the result is recorded.
                score = benchmark.score(
                    fixture,
                    model_output,
                    repo_path=repo_path,
                    diff=diff,
                    prompt=fixture.prompt,
                )
                # Scoring-framework errors (unsupported type, configuration
                # errors) are infrastructure failures, not quality failures.
                if score.error and score.error.startswith("Scoring error:"):
                    score.operational_failure = True
            score.reasoning_level = getattr(
                self._model_client, "reasoning_level", None
            )
            score.prompt = fixture.prompt
            score.expected = fixture.expected
            score.description = fixture.description

            # Wire transcript, api_duration_ms, and request_telemetry from response dict
            if isinstance(response, dict):
                score.transcript = response.get("transcript")
                score.api_duration_ms = response.get("api_duration_ms")
                if request_telemetry is not None:
                    score.request_telemetry = request_telemetry

            if usage and isinstance(usage, dict):
                score.input_tokens = usage.get("input_tokens")
                score.output_tokens = usage.get("output_tokens")
                score.total_tokens = usage.get("total_tokens")
                score.reasoning_tokens = usage.get("reasoning_tokens")
                if usage.get("cost") is not None:
                    score.cost_usd = usage.get("cost")

            # Record provider-route and normalized request provenance.
            score.provider_route_metadata = self._provider_route_metadata()
            score.request_config = self._normalized_request_config(
                output_mode=output_mode,
                structured_output_contract=structured_output_contract,
            )

            # Attach structured-output fields
            score._output_mode = output_mode
            score._parsed_payload = parsed_payload
            score._raw_structured_output = raw_structured_output
            score._structured_error = structured_error

            return fixture.id, score
        except RetriesExhaustedError as exc:
            logger.error(
                "All retries exhausted for fixture %s: %s",
                fixture.id,
                exc.last_error,
            )
            score = Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output="",
                error=str(exc.last_error),
                reasoning_level=getattr(
                    self._model_client, "reasoning_level", None
                ),
                prompt=fixture.prompt,
                expected=fixture.expected,
                description=fixture.description,
                operational_failure=True,
            )
            score.provider_route_metadata = self._provider_route_metadata()
            if exc.telemetry is not None:
                score.request_telemetry = exc.telemetry.to_dict()
            return fixture.id, score
        except ReasoningDisableError as exc:
            logger.error(
                "Reasoning-disable violation for fixture %s: %s",
                fixture.id,
                exc,
            )
            score = Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output="",
                error=str(exc),
                reasoning_level=getattr(
                    self._model_client, "reasoning_level", None
                ),
                reasoning_tokens=exc.reasoning_tokens,
                prompt=fixture.prompt,
                expected=fixture.expected,
                description=fixture.description,
            )
            return fixture.id, score
        except Exception as exc:
            logger.error("Error processing fixture %s: %s", fixture.id, exc)
            score = Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output="",
                error=str(exc),
                reasoning_level=getattr(
                    self._model_client, "reasoning_level", None
                ),
                prompt=fixture.prompt,
                expected=fixture.expected,
                description=fixture.description,
                operational_failure=True,
            )
            return fixture.id, score
        finally:
            elapsed = time.perf_counter() - t_start
            if score is not None:
                score.duration_ms = round(elapsed * 1000, 2)
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
        """Run fixtures in parallel, preserving fixture order in the output.

        Each fixture receives a fresh benchmark instance so that mutable
        state (e.g. ``worktree_usage._current_executor``) is not shared
        across concurrently executing fixtures.
        """
        ordered_scores: list[Score | None] = [None] * len(fixtures)
        executor = ThreadPoolExecutor(max_workers=workers)
        future_map: dict[Future, int] = {}
        next_index = 0
        benchmark_class = self._registry[benchmark_name]

        def submit_next() -> bool:
            nonlocal next_index
            if next_index >= len(fixtures):
                return False
            index = next_index
            next_index += 1
            future_map[
                executor.submit(
                    self._run_fixture, benchmark_class(), fixtures[index]
                )
            ] = index
            return True

        try:
            for _ in range(min(workers, len(fixtures))):
                submit_next()

            while future_map:
                done, _pending = wait(
                    future_map,
                    return_when=FIRST_COMPLETED,
                )
                completed: list[tuple[int, int, Score]] = []
                for future in done:
                    idx = future_map.pop(future)
                    fixture_id, score = future.result()
                    completed.append((idx, fixture_id, score))

                for idx, fixture_id, score in completed:
                    ordered_scores[idx] = score
                    if progress:
                        progress.fixture_finished(
                            model_name, benchmark_name, score.passed,
                            fixture_id=fixture_id,
                            similarity=score.similarity,
                        )
                    submit_next()
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

        return [score for score in ordered_scores if score is not None]

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

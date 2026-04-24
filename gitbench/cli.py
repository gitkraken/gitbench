"""CLI for GitBench."""

import importlib
import inspect
import json
import logging
import shutil
import sys
from pathlib import Path

import click

from gitbench.benchmarks import Benchmark
from gitbench.harness.model import MockModelClient, OpenAIAdapter
from gitbench.harness.types import BenchmarkResult, ModelMessage, Score

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Global registry for discovered benchmarks
_benchmark_registry: dict[str, type[Benchmark]] = {}


def discover_benchmarks() -> dict[str, type[Benchmark]]:
    """Auto-discover all Benchmark subclasses from the benchmarks package.

    Returns:
        Dictionary mapping benchmark names to their classes.
    """
    benchmarks_dir = Path(__file__).parent / "benchmarks"

    if not benchmarks_dir.exists():
        logger.warning(f"Benchmarks directory not found: {benchmarks_dir}")
        return {}

    discovered: dict[str, type[Benchmark]] = {}

    for file_path in benchmarks_dir.glob("*.py"):
        if file_path.name.startswith("_") or file_path.name == "__init__.py":
            continue

        module_name = f"gitbench.benchmarks.{file_path.stem}"

        try:
            module = importlib.import_module(module_name)

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, Benchmark)
                    and obj is not Benchmark
                    and obj is not None
                ):
                    if hasattr(obj, "name") and obj.name:
                        discovered[obj.name] = obj
                        logger.debug(f"Discovered benchmark: {obj.name} from {module_name}")
                    else:
                        logger.warning(
                            f"Benchmark class {name} in {module_name} has no name attribute"
                        )

        except Exception as e:
            logger.error(f"Failed to load benchmarks from {module_name}: {e}")

    return discovered


def check_git_availability() -> bool:
    """Check if git CLI is available.

    Returns:
        True if git is available, False otherwise.
    """
    git_path = shutil.which("git")
    if git_path:
        logger.info(f"Git CLI found at: {git_path}")
        return True
    else:
        logger.error("Git CLI not found in PATH")
        return False


def get_model_client(model_type: str) -> OpenAIAdapter | MockModelClient:
    """Get the model client based on type.

    Args:
        model_type: Either 'openai' or 'mock'.

    Returns:
        The appropriate model client instance.

    Raises:
        click.ClickException: If model type is invalid.
    """
    if model_type == "openai":
        return OpenAIAdapter()
    elif model_type == "mock":
        return MockModelClient()
    else:
        raise click.ClickException(
            f"Unknown model type: {model_type}. Use 'openai' or 'mock'."
        )


def run_benchmark(benchmark_name: str, model_client, verbose: bool = False) -> BenchmarkResult:
    """Run a specific benchmark with the given model client.

    Args:
        benchmark_name: Name of the benchmark to run.
        model_client: The model client to use for generating outputs.
        verbose: Whether to print verbose output.

    Returns:
        The benchmark result.

    Raises:
        ValueError: If the benchmark is not found.
    """
    global _benchmark_registry

    if not _benchmark_registry:
        _benchmark_registry = discover_benchmarks()

    if benchmark_name not in _benchmark_registry:
        available = list(_benchmark_registry.keys())
        raise ValueError(
            f"Unknown benchmark: {benchmark_name}. Available: {available}"
        )

    benchmark_class = _benchmark_registry[benchmark_name]
    benchmark = benchmark_class()

    logger.info(f"Loading fixtures for {benchmark_name}...")
    fixtures = benchmark.load_fixtures()
    logger.info(f"Loaded {len(fixtures)} fixtures")

    scores: list[Score] = []
    errors = 0

    for fixture in fixtures:
        logger.info(f"Processing fixture {fixture.id}...")

        try:
            executor, repo_path = benchmark.setup_fixture(fixture)
            diff = benchmark.get_diff(repo_path)
            prompt = benchmark.format_prompt(fixture, diff)

            messages = [ModelMessage(role="user", content=prompt)]
            response = model_client.generate(messages)

            # Extract text from response (handle both string and dict responses)
            if isinstance(response, dict):
                model_output = response.get("text", response.get("content", ""))
            else:
                model_output = str(response)

            score = benchmark.score(fixture, model_output)
            scores.append(score)

            if verbose:
                click.echo(
                    f"  {fixture.id}: passed={score.passed}, "
                    f"similarity={score.similarity:.4f}"
                )

        except Exception as e:
            logger.error(f"Error processing fixture {fixture.id}: {e}")
            scores.append(
                Score(
                    fixture_id=fixture.id,
                    passed=False,
                    similarity=0.0,
                    model_output="",
                    error=str(e),
                )
            )
            errors += 1

        finally:
            # Clean up the temporary repo
            if "executor" in locals():
                executor.cleanup()

    total = len(fixtures)
    passed = sum(1 for s in scores if s.passed)
    pass_at_k = passed / total if total > 0 else 0.0

    return BenchmarkResult(
        benchmark=benchmark_name,
        total=total,
        passed=passed,
        pass_at_k=round(pass_at_k, 4),
        scores=scores,
        errors=errors,
    )


@click.group()
def cli():
    """GitBench: Benchmark harness for evaluating LLM-generated git commit messages."""
    pass


@cli.command()
@click.option(
    "--benchmark",
    "-b",
    required=True,
    help="Name of the benchmark to run",
)
@click.option(
    "--model",
    "-m",
    default="mock",
    type=click.Choice(["mock", "openai"]),
    help="Model type to use (default: mock)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (writes JSON, defaults to stdout)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Print detailed per-fixture results",
)
def run(benchmark: str, model: str, output: str | None, verbose: bool):
    """Run a benchmark against the specified model."""
    # Check git availability on startup
    if not check_git_availability():
        click.echo("Error: Git CLI is required but not found in PATH", err=True)
        sys.exit(1)

    logger.info(f"Starting benchmark: {benchmark} with model: {model}")
    click.echo(f"Running benchmark '{benchmark}' with model '{model}'...", err=True)

    try:
        model_client = get_model_client(model)
        result = run_benchmark(benchmark, model_client, verbose)

        # Output results
        output_dict = result.to_dict()

        if verbose:
            click.echo("\nPer-fixture results:")
            for score in result.scores:
                click.echo(f"  {score.fixture_id}: passed={score.passed}, similarity={score.similarity}")
                if score.error:
                    click.echo(f"    Error: {score.error}")
                if score.model_output:
                    output_preview = score.model_output[:100] + "..." if len(score.model_output) > 100 else score.model_output
                    click.echo(f"    Output: {output_preview}")

        output_json = json.dumps(output_dict, indent=2)

        if output:
            Path(output).write_text(output_json)
            click.echo(f"\nResults written to: {output}", err=True)
        else:
            click.echo(output_json)

        logger.info(f"Benchmark completed: {result.passed}/{result.total} passed")

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("list")
def list_benchmarks():
    """List available benchmarks."""
    # Check git availability
    if not check_git_availability():
        click.echo("Warning: Git CLI not found - some benchmarks may not work", err=True)

    # Discover and list benchmarks
    benchmarks = discover_benchmarks()

    if not benchmarks:
        click.echo("No benchmarks found.")
        return

    click.echo("Available benchmarks:")
    for name, benchmark_class in benchmarks.items():
        desc = getattr(benchmark_class, "description", "")
        click.echo(f"  - {name}: {desc}")


if __name__ == "__main__":
    cli()
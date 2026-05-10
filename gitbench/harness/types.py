"""Core types for the GitBench harness."""

from dataclasses import dataclass, asdict, field
from typing import Any


@dataclass
class ModelMessage:
    """A message in a model conversation."""

    role: str
    content: str

    def to_dict(self) -> dict:
        """Convert to dictionary format expected by model APIs."""
        return {"role": self.role, "content": self.content}

    @classmethod
    def from_dict(cls, data: dict) -> "ModelMessage":
        """Create from dictionary."""
        return cls(role=data["role"], content=data["content"])


@dataclass
class Fixture:
    """A test fixture for benchmarking."""

    id: str
    description: str
    setup: list[str]  # List of git commands to run as setup
    prompt: str
    expected: str
    scoring: dict[str, Any]  # Contains 'type' and 'threshold'
    purpose: str = ""       # What Git skill this tests and why it matters
    difficulty: str = ""    # One of: trivial, easy, medium, hard, expert
    tags: list[str] = field(default_factory=list)  # Searchable keywords

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Fixture":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Score:
    """A scoring result for a single fixture."""

    fixture_id: str
    passed: bool
    similarity: float
    model_output: str
    error: str | None = None
    reasoning_level: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None
    provider_cost_usd: float | None = None
    purpose: str | None = None
    difficulty: str | None = None
    tags: list[str] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        none_fields = (
            "reasoning_level", "input_tokens", "output_tokens",
            "total_tokens", "cost_usd", "provider_cost_usd",
            "purpose", "difficulty", "tags",
        )
        for field in none_fields:
            if result.get(field) is None:
                del result[field]
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Score":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class BenchmarkResult:
    """The result of running a benchmark."""

    benchmark: str
    total: int
    passed: int
    pass_at_k: float
    scores: list[Score]
    errors: int

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "benchmark": self.benchmark,
            "total": self.total,
            "passed": self.passed,
            "pass_at_k": self.pass_at_k,
            "scores": [s.to_dict() for s in self.scores],
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BenchmarkResult":
        """Create from dictionary."""
        scores = [Score.from_dict(s) for s in data["scores"]]
        return cls(
            benchmark=data["benchmark"],
            total=data["total"],
            passed=data["passed"],
            pass_at_k=data["pass_at_k"],
            scores=scores,
            errors=data["errors"],
        )
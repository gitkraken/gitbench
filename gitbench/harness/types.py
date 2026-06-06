"""Core types for the GitBench harness."""

from dataclasses import dataclass, asdict, field
from typing import Any


@dataclass
class StructuredOutputContract:
    """A fixture-level structured-output contract for JSON-schema runs."""

    schema: dict[str, Any]
    primary_path: str
    canonicalize: str = "string"
    display_label: str = ""

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "StructuredOutputContract":
        """Create from dict."""
        return cls(**{k: v for k, v in data.items() if k in ("schema", "primary_path", "canonicalize", "display_label")})


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
    structured_output: StructuredOutputContract | None = None  # JSON-schema contract

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        if result.get("structured_output") is None:
            del result["structured_output"]
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Fixture":
        """Create from dictionary."""
        contract_data = data.pop("structured_output", None)
        fixture = cls(**data)
        if contract_data:
            fixture.structured_output = StructuredOutputContract.from_dict(contract_data)
        return fixture


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
    reasoning_tokens: int | None = None
    api_duration_ms: float | None = None
    transcript: list[dict] | None = None
    purpose: str | None = None
    difficulty: str | None = None
    tags: list[str] | None = None
    prompt: str | None = None
    expected: str | None = None
    description: str | None = None
    duration_ms: float | None = None
    # Structured-output fields (attached at runtime, not in default serialization)
    _output_mode: str | None = field(default=None, repr=False)
    _parsed_payload: dict | None = field(default=None, repr=False)
    _raw_structured_output: str | None = field(default=None, repr=False)
    _structured_error: str | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        none_fields = (
            "reasoning_level", "input_tokens", "output_tokens",
            "total_tokens", "cost_usd", "provider_cost_usd",
            "reasoning_tokens", "api_duration_ms", "transcript",
            "purpose", "difficulty", "tags",
            "prompt", "expected", "description",
            "duration_ms",
        )
        for field_name in none_fields:
            if result.get(field_name) is None:
                del result[field_name]
        # Remove private underscore-prefixed fields leaked by asdict()
        for key in list(result.keys()):
            if key.startswith("_"):
                del result[key]
        # Include structured-output fields under clean names when present
        if self._output_mode is not None:
            result["output_mode"] = self._output_mode
        if self._parsed_payload is not None:
            result["parsed_payload"] = self._parsed_payload
        if self._raw_structured_output is not None:
            result["raw_structured_output"] = self._raw_structured_output
        if self._structured_error is not None:
            result["structured_error"] = self._structured_error
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Score":
        """Create from dictionary."""
        kwargs = dict(data)
        kwargs.setdefault("duration_ms", None)
        # Extract structured-output fields if present in serialized form
        output_mode = kwargs.pop("output_mode", None)
        parsed_payload = kwargs.pop("parsed_payload", None)
        raw_structured_output = kwargs.pop("raw_structured_output", None)
        structured_error = kwargs.pop("structured_error", None)
        score = cls(**kwargs)
        if output_mode is not None:
            score._output_mode = output_mode
        if parsed_payload is not None:
            score._parsed_payload = parsed_payload
        if raw_structured_output is not None:
            score._raw_structured_output = raw_structured_output
        if structured_error is not None:
            score._structured_error = structured_error
        return score


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
        non_null_durations = [
            s.duration_ms
            for s in self.scores
            if s.duration_ms is not None
        ]
        total_duration_ms = round(sum(non_null_durations), 2) if non_null_durations else None
        result = {
            "benchmark": self.benchmark,
            "total": self.total,
            "passed": self.passed,
            "pass_at_k": self.pass_at_k,
            "scores": [s.to_dict() for s in self.scores],
            "errors": self.errors,
        }
        if total_duration_ms is not None:
            result["total_duration_ms"] = total_duration_ms
        return result

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
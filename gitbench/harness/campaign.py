"""Campaign-aware result model for repeated evaluation runs.

This module introduces the data structures that represent an evaluation
campaign: an immutable configuration, a deterministic schedule of raw
attempts, and the aggregates needed for reliable reporting.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TypeVar, get_args, get_origin, get_type_hints

from gitbench.version import CAMPAIGN_SCHEMA_VERSION

T = TypeVar("T")


def _now_iso() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _encode(value: Any) -> Any:
    """Recursively encode a value for JSON serialization.

    Handles dataclass instances, enums, lists, and dicts.  Private
    underscore-prefixed fields are stripped from dataclass dictionaries.
    """
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return _encode(asdict(value))
    if isinstance(value, list):
        return [_encode(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _encode(val)
            for key, val in value.items()
            if not (isinstance(key, str) and key.startswith("_"))
        }
    return value


def _unwrap_optional(annotation: Any) -> Any:
    """Return the non-None type for ``X | None`` unions."""
    args = get_args(annotation)
    if type(None) in args:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return annotation


def _decode(value: Any, annotation: Any) -> Any:
    """Recursively decode a JSON-loaded value into the requested annotation."""
    if value is None:
        return None

    annotation = _unwrap_optional(annotation)
    origin = get_origin(annotation)

    if origin is list:
        item_type = get_args(annotation)[0]
        return [_decode(item, item_type) for item in value]

    if origin is dict:
        _, value_type = get_args(annotation)
        return {k: _decode(v, value_type) for k, v in value.items()}

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(value)

    if is_dataclass(annotation):
        return annotation.from_dict(value)

    return value


def _dataclass_from_dict(cls: type[T], data: dict[str, Any]) -> T:
    """Create a dataclass instance from a dictionary using type hints."""
    hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for key, annotation in hints.items():
        if key.startswith("_"):
            continue
        if key in data:
            kwargs[key] = _decode(data[key], annotation)
    return cls(**kwargs)


def compute_config_hash(config_dict: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 hash for a campaign configuration.

    The dict is serialized to canonical JSON so that equivalent
    configurations always produce the same hash.
    """
    canonical = json.dumps(
        _encode(config_dict), sort_keys=True, ensure_ascii=True, default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def hash_text(value: str) -> str:
    """Return a deterministic SHA-256 hash of a string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    """Serialize a value to canonical JSON for hashing."""
    return json.dumps(
        _encode(value), sort_keys=True, ensure_ascii=True, default=str
    )


def hash_fixture_input(fixture: Any, context: Any) -> str:
    """Return a deterministic hash for the reproducible fixture input.

    Includes the fixture-generation context (version, seed, identities,
    timestamp, timezone, locale) and the fixture definition so that any
    change to either invalidates previously recorded attempts.
    """
    canonical = _canonical_json([_encode(context), _encode(fixture)])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def hash_rendered_prompt(prompt: str) -> str:
    """Hash a rendered prompt after deterministic fixture setup."""
    return hash_text(prompt)


def hash_expected_scoring_input(fixture: Any) -> str:
    """Hash the expected value and scoring configuration for a fixture."""
    canonical = _canonical_json(
        {
            "expected": getattr(fixture, "expected", None),
            "scoring": getattr(fixture, "scoring", None),
        }
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def hash_request_config(request_config: dict[str, Any] | None) -> str:
    """Hash a normalized target-model request configuration."""
    return hashlib.sha256(
        _canonical_json(request_config or {}).encode("utf-8")
    ).hexdigest()


def hash_scorer_config(scorer_config: dict[str, Any] | None) -> str:
    """Hash a scorer/judge configuration."""
    return hashlib.sha256(
        _canonical_json(scorer_config or {}).encode("utf-8")
    ).hexdigest()


def compute_fixture_expected_hashes(
    fixture: Any,
    context: Any,
    *,
    rendered_prompt: str,
    request_config: dict[str, Any] | None = None,
    scorer_config: dict[str, Any] | None = None,
) -> "FixtureExpectedHashes":
    """Compute the expected provenance hashes for a fixture.

    This is used when planning a campaign: every selected fixture is set up
    once with the deterministic context, its prompt is rendered, and the
    resulting hashes are persisted in the campaign manifest.  Later attempts
    can be rejected if their provenance does not match these expected hashes.
    """
    return FixtureExpectedHashes(
        fixture_input_hash=hash_fixture_input(fixture, context),
        rendered_prompt_hash=hash_rendered_prompt(rendered_prompt),
        expected_hash=hash_text(getattr(fixture, "expected", "")),
        scoring_input_hash=hash_expected_scoring_input(fixture),
        request_config_hash=hash_request_config(request_config),
        scorer_config_hash=hash_scorer_config(scorer_config),
    )


# ── Enums ────────────────────────────────────────────────────────────────────


class CampaignState(Enum):
    """High-level lifecycle state of a campaign."""

    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class AttemptStatus(Enum):
    """Status of a single raw attempt.

    The statuses explicitly separate model-quality outcomes from operational
    failures, invalid inputs, unscored attempts, and safety gating.
    """

    PENDING = "pending"
    VALID_PASS = "valid_pass"
    VALID_FAIL = "valid_fail"
    INVALID_INPUT = "invalid_input"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    UNSCORED = "unscored"
    SAFETY_BLOCKED = "safety_blocked"
    HASH_MISMATCH = "hash_mismatch"

    def is_quality_outcome(self) -> bool:
        """Return True when the attempt is a valid model-quality result."""
        return self in (AttemptStatus.VALID_PASS, AttemptStatus.VALID_FAIL)


class FixtureReliability(Enum):
    """Classification of a fixture's repeated-trial behavior."""

    STABLE_PASS = "stable_pass"
    FLAKY = "flaky"
    STABLE_FAIL = "stable_fail"
    UNKNOWN = "unknown"


class PublicationState(Enum):
    """Publication readiness of a campaign."""

    DRAFT = "draft"
    PUBLISHABLE = "publishable"
    PUBLISHED = "published"


# ── Core identity and provenance ────────────────────────────────────────────


@dataclass
class AttemptIdentity:
    """Exact identity key for a single raw attempt.

    Uniqueness: (campaign_id, trial_index, model_id, reasoning_effort,
    output_mode, benchmark, fixture_id).
    """

    campaign_id: str
    trial_index: int
    model_id: str
    reasoning_effort: str
    output_mode: str
    fixture_id: str
    benchmark: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _encode(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttemptIdentity:
        return _dataclass_from_dict(cls, data)


@dataclass
class Provenance:
    """Immutable input and configuration provenance recorded for an attempt."""

    fixture_input_hash: str
    rendered_prompt_hash: str
    expected_hash: str
    scoring_input_hash: str | None = None
    request_config_hash: str | None = None
    scorer_config_hash: str | None = None
    judge_config_hash: str | None = None
    fixture_generation_version: str = ""
    scheduler_seed: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return _encode(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Provenance:
        return _dataclass_from_dict(cls, data)


@dataclass
class FixtureExpectedHashes:
    """Expected provenance hashes for a single fixture in a campaign manifest."""

    fixture_input_hash: str
    rendered_prompt_hash: str | None = None
    expected_hash: str | None = None
    scoring_input_hash: str | None = None
    request_config_hash: str | None = None
    scorer_config_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _encode(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FixtureExpectedHashes":
        return _dataclass_from_dict(cls, data)


@dataclass
class ResourceSummary:
    """Aggregated cost, token, and timing resources for a campaign scope."""

    total_cost_usd: float | None = None
    total_provider_cost_usd: float | None = None
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    total_tokens: int | None = None
    total_reasoning_tokens: int | None = None
    total_api_duration_ms: float | None = None
    total_wall_duration_ms: float | None = None
    mean_cost_per_complete_trial_usd: float | None = None
    mean_tokens_per_complete_trial: float | None = None
    mean_api_duration_per_complete_trial_ms: float | None = None
    partial_pricing: bool = False
    retained_failed_call_cost_usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return _encode(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResourceSummary:
        return _dataclass_from_dict(cls, data)


# ── Judge evidence and raw attempts ──────────────────────────────────────────


@dataclass
class JudgeMemberResult:
    """One judge member's score for a single target output."""

    member_id: str
    model_id: str
    passed: bool | None = None
    score: float | None = None
    rationale: str | None = None
    structured_result: dict[str, Any] | None = None
    provider_route_metadata: dict[str, Any] | None = None
    token_usage: dict[str, Any] | None = None
    api_duration_ms: float | None = None
    cost_usd: float | None = None
    error: str | None = None
    cache_hit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _encode(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JudgeMemberResult:
        return _dataclass_from_dict(cls, data)


@dataclass
class JudgeEvidence:
    """Campaign-scoped judge evidence for an attempt or fixture aggregate."""

    judge_config_hash: str | None = None
    aggregation_method: str = "majority"
    final_passed: bool | None = None
    final_score: float | None = None
    members: list[JudgeMemberResult] = field(default_factory=list)
    cache_key: str | None = None
    error: str | None = None
    exhausted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _encode(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JudgeEvidence:
        return _dataclass_from_dict(cls, data)


@dataclass
class RawAttempt:
    """One immutable raw attempt within a campaign trial."""

    identity: AttemptIdentity
    status: AttemptStatus
    model_output: str = ""
    parsed_payload: dict[str, Any] | None = None
    raw_structured_output: str | None = None
    structured_error: str | None = None
    passed: bool | None = None
    similarity: float | None = None
    error: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None
    cost_usd: float | None = None
    provider_cost_usd: float | None = None
    api_duration_ms: float | None = None
    duration_ms: float | None = None
    request_telemetry: dict[str, Any] | None = None
    provider_route_metadata: dict[str, Any] | None = None
    provenance: Provenance | None = None
    retry_history: list[dict[str, Any]] = field(default_factory=list)
    judge_evidence: JudgeEvidence | None = None
    safety_state: str | None = None
    safety_cost_usd: float | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _encode(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RawAttempt:
        return _dataclass_from_dict(cls, data)


# ── Aggregates and trials ────────────────────────────────────────────────────


@dataclass
class FixtureAggregate:
    """Repeated-trial aggregate for a single fixture."""

    fixture_id: str
    benchmark: str | None = None
    model_id: str | None = None
    reasoning_effort: str | None = None
    output_mode: str | None = None
    planned_trials: int = 0
    completed_trials: int = 0
    valid_attempts: int = 0
    passing_attempts: int = 0
    failing_attempts: int = 0
    excluded_attempts: int = 0
    mean_success_rate: float | None = None
    pass_any_at_n: dict[int, bool] = field(default_factory=dict)
    reliability_classification: FixtureReliability = FixtureReliability.UNKNOWN
    incomplete: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = _encode(asdict(self))
        # JSON keys must be strings; preserve int-key semantics on load.
        if "pass_any_at_n" in data:
            data["pass_any_at_n"] = {
                str(k): v for k, v in data["pass_any_at_n"].items()
            }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FixtureAggregate:
        if "pass_any_at_n" in data:
            data["pass_any_at_n"] = {
                int(k): v for k, v in data["pass_any_at_n"].items()
            }
        return _dataclass_from_dict(cls, data)


def _identity_benchmark(identity: AttemptIdentity) -> str:
    """Return the benchmark for an identity, falling back to qualified IDs."""
    if identity.benchmark:
        return identity.benchmark
    if "/" in identity.fixture_id:
        return identity.fixture_id.split("/", 1)[0]
    return ""


def _identity_fixture_key(identity: AttemptIdentity) -> tuple[str, str]:
    """Return the benchmark/fixture pair for exact aggregate grouping."""
    return (_identity_benchmark(identity), identity.fixture_id)


def compute_fixture_aggregates(campaign: Campaign) -> list[FixtureAggregate]:
    """Compute fixture-level reliability aggregates from raw attempts.

    Groups attempts by fixture and computes explicit reliability metrics:
    mean success rate, pass-any-at-N, and stable/flaky/stable-fail
    classifications.  Only valid quality attempts contribute to the
    success-rate denominator.
    """
    # Index attempts by exact comparison dimensions.
    attempts_by_fixture: dict[
        tuple[str, str, str, str, str], list[RawAttempt]
    ] = {}
    for attempt in campaign.raw_attempts:
        key = (
            _identity_benchmark(attempt.identity),
            attempt.identity.fixture_id,
            attempt.identity.model_id,
            attempt.identity.reasoning_effort,
            attempt.identity.output_mode,
        )
        attempts_by_fixture.setdefault(key, []).append(attempt)

    planned_keys: set[tuple[str, str, str, str, str]] = set()
    for trial in campaign.trials:
        for identity in trial.attempt_identities:
            planned_keys.add(
                (
                    _identity_benchmark(identity),
                    identity.fixture_id,
                    identity.model_id,
                    identity.reasoning_effort,
                    identity.output_mode,
                )
            )
    if not planned_keys:
        if campaign.raw_attempts:
            planned_keys.update(attempts_by_fixture.keys())
        else:
            for benchmark_id in campaign.config.benchmark_ids or [""]:
                for fixture_id in campaign.config.fixture_ids:
                    for model_id in campaign.config.model_ids:
                        for reasoning_effort in campaign.config.reasoning_efforts or ["none"]:
                            for output_mode in campaign.config.output_modes:
                                planned_keys.add(
                                    (
                                        benchmark_id,
                                        fixture_id,
                                        model_id,
                                        reasoning_effort,
                                        output_mode,
                                    )
                                )

    aggregates: list[FixtureAggregate] = []
    for benchmark, fixture_id, model_id, reasoning_effort, output_mode in sorted(planned_keys):
        attempts = attempts_by_fixture.get(
            (benchmark, fixture_id, model_id, reasoning_effort, output_mode), []
        )
        valid_attempts = [a for a in attempts if a.status.is_quality_outcome()]
        passing = [a for a in valid_attempts if a.passed]
        failing = [a for a in valid_attempts if not a.passed]
        excluded = [a for a in attempts if not a.status.is_quality_outcome()]

        valid_count = len(valid_attempts)
        passing_count = len(passing)
        mean_success_rate = (
            round(passing_count / valid_count, 4) if valid_count > 0 else None
        )

        # Completed trials are those with at least one attempt recorded for
        # this fixture.  For a balanced campaign this equals the number of
        # trials where the fixture was attempted.
        trial_indices = {a.identity.trial_index for a in attempts}
        completed_trials = len(trial_indices)

        # pass_any_at_n for each planned trial count up to the actual count.
        pass_any_at_n: dict[int, bool] = {}
        sorted_valid = sorted(
            valid_attempts, key=lambda a: a.identity.trial_index
        )
        for n in range(1, max(completed_trials, 1) + 1):
            first_n = sorted_valid[:n]
            pass_any_at_n[n] = any(a.passed for a in first_n)

        if valid_count == 0:
            classification = FixtureReliability.UNKNOWN
        elif passing_count == valid_count:
            classification = FixtureReliability.STABLE_PASS
        elif passing_count == 0:
            classification = FixtureReliability.STABLE_FAIL
        else:
            classification = FixtureReliability.FLAKY

        if campaign.legacy:
            classification = FixtureReliability.UNKNOWN

        incomplete = completed_trials < campaign.config.planned_trial_count or bool(
            excluded
        )

        aggregates.append(
            FixtureAggregate(
                fixture_id=fixture_id,
                benchmark=benchmark or None,
                model_id=model_id or None,
                reasoning_effort=reasoning_effort or None,
                output_mode=output_mode or None,
                planned_trials=campaign.config.planned_trial_count,
                completed_trials=completed_trials,
                valid_attempts=valid_count,
                passing_attempts=passing_count,
                failing_attempts=len(failing),
                excluded_attempts=len(excluded),
                mean_success_rate=mean_success_rate,
                pass_any_at_n=pass_any_at_n,
                reliability_classification=classification,
                incomplete=incomplete,
            )
        )

    return aggregates


@dataclass
class Trial:
    """One complete numbered trial round within a campaign."""

    trial_index: int
    planned_attempts: int = 0
    completed_attempts: int = 0
    valid_attempts: int = 0
    passing_attempts: int = 0
    excluded_attempts: int = 0
    complete: bool = False
    attempt_identities: list[AttemptIdentity] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _encode(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Trial:
        return _dataclass_from_dict(cls, data)


@dataclass
class ModelCampaignSummary:
    """Campaign-level aggregate for a single model."""

    model_id: str
    reasoning_effort: str | None = None
    output_mode: str | None = None
    planned_trials: int = 0
    completed_trials: int = 0
    valid_attempts: int = 0
    passing_attempts: int = 0
    excluded_attempts: int = 0
    mean_success_rate: float | None = None
    pass_any_at_n: dict[int, bool] = field(default_factory=dict)
    resource_summary: ResourceSummary | None = None
    incomplete: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = _encode(asdict(self))
        if "pass_any_at_n" in data:
            data["pass_any_at_n"] = {
                str(k): v for k, v in data["pass_any_at_n"].items()
            }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelCampaignSummary:
        if "pass_any_at_n" in data:
            data["pass_any_at_n"] = {
                int(k): v for k, v in data["pass_any_at_n"].items()
            }
        return _dataclass_from_dict(cls, data)


@dataclass
class BenchmarkCampaignSummary:
    """Campaign-level aggregate for a single benchmark."""

    benchmark: str
    planned_trials: int = 0
    completed_trials: int = 0
    valid_attempts: int = 0
    passing_attempts: int = 0
    excluded_attempts: int = 0
    mean_success_rate: float | None = None
    pass_any_at_n: dict[int, bool] = field(default_factory=dict)
    resource_summary: ResourceSummary | None = None
    incomplete: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = _encode(asdict(self))
        if "pass_any_at_n" in data:
            data["pass_any_at_n"] = {
                str(k): v for k, v in data["pass_any_at_n"].items()
            }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkCampaignSummary:
        if "pass_any_at_n" in data:
            data["pass_any_at_n"] = {
                int(k): v for k, v in data["pass_any_at_n"].items()
            }
        return _dataclass_from_dict(cls, data)


# ── Campaign configuration and manifest ───────────────────────────────────────


@dataclass
class CampaignConfig:
    """Immutable campaign configuration recorded at creation time."""

    campaign_id: str
    created_at: str
    benchmark_ids: list[str] = field(default_factory=list)
    fixture_ids: list[str] = field(default_factory=list)
    model_ids: list[str] = field(default_factory=list)
    reasoning_efforts: list[str] = field(default_factory=list)
    output_modes: list[str] = field(default_factory=list)
    planned_trial_count: int = 3
    scorer_config: dict[str, Any] | None = None
    judge_config: dict[str, Any] | None = None
    request_config: dict[str, Any] | None = None
    request_config_hash: str | None = None
    scorer_config_hash: str | None = None
    expected_fixture_hashes: dict[str, FixtureExpectedHashes] = field(
        default_factory=dict
    )
    fixture_generation_version: str = ""
    result_schema_version: int = 1
    scheduler_version: str = "campaign-scheduler-v1"
    scheduler_seed: int | None = None
    safety_review_config: dict[str, Any] | None = None
    campaign_schema_version: str = CAMPAIGN_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _encode(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CampaignConfig:
        return _dataclass_from_dict(cls, data)

    def compute_hash(self) -> str:
        """Return a deterministic hash of this configuration."""
        return compute_config_hash(self.to_dict())


@dataclass
class Campaign:
    """Versioned campaign manifest and all associated attempts/aggregates."""

    campaign_id: str
    config: CampaignConfig
    config_hash: str
    state: CampaignState
    planned_attempts: int = 0
    completed_attempts: int = 0
    valid_attempts: int = 0
    passing_attempts: int = 0
    excluded_attempts: int = 0
    trials: list[Trial] = field(default_factory=list)
    raw_attempts: list[RawAttempt] = field(default_factory=list)
    fixture_aggregates: list[FixtureAggregate] = field(default_factory=list)
    resource_summary: ResourceSummary | None = None
    publication_state: PublicationState = PublicationState.DRAFT
    safety_summary: dict[str, Any] | None = None
    legacy: bool = False
    created_at: str = field(default_factory=_now_iso)
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _encode(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Campaign:
        return _dataclass_from_dict(cls, data)

    def to_manifest_dict(self) -> dict[str, Any]:
        """Return the ``campaign.json`` manifest representation."""
        return self.to_dict()

    @classmethod
    def from_manifest_dict(cls, data: dict[str, Any]) -> Campaign:
        """Load a campaign from a ``campaign.json`` manifest."""
        return cls.from_dict(data)

    def refresh_config_hash(self) -> None:
        """Recompute and store the configuration hash from ``config``."""
        self.config_hash = self.config.compute_hash()

    def validate_attempt(
        self, attempt: RawAttempt
    ) -> AttemptStatus | None:
        """Compare an attempt's provenance against the campaign manifest.

        Returns :attr:`AttemptStatus.HASH_MISMATCH` when the fixture or
        configuration hashes recorded by the attempt differ from the expected
        hashes in ``config``.  Returns ``None`` when the attempt is compatible
        or when no expected hashes are configured for the fixture.
        """
        provenance = attempt.provenance
        if provenance is None:
            return AttemptStatus.HASH_MISMATCH

        cfg = self.config
        if (
            cfg.fixture_generation_version
            and provenance.fixture_generation_version != cfg.fixture_generation_version
        ):
            return AttemptStatus.HASH_MISMATCH
        if (
            cfg.scheduler_seed is not None
            and provenance.scheduler_seed != cfg.scheduler_seed
        ):
            return AttemptStatus.HASH_MISMATCH

        expected = cfg.expected_fixture_hashes.get(attempt.identity.fixture_id)
        if expected is None and attempt.identity.benchmark:
            expected = cfg.expected_fixture_hashes.get(
                f"{attempt.identity.benchmark}/{attempt.identity.fixture_id}"
            )
        if expected is None:
            return AttemptStatus.HASH_MISMATCH

        checks: list[tuple[str | None, str | None]] = [
            (expected.fixture_input_hash, provenance.fixture_input_hash),
            (expected.rendered_prompt_hash, provenance.rendered_prompt_hash),
            (expected.expected_hash, provenance.expected_hash),
            (expected.scoring_input_hash, provenance.scoring_input_hash),
            (expected.request_config_hash, provenance.request_config_hash),
            (expected.scorer_config_hash, provenance.scorer_config_hash),
        ]
        for expected_value, actual_value in checks:
            if expected_value is not None and actual_value != expected_value:
                return AttemptStatus.HASH_MISMATCH
        return None

    def classify_attempts(self) -> list[RawAttempt]:
        """Re-evaluate every raw attempt against the manifest and update status.

        Attempts that fail the provenance check are marked
        :attr:`AttemptStatus.HASH_MISMATCH`.  Other statuses are preserved.
        """
        for attempt in self.raw_attempts:
            mismatch = self.validate_attempt(attempt)
            if mismatch is not None:
                attempt.status = mismatch
        return self.raw_attempts


# ── Versioned campaign report schema ─────────────────────────────────────────


CAMPAIGN_REPORT_SCHEMA_VERSION = 2


@dataclass
class CampaignReport:
    """Generated report artifact for a completed campaign.

    Replaces the previous single-result-per-fixture schema with explicit
    campaign summaries, reliability aggregates, and raw-attempt references.
    """

    version: int
    schema_version: int
    generated_at: str
    campaign: Campaign
    model_summaries: list[ModelCampaignSummary] = field(default_factory=list)
    benchmark_summaries: list[BenchmarkCampaignSummary] = field(default_factory=list)
    resource_summaries: list[ResourceSummary] = field(default_factory=list)
    judge_evidence: list[JudgeEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _encode(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CampaignReport:
        return _dataclass_from_dict(cls, data)


# ── Convenience factories ────────────────────────────────────────────────────


def make_campaign(
    campaign_id: str,
    *,
    benchmark_ids: list[str] | None = None,
    fixture_ids: list[str] | None = None,
    model_ids: list[str] | None = None,
    reasoning_efforts: list[str] | None = None,
    output_modes: list[str] | None = None,
    planned_trial_count: int = 3,
    scheduler_seed: int | None = None,
    fixture_generation_version: str = "",
    result_schema_version: int = 1,
    scorer_config: dict[str, Any] | None = None,
    judge_config: dict[str, Any] | None = None,
    request_config: dict[str, Any] | None = None,
    request_config_hash: str | None = None,
    scorer_config_hash: str | None = None,
    scheduler_version: str = "campaign-scheduler-v1",
    safety_review_config: dict[str, Any] | None = None,
) -> Campaign:
    """Create a new campaign with a consistent manifest hash and timestamps."""
    created_at = _now_iso()
    config = CampaignConfig(
        campaign_id=campaign_id,
        created_at=created_at,
        benchmark_ids=list(benchmark_ids or []),
        fixture_ids=list(fixture_ids or []),
        model_ids=list(model_ids or []),
        reasoning_efforts=list(reasoning_efforts or []),
        output_modes=list(output_modes or []),
        planned_trial_count=planned_trial_count,
        scheduler_seed=scheduler_seed,
        fixture_generation_version=fixture_generation_version,
        result_schema_version=result_schema_version,
        scorer_config=scorer_config,
        judge_config=judge_config,
        request_config=request_config,
        request_config_hash=request_config_hash,
        scorer_config_hash=scorer_config_hash,
        scheduler_version=scheduler_version,
        safety_review_config=safety_review_config,
    )
    return Campaign(
        campaign_id=campaign_id,
        config=config,
        config_hash=config.compute_hash(),
        state=CampaignState.PLANNED,
        created_at=created_at,
    )

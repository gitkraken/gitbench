"""Campaign result store for immutable raw-attempt envelopes.

This module handles persistence of campaign manifests and per-attempt
envelopes under ``gitbench-results/<campaign-id>/``.  It is intentionally
separate from execution logic so that runners and resume logic can share a
single atomic update mechanism.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from gitbench.harness.campaign import (
    AttemptIdentity,
    AttemptStatus,
    Campaign,
    CampaignState,
    PublicationState,
    RawAttempt,
    hash_request_config,
    hash_scorer_config,
)
from gitbench.harness.scheduler import SCHEDULER_VERSION


def _identity_key(identity: AttemptIdentity) -> tuple[str, int, str, str, str, str, str]:
    """Return the exact key used for campaign attempt identity comparisons."""
    return (
        identity.campaign_id,
        identity.trial_index,
        identity.model_id,
        identity.reasoning_effort,
        identity.output_mode,
        identity.benchmark,
        identity.fixture_id,
    )


def validate_resume_compatibility(
    campaign: Campaign,
    *,
    benchmark_ids: list[str] | None = None,
    fixture_ids: list[str] | None = None,
    model_ids: list[str] | None = None,
    reasoning_efforts: list[str] | None = None,
    output_modes: list[str] | None = None,
    planned_trial_count: int | None = None,
    request_config: dict[str, Any] | None = None,
    scorer_config: dict[str, Any] | None = None,
    fixture_generation_version: str | None = None,
    scheduler_seed: int | None = None,
    scheduler_version: str | None = None,
) -> None:
    """Reject resume when requested immutable inputs differ from the manifest."""
    cfg = campaign.config
    checks: list[tuple[str, Any, Any]] = []
    if benchmark_ids is not None:
        checks.append(("benchmark_ids", sorted(benchmark_ids), sorted(cfg.benchmark_ids)))
    if fixture_ids is not None:
        checks.append(("fixture_ids", sorted(fixture_ids), sorted(cfg.fixture_ids)))
    if model_ids is not None:
        checks.append(("model_ids", sorted(model_ids), sorted(cfg.model_ids)))
    if reasoning_efforts is not None:
        checks.append(
            ("reasoning_efforts", sorted(reasoning_efforts), sorted(cfg.reasoning_efforts))
        )
    if output_modes is not None:
        checks.append(("output_modes", list(output_modes), list(cfg.output_modes)))
    if planned_trial_count is not None:
        checks.append(("planned_trial_count", planned_trial_count, cfg.planned_trial_count))
    if fixture_generation_version is not None:
        checks.append(
            (
                "fixture_generation_version",
                fixture_generation_version,
                cfg.fixture_generation_version,
            )
        )
    if scheduler_seed is not None:
        checks.append(("scheduler_seed", scheduler_seed, cfg.scheduler_seed))
    if scheduler_version is not None:
        checks.append(("scheduler_version", scheduler_version, cfg.scheduler_version))
    if request_config is not None:
        checks.append(
            (
                "request_config_hash",
                hash_request_config(request_config),
                cfg.request_config_hash,
            )
        )
    if scorer_config is not None:
        checks.append(
            (
                "scorer_config_hash",
                hash_scorer_config(scorer_config),
                cfg.scorer_config_hash,
            )
        )

    for field, requested, persisted in checks:
        if requested != persisted:
            raise ValueError(
                f"Campaign resume incompatible for {field}: "
                f"requested {requested!r}, persisted {persisted!r}"
            )


def build_resume_plan(campaign: Campaign, store: CampaignStore) -> list[AttemptIdentity]:
    """Return identities that must be executed to resume a campaign.

    Loads existing envelopes from ``store`` and the campaign's schedule
    (expected to be present in ``campaign._schedule``).  Returns identities
    that are missing, have incompatible provenance, or are marked for repair.
    Valid compatible existing attempts are not rescheduled.

    Args:
        campaign: Campaign manifest with schedule information.
        store: Store used to read existing attempt envelopes.

    Returns:
        List of attempt identities still needed to complete the campaign.
    """
    if campaign.config.scheduler_version != SCHEDULER_VERSION:
        raise ValueError(
            "Campaign resume incompatible for scheduler_version: "
            f"persisted {campaign.config.scheduler_version!r}, "
            f"supported {SCHEDULER_VERSION!r}"
        )

    schedule = getattr(campaign, "_schedule", None)
    if schedule is None:
        schedule_identities = [
            identity
            for trial in campaign.trials
            for identity in trial.attempt_identities
        ]
    else:
        schedule_identities = list(schedule.identities)

    existing: set[tuple[str, int, str, str, str, str, str]] = set()
    for attempt in store.load_all_attempts():
        existing.add(_identity_key(attempt.identity))

    missing: list[AttemptIdentity] = []
    for identity in schedule_identities:
        key = _identity_key(identity)
        if key not in existing:
            missing.append(identity)
            continue
        attempt = store.load_attempt(identity)
        mismatch = campaign.validate_attempt(attempt)
        if mismatch is not None or attempt.status in (
            AttemptStatus.HASH_MISMATCH,
            AttemptStatus.INVALID_INPUT,
        ):
            missing.append(identity)

    return missing


class CampaignStore:
    """Filesystem-backed store for a single campaign."""

    def __init__(self, campaign_id: str, base_dir: str | Path = "gitbench-results") -> None:
        self.campaign_id = campaign_id
        self.base_dir = Path(base_dir)
        self.campaign_dir = self.base_dir / campaign_id
        self.manifest_path = self.campaign_dir / "campaign.json"
        self.envelopes_dir = self.campaign_dir / "envelopes"

    def ensure_dirs(self) -> None:
        """Create campaign directories if they do not exist."""
        self.campaign_dir.mkdir(parents=True, exist_ok=True)
        self.envelopes_dir.mkdir(parents=True, exist_ok=True)

    def load_manifest(self) -> Campaign | None:
        """Load the campaign manifest if it exists."""
        if not self.manifest_path.exists():
            return None
        data = json.loads(self.manifest_path.read_text())
        return Campaign.from_manifest_dict(data)

    def save_manifest(self, campaign: Campaign) -> Path:
        """Atomically write the campaign manifest."""
        self.ensure_dirs()
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(self.campaign_dir),
            prefix=".campaign.json.tmp-",
        )
        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(campaign.to_manifest_dict(), f, indent=2)
            os.replace(tmp_path, self.manifest_path)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise
        return self.manifest_path

    def _envelope_path(self, identity: AttemptIdentity) -> Path:
        """Return the envelope path for an attempt identity."""
        benchmark = identity.benchmark.replace("/", "_").replace(":", "-")
        benchmark_segment = f"{benchmark}_" if benchmark else ""
        filename = (
            f"trial-{identity.trial_index:04d}_"
            f"{identity.model_id.replace('/', '_').replace(':', '-')}_"
            f"{identity.reasoning_effort}_"
            f"{identity.output_mode}_"
            f"{benchmark_segment}"
            f"{identity.fixture_id.replace('/', '_')}.json"
        )
        return self.envelopes_dir / filename

    def _legacy_envelope_path(self, identity: AttemptIdentity) -> Path:
        """Return the pre-benchmark-dimension envelope path for compatibility."""
        filename = (
            f"trial-{identity.trial_index:04d}_"
            f"{identity.model_id.replace('/', '_').replace(':', '-')}_"
            f"{identity.reasoning_effort}_"
            f"{identity.output_mode}_"
            f"{identity.fixture_id.replace('/', '_')}.json"
        )
        return self.envelopes_dir / filename

    def attempt_exists(self, identity: AttemptIdentity) -> bool:
        """Return True when an envelope exists for the identity."""
        if self._envelope_path(identity).exists():
            return True
        try:
            self.load_attempt(identity)
            return True
        except FileNotFoundError:
            return False

    def write_attempt(self, attempt: RawAttempt) -> Path:
        """Atomically write a raw-attempt envelope and return its path."""
        self.ensure_dirs()
        path = self._envelope_path(attempt.identity)
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(self.envelopes_dir),
            prefix=f".{path.name}.tmp-",
        )
        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(attempt.to_dict(), f, indent=2)
            os.replace(tmp_path, path)
            legacy_path = self._legacy_envelope_path(attempt.identity)
            if legacy_path != path and legacy_path.exists():
                try:
                    legacy_attempt = RawAttempt.from_dict(
                        json.loads(legacy_path.read_text())
                    )
                except Exception:
                    legacy_attempt = None
                if legacy_attempt is not None and _identity_key(
                    legacy_attempt.identity
                ) == _identity_key(attempt.identity):
                    legacy_path.unlink()
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise
        return path

    def repair_attempt(self, attempt: RawAttempt) -> Path:
        """Write a replacement attempt while preserving prior failure history.

        Loads any existing envelope for the same identity and appends its
        contents to the new attempt's ``retry_history`` before writing, so
        transient repair does not erase earlier retries or failures.
        """
        if self.attempt_exists(attempt.identity):
            existing = self.load_attempt(attempt.identity)
            prior_history: list[dict[str, Any]] = list(existing.retry_history or [])
            prior = existing.to_dict()
            # Keep a lightweight snapshot of the prior attempt for auditability.
            prior_history.append(
                {
                    "status": prior.get("status"),
                    "error": prior.get("error"),
                    "request_telemetry": prior.get("request_telemetry"),
                    "created_at": prior.get("created_at"),
                }
            )
            attempt.retry_history = prior_history + list(attempt.retry_history or [])
        return self.write_attempt(attempt)

    def load_attempt(self, identity: AttemptIdentity) -> RawAttempt:
        """Load a raw-attempt envelope by identity."""
        path = self._envelope_path(identity)
        if path.exists():
            data = json.loads(path.read_text())
            return RawAttempt.from_dict(data)

        legacy_path = self._legacy_envelope_path(identity)
        if legacy_path.exists():
            attempt = RawAttempt.from_dict(json.loads(legacy_path.read_text()))
            if _identity_key(attempt.identity) == _identity_key(identity):
                return attempt

        raise FileNotFoundError(path)

    def list_attempt_envelopes(self) -> list[Path]:
        """Return all attempt envelope paths."""
        if not self.envelopes_dir.exists():
            return []
        return sorted(self.envelopes_dir.glob("trial-*.json"))

    def load_all_attempts(self) -> list[RawAttempt]:
        """Load every attempt envelope in this campaign."""
        attempts_by_identity: dict[
            tuple[str, int, str, str, str, str, str], RawAttempt
        ] = {}
        for path in self.list_attempt_envelopes():
            try:
                attempt = RawAttempt.from_dict(json.loads(path.read_text()))
                attempts_by_identity[_identity_key(attempt.identity)] = attempt
            except Exception:
                continue
        return list(attempts_by_identity.values())


def review_campaign_safety(
    campaign: Campaign,
    processor: Any,
    store: CampaignStore,
) -> Campaign:
    """Review every retained raw attempt with the configured safety processor.

    Mutates ``campaign`` in place: sets ``safety_state`` and
    ``safety_cost_usd`` on each raw attempt, updates ``publication_state``,
    and stores a ``safety_summary`` with reviewed/sanitized/blocked/pending
    counts.  The updated manifest is persisted through ``store``.
    """
    attempts = store.load_all_attempts() or campaign.raw_attempts
    reviewed = 0
    sanitized = 0
    blocked = 0
    pending = 0

    for attempt in attempts:
        if not attempt.model_output:
            attempt.safety_state = "reviewed"
            reviewed += 1
            continue

        payload = {
            "results": [
                {
                    "benchmark": attempt.identity.fixture_id.split("/")[0]
                    if "/" in attempt.identity.fixture_id
                    else "",
                    "scores": [
                        {
                            "fixture_id": attempt.identity.fixture_id,
                            "model_output": attempt.model_output,
                            "passed": attempt.passed,
                            "similarity": attempt.similarity,
                            "error": attempt.error,
                            "raw_structured_output": attempt.raw_structured_output,
                            "parsed_payload": attempt.parsed_payload,
                            "structured_error": attempt.structured_error,
                        }
                    ],
                }
            ]
        }

        try:
            reviewed_result = processor.review_payload(payload)
            score = reviewed_result.payload["results"][0]["scores"][0]
            metadata = score.get("safety_review", {})
            status = metadata.get("status")
            if status == "redacted":
                attempt.safety_state = "blocked"
                attempt.model_output = score.get("model_output", attempt.model_output)
                blocked += 1
                if score.get("model_output") != attempt.model_output:
                    sanitized += 1
            else:
                attempt.safety_state = "reviewed"
                reviewed += 1
            attempt.safety_cost_usd = attempt.safety_cost_usd or 0.0
        except Exception:
            attempt.safety_state = "pending"
            pending += 1

        store.write_attempt(attempt)

    campaign.safety_summary = {
        "reviewed": reviewed,
        "sanitized": sanitized,
        "blocked": blocked,
        "pending": pending,
    }

    if pending or blocked:
        campaign.publication_state = PublicationState.DRAFT
    elif campaign.state == CampaignState.COMPLETE and reviewed:
        campaign.publication_state = PublicationState.PUBLISHED
    elif reviewed:
        campaign.publication_state = PublicationState.PUBLISHABLE
    else:
        campaign.publication_state = PublicationState.DRAFT

    store.save_manifest(campaign)
    return campaign


def update_campaign_counts(campaign: Campaign) -> None:
    """Recompute campaign completion and validity counts from raw attempts.

    Mutates ``campaign`` in place: updates ``planned_attempts``,
    ``completed_attempts``, ``valid_attempts``, ``passing_attempts``,
    ``excluded_attempts``, and trial summaries.  The campaign state is set to
    :attr:`CampaignState.COMPLETE` when every planned attempt has a valid
    quality outcome, otherwise :attr:`CampaignState.INCOMPLETE`.
    """
    campaign.raw_attempts = list(campaign.raw_attempts)

    # Planned attempts come from trial metadata; fall back to the number of
    # recorded identities when planned_attempts has not been initialized.
    campaign.planned_attempts = sum(
        trial.planned_attempts
        if trial.planned_attempts > 0
        else len(trial.attempt_identities)
        for trial in campaign.trials
    )

    # Index attempts by identity and trial.
    attempts_by_trial: dict[int, list[RawAttempt]] = {}
    for attempt in campaign.raw_attempts:
        attempts_by_trial.setdefault(attempt.identity.trial_index, []).append(attempt)

    completed = 0
    valid = 0
    passing = 0
    excluded = 0
    for trial in campaign.trials:
        trial_identities = set(
            (a.model_id, a.reasoning_effort, a.output_mode, a.benchmark, a.fixture_id)
            for a in trial.attempt_identities
        )
        trial_attempts = attempts_by_trial.get(trial.trial_index, [])
        trial_completed: list[RawAttempt] = []
        for attempt in trial_attempts:
            key = (
                attempt.identity.model_id,
                attempt.identity.reasoning_effort,
                attempt.identity.output_mode,
                attempt.identity.benchmark,
                attempt.identity.fixture_id,
            )
            if key in trial_identities:
                trial_completed.append(attempt)

        trial.completed_attempts = len(trial_completed)
        trial.valid_attempts = sum(
            1 for a in trial_completed if a.status.is_quality_outcome()
        )
        trial.passing_attempts = sum(
            1 for a in trial_completed
            if a.status.is_quality_outcome() and a.passed
        )
        trial.excluded_attempts = len(trial_completed) - trial.valid_attempts
        planned = (
            trial.planned_attempts
            if trial.planned_attempts > 0
            else len(trial.attempt_identities)
        )
        trial.complete = (
            trial.completed_attempts == planned
            and trial.excluded_attempts == 0
        )

        completed += trial.completed_attempts
        valid += trial.valid_attempts
        passing += trial.passing_attempts
        excluded += trial.excluded_attempts

    campaign.completed_attempts = completed
    campaign.valid_attempts = valid
    campaign.passing_attempts = passing
    campaign.excluded_attempts = excluded

    if (
        campaign.planned_attempts > 0
        and campaign.completed_attempts == campaign.planned_attempts
        and campaign.excluded_attempts == 0
    ):
        campaign.state = CampaignState.COMPLETE
    else:
        campaign.state = CampaignState.INCOMPLETE

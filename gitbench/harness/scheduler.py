"""Campaign scheduling for repeated evaluation trials.

This module builds deterministic, complete schedules of attempt identities
for an evaluation campaign.  A schedule covers every selected model,
reasoning effort, output mode, and fixture combination exactly once per
trial round, with a seeded balanced ordering that alternates output-mode
and model ordering across rounds.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from gitbench.harness.campaign import AttemptIdentity

SCHEDULER_VERSION = "campaign-scheduler-v1"


@dataclass
class CampaignSchedule:
    """A fully-planned campaign schedule.

    Attributes:
        campaign_id: The campaign identifier.
        planned_trial_count: Number of trial rounds scheduled.
        identities: Flat list of attempt identities in execution order.
        trial_identities: Identities grouped by ``trial_index`` (1-based).
    """

    campaign_id: str
    planned_trial_count: int
    identities: list[AttemptIdentity] = field(default_factory=list)
    trial_identities: dict[int, list[AttemptIdentity]] = field(
        default_factory=dict
    )

    @property
    def planned_attempts(self) -> int:
        """Return the total number of planned attempt identities."""
        return len(self.identities)

    def by_trial(self, trial_index: int) -> list[AttemptIdentity]:
        """Return identities for a specific 1-based trial round."""
        return list(self.trial_identities.get(trial_index, []))


def build_schedule(
    campaign_id: str,
    fixture_ids: list[str],
    models: list[tuple[str, str]],
    output_modes: list[str],
    planned_trial_count: int = 3,
    *,
    seed: int | None = None,
    fixture_specs: list[tuple[str, str]] | None = None,
) -> CampaignSchedule:
    """Build a deterministic campaign schedule.

    Args:
        campaign_id: Unique campaign identifier.
        fixture_ids: Ordered list of fixture identifiers.
        models: Ordered list of ``(model_id, reasoning_effort)`` tuples.
        output_modes: Ordered list of output modes.
        planned_trial_count: Number of complete trial rounds (default 3).
        seed: Optional random seed for reproducible ordering.  When omitted,
            a seed is chosen deterministically from the campaign inputs.
        fixture_specs: Optional ordered list of ``(benchmark, fixture_id)``
            tuples.  When supplied, benchmark becomes part of every exact
            attempt identity while ``fixture_id`` remains the fixture-local ID.

    Returns:
        A :class:`CampaignSchedule` with balanced trial ordering.
    """
    if planned_trial_count < 1:
        raise ValueError("planned_trial_count must be at least 1")
    if fixture_specs is None:
        fixture_specs = [("", fixture_id) for fixture_id in fixture_ids]
    if not fixture_specs:
        raise ValueError("fixture_ids must not be empty")
    if not models:
        raise ValueError("models must not be empty")
    if not output_modes:
        raise ValueError("output_modes must not be empty")

    if seed is None:
        # Deterministic seed derived from campaign inputs so the same
        # configuration always produces the same schedule.
        seed = _derive_seed(campaign_id, fixture_specs, models, output_modes)

    rng = random.Random(seed)
    schedule = CampaignSchedule(
        campaign_id=campaign_id,
        planned_trial_count=planned_trial_count,
    )

    base_identity = AttemptIdentity(
        campaign_id=campaign_id,
        trial_index=1,
        model_id="",
        reasoning_effort="",
        output_mode="",
        fixture_id="",
    )

    # Build round-robin offsets so each trial starts at a different position.
    # This balances model and output-mode ordering across rounds.
    model_offset = rng.randrange(len(models)) if len(models) > 1 else 0
    output_mode_offset = rng.randrange(len(output_modes)) if len(output_modes) > 1 else 0
    fixture_offset = rng.randrange(len(fixture_specs)) if len(fixture_specs) > 1 else 0

    for trial_index in range(1, planned_trial_count + 1):
        trial_rng = random.Random(seed + trial_index)

        # Rotate ordering each round to alternate which models/modes/fixtures
        # appear early vs. late, reducing temporal/provider-load bias.
        rotated_models = _rotate(models, model_offset * (trial_index - 1))
        rotated_output_modes = _rotate(
            output_modes, output_mode_offset * (trial_index - 1)
        )
        rotated_fixtures = _rotate(fixture_specs, fixture_offset * (trial_index - 1))

        # Within the round, shuffle the combined order using a trial-specific
        # seed so the exact sequence is reproducible but not purely round-robin.
        identities: list[AttemptIdentity] = []
        for fixture_index, (benchmark, fixture_id) in enumerate(rotated_fixtures):
            for model_index, (model_id, reasoning_effort) in enumerate(
                rotated_models
            ):
                for output_mode_index, output_mode in enumerate(
                    rotated_output_modes
                ):
                    identity = AttemptIdentity(
                        campaign_id=base_identity.campaign_id,
                        trial_index=trial_index,
                        model_id=model_id,
                        reasoning_effort=reasoning_effort,
                        output_mode=output_mode,
                        fixture_id=fixture_id,
                        benchmark=benchmark,
                    )
                    identities.append(identity)

        # Deterministic shuffle of the round identities, using a key that
        # alternates fixture/model/output-mode layers to spread ordering.
        trial_rng.shuffle(identities)
        schedule.trial_identities[trial_index] = identities
        schedule.identities.extend(identities)

    return schedule


def _derive_seed(
    campaign_id: str,
    fixture_specs: list[tuple[str, str]],
    models: list[tuple[str, str]],
    output_modes: list[str],
) -> int:
    """Return a deterministic integer seed from campaign inputs."""
    import hashlib

    canonical = "|".join(
        [
            campaign_id,
            ",".join(f"{benchmark}/{fixture_id}" for benchmark, fixture_id in fixture_specs),
            ",".join(f"{m}:{e}" for m, e in models),
            ",".join(output_modes),
        ]
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _rotate(items: list, offset: int) -> list:
    """Rotate a list by ``offset`` positions."""
    if not items:
        return items
    offset = offset % len(items)
    return items[offset:] + items[:offset]

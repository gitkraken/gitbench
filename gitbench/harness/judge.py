"""LLM judge client for evaluating free-form text outputs."""

import hashlib
import json
import logging
import re
from typing import Any

from gitbench.harness.campaign import JudgeEvidence, JudgeMemberResult
from gitbench.harness.model import ModelInterface
from gitbench.harness.types import ModelMessage

logger = logging.getLogger(__name__)

JUDGE_COMMIT_MESSAGE_PROMPT = """You are evaluating the quality of a commit message for a git diff.

First, review the original prompt given to the model:

<original_prompt>
{prompt}
</original_prompt>

Score the commit message on a scale from 0.0 to 1.0 based on:
- Does it accurately describe the changes in the diff?
- Is it concise and well-structured?
- Does it follow the instructions in the original prompt (length limits, format, etc.)?
- Does it contain ONLY the commit message (no reasoning, no extra commentary)?
- Does it follow conventional commit message format?
- Does it capture the intent and scope of the change?

Penalize heavily if the response includes reasoning, explanations, or anything
other than the requested commit message.

Return ONLY a number between 0.0 and 1.0. Do not include any explanation.

Git diff:
{diff}

Commit message:
{message}

Score:"""


def _extract_text(response) -> str:
    """Extract text from a model response (dict or string)."""
    if isinstance(response, dict):
        return response.get("text", response.get("content", ""))
    return str(response)


def _parse_score(text: str) -> float:
    """Parse a numeric score from the judge model response.

    Args:
        text: The raw response text from the judge model.

    Returns:
        A float between 0.0 and 1.0.

    Raises:
        ValueError: If no numeric score can be extracted.
    """
    match = re.search(r"(-?\d+(?:\.\d+)?)", text)
    if not match:
        raise ValueError(
            f"Judge response could not be parsed as a number: {text!r}"
        )

    score = float(match.group(1))
    if score < 0.0:
        score = 0.0
    elif score > 1.0:
        score = 1.0
    return score


def compute_judge_config_hash(model_clients: list[ModelInterface]) -> str:
    """Return a deterministic hash for the judge configuration.

    The hash is based on the model identifiers, reasoning levels, and base
    URLs of the judge clients so that any change to the judge setup
    invalidates cached decisions.
    """
    identities: list[dict[str, Any]] = []
    for i, client in enumerate(model_clients):
        identities.append(
            {
                "index": i,
                "model_id": str(getattr(client, "model", None) or ""),
                "reasoning_level": str(getattr(client, "reasoning_level", None) or ""),
                "base_url": str(
                    getattr(client, "base_url", None)
                    or getattr(client, "_base_url", None)
                    or ""
                ),
            }
        )
    canonical = json.dumps(identities, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class JudgeCache:
    """Campaign-scoped cache for LLM-judge decisions.

    Keys are tuples of ``(fixture_input_hash, target_output_hash,
    judge_config_hash)``.  Values store the aggregated judge score and the
    per-member results so that repeated identical evaluations within a
    campaign reuse prior work without issuing duplicate judge calls.
    """

    def __init__(self) -> None:
        """Initialise an empty cache."""
        self._cache: dict[tuple[str, str, str], float] = {}

    def get(
        self,
        fixture_input_hash: str,
        target_output_hash: str,
        judge_config_hash: str,
    ) -> float | None:
        """Return a cached score or ``None`` when not present."""
        return self._cache.get((fixture_input_hash, target_output_hash, judge_config_hash))

    def set(
        self,
        fixture_input_hash: str,
        target_output_hash: str,
        judge_config_hash: str,
        score: float,
    ) -> None:
        """Store a score in the campaign-scoped cache."""
        self._cache[(fixture_input_hash, target_output_hash, judge_config_hash)] = score


class JudgeClient:
    """Wraps multiple model clients to evaluate free-form text outputs.

    The judge calls every model client in the profile and averages their
    scores. Each client is configured with ``retry_count=5`` and handles
    rate limiting via ``Retry-After`` headers internally.

    Only when *all* clients fail does the judge raise an error — which the
    Scorer catches and falls back to SequenceMatcher.
    """

    def __init__(
        self,
        model_clients: list[ModelInterface],
        *,
        cache: JudgeCache | None = None,
    ) -> None:
        """Initialise the judge client.

        Args:
            model_clients: One or more model adapters. Every client is
                called and their scores are averaged. Each should be
                configured with ``retry_count=5``.
            cache: Optional campaign-scoped judge cache. When provided,
                callers should supply a cache key to
                ``evaluate_commit_message`` to enable reuse.
        """
        if not model_clients:
            raise ValueError("JudgeClient requires at least one model client")
        self._model_clients = model_clients
        self._cache = cache
        self._config_hash = compute_judge_config_hash(model_clients)

    def evaluate_commit_message(
        self,
        diff: str,
        message: str,
        prompt: str = "",
        *,
        cache_key: tuple[str, str] | None = None,
    ) -> float:
        """Evaluate a commit message and return the aggregated score.

        This is the backward-compatible thin wrapper around
        :meth:`evaluate_commit_message_evidence`.
        """
        evidence = self.evaluate_commit_message_evidence(
            diff, message, prompt=prompt, cache_key=cache_key
        )
        if evidence.final_score is None:
            raise ValueError(evidence.error or "Judge produced no usable score")
        return evidence.final_score

    def evaluate_commit_message_evidence(
        self,
        diff: str,
        message: str,
        prompt: str = "",
        *,
        cache_key: tuple[str, str] | None = None,
    ) -> JudgeEvidence:
        """Evaluate a commit message and return full member-level evidence.

        Args:
            diff: The git diff to evaluate against.
            message: The commit message generated by the model under test.
            prompt: The original prompt given to the model under test.
            cache_key: Optional cache key used with a campaign cache.

        Returns:
            A :class:`JudgeEvidence` object with member results, final
            aggregation, and failure state.

        Raises:
            ValueError: If all judge models fail.
        """
        if self._cache is not None and cache_key is not None:
            fixture_input_hash, target_output_hash = cache_key
            cached = self._cache.get(
                fixture_input_hash, target_output_hash, self._config_hash
            )
            if cached is not None:
                logger.debug(
                    "Judge cache hit for fixture input %s, output %s",
                    fixture_input_hash[:8],
                    target_output_hash[:8],
                )
                return JudgeEvidence(
                    judge_config_hash=self._config_hash,
                    aggregation_method="average",
                    final_passed=None,
                    final_score=cached,
                    members=[],
                    cache_key=f"{fixture_input_hash}:{target_output_hash}:{self._config_hash}",
                )

        judge_prompt = JUDGE_COMMIT_MESSAGE_PROMPT.format(
            diff=diff, message=message, prompt=prompt
        )
        messages = [ModelMessage(role="user", content=judge_prompt)]

        members: list[JudgeMemberResult] = []
        scores: list[float] = []

        for i, client in enumerate(self._model_clients):
            model_name = getattr(client, "model", f"client-{i}")
            member = JudgeMemberResult(
                member_id=f"judge-{i}",
                model_id=model_name,
            )
            try:
                logger.debug(
                    "Judge calling model %d/%d (%s)",
                    i + 1,
                    len(self._model_clients),
                    model_name,
                )
                response = client.generate(messages)
                text = _extract_text(response)
                score = _parse_score(text)
                scores.append(score)
                member.score = score
                member.passed = None  # Threshold is applied by the scorer.
                logger.debug("Judge model '%s' scored %.2f", model_name, score)
            except Exception as exc:
                logger.warning(
                    "Judge model '%s' failed (%d/%d): %s",
                    model_name,
                    i + 1,
                    len(self._model_clients),
                    exc,
                )
                member.error = str(exc)
            # Capture available provider-route provenance.
            member.provider_route_metadata = {
                k: v
                for k, v in {
                    "model_id": getattr(client, "model", None),
                    "reasoning_level": getattr(client, "reasoning_level", None),
                    "base_url": getattr(client, "base_url", None)
                    or getattr(client, "_base_url", None),
                }.items()
                if v is not None
            }
            members.append(member)

        evidence = JudgeEvidence(
            judge_config_hash=self._config_hash,
            aggregation_method="average",
            members=members,
        )

        if not scores:
            member_errors = "; ".join(
                f"{m.member_id}: {m.error}" for m in members if m.error
            )
            evidence.error = (
                f"All {len(self._model_clients)} judge model(s) failed. "
                f"Errors: {member_errors}"
            )
            evidence.exhausted = True
            return evidence

        average = sum(scores) / len(scores)
        logger.info(
            "Judge ensemble: %d/%d models returned scores, average=%.3f",
            len(scores),
            len(self._model_clients),
            average,
        )
        evidence.final_score = round(average, 4)
        if self._cache is not None and cache_key is not None:
            fixture_input_hash, target_output_hash = cache_key
            self._cache.set(
                fixture_input_hash, target_output_hash, self._config_hash, evidence.final_score
            )
        return evidence

    def _extract_text(self, response) -> str:
        """Extract text from a model response (dict or string)."""
        return _extract_text(response)

    def _parse_score(self, text: str) -> float:
        """Parse a numeric score from the judge model response."""
        return _parse_score(text)

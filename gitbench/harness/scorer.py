"""Scoring engine for GitBench benchmarks."""

import difflib
import json
import logging
import os
import re
import shlex
import subprocess
from typing import Any

from gitbench.harness.types import Fixture, Score

logger = logging.getLogger(__name__)


def _check_assertion(assertion: dict[str, Any], repo_path: str, model_output: str = "") -> bool:
    """Check a single state assertion against the repo.

    Args:
        assertion: Dict with 'type' and assertion-specific params.
        repo_path: Path to the git repository.
        model_output: The model's command output (used for model_output assertions).

    Returns:
        True if the assertion passes, False otherwise.
    """
    assertion_type = assertion["type"]

    if assertion_type == "file_exists":
        path = os.path.join(repo_path, assertion["path"])
        return os.path.isfile(path)

    elif assertion_type == "file_not_exists":
        path = os.path.join(repo_path, assertion["path"])
        return not os.path.isfile(path)

    elif assertion_type == "dir_exists":
        path = os.path.join(repo_path, assertion["path"])
        return os.path.isdir(path)

    elif assertion_type == "dir_not_exists":
        path = os.path.join(repo_path, assertion["path"])
        return not os.path.isdir(path)

    elif assertion_type == "file_content":
        path = os.path.join(repo_path, assertion["path"])
        if not os.path.isfile(path):
            return False
        actual = open(path).read()
        expected = assertion.get("value")
        contains = assertion.get("contains", False)
        if isinstance(contains, str):
            return contains in actual
        if contains:
            expected = expected or ""
            return expected in actual
        if expected is None:
            return False
        return actual.strip() == expected.strip()

    elif assertion_type == "file_not_contains":
        path = os.path.join(repo_path, assertion["path"])
        if not os.path.isfile(path):
            return True
        actual = open(path).read()
        unexpected = assertion["value"]
        return unexpected not in actual

    elif assertion_type == "branch_exists":
        name = assertion["name"]
        # Check in a specific worktree path if provided
        worktree_path = assertion.get("in_worktree")
        cwd = os.path.join(repo_path, worktree_path) if worktree_path else repo_path
        result = subprocess.run(
            ["git", "branch", "--list", name],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return name in result.stdout

    elif assertion_type == "git_config":
        key = assertion["key"]
        expected = assertion["value"]
        result = subprocess.run(
            ["git", "config", "--get", key],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0 and result.stdout.strip() == expected

    elif assertion_type == "git_output":
        command = assertion["command"]
        # Run command relative to repo
        parts = command.split()
        result = subprocess.run(
            parts,
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        if "contains" in assertion:
            return assertion["contains"] in output
        if "not_contains" in assertion:
            return assertion["not_contains"] not in output
        return result.returncode == 0

    elif assertion_type == "model_output":
        if "contains" in assertion:
            return assertion["contains"] in model_output
        if "exact" in assertion:
            return model_output.strip() == assertion["exact"]
        return len(model_output.strip()) > 0

    else:
        logger.warning(f"Unknown assertion type: {assertion_type}")
        return False


def _strip_wrapping_fence(text: str) -> str:
    """Remove a single wrapping triple-backtick fence from text.

    Handles an optional language tag on the opening fence line. Returns the
    input unchanged when no complete wrapping fence is present (including
    unterminated fences).
    """
    stripped = text.strip()
    lines = stripped.splitlines()
    if len(lines) < 2:
        return text
    opening = lines[0].strip()
    closing = lines[-1].strip()
    if not opening.startswith("```") or closing != "```":
        return text
    # Opening line must be the fence plus an optional language tag only
    tag = opening[3:].strip()
    if tag and not re.fullmatch(r"[\w+.-]+", tag):
        return text
    return "\n".join(lines[1:-1]).strip()


def _parse_structured_output(model_output: str) -> dict[str, str]:
    """Parse structured key-value output from model.

    Expected format:
        key1: value1
        key2: value2
        ...

    Args:
        model_output: Raw model output string.

    Returns:
        Dict of field_name -> field_value.
    """
    fields: dict[str, str] = {}
    for line in model_output.strip().split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key:
                fields[key] = value
    return fields


def _score_result(
    fixture: Fixture,
    model_output: str,
    passed: bool,
    similarity: float,
    error: str | None = None,
) -> Score:
    return Score(
        fixture_id=fixture.id,
        passed=passed,
        similarity=round(similarity, 4),
        model_output=model_output,
        error=error,
        purpose=fixture.purpose or None,
        difficulty=fixture.difficulty or None,
        tags=fixture.tags or None,
    )


class StateAssertionScorer:
    """Scores based on repo state assertions after model commands execute."""

    def score(
        self, fixture: Fixture, repo_path: str, model_output: str = ""
    ) -> Score:
        """Score fixture by checking state assertions.

        Args:
            fixture: Fixture with expected_state.assertions.
            repo_path: Path to the git repository.
            model_output: The model's command output (unused for state scoring).

        Returns:
            A Score object with pass/fail based on assertion results.
        """
        expected_state = fixture.scoring.get("expected_state", {})
        assertions = expected_state.get("assertions", [])

        if not assertions:
            return Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output=model_output,
                error="No assertions defined in fixture",
                purpose=fixture.purpose or None,
                difficulty=fixture.difficulty or None,
                tags=fixture.tags or None,
            )

        results = []
        for assertion in assertions:
            try:
                passed = _check_assertion(assertion, repo_path, model_output)
                results.append((assertion, passed))
            except Exception as e:
                logger.error(f"Assertion error for {assertion}: {e}")
                results.append((assertion, False))

        total = len(results)
        passed_count = sum(1 for _, p in results if p)
        similarity = passed_count / total if total > 0 else 0.0

        # Build detailed error for failures
        failed_assertions = [a for a, p in results if not p]
        error = None
        if failed_assertions:
            error = f"Failed assertions: {failed_assertions}"

        return Score(
            fixture_id=fixture.id,
            passed=passed_count == total,
            similarity=round(similarity, 4),
            model_output=model_output,
            error=error,
            purpose=fixture.purpose or None,
            difficulty=fixture.difficulty or None,
            tags=fixture.tags or None,
        )


class StructuredScorer:
    """Scores structured model output with per-field scoring."""

    def score(self, fixture: Fixture, model_output: str) -> Score:
        """Score structured output with per-field comparison.

        Args:
            fixture: Fixture with scoring.fields config and expected values.
            model_output: Model output in 'key: value' format.

        Returns:
            A Score object. Passes only if all exact_match fields pass.
        """
        fields_config = fixture.scoring.get("fields", {})
        expected = fixture.expected

        # Parse model output into fields
        model_fields = _parse_structured_output(model_output)

        # Parse expected output into fields
        expected_fields = _parse_structured_output(expected)

        if not model_fields and not expected_fields:
            # Fallback to similarity on raw strings
            similarity = difflib.SequenceMatcher(None, model_output, expected).ratio()
            return Score(
                fixture_id=fixture.id,
                passed=similarity >= 0.5,
                similarity=round(similarity, 4),
                model_output=model_output,
                purpose=fixture.purpose or None,
                difficulty=fixture.difficulty or None,
                tags=fixture.tags or None,
            )

        field_scores: dict[str, dict[str, Any]] = {}
        all_exact_pass = True

        for field_name, expected_value in expected_fields.items():
            field_config = fields_config.get(field_name, {})
            field_type = field_config.get("type", "similarity")
            threshold = field_config.get("threshold", 0.5)

            model_value = model_fields.get(field_name, "")

            if field_type == "exact_match":
                field_passed = model_value.strip() == expected_value.strip()
                field_similarity = 1.0 if field_passed else 0.0
                if not field_passed:
                    all_exact_pass = False
            else:
                field_similarity = difflib.SequenceMatcher(
                    None, model_value, expected_value
                ).ratio()
                field_passed = field_similarity >= threshold

            field_scores[field_name] = {
                "expected": expected_value,
                "actual": model_value,
                "type": field_type,
                "similarity": round(field_similarity, 4),
                "passed": field_passed,
            }

        # Overall similarity = average of field similarities
        if field_scores:
            overall_similarity = sum(
                f["similarity"] for f in field_scores.values()
            ) / len(field_scores)
        else:
            overall_similarity = 0.0

        error = None
        if not all_exact_pass:
            failed = [k for k, v in field_scores.items() if not v["passed"]]
            error = f"Failed fields: {failed}"

        return Score(
            fixture_id=fixture.id,
            passed=all_exact_pass,
            similarity=round(overall_similarity, 4),
            model_output=model_output,
            error=error,
            purpose=fixture.purpose or None,
            difficulty=fixture.difficulty or None,
            tags=fixture.tags or None,
        )


class CommandEquivalenceScorer:
    """Scores command answers against fixture-declared equivalent commands."""

    def score(self, fixture: Fixture, model_output: str) -> Score:
        """Score command output by comparing normalized command token sequences."""
        try:
            accepted_sequences = self._normalize_accepted(fixture.scoring.get("accepted"))
            model_sequence = self._normalize_command_sequence(model_output, "model output")
        except ValueError as e:
            return self._score(fixture, model_output, False, str(e))

        if not accepted_sequences:
            return self._score(
                fixture,
                model_output,
                False,
                "No accepted command alternatives defined",
            )

        for accepted in accepted_sequences:
            if model_sequence == accepted:
                return self._score(fixture, model_output, True, None)

        expected_display = [
            " && ".join(" ".join(command) for command in sequence)
            for sequence in accepted_sequences
        ]
        return self._score(
            fixture,
            model_output,
            False,
            f"Command did not match accepted alternatives: {expected_display}",
        )

    def _normalize_accepted(self, accepted: Any) -> list[list[list[str]]]:
        """Normalize accepted alternatives into command-token sequences."""
        if not isinstance(accepted, list):
            raise ValueError("command_equivalence scoring requires an accepted list")

        normalized = []
        for index, alternative in enumerate(accepted):
            label = f"accepted alternative {index + 1}"
            if isinstance(alternative, str):
                normalized.append(self._normalize_command_sequence(alternative, label))
            elif isinstance(alternative, list) and all(
                isinstance(command, str) for command in alternative
            ):
                normalized.append(self._normalize_command_sequence("\n".join(alternative), label))
            else:
                raise ValueError(
                    "accepted alternatives must be command strings or lists of command strings"
                )
        return normalized

    def _normalize_command_sequence(self, value: str, label: str) -> list[list[str]]:
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        if not lines:
            raise ValueError(f"Could not parse {label}: no command lines found")

        sequence = []
        for line in lines:
            try:
                tokens = shlex.split(line)
            except ValueError as e:
                raise ValueError(f"Could not parse {label}: {e}") from e
            if not tokens:
                raise ValueError(f"Could not parse {label}: empty command line")
            sequence.append(tokens)
        return sequence

    def _score(
        self,
        fixture: Fixture,
        model_output: str,
        passed: bool,
        error: str | None,
    ) -> Score:
        return Score(
            fixture_id=fixture.id,
            passed=passed,
            similarity=1.0 if passed else 0.0,
            model_output=model_output,
            error=error,
            purpose=fixture.purpose or None,
            difficulty=fixture.difficulty or None,
            tags=fixture.tags or None,
        )


class UnorderedLineSetScorer:
    """Scores newline-delimited answers as an order-insensitive set."""

    def score(self, fixture: Fixture, model_output: str) -> Score:
        expected_lines = self._lines(fixture.expected)
        actual_lines = self._lines(model_output)
        allow_extra = fixture.scoring.get("allow_extra", False)

        missing = sorted(expected_lines - actual_lines)
        extra = sorted(actual_lines - expected_lines)
        passed = not missing and (allow_extra or not extra)

        if expected_lines:
            similarity = len(expected_lines & actual_lines) / len(expected_lines)
        else:
            similarity = 1.0 if not actual_lines else 0.0

        errors = []
        if missing:
            errors.append(f"Missing lines: {missing}")
        if extra and not allow_extra:
            errors.append(f"Extra lines: {extra}")

        return _score_result(
            fixture,
            model_output,
            passed,
            similarity,
            "; ".join(errors) if errors else None,
        )

    def _lines(self, value: str) -> set[str]:
        return {line.strip() for line in value.splitlines() if line.strip()}


class NumericExactScorer:
    """Scores integer/count answers while tolerating optional formatting noise."""

    _NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")

    def score(self, fixture: Fixture, model_output: str) -> Score:
        expected = fixture.expected.strip()
        actual = self._normalize(model_output, fixture.scoring.get("allow_prose", False))
        passed = actual == expected
        return _score_result(
            fixture,
            model_output,
            passed,
            1.0 if passed else 0.0,
            None if passed else f"Expected numeric answer {expected!r}, got {actual!r}",
        )

    def _normalize(self, value: str, allow_prose: bool) -> str:
        stripped = value.strip()
        if not allow_prose:
            return stripped
        numbers = self._NUMBER_RE.findall(stripped)
        return numbers[0] if len(numbers) == 1 else stripped


class CommitHashBySubjectScorer:
    """Scores commit hash answers derived from a commit subject in the repo."""

    _HASH_RE = re.compile(r"\b[0-9a-fA-F]{7,40}\b")

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None) -> Score:
        if repo_path is None:
            return _score_result(
                fixture,
                model_output,
                False,
                0.0,
                "repo_path required for commit_hash_by_subject scoring",
            )

        subject = fixture.scoring.get("subject")
        if not subject:
            return _score_result(
                fixture,
                model_output,
                False,
                0.0,
                "commit_hash_by_subject scoring requires subject",
            )

        result = subprocess.run(
            ["git", "log", "--format=%H%x00%s"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return _score_result(
                fixture,
                model_output,
                False,
                0.0,
                f"git log failed: {result.stderr.strip()}",
            )

        expected_hash = None
        for line in result.stdout.splitlines():
            commit_hash, _, commit_subject = line.partition("\0")
            if commit_subject == subject:
                expected_hash = commit_hash.lower()
                break

        if expected_hash is None:
            return _score_result(
                fixture,
                model_output,
                False,
                0.0,
                f"Could not find commit with subject: {subject}",
            )

        length = fixture.scoring.get("hash_length", "full")
        expected = expected_hash[:7] if length == "short" else expected_hash
        actual = model_output.strip().lower()
        exact = actual == expected
        embedded_hashes = {match.group(0).lower() for match in self._HASH_RE.finditer(actual)}
        passed = exact or expected in embedded_hashes
        return _score_result(
            fixture,
            model_output,
            passed,
            1.0 if passed else 0.0,
            None if passed else f"Expected {length} hash {expected}, got {model_output.strip()}",
        )


class JsonSemanticEqualScorer:
    """Scores JSON answers by parsed semantic value."""

    def score(self, fixture: Fixture, model_output: str) -> Score:
        try:
            expected = json.loads(fixture.expected)
        except json.JSONDecodeError as e:
            return _score_result(
                fixture,
                model_output,
                False,
                0.0,
                f"Invalid expected JSON: {e}",
            )

        try:
            actual = json.loads(model_output)
        except json.JSONDecodeError as e:
            return _score_result(
                fixture,
                model_output,
                False,
                0.0,
                f"Invalid model JSON: {e}",
            )

        passed = actual == expected
        return _score_result(
            fixture,
            model_output,
            passed,
            1.0 if passed else 0.0,
            None if passed else f"Expected JSON value {expected!r}, got {actual!r}",
        )


class Scorer:
    """Computes similarity scores for model outputs against expected values.

    Supports multiple scoring types:
    - similarity: difflib SequenceMatcher (default)
    - exact_match: exact string comparison
    - unordered_line_set: order-insensitive newline-delimited set comparison
    - numeric_exact: exact numeric comparison with optional one-number prose normalization
    - commit_hash_by_subject: repo-derived commit hash comparison
    - json_semantic_equal: parsed JSON value comparison
    - command_equivalence: tokenized command sequence comparison
    - state_assertions: repo state checking (needs repo_path)
    - structured: per-field scoring
    """

    def __init__(self, judge_client=None):
        """Initialize the scorer with sub-scorers.

        Args:
            judge_client: Optional JudgeClient for LLM-based scoring.
        """
        self._state_scorer = StateAssertionScorer()
        self._structured_scorer = StructuredScorer()
        self._command_equivalence_scorer = CommandEquivalenceScorer()
        self._unordered_line_set_scorer = UnorderedLineSetScorer()
        self._numeric_exact_scorer = NumericExactScorer()
        self._commit_hash_by_subject_scorer = CommitHashBySubjectScorer()
        self._json_semantic_equal_scorer = JsonSemanticEqualScorer()
        self._judge_client = judge_client

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None, diff: str | None = None, prompt: str | None = None) -> Score:
        """Score a model output against the expected value.

        Args:
            fixture: The fixture containing the expected output and scoring config.
            model_output: The string produced by the model.
            repo_path: Optional path to the git repository (required for state_assertions).

        Returns:
            A Score object with passed/failed status and similarity value.

        Raises:
            ValueError: If the scoring type in the fixture is unsupported.
        """
        scoring = fixture.scoring
        scoring_type = scoring.get("type", "similarity")
        threshold = scoring.get("threshold", 0.5)

        try:
            if scoring_type == "similarity":
                similarity = difflib.SequenceMatcher(
                    None, model_output, fixture.expected
                ).ratio()
                passed = similarity >= threshold

                return Score(
                    fixture_id=fixture.id,
                    passed=passed,
                    similarity=round(similarity, 4),
                    model_output=model_output,
                    error=None,
                    purpose=fixture.purpose or None,
                    difficulty=fixture.difficulty or None,
                    tags=fixture.tags or None,
                )

            elif scoring_type == "llm_judge":
                if self._judge_client is None:
                    return Score(
                        fixture_id=fixture.id,
                        passed=False,
                        similarity=0.0,
                        model_output=model_output,
                        error="Scoring error: llm_judge requires a judge client",
                        purpose=fixture.purpose or None,
                        difficulty=fixture.difficulty or None,
                        tags=fixture.tags or None,
                    )

                try:
                    similarity = self._judge_client.evaluate_commit_message(
                        diff or "", model_output, prompt=prompt or fixture.prompt
                    )
                    passed = similarity >= threshold
                    return Score(
                        fixture_id=fixture.id,
                        passed=passed,
                        similarity=round(similarity, 4),
                        model_output=model_output,
                        error=None,
                        purpose=fixture.purpose or None,
                        difficulty=fixture.difficulty or None,
                        tags=fixture.tags or None,
                    )
                except ValueError as e:
                    logger.warning(
                        "Judge failed for fixture %s, falling back to "
                        "SequenceMatcher: %s",
                        fixture.id,
                        e,
                    )
                    similarity = difflib.SequenceMatcher(
                        None, model_output, fixture.expected
                    ).ratio()
                    passed = similarity >= threshold
                    return Score(
                        fixture_id=fixture.id,
                        passed=passed,
                        similarity=round(similarity, 4),
                        model_output=model_output,
                        error=f"judge_failed: {e}",
                        purpose=fixture.purpose or None,
                        difficulty=fixture.difficulty or None,
                        tags=fixture.tags or None,
                    )

            elif scoring_type == "exact_match":
                compared_output = model_output
                if scoring.get("strip_fences"):
                    compared_output = _strip_wrapping_fence(compared_output)
                match = compared_output.strip() == fixture.expected.strip()
                return Score(
                    fixture_id=fixture.id,
                    passed=match,
                    similarity=1.0 if match else 0.0,
                    model_output=model_output,
                    error=None if match else f"Expected '{fixture.expected}', got '{model_output}'",
                    purpose=fixture.purpose or None,
                    difficulty=fixture.difficulty or None,
                    tags=fixture.tags or None,
                )

            elif scoring_type == "unordered_line_set":
                return self._unordered_line_set_scorer.score(fixture, model_output)

            elif scoring_type == "numeric_exact":
                return self._numeric_exact_scorer.score(fixture, model_output)

            elif scoring_type == "commit_hash_by_subject":
                return self._commit_hash_by_subject_scorer.score(
                    fixture, model_output, repo_path
                )

            elif scoring_type == "json_semantic_equal":
                return self._json_semantic_equal_scorer.score(fixture, model_output)

            elif scoring_type == "state_assertions":
                if repo_path is None:
                    raise ValueError("state_assertions scoring requires repo_path")
                return self._state_scorer.score(fixture, repo_path, model_output)

            elif scoring_type == "structured":
                return self._structured_scorer.score(fixture, model_output)

            elif scoring_type == "command_equivalence":
                return self._command_equivalence_scorer.score(fixture, model_output)

            else:
                raise ValueError(f"Unsupported scoring type: {scoring_type}")

        except Exception as e:
            logger.error(f"Scoring error for fixture {fixture.id}: {e}")
            return Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output=model_output,
                error=f"Scoring error: {e}",
                purpose=fixture.purpose or None,
                difficulty=fixture.difficulty or None,
                tags=fixture.tags or None,
            )

    def pass_at_k(self, scores: list[Score], k: int = 1) -> float:
        """Compute pass@k metric.

        Args:
            scores: List of Score objects (one per fixture/attempt).
            k: Number of attempts considered per fixture.

        Returns:
            Fraction of fixtures where at least one of k attempts passed.
            Returns 0.0 if scores list is empty.
        """
        if not scores:
            return 0.0

        from collections import defaultdict

        by_fixture: dict[str, list[Score]] = defaultdict(list)
        for s in scores:
            by_fixture[s.fixture_id].append(s)

        total_fixtures = len(by_fixture)
        passed_fixtures = 0

        for fixture_id, fixture_scores in by_fixture.items():
            if any(s.passed for s in fixture_scores):
                passed_fixtures += 1

        return round(passed_fixtures / total_fixtures, 4)

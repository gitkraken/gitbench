"""Tests for JudgeClient."""

from unittest.mock import MagicMock, patch

import pytest

from gitbench.harness.judge import (
    JUDGE_COMMIT_MESSAGE_PROMPT,
    JudgeCache,
    JudgeClient,
    compute_judge_config_hash,
)
from gitbench.harness.model import DEFAULT_MODEL_TIMEOUT
from gitbench.harness.types import ModelMessage


class TestJudgeClient:
    """Tests for JudgeClient class."""

    @pytest.fixture
    def mock_client(self):
        """Create a single mock model client."""
        return MagicMock()

    @pytest.fixture
    def judge(self, mock_client):
        """Create a JudgeClient with one mock client."""
        return JudgeClient([mock_client])

    def test_init_accepts_model_client_list(self, mock_client):
        """JudgeClient stores the model client list."""
        judge = JudgeClient([mock_client])
        assert judge._model_clients == [mock_client]

    def test_init_raises_on_empty_list(self):
        """JudgeClient requires at least one client."""
        with pytest.raises(ValueError, match="at least one"):
            JudgeClient([])

    def test_evaluate_commit_message_returns_float(self, judge, mock_client):
        """Judge returns a float score for a valid response."""
        mock_client.generate.return_value = {"text": "0.85", "content": "0.85"}

        score = judge.evaluate_commit_message("diff content", "Add feature X")

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_evaluate_commit_message_calls_model_with_prompt(self, judge, mock_client):
        """Judge constructs the correct prompt and calls the model."""
        mock_client.generate.return_value = {"text": "0.9"}

        judge.evaluate_commit_message("git diff --staged", "feat: add login")

        mock_client.generate.assert_called_once()
        call_args = mock_client.generate.call_args[0][0]
        assert len(call_args) == 1
        assert isinstance(call_args[0], ModelMessage)
        assert "git diff --staged" in call_args[0].content
        assert "feat: add login" in call_args[0].content
        assert "Score:" in call_args[0].content

    def test_evaluate_commit_message_high_score(self, judge, mock_client):
        """Judge returns high score for a good response."""
        mock_client.generate.return_value = {"text": "0.95", "content": "0.95"}

        score = judge.evaluate_commit_message(
            "Add hello.txt with greeting", "Add hello.txt with greeting message"
        )

        assert score == 0.95

    def test_evaluate_commit_message_low_score(self, judge, mock_client):
        """Judge returns low score for a bad response."""
        mock_client.generate.return_value = {"text": "0.1", "content": "0.1"}

        score = judge.evaluate_commit_message(
            "Add hello.txt with greeting", "Fix login bug"
        )

        assert score == 0.1

    def test_evaluate_commit_message_medium_score(self, judge, mock_client):
        """Judge returns medium score for a vague response."""
        mock_client.generate.return_value = {"text": "0.4", "content": "0.4"}

        score = judge.evaluate_commit_message(
            "Add three files: config.py, main.py, utils.py", "Update files"
        )

        assert score == 0.4

    def test_evaluate_commit_message_parses_integer_score(self, judge, mock_client):
        """Judge parses integer scores (0 or 1)."""
        mock_client.generate.return_value = {"text": "1", "content": "1"}

        score = judge.evaluate_commit_message("diff", "perfect message")

        assert score == 1.0

    def test_evaluate_commit_message_parses_score_with_text(self, judge, mock_client):
        """Judge extracts score from response with surrounding text."""
        mock_client.generate.return_value = {
            "text": "The score is 0.75 because the message is good.",
            "content": "The score is 0.75 because the message is good.",
        }

        score = judge.evaluate_commit_message("diff", "message")

        assert score == 0.75

    def test_evaluate_commit_message_clamps_below_zero(self, judge, mock_client):
        """Judge clamps scores below 0.0 to 0.0."""
        mock_client.generate.return_value = {"text": "-0.5"}

        score = judge.evaluate_commit_message("diff", "message")

        assert score == 0.0

    def test_evaluate_commit_message_clamps_above_one(self, judge, mock_client):
        """Judge clamps scores above 1.0 to 1.0."""
        mock_client.generate.return_value = {"text": "1.5"}

        score = judge.evaluate_commit_message("diff", "message")

        assert score == 1.0

    def test_evaluate_commit_message_handles_string_response(self, judge, mock_client):
        """Judge handles plain string responses from model."""
        mock_client.generate.return_value = "0.8"

        score = judge.evaluate_commit_message("diff", "message")

        assert score == 0.8

    def test_evaluate_commit_message_raises_on_non_numeric(self, judge, mock_client):
        """Judge raises ValueError when response has no number."""
        mock_client.generate.return_value = {"text": "This is a great message!"}

        with pytest.raises(ValueError, match="could not be parsed as a number"):
            judge.evaluate_commit_message("diff", "message")

    def test_evaluate_commit_message_raises_on_empty_response(self, judge, mock_client):
        """Judge raises ValueError when response is empty."""
        mock_client.generate.return_value = {"text": ""}

        with pytest.raises(ValueError, match="could not be parsed as a number"):
            judge.evaluate_commit_message("diff", "message")

    # --- Ensemble (multi-client) tests ---

    def test_averages_scores_from_all_clients(self):
        """Judge calls every client and returns the average score."""
        client1 = MagicMock()
        client1.generate.return_value = {"text": "0.8"}
        client2 = MagicMock()
        client2.generate.return_value = {"text": "0.6"}
        client3 = MagicMock()
        client3.generate.return_value = {"text": "0.7"}

        judge = JudgeClient([client1, client2, client3])
        score = judge.evaluate_commit_message("diff", "message")

        assert score == 0.7  # (0.8 + 0.6 + 0.7) / 3
        client1.generate.assert_called_once()
        client2.generate.assert_called_once()
        client3.generate.assert_called_once()

    def test_calls_all_clients_even_when_first_succeeds(self):
        """Judge does not short-circuit — calls every model in the profile."""
        client1 = MagicMock()
        client1.generate.return_value = {"text": "1.0"}
        client2 = MagicMock()
        client2.generate.return_value = {"text": "0.0"}

        judge = JudgeClient([client1, client2])
        score = judge.evaluate_commit_message("diff", "message")

        assert score == 0.5
        client1.generate.assert_called_once()
        client2.generate.assert_called_once()

    def test_skips_failed_clients_in_average(self):
        """Judge averages only successful responses, ignoring failures."""
        client1 = MagicMock()
        client1.generate.side_effect = RuntimeError("Down")
        client2 = MagicMock()
        client2.generate.return_value = {"text": "0.8"}
        client3 = MagicMock()
        client3.generate.return_value = {"text": "0.4"}

        judge = JudgeClient([client1, client2, client3])
        score = judge.evaluate_commit_message("diff", "message")

        assert score == 0.6  # (0.8 + 0.4) / 2, ignoring failed client1
        client1.generate.assert_called_once()
        client2.generate.assert_called_once()
        client3.generate.assert_called_once()

    def test_raises_when_all_clients_fail(self):
        """Judge raises ValueError when every client fails."""
        client1 = MagicMock()
        client1.generate.side_effect = RuntimeError("Down")
        client2 = MagicMock()
        client2.generate.side_effect = RuntimeError("Also down")

        judge = JudgeClient([client1, client2])

        with pytest.raises(ValueError, match="All 2 judge model"):
            judge.evaluate_commit_message("diff", "message")

        assert client1.generate.call_count == 1
        assert client2.generate.call_count == 1

    def test_retries_are_handled_by_adapter(self):
        """The judge does not add its own retry layer — the adapter handles it."""
        client = MagicMock()
        client.generate.side_effect = RuntimeError("Boom")

        judge = JudgeClient([client])

        with pytest.raises(ValueError, match="All 1 judge model"):
            judge.evaluate_commit_message("diff", "message")

        assert client.generate.call_count == 1

    # --- Parsing tests ---

    def test_parse_score_extracts_first_number(self, judge):
        """_parse_score extracts the first numeric value."""
        result = judge._parse_score("0.67 is the score")
        assert result == 0.67

    def test_parse_score_handles_leading_zeros(self, judge):
        """_parse_score handles scores with leading zeros."""
        result = judge._parse_score("Score: 0.05")
        assert result == 0.05

    def test_judge_prompt_includes_diff_message_and_prompt(self):
        """The judge prompt template contains placeholders for diff, message, and original prompt."""
        formatted = JUDGE_COMMIT_MESSAGE_PROMPT.format(
            diff="DIFF", message="MSG", prompt="ORIGINAL_PROMPT"
        )
        assert "DIFF" in formatted
        assert "MSG" in formatted
        assert "ORIGINAL_PROMPT" in formatted
        assert "Score:" in formatted
        assert "<original_prompt>" in formatted


class TestJudgeTimeoutIntegration:
    """Tests that judge model clients receive the resolved timeout."""

    def test_runner_passes_model_timeout_to_judge_clients(self):
        """BenchmarkRunner passes model_timeout to judge model clients."""
        from gitbench.harness.runner import BenchmarkRunner

        registry = {}
        model_client = MagicMock()
        judge_config = {
            "profile": "judge-profile",
            "_config": {
                "models": {
                    "judge-profile": {
                        "models": ["judge-model"],
                        "provider": "openai",
                    }
                }
            },
        }

        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            with patch("gitbench.cli.get_model_client") as mock_get_client:
                mock_judge_client = MagicMock()
                mock_get_client.return_value = mock_judge_client

                runner = BenchmarkRunner(
                    registry,
                    model_client,
                    judge_config=judge_config,
                    model_timeout=120,
                )

                mock_get_client.assert_called_once()
                call_kwargs = mock_get_client.call_args
                assert call_kwargs.kwargs["timeout"] == 120
                assert call_kwargs.kwargs["retry_count"] == 5

    def test_runner_default_model_timeout_is_240(self):
        """BenchmarkRunner defaults model_timeout to 240."""
        from gitbench.harness.runner import BenchmarkRunner

        registry = {}
        model_client = MagicMock()
        judge_config = {
            "profile": "judge-profile",
            "_config": {
                "models": {
                    "judge-profile": {
                        "models": ["judge-model"],
                        "provider": "openai",
                    }
                }
            },
        }

        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            with patch("gitbench.cli.get_model_client") as mock_get_client:
                mock_judge_client = MagicMock()
                mock_get_client.return_value = mock_judge_client

                runner = BenchmarkRunner(
                    registry,
                    model_client,
                    judge_config=judge_config,
                )

                mock_get_client.assert_called_once()
                call_kwargs = mock_get_client.call_args
                assert call_kwargs.kwargs["timeout"] == DEFAULT_MODEL_TIMEOUT


class TestJudgeCache:
    """Campaign-scoped judge caching."""

    @pytest.fixture
    def mock_client(self):
        """Create a single mock model client."""
        return MagicMock()

    def test_cache_stores_and_returns_score(self, mock_client):
        """A cached score is returned without calling the judge model."""
        cache = JudgeCache()
        client = JudgeClient([mock_client], cache=cache)
        mock_client.generate.return_value = {"text": "0.85"}

        score = client.evaluate_commit_message(
            "diff", "message", cache_key=("fixture-hash", "output-hash")
        )
        assert score == 0.85
        assert mock_client.generate.call_count == 1

        cached = client.evaluate_commit_message(
            "diff", "message", cache_key=("fixture-hash", "output-hash")
        )
        assert cached == 0.85
        assert mock_client.generate.call_count == 1

    def test_cache_key_includes_all_three_hashes(self, mock_client):
        """Changing any component of the cache key misses the cache."""
        cache = JudgeCache()
        client = JudgeClient([mock_client], cache=cache)
        mock_client.generate.return_value = {"text": "0.90"}

        client.evaluate_commit_message(
            "diff", "message", cache_key=("fixture-a", "output-a")
        )

        # Different fixture input hash.
        mock_client.generate.return_value = {"text": "0.80"}
        score = client.evaluate_commit_message(
            "diff", "message", cache_key=("fixture-b", "output-a")
        )
        assert score == 0.80
        assert mock_client.generate.call_count == 2

    def test_cache_disabled_without_cache_key(self, mock_client):
        """When no cache key is supplied, every call invokes the judge."""
        cache = JudgeCache()
        client = JudgeClient([mock_client], cache=cache)
        mock_client.generate.return_value = {"text": "0.75"}

        client.evaluate_commit_message("diff", "message")
        client.evaluate_commit_message("diff", "message")
        assert mock_client.generate.call_count == 2

    def test_compute_judge_config_hash_is_stable(self):
        """Equivalent judge client configurations produce the same hash."""
        from gitbench.harness.model import MockModelClient

        clients_a = [MockModelClient(model="mock-judge-1")]
        clients_b = [MockModelClient(model="mock-judge-1")]
        assert compute_judge_config_hash(clients_a) == compute_judge_config_hash(clients_b)

    def test_compute_judge_config_hash_detects_model_change(self):
        """A different judge model produces a different config hash."""
        from gitbench.harness.model import MockModelClient

        clients_a = [MockModelClient(model="mock-judge-1")]
        clients_b = [MockModelClient(model="mock-judge-2")]
        assert compute_judge_config_hash(clients_a) != compute_judge_config_hash(clients_b)


class TestJudgeEvidence:
    """Member-level judge evidence is returned for auditability."""

    @pytest.fixture
    def mock_client(self):
        """Create a single mock model client."""
        return MagicMock()

    def test_evidence_includes_member_results(self, mock_client):
        """Successful evaluations return per-member scores."""
        mock_client.generate.return_value = {"text": "0.92"}
        mock_client.model = "judge-model"
        client = JudgeClient([mock_client])

        evidence = client.evaluate_commit_message_evidence("diff", "message")
        assert evidence.final_score == 0.92
        assert len(evidence.members) == 1
        assert evidence.members[0].model_id == "judge-model"
        assert evidence.members[0].score == 0.92
        assert evidence.judge_config_hash is not None

    def test_evidence_records_failure_state(self, mock_client):
        """All-judge failures are captured without raising."""
        mock_client.generate.side_effect = ValueError("API error")
        client = JudgeClient([mock_client])

        evidence = client.evaluate_commit_message_evidence("diff", "message")
        assert evidence.final_score is None
        assert evidence.exhausted is True
        assert evidence.error is not None
        assert evidence.members[0].error is not None

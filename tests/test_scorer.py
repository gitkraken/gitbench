"""Tests for the scoring engine."""

import subprocess

import pytest

from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score


class TestScorer:
    """Tests for Scorer class."""

    @pytest.fixture
    def scorer(self):
        """Create a Scorer instance."""
        return Scorer()

    @pytest.fixture
    def fixture_high_threshold(self):
        """Create a fixture with high threshold."""
        return Fixture(
            id="score_001",
            description="High threshold fixture",
            setup=["git init"],
            prompt="Generate commit message",
            expected="fix: correct spelling error in file.txt",
            scoring={"type": "similarity", "threshold": 0.7},
        )

    @pytest.fixture
    def fixture_default_threshold(self):
        """Create a fixture with default threshold (0.5)."""
        return Fixture(
            id="score_002",
            description="Default threshold fixture",
            setup=["git init"],
            prompt="Generate commit message",
            expected="feat: add new feature",
            scoring={"type": "similarity", "threshold": 0.5},
        )

    def test_score_exact_match(self, scorer, fixture_high_threshold):
        """Test that an exact match scores 1.0 and passes."""
        result = scorer.score(fixture_high_threshold, fixture_high_threshold.expected)

        assert result.passed is True
        assert result.similarity == 1.0
        assert result.fixture_id == "score_001"
        assert result.model_output == fixture_high_threshold.expected
        assert result.error is None

    def test_score_near_match_passes(self, scorer, fixture_high_threshold):
        """Test that a near-match output passes when above threshold."""
        output = "fix: correct spelling error in file.py"  # Very similar
        result = scorer.score(fixture_high_threshold, output)

        assert result.passed is True
        assert result.similarity > 0.7
        assert result.error is None

    def test_score_low_similarity_fails(self, scorer, fixture_high_threshold):
        """Test that low similarity output fails when below threshold."""
        output = "totally unrelated output that has nothing to do with commit messages"
        result = scorer.score(fixture_high_threshold, output)

        assert result.passed is False
        assert result.similarity < 0.7
        assert result.error is None

    def test_score_at_threshold_passes(self, scorer, fixture_high_threshold):
        """Test that output at exactly the threshold passes."""
        # Build an output with similarity >= 0.7
        output = "fix: correct spelling error"
        result = scorer.score(fixture_high_threshold, output)

        # Check it passes (ratio should be at least threshold)
        if result.similarity >= 0.7:
            assert result.passed is True
        else:
            assert result.passed is False

    def test_score_default_threshold(self, scorer, fixture_default_threshold):
        """Test that default threshold of 0.5 is used."""
        output = "feat: add feature"  # Similar but not exact
        result = scorer.score(fixture_default_threshold, output)

        # Should pass with 0.5 threshold
        assert result.passed is True
        assert result.similarity > 0.5

    def test_score_returns_score_object(self, scorer, fixture_high_threshold):
        """Test that score() returns a proper Score object."""
        result = scorer.score(fixture_high_threshold, "fix: typo")
        assert isinstance(result, Score)
        assert hasattr(result, "fixture_id")
        assert hasattr(result, "passed")
        assert hasattr(result, "similarity")
        assert hasattr(result, "model_output")
        assert hasattr(result, "error")

    def test_pass_at_k_single_attempt(self, scorer):
        """Test pass_at_k with single attempt per fixture."""
        scores = [
            Score(fixture_id="f1", passed=True, similarity=0.9, model_output="a", error=None),
            Score(fixture_id="f2", passed=False, similarity=0.3, model_output="b", error=None),
            Score(fixture_id="f3", passed=True, similarity=0.8, model_output="c", error=None),
        ]

        result = scorer.pass_at_k(scores, k=1)
        assert result == pytest.approx(0.6667)

    def test_pass_at_k_empty_list(self, scorer):
        """Test pass_at_k with empty list returns 0.0."""
        result = scorer.pass_at_k([], k=1)
        assert result == 0.0

    def test_pass_at_k_all_pass(self, scorer):
        """Test pass_at_k when all fixtures pass."""
        scores = [
            Score(fixture_id="f1", passed=True, similarity=0.9, model_output="a", error=None),
            Score(fixture_id="f2", passed=True, similarity=0.8, model_output="b", error=None),
        ]

        result = scorer.pass_at_k(scores, k=1)
        assert result == 1.0

    def test_pass_at_k_none_pass(self, scorer):
        """Test pass_at_k when no fixtures pass."""
        scores = [
            Score(fixture_id="f1", passed=False, similarity=0.2, model_output="a", error=None),
            Score(fixture_id="f2", passed=False, similarity=0.1, model_output="b", error=None),
        ]

        result = scorer.pass_at_k(scores, k=1)
        assert result == 0.0

    def test_pass_at_k_multiple_attempts(self, scorer):
        """Test pass_at_k with multiple attempts per fixture (k=2 scenario)."""
        # Fixture f1: attempt 1 fails, attempt 2 passes
        # Fixture f2: both attempts fail
        scores = [
            Score(fixture_id="f1", passed=False, similarity=0.3, model_output="a1", error=None),
            Score(fixture_id="f1", passed=True, similarity=0.8, model_output="a2", error=None),
            Score(fixture_id="f2", passed=False, similarity=0.2, model_output="b1", error=None),
            Score(fixture_id="f2", passed=False, similarity=0.1, model_output="b2", error=None),
        ]

        result = scorer.pass_at_k(scores, k=2)
        # f1 has at least one pass, f2 has none -> 1/2
        assert result == 0.5

    def test_pass_at_k_multiple_attempts_all_pass(self, scorer):
        """Test pass_at_k where each fixture has at least one pass among attempts."""
        scores = [
            Score(fixture_id="f1", passed=False, similarity=0.3, model_output="a1", error=None),
            Score(fixture_id="f1", passed=True, similarity=0.8, model_output="a2", error=None),
            Score(fixture_id="f2", passed=True, similarity=0.7, model_output="b1", error=None),
        ]

        result = scorer.pass_at_k(scores, k=3)
        assert result == 1.0

    def test_score_with_empty_output(self, scorer, fixture_default_threshold):
        """Test scoring with empty model output."""
        result = scorer.score(fixture_default_threshold, "")

        assert result.passed is False
        assert result.similarity == 0.0
        assert result.error is None

    def test_command_equivalence_single_command_matches(self, scorer):
        fixture = Fixture(
            id="cmd_001",
            description="Command equivalence fixture",
            setup=[],
            prompt="List worktrees",
            expected="",
            scoring={"type": "command_equivalence", "accepted": ["git worktree list"]},
        )

        result = scorer.score(fixture, "git worktree list")

        assert result.passed is True
        assert result.similarity == 1.0
        assert result.error is None

    def test_command_equivalence_accepts_equivalent_alternative(self, scorer):
        fixture = Fixture(
            id="cmd_002",
            description="Command equivalence fixture",
            setup=[],
            prompt="List submodules",
            expected="",
            scoring={
                "type": "command_equivalence",
                "accepted": ["git submodule", "git submodule status"],
            },
        )

        result = scorer.score(fixture, "git submodule status")

        assert result.passed is True
        assert result.similarity == 1.0

    def test_command_equivalence_normalizes_whitespace(self, scorer):
        fixture = Fixture(
            id="cmd_003",
            description="Command equivalence fixture",
            setup=[],
            prompt="List submodules",
            expected="",
            scoring={"type": "command_equivalence", "accepted": ["git submodule status"]},
        )

        result = scorer.score(fixture, "\n  git   submodule    status  \n\n")

        assert result.passed is True

    def test_command_equivalence_normalizes_quotes(self, scorer):
        fixture = Fixture(
            id="cmd_004",
            description="Command equivalence fixture",
            setup=[],
            prompt="Lock worktree",
            expected="",
            scoring={
                "type": "command_equivalence",
                "accepted": ["git worktree lock --reason 'do not delete' ../feature-wt"],
            },
        )

        result = scorer.score(
            fixture,
            'git worktree lock --reason "do not delete" ../feature-wt',
        )

        assert result.passed is True

    def test_command_equivalence_invalid_syntax_fails_with_error(self, scorer):
        fixture = Fixture(
            id="cmd_005",
            description="Command equivalence fixture",
            setup=[],
            prompt="List worktrees",
            expected="",
            scoring={"type": "command_equivalence", "accepted": ["git worktree list"]},
        )

        result = scorer.score(fixture, "git worktree list 'unterminated")

        assert result.passed is False
        assert result.similarity == 0.0
        assert "Could not parse model output" in result.error

    def test_command_equivalence_multi_command_sequence_matches(self, scorer):
        fixture = Fixture(
            id="cmd_006",
            description="Command equivalence fixture",
            setup=[],
            prompt="Initialize submodules",
            expected="",
            scoring={
                "type": "command_equivalence",
                "accepted": [["git submodule init", "git submodule update"]],
            },
        )

        result = scorer.score(fixture, "git submodule init\ngit submodule update")

        assert result.passed is True

    def test_command_equivalence_multi_command_alternative_matches(self, scorer):
        fixture = Fixture(
            id="cmd_007",
            description="Command equivalence fixture",
            setup=[],
            prompt="Initialize submodules",
            expected="",
            scoring={
                "type": "command_equivalence",
                "accepted": [
                    ["git submodule init", "git submodule update"],
                    ["git submodule update --init"],
                ],
            },
        )

        result = scorer.score(fixture, "git submodule update --init")

        assert result.passed is True

    def test_command_equivalence_wrong_command_order_fails(self, scorer):
        fixture = Fixture(
            id="cmd_008",
            description="Command equivalence fixture",
            setup=[],
            prompt="Initialize submodules",
            expected="",
            scoring={
                "type": "command_equivalence",
                "accepted": [["git submodule init", "git submodule update"]],
            },
        )

        result = scorer.score(fixture, "git submodule update\ngit submodule init")

        assert result.passed is False
        assert "Command did not match accepted alternatives" in result.error

    def test_unordered_line_set_accepts_reordered_lines(self, scorer):
        fixture = Fixture(
            id="lines_001",
            description="Line set fixture",
            setup=[],
            prompt="List messages",
            expected="A\nB",
            scoring={"type": "unordered_line_set"},
        )

        result = scorer.score(fixture, "B\nA")

        assert result.passed is True
        assert result.similarity == 1.0

    def test_unordered_line_set_rejects_missing_line(self, scorer):
        fixture = Fixture(
            id="lines_002",
            description="Line set fixture",
            setup=[],
            prompt="List messages",
            expected="A\nB",
            scoring={"type": "unordered_line_set"},
        )

        result = scorer.score(fixture, "A")

        assert result.passed is False
        assert "Missing lines" in result.error

    def test_unordered_line_set_rejects_extra_line(self, scorer):
        fixture = Fixture(
            id="lines_003",
            description="Line set fixture",
            setup=[],
            prompt="List messages",
            expected="A\nB",
            scoring={"type": "unordered_line_set"},
        )

        result = scorer.score(fixture, "A\nB\nC")

        assert result.passed is False
        assert "Extra lines" in result.error

    def test_numeric_exact_accepts_whitespace(self, scorer):
        fixture = Fixture(
            id="num_001",
            description="Numeric fixture",
            setup=[],
            prompt="Count",
            expected="7",
            scoring={"type": "numeric_exact"},
        )

        result = scorer.score(fixture, "  7  ")

        assert result.passed is True

    def test_numeric_exact_accepts_single_number_prose_when_enabled(self, scorer):
        fixture = Fixture(
            id="num_002",
            description="Numeric fixture",
            setup=[],
            prompt="Count",
            expected="7",
            scoring={"type": "numeric_exact", "allow_prose": True},
        )

        result = scorer.score(fixture, "The answer is 7.")

        assert result.passed is True

    def test_numeric_exact_rejects_wrong_number(self, scorer):
        fixture = Fixture(
            id="num_003",
            description="Numeric fixture",
            setup=[],
            prompt="Count",
            expected="7",
            scoring={"type": "numeric_exact"},
        )

        result = scorer.score(fixture, "6")

        assert result.passed is False

    def test_commit_hash_by_subject_accepts_short_hash(self, scorer, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        (repo / "app.py").write_text("v1\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=repo, check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "commit", "-m", "Fix null pointer bug"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        short_hash = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        fixture = Fixture(
            id="hash_001",
            description="Hash fixture",
            setup=[],
            prompt="Hash?",
            expected="",
            scoring={
                "type": "commit_hash_by_subject",
                "subject": "Fix null pointer bug",
                "hash_length": "short",
            },
        )

        result = scorer.score(fixture, short_hash, repo_path=str(repo))
        message_result = scorer.score(fixture, "Fix null pointer bug", repo_path=str(repo))
        wrong_result = scorer.score(fixture, "deadbee", repo_path=str(repo))

        assert result.passed is True
        assert message_result.passed is False
        assert wrong_result.passed is False

    def test_json_semantic_equal_accepts_formatting_differences(self, scorer):
        fixture = Fixture(
            id="json_001",
            description="JSON fixture",
            setup=[],
            prompt="JSON",
            expected='{"name":"MyApp","version":"2.0.0"}',
            scoring={"type": "json_semantic_equal"},
        )

        result = scorer.score(fixture, '{\n  "version": "2.0.0",\n  "name": "MyApp"\n}')

        assert result.passed is True

    def test_json_semantic_equal_rejects_invalid_json(self, scorer):
        fixture = Fixture(
            id="json_002",
            description="JSON fixture",
            setup=[],
            prompt="JSON",
            expected='{"version":"2.0.0"}',
            scoring={"type": "json_semantic_equal"},
        )

        result = scorer.score(fixture, "version: 2.0.0")

        assert result.passed is False
        assert "Invalid model JSON" in result.error

    def test_json_semantic_equal_rejects_wrong_value(self, scorer):
        fixture = Fixture(
            id="json_003",
            description="JSON fixture",
            setup=[],
            prompt="JSON",
            expected='{"version":"2.0.0"}',
            scoring={"type": "json_semantic_equal"},
        )

        result = scorer.score(fixture, '{"version":"1.0.0"}')

        assert result.passed is False


class TestScorerJudgeIntegration:
    """Tests for Scorer with JudgeClient integration."""

    @pytest.fixture
    def mock_judge_client(self):
        """Create a mock JudgeClient."""
        from unittest.mock import MagicMock
        mock = MagicMock()
        mock.evaluate_commit_message.return_value = 0.85
        return mock

    @pytest.fixture
    def similarity_fixture(self):
        """Create a similarity-type fixture."""
        return Fixture(
            id="judge_001",
            description="Judge-enabled fixture",
            setup=["git init"],
            prompt="Generate commit message",
            expected="fix: correct spelling error in file.txt",
            scoring={"type": "similarity", "threshold": 0.7},
        )

    def test_scorer_uses_judge_when_diff_provided(
        self, mock_judge_client, similarity_fixture
    ):
        """Scorer uses judge when judge_client and diff are provided."""
        scorer = Scorer(judge_client=mock_judge_client)

        result = scorer.score(
            similarity_fixture,
            "fix: correct spelling error",
            diff="diff --git a/file.txt b/file.txt",
        )

        assert result.passed is True
        assert result.similarity == 0.85
        mock_judge_client.evaluate_commit_message.assert_called_once_with(
            "diff --git a/file.txt b/file.txt",
            "fix: correct spelling error",
            prompt="Generate commit message",
        )

    def test_scorer_falls_back_when_no_diff(
        self, mock_judge_client, similarity_fixture
    ):
        """Scorer uses SequenceMatcher when judge_client exists but no diff."""
        scorer = Scorer(judge_client=mock_judge_client)

        result = scorer.score(
            similarity_fixture,
            similarity_fixture.expected,
        )

        # No diff, so should use SequenceMatcher (exact match = 1.0)
        assert result.passed is True
        assert result.similarity == 1.0
        mock_judge_client.evaluate_commit_message.assert_not_called()

    def test_scorer_falls_back_when_no_judge(self, similarity_fixture):
        """Scorer uses SequenceMatcher when no judge_client configured."""
        scorer = Scorer()

        result = scorer.score(
            similarity_fixture,
            similarity_fixture.expected,
            diff="diff content",
        )

        # No judge, so should use SequenceMatcher (exact match = 1.0)
        assert result.passed is True
        assert result.similarity == 1.0

    def test_scorer_falls_back_on_judge_error(
        self, mock_judge_client, similarity_fixture
    ):
        """Scorer falls back to SequenceMatcher and sets error on judge failure."""
        mock_judge_client.evaluate_commit_message.side_effect = ValueError(
            "Judge call failed after retry: connection error"
        )
        scorer = Scorer(judge_client=mock_judge_client)

        result = scorer.score(
            similarity_fixture,
            "fix: correct spelling error",
            diff="diff content",
        )

        assert result.error is not None
        assert "judge_failed" in result.error
        # Should have fallen back to SequenceMatcher
        assert 0.0 <= result.similarity <= 1.0

    def test_scorer_ignores_judge_for_non_similarity_type(
        self, mock_judge_client
    ):
        """Scorer does not use judge for non-similarity scoring types."""
        fixture = Fixture(
            id="exact_001",
            description="Exact match fixture",
            setup=[],
            prompt="Give answer",
            expected="hello",
            scoring={"type": "exact_match"},
        )
        scorer = Scorer(judge_client=mock_judge_client)

        result = scorer.score(fixture, "hello", diff="some diff")

        assert result.passed is True
        mock_judge_client.evaluate_commit_message.assert_not_called()

"""Tests for the scoring engine."""

import subprocess
from pathlib import Path

import pytest

from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import (
    CommandAnswerNormalizationError,
    Scorer,
    _strip_wrapping_fence,
    normalize_command_answer,
)
from gitbench.harness.types import Fixture, Score

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


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

    def test_resolved_file_blocks_accepts_heading_variants_and_reordered_files(self, scorer):
        fixture = Fixture(
            id="files_001",
            description="Multi-file fixture",
            setup=[],
            prompt="Resolve files",
            expected="",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {
                    "main.py": 'def main():\n    print("Running enterprise")\n',
                    "utils.py": "DEBUG = True\nPORT = 9000\n",
                },
            },
        )

        result = scorer.score(
            fixture,
            "### `utils.py`:\nDEBUG = True\nPORT = 9000\n\n"
            "--- main.py\n"
            'def main():\n    print("Running enterprise")\n',
        )

        assert result.passed is True
        assert result.similarity == 1.0

    def test_resolved_file_blocks_accepts_per_file_fences(self, scorer):
        fixture = Fixture(
            id="files_002",
            description="Multi-file fixture",
            setup=[],
            prompt="Resolve files",
            expected="",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {
                    "main.py": 'def main():\n    print("Running enterprise")\n',
                    "utils.py": "DEBUG = True\nPORT = 9000\n",
                },
            },
        )

        result = scorer.score(
            fixture,
            "main.py:\n```python\n"
            'def main():\n    print("Running enterprise")\n'
            "```\n\n"
            "utils.py:\n```\nDEBUG = True\nPORT = 9000\n```\n",
        )

        assert result.passed is True

    def test_resolved_file_blocks_rejects_missing_file(self, scorer):
        fixture = Fixture(
            id="files_003",
            description="Multi-file fixture",
            setup=[],
            prompt="Resolve files",
            expected="",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {
                    "main.py": 'def main():\n    print("Running enterprise")\n',
                    "utils.py": "DEBUG = True\nPORT = 9000\n",
                },
            },
        )

        result = scorer.score(
            fixture,
            "main.py:\n"
            'def main():\n    print("Running enterprise")\n',
        )

        assert result.passed is False
        assert "Missing files" in result.error

    def test_resolved_file_blocks_rejects_extra_file_by_default(self, scorer):
        fixture = Fixture(
            id="files_004",
            description="Multi-file fixture",
            setup=[],
            prompt="Resolve files",
            expected="",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {"main.py": "print('ok')\n"},
            },
        )

        result = scorer.score(
            fixture,
            "main.py:\nprint('ok')\n\nREADME.md:\nextra\n",
        )

        assert result.passed is False
        assert "Extra files" in result.error

    def test_resolved_file_blocks_can_allow_extra_files(self, scorer):
        fixture = Fixture(
            id="files_005",
            description="Multi-file fixture",
            setup=[],
            prompt="Resolve files",
            expected="",
            scoring={
                "type": "resolved_file_blocks",
                "allow_extra_files": True,
                "expected_files": {"main.py": "print('ok')\n"},
            },
        )

        result = scorer.score(
            fixture,
            "main.py:\nprint('ok')\n\nREADME.md:\nextra\n",
        )

        assert result.passed is True

    def test_resolved_file_blocks_ignores_trailing_whitespace_and_final_newline(self, scorer):
        fixture = Fixture(
            id="files_006",
            description="Multi-file fixture",
            setup=[],
            prompt="Resolve files",
            expected="",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {"main.py": "if ok:\n    return True\n"},
            },
        )

        result = scorer.score(fixture, "main.py:\nif ok:   \n    return True")

        assert result.passed is True

    def test_resolved_file_blocks_accepts_expected_extensionless_filenames(self, scorer):
        fixture = Fixture(
            id="files_extensionless",
            description="Extensionless file fixture",
            setup=[],
            prompt="Resolve files",
            expected="",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {
                    "Dockerfile": "FROM python:3.12\n",
                    "Makefile": "test:\n\tpytest\n",
                },
            },
        )

        result = scorer.score(
            fixture,
            "Dockerfile:\nFROM python:3.12\n\nMakefile:\ntest:\n\tpytest\n",
        )

        assert result.passed is True

    def test_resolved_file_blocks_accepts_unheaded_single_file_content(self, scorer):
        fixture = Fixture(
            id="files_single_001",
            description="Single-file fixture",
            setup=[],
            prompt="Resolve greeting.txt",
            expected="Hello, Planet!!!",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {"greeting.txt": "Hello, Planet!!!"},
            },
        )

        result = scorer.score(fixture, "Hello, Planet!!!")

        assert result.passed is True
        assert result.similarity == 1.0

    def test_resolved_file_blocks_accepts_fenced_unheaded_single_file_content(self, scorer):
        fixture = Fixture(
            id="files_single_002",
            description="Single-file fixture",
            setup=[],
            prompt="Resolve greeting.txt",
            expected="Hello, Planet!!!",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {"greeting.txt": "Hello, Planet!!!"},
            },
        )

        result = scorer.score(fixture, "```text\nHello, Planet!!!\n```")

        assert result.passed is True

    def test_resolved_file_blocks_rejects_single_file_prose(self, scorer):
        fixture = Fixture(
            id="files_single_003",
            description="Single-file fixture",
            setup=[],
            prompt="Resolve greeting.txt",
            expected="Hello, Planet!!!",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {"greeting.txt": "Hello, Planet!!!"},
            },
        )

        result = scorer.score(fixture, "Here is the answer:\nHello, Planet!!!")

        assert result.passed is False
        assert "Content mismatch" in result.error

    def test_resolved_file_blocks_does_not_treat_yaml_key_as_heading(self, scorer):
        fixture = Fixture(
            id="files_single_yaml",
            description="Single-file YAML fixture",
            setup=[],
            prompt="Resolve config.yaml",
            expected="server:\n  port: 443\n  host: 0.0.0.0\n",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {
                    "config.yaml": "server:\n  port: 443\n  host: 0.0.0.0\n",
                },
            },
        )

        result = scorer.score(
            fixture,
            "config.yaml:\nserver:\n  port: 443\n  host: 0.0.0.0\n",
        )

        assert result.passed is True

    def test_resolved_file_blocks_does_not_treat_dotted_yaml_key_as_raw_heading(self, scorer):
        fixture = Fixture(
            id="files_single_yaml_domain",
            description="Single-file YAML fixture",
            setup=[],
            prompt="Resolve config.yaml",
            expected="example.com:\n  enabled: true\n",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {
                    "config.yaml": "example.com:\n  enabled: true\n",
                },
            },
        )

        result = scorer.score(fixture, "example.com:\n  enabled: true\n")

        assert result.passed is True

    def test_resolved_file_blocks_does_not_treat_dotted_yaml_key_as_block_heading(self, scorer):
        fixture = Fixture(
            id="files_single_yaml_domain_block",
            description="Single-file YAML fixture",
            setup=[],
            prompt="Resolve config.yaml",
            expected="example.com:\n  enabled: true\n",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {
                    "config.yaml": "example.com:\n  enabled: true\n",
                },
            },
        )

        result = scorer.score(
            fixture,
            "config.yaml:\nexample.com:\n  enabled: true\n",
        )

        assert result.passed is True

    def test_resolved_file_blocks_rejects_prose_before_file_heading(self, scorer):
        fixture = Fixture(
            id="files_single_004",
            description="Single-file fixture",
            setup=[],
            prompt="Resolve greeting.txt",
            expected="Hello, Planet!!!",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {"greeting.txt": "Hello, Planet!!!"},
            },
        )

        result = scorer.score(
            fixture,
            "Here is the file:\n\ngreeting.txt:\nHello, Planet!!!",
        )

        assert result.passed is False
        assert result.error == "Expected file heading before file content"

    def test_resolved_file_blocks_rejects_indentation_changes(self, scorer):
        fixture = Fixture(
            id="files_007",
            description="Multi-file fixture",
            setup=[],
            prompt="Resolve files",
            expected="",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {"main.py": "if ok:\n    return True\n"},
            },
        )

        result = scorer.score(fixture, "main.py:\nif ok:\nreturn True\n")

        assert result.passed is False
        assert "Content mismatch" in result.error

    def test_resolved_file_blocks_rejects_malformed_config(self, scorer):
        fixture = Fixture(
            id="files_008",
            description="Malformed fixture",
            setup=[],
            prompt="Resolve files",
            expected="",
            scoring={"type": "resolved_file_blocks"},
        )

        result = scorer.score(fixture, "main.py:\nprint('ok')\n")

        assert result.passed is False
        assert "expected_files" in result.error


class TestCommandAnswerNormalization:
    def test_plain_command_text(self):
        assert normalize_command_answer(" git status \n\ngit log --oneline ") == [
            "git status",
            "git log --oneline",
        ]

    def test_whole_answer_fence(self):
        assert normalize_command_answer("```bash\ngit submodule status\n```") == [
            "git submodule status"
        ]

    def test_prose_around_fence_is_rejected(self):
        with pytest.raises(CommandAnswerNormalizationError, match="prose around"):
            normalize_command_answer("Run this:\n```bash\ngit status\n```")

    def test_invalid_command_syntax_is_rejected(self):
        with pytest.raises(CommandAnswerNormalizationError, match="No closing quotation"):
            normalize_command_answer("git status 'unterminated")


class TestStripWrappingFence:
    """Tests for the _strip_wrapping_fence helper."""

    def test_bare_fence_stripped(self):
        assert _strip_wrapping_fence("```\nHello, Planet!!!\n```") == "Hello, Planet!!!"

    def test_fence_with_language_tag_stripped(self):
        assert _strip_wrapping_fence("```python\nx = 1\ny = 2\n```") == "x = 1\ny = 2"

    def test_no_fence_unchanged(self):
        assert _strip_wrapping_fence("Hello, Planet!!!") == "Hello, Planet!!!"

    def test_unterminated_fence_unchanged(self):
        text = "```\nHello, Planet!!!"
        assert _strip_wrapping_fence(text) == text

    def test_internal_backticks_preserved(self):
        text = "```\nuse `git log` here\n```"
        assert _strip_wrapping_fence(text) == "use `git log` here"

    def test_surrounding_whitespace_tolerated(self):
        assert _strip_wrapping_fence("  \n```\ncontent\n```\n  ") == "content"

    def test_non_language_opening_line_unchanged(self):
        text = "```not a language tag\ncontent\n```"
        assert _strip_wrapping_fence(text) == text


class TestExactMatchStripFences:
    """Tests for exact_match scoring with the strip_fences option."""

    @pytest.fixture
    def scorer(self):
        return Scorer()

    def fixture_with(self, scoring):
        return Fixture(
            id="fence_001",
            description="Conflict resolution fixture",
            setup=[],
            prompt="Provide ONLY the resolved file content",
            expected="Hello, Planet!!!",
            scoring=scoring,
        )

    def test_fenced_correct_output_passes(self, scorer):
        fixture = self.fixture_with({"type": "exact_match", "strip_fences": True})

        result = scorer.score(fixture, "```\nHello, Planet!!!\n```")

        assert result.passed is True
        assert result.similarity == 1.0

    def test_unfenced_wrong_output_fails(self, scorer):
        fixture = self.fixture_with({"type": "exact_match", "strip_fences": True})

        result = scorer.score(fixture, "Hello, World!!!")

        assert result.passed is False
        assert result.similarity == 0.0

    def test_fenced_output_fails_without_flag(self, scorer):
        fixture = self.fixture_with({"type": "exact_match"})

        result = scorer.score(fixture, "```\nHello, Planet!!!\n```")

        assert result.passed is False

    def test_original_false_positive_now_fails(self, scorer):
        """Regression: 'Hello, Planet!' scored 0.933 similarity against
        'Hello, Planet!!!' and passed the 0.9 threshold before migration."""
        fixture = self.fixture_with({"type": "exact_match", "strip_fences": True})

        result = scorer.score(fixture, "Hello, Planet!")

        assert result.passed is False
        assert result.similarity == 0.0


class TestMigratedGitGrepFixture:
    """Tests for git_grep/f001 under unordered_line_set scoring."""

    @pytest.fixture
    def fixture(self):
        loader = FixtureLoader()
        fixtures = loader.load_file(str(FIXTURES_DIR / "git_grep" / "f001.yaml"))
        return fixtures[0]

    def test_migrated_scoring_type(self, fixture):
        assert fixture.scoring == {"type": "unordered_line_set"}

    def test_expected_answer_passes(self, fixture):
        result = Scorer().score(fixture, fixture.expected)

        assert result.passed is True

    def test_reordered_lines_pass(self, fixture):
        reordered = "\n".join(reversed(fixture.expected.splitlines()))
        result = Scorer().score(fixture, reordered)

        assert result.passed is True

    def test_extra_filename_fails(self, fixture):
        result = Scorer().score(fixture, fixture.expected + "\nsrc/db.py")

        assert result.passed is False
        assert "Extra lines" in result.error


class TestScorerJudgeIntegration:
    """Tests for Scorer with JudgeClient integration."""

    @pytest.fixture
    def mock_judge_client(self):
        """Create a mock JudgeClient."""
        from unittest.mock import MagicMock
        from gitbench.harness.campaign import JudgeEvidence

        mock = MagicMock()
        mock.evaluate_commit_message.return_value = 0.85
        mock.evaluate_commit_message_evidence.return_value = JudgeEvidence(
            final_score=0.85,
            members=[],
        )
        return mock

    @pytest.fixture
    def llm_judge_fixture(self):
        """Create an llm_judge-type fixture."""
        return Fixture(
            id="judge_001",
            description="Judge-enabled fixture",
            setup=["git init"],
            prompt="Generate commit message",
            expected="fix: correct spelling error in file.txt",
            scoring={"type": "llm_judge", "threshold": 0.7},
        )

    @pytest.fixture
    def similarity_fixture(self):
        """Create a similarity-type fixture."""
        return Fixture(
            id="sim_001",
            description="Similarity fixture",
            setup=["git init"],
            prompt="Generate commit message",
            expected="fix: correct spelling error in file.txt",
            scoring={"type": "similarity", "threshold": 0.7},
        )

    def test_llm_judge_type_routes_to_judge(
        self, mock_judge_client, llm_judge_fixture
    ):
        """llm_judge type routes to judge when judge client is configured."""
        scorer = Scorer(judge_client=mock_judge_client)

        result = scorer.score(
            llm_judge_fixture,
            "fix: correct spelling error",
            diff="diff --git a/file.txt b/file.txt",
        )

        assert result.passed is True
        assert result.similarity == 0.85
        mock_judge_client.evaluate_commit_message_evidence.assert_called_once_with(
            "diff --git a/file.txt b/file.txt",
            "fix: correct spelling error",
            prompt="Generate commit message",
        )

    def test_llm_judge_passes_empty_diff(
        self, mock_judge_client, llm_judge_fixture
    ):
        """llm_judge passes empty string when diff is None."""
        scorer = Scorer(judge_client=mock_judge_client)

        result = scorer.score(
            llm_judge_fixture,
            llm_judge_fixture.expected,
        )

        assert result.passed is True
        assert result.similarity == 0.85
        mock_judge_client.evaluate_commit_message_evidence.assert_called_once_with(
            "",
            llm_judge_fixture.expected,
            prompt="Generate commit message",
        )

    def test_llm_judge_without_client_errors(self, llm_judge_fixture):
        """llm_judge without judge client returns a scoring error."""
        scorer = Scorer()

        result = scorer.score(
            llm_judge_fixture,
            llm_judge_fixture.expected,
            diff="diff content",
        )

        assert result.passed is False
        assert result.similarity == 0.0
        assert "llm_judge requires a judge client" in result.error

    def test_llm_judge_exhausted_falls_back_for_legacy_scoring(
        self, mock_judge_client, llm_judge_fixture
    ):
        """Exhausted judge failures fall back outside campaign scoring."""
        from gitbench.harness.campaign import JudgeEvidence

        mock_judge_client.evaluate_commit_message_evidence.return_value = JudgeEvidence(
            final_score=None,
            members=[],
            error="All 1 judge model(s) failed.",
            exhausted=True,
        )
        scorer = Scorer(judge_client=mock_judge_client)

        result = scorer.score(
            llm_judge_fixture,
            "fix: correct spelling error",
            diff="diff content",
        )

        assert result.passed is True
        assert result.unscored is False
        assert "judge_failed" in result.error
        assert result.similarity > 0.0

    def test_llm_judge_exhausted_marks_campaign_attempt_unscored(
        self, mock_judge_client, llm_judge_fixture
    ):
        """Campaign scoring preserves judge exhaustion as unscored."""
        from gitbench.harness.campaign import JudgeEvidence

        mock_judge_client.evaluate_commit_message_evidence.return_value = JudgeEvidence(
            final_score=None,
            members=[],
            error="All 1 judge model(s) failed.",
            exhausted=True,
        )
        scorer = Scorer(judge_client=mock_judge_client)

        result = scorer.score(
            llm_judge_fixture,
            "fix: correct spelling error",
            diff="diff content",
            campaign_scoring_context={
                "fixture_input_hash": "input-a",
                "target_output_hash": "output-a",
            },
        )

        assert result.passed is False
        assert result.similarity == 0.0
        assert result.unscored is True
        assert "judge_exhausted" in result.error

    def test_similarity_never_calls_judge(
        self, mock_judge_client, similarity_fixture
    ):
        """similarity type never calls the judge even when one is configured."""
        scorer = Scorer(judge_client=mock_judge_client)

        result = scorer.score(
            similarity_fixture,
            similarity_fixture.expected,
            diff="diff content",
        )

        # Pure SequenceMatcher — exact match = 1.0
        assert result.passed is True
        assert result.similarity == 1.0
        mock_judge_client.evaluate_commit_message.assert_not_called()

    def test_similarity_ignores_judge_with_diff(
        self, mock_judge_client, similarity_fixture
    ):
        """similarity type uses SequenceMatcher even with diff and judge."""
        scorer = Scorer(judge_client=mock_judge_client)

        result = scorer.score(
            similarity_fixture,
            "fix: correct spelling error",
            diff="diff --git a/file.txt b/file.txt",
        )

        # SequenceMatcher, not judge
        assert 0.0 <= result.similarity <= 1.0
        mock_judge_client.evaluate_commit_message.assert_not_called()

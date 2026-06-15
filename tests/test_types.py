"""Tests for GitBench core types."""

from gitbench.harness.types import BenchmarkResult, Fixture, ModelMessage, Score


class TestModelMessage:
    """Tests for ModelMessage dataclass."""

    def test_creation(self):
        """Test creating a ModelMessage."""
        msg = ModelMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_to_dict(self):
        """Test converting ModelMessage to dictionary."""
        msg = ModelMessage(role="assistant", content="Hi there")
        d = msg.to_dict()
        assert d == {"role": "assistant", "content": "Hi there"}

    def test_from_dict(self):
        """Test creating ModelMessage from dictionary."""
        d = {"role": "system", "content": "You are helpful"}
        msg = ModelMessage.from_dict(d)
        assert msg.role == "system"
        assert msg.content == "You are helpful"

    def test_roundtrip(self):
        """Test to_dict -> from_dict roundtrip."""
        original = ModelMessage(role="user", content="Test content")
        reconstructed = ModelMessage.from_dict(original.to_dict())
        assert reconstructed.role == original.role
        assert reconstructed.content == original.content


class TestFixture:
    """Tests for Fixture dataclass."""

    def test_creation(self):
        """Test creating a Fixture."""
        fixture = Fixture(
            id="fixture_001",
            description="Test fixture",
            setup=["git init", "git add ."],
            prompt="Generate commit message",
            expected="feat: add feature",
            scoring={"type": "similarity", "threshold": 0.5},
        )
        assert fixture.id == "fixture_001"
        assert fixture.description == "Test fixture"
        assert len(fixture.setup) == 2
        assert fixture.prompt == "Generate commit message"

    def test_to_dict(self):
        """Test converting Fixture to dictionary."""
        fixture = Fixture(
            id="test",
            description="desc",
            setup=["cmd1"],
            prompt="prompt",
            expected="expected",
            scoring={"type": "exact"},
        )
        d = fixture.to_dict()
        assert d["id"] == "test"
        assert d["setup"] == ["cmd1"]
        assert d["scoring"]["type"] == "exact"

    def test_from_dict(self):
        """Test creating Fixture from dictionary."""
        d = {
            "id": "from_dict_test",
            "description": "From dict test",
            "setup": ["git commit"],
            "prompt": "prompt",
            "expected": "expected",
            "scoring": {"type": "similarity", "threshold": 0.8},
        }
        fixture = Fixture.from_dict(d)
        assert fixture.id == "from_dict_test"
        assert len(fixture.setup) == 1

    def test_roundtrip(self):
        """Test to_dict -> from_dict roundtrip."""
        original = Fixture(
            id="roundtrip",
            description="Roundtrip test",
            setup=["setup1", "setup2"],
            prompt="Test prompt",
            expected="Expected output",
            scoring={"type": "fuzzy", "threshold": 0.6},
        )
        reconstructed = Fixture.from_dict(original.to_dict())
        assert reconstructed.id == original.id
        assert reconstructed.setup == original.setup
        assert reconstructed.scoring == original.scoring


class TestScore:
    """Tests for Score dataclass."""

    def test_creation(self):
        """Test creating a Score."""
        score = Score(
            fixture_id="f001",
            passed=True,
            similarity=0.95,
            model_output="feat: great output",
            error=None,
        )
        assert score.passed is True
        assert score.similarity == 0.95

    def test_creation_with_error(self):
        """Test creating a Score with an error."""
        score = Score(
            fixture_id="f002",
            passed=False,
            similarity=0.0,
            model_output="",
            error="API timeout",
        )
        assert score.error == "API timeout"
        assert score.passed is False

    def test_to_dict(self):
        """Test converting Score to dictionary."""
        score = Score(
            fixture_id="test",
            passed=True,
            similarity=0.75,
            model_output="output",
            error=None,
        )
        d = score.to_dict()
        assert d["fixture_id"] == "test"
        assert d["passed"] is True
        assert d["similarity"] == 0.75

    def test_from_dict(self):
        """Test creating Score from dictionary."""
        d = {
            "fixture_id": "from_dict",
            "passed": False,
            "similarity": 0.3,
            "model_output": "bad output",
            "error": "Test error",
        }
        score = Score.from_dict(d)
        assert score.passed is False
        assert score.error == "Test error"

    def test_roundtrip(self):
        """Test to_dict -> from_dict roundtrip."""
        original = Score(
            fixture_id="roundtrip",
            passed=True,
            similarity=0.88,
            model_output="Good output",
            error=None,
        )
        reconstructed = Score.from_dict(original.to_dict())
        assert reconstructed.fixture_id == original.fixture_id
        assert reconstructed.passed == original.passed
        assert reconstructed.similarity == original.similarity

    def test_operational_failure_roundtrip(self):
        """Operational failure flag survives serialization."""
        original = Score(
            fixture_id="f1",
            passed=False,
            similarity=0.0,
            model_output="",
            error="timeout",
            operational_failure=True,
        )
        data = original.to_dict()
        assert data["operational_failure"] is True
        reconstructed = Score.from_dict(data)
        assert reconstructed.operational_failure is True

    def test_operational_failure_false_is_omitted(self):
        """Non-operational failures keep the serialized shape compact."""
        score = Score(
            fixture_id="f1",
            passed=False,
            similarity=0.0,
            model_output="bad",
            error="schema failure",
        )
        data = score.to_dict()
        assert "operational_failure" not in data


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass."""

    def test_creation(self):
        """Test creating a BenchmarkResult."""
        scores = [
            Score("f1", True, 0.9, "out1"),
            Score("f2", False, 0.5, "out2"),
        ]
        result = BenchmarkResult(
            benchmark="test_benchmark",
            total=2,
            passed=1,
            pass_at_k=0.5,
            scores=scores,
            errors=0,
        )
        assert result.total == 2
        assert result.passed == 1
        assert result.pass_at_k == 0.5
        assert len(result.scores) == 2

    def test_to_dict(self):
        """Test converting BenchmarkResult to dictionary."""
        scores = [Score("f1", True, 0.8, "output")]
        result = BenchmarkResult(
            benchmark="bench",
            total=1,
            passed=1,
            pass_at_k=1.0,
            scores=scores,
            errors=0,
        )
        d = result.to_dict()
        assert d["benchmark"] == "bench"
        assert d["total"] == 1
        assert d["pass_at_k"] == 1.0
        assert len(d["scores"]) == 1

    def test_from_dict(self):
        """Test creating BenchmarkResult from dictionary."""
        d = {
            "benchmark": "test_from_dict",
            "total": 2,
            "passed": 1,
            "pass_at_k": 0.5,
            "scores": [
                {"fixture_id": "f1", "passed": True, "similarity": 0.9, "model_output": "o1"},
                {"fixture_id": "f2", "passed": False, "similarity": 0.4, "model_output": "o2", "error": None},
            ],
            "errors": 0,
        }
        result = BenchmarkResult.from_dict(d)
        assert result.benchmark == "test_from_dict"
        assert len(result.scores) == 2
        assert result.scores[0].passed is True

    def test_roundtrip(self):
        """Test to_dict -> from_dict roundtrip."""
        original = BenchmarkResult(
            benchmark="roundtrip_bench",
            total=3,
            passed=2,
            pass_at_k=0.666,
            scores=[
                Score("f1", True, 0.9, "o1"),
                Score("f2", True, 0.8, "o2"),
                Score("f3", False, 0.3, "o3"),
            ],
            errors=0,
        )
        reconstructed = BenchmarkResult.from_dict(original.to_dict())
        assert reconstructed.benchmark == original.benchmark
        assert reconstructed.total == original.total
        assert len(reconstructed.scores) == 3
"""Tests for gitbench.harness.capabilities validation module."""

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from gitbench.harness.capabilities import (
    CACHE_DIR,
    CACHE_FILE,
    CACHE_TTL,
    _load_cache,
    _save_cache,
    fetch_model_capabilities,
    load_effort_matrix,
    resolve_capabilities,
    validate_models,
)


@pytest.fixture
def tmp_cache_dir(tmp_path):
    """Override cache location to a temporary directory."""
    real_cache_dir = CACHE_DIR
    real_cache_file = CACHE_FILE
    import gitbench.harness.capabilities as mod

    mod.CACHE_DIR = tmp_path / "cache" / "gitbench"
    mod.CACHE_FILE = mod.CACHE_DIR / "model-capabilities.json"
    yield mod.CACHE_FILE
    mod.CACHE_DIR = real_cache_dir
    mod.CACHE_FILE = real_cache_file


# ---------------------------------------------------------------------------
# Cache read / write
# ---------------------------------------------------------------------------

class TestCacheIO:
    """Tests for _load_cache and _save_cache."""

    def test_load_cache_missing_file(self, tmp_cache_dir):
        """None is returned when cache file doesn't exist."""
        assert _load_cache() is None

    def test_save_and_load_roundtrip(self, tmp_cache_dir):
        """Saved cache should be loadable."""
        data = {
            "fetched_at": "2026-01-01T00:00:00+00:00",
            "reasoning_models": ["openai/gpt-4o", "anthropic/claude-sonnet-4"],
        }
        _save_cache(data)
        loaded = _load_cache()
        assert loaded == data

    def test_corrupt_cache_returns_none(self, tmp_cache_dir):
        """Corrupt JSON returns None."""
        tmp_cache_dir.parent.mkdir(parents=True, exist_ok=True)
        tmp_cache_dir.write_text("not json")
        assert _load_cache() is None


# ---------------------------------------------------------------------------
# fetch_model_capabilities
# ---------------------------------------------------------------------------

class TestFetchModelCapabilities:
    """Tests for fetch_model_capabilities."""

    def test_successful_fetch(self, tmp_cache_dir):
        """A valid JSON response is parsed and cached."""
        mock_response = {
            "data": [
                {"id": "openai/gpt-4o", "supported_parameters": ["temperature", "reasoning"]},
                {"id": "openai/gpt-4o-mini", "supported_parameters": ["temperature"]},
                {"id": "anthropic/claude-opus-4.7", "supported_parameters": ["reasoning"]},
            ]
        }
        from unittest.mock import patch

        with patch("gitbench.harness.capabilities.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
                mock_response
            ).encode()
            result = fetch_model_capabilities()

        assert "reasoning_models" in result
        assert result["reasoning_models"] == [
            "openai/gpt-4o",
            "anthropic/claude-opus-4.7",
        ]
        assert "fetched_at" in result

        # Must be written to disk
        cached = _load_cache()
        assert cached is not None
        assert cached["reasoning_models"] == result["reasoning_models"]

    def test_http_error_propagates(self, tmp_cache_dir):
        """Network errors raise RuntimeError."""
        from unittest.mock import patch

        import urllib.error

        with patch("gitbench.harness.capabilities.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("connection refused")
            with pytest.raises(RuntimeError, match="Failed to fetch"):
                fetch_model_capabilities()

    def test_invalid_json_response(self, tmp_cache_dir):
        """Non-JSON response raises RuntimeError."""
        from unittest.mock import patch

        with patch("gitbench.harness.capabilities.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.read.return_value = (
                b"not json"
            )
            with pytest.raises(RuntimeError, match="Invalid JSON"):
                fetch_model_capabilities()

    def test_unexpected_payload_format(self, tmp_cache_dir):
        """Malformed payload raises RuntimeError."""
        from unittest.mock import patch

        with patch("gitbench.harness.capabilities.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.read.return_value = (
                json.dumps({"wrong_key": "value"}).encode()
            )
            with pytest.raises(RuntimeError, match="Unexpected response format"):
                fetch_model_capabilities()


# ---------------------------------------------------------------------------
# load_effort_matrix
# ---------------------------------------------------------------------------

class TestLoadEffortMatrix:
    """Tests for load_effort_matrix."""

    def test_loads_bundled_matrix(self, tmp_path, monkeypatch):
        """The matrix should load as a dict."""
        import gitbench.harness.capabilities as mod

        test_matrix = tmp_path / "test_matrix.json"
        test_matrix.write_text(json.dumps({
            "_preflight_version": 1,
            "_comment": "test",
            "models": {
                "gpt-4o": {"mappings": {"high": "high", "xhigh": "xhigh"}}
            }
        }))

        with monkeypatch.context() as m:
            m.setattr(mod, "_EFFORT_MATRIX_PATH", str(test_matrix))
            matrix = load_effort_matrix()

        assert isinstance(matrix, dict)
        assert matrix["gpt-4o"] == {"high": "high", "xhigh": "xhigh"}

    def test_entry_has_mappings_dict(self, monkeypatch, tmp_path):
        """An entry with 'mappings' key is loaded correctly."""
        import gitbench.harness.capabilities as mod

        test_matrix = tmp_path / "test_matrix.json"
        test_matrix.write_text(json.dumps({
            "_preflight_version": 1,
            "_comment": "test",
            "models": {
                "deepseek-v4-flash": {
                    "mappings": {
                        "high": "high",
                        "xhigh": "xhigh",
                        "low": "high"
                    }
                }
            }
        }))

        with monkeypatch.context() as m:
            m.setattr(mod, "_EFFORT_MATRIX_PATH", str(test_matrix))
            matrix = load_effort_matrix()

        assert matrix["deepseek-v4-flash"] == {
            "high": "high",
            "xhigh": "xhigh",
            "low": "high",
        }

    @pytest.mark.parametrize("model_id", ["deepseek-v4-flash", "deepseek-v4-pro"])
    def test_empty_matrix_has_no_entries(self, model_id, tmp_path, monkeypatch):
        """An empty matrix file returns no entries."""
        import gitbench.harness.capabilities as mod

        test_matrix = tmp_path / "test_matrix.json"
        test_matrix.write_text(json.dumps({
            "_preflight_version": 1,
            "_comment": "test",
            "models": {}
        }))

        with monkeypatch.context() as m:
            m.setattr(mod, "_EFFORT_MATRIX_PATH", str(test_matrix))
            matrix = load_effort_matrix()
        assert matrix == {}

    def test_missing_file_returns_empty(self, monkeypatch):
        """Missing file returns empty dict."""
        import gitbench.harness.capabilities as mod

        with monkeypatch.context() as m:
            m.setattr(mod, "_EFFORT_MATRIX_PATH", "/nonexistent/path.json")
            assert load_effort_matrix() == {}


# ---------------------------------------------------------------------------
# resolve_capabilities
# ---------------------------------------------------------------------------

class TestResolveCapabilities:
    """Tests for resolve_capabilities."""

    def test_cache_miss_fetches_data(self, tmp_cache_dir):
        """When no cache exists, fetch fresh data."""
        mock_response = {
            "data": [
                {
                    "id": "openai/gpt-4o",
                    "supported_parameters": ["temperature", "reasoning"],
                },
            ]
        }
        from unittest.mock import patch

        with patch("gitbench.harness.capabilities.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
                mock_response
            ).encode()
            result = resolve_capabilities()

        assert result["reasoning_models"] == {"openai/gpt-4o"}
        assert isinstance(result["effort_matrix"], dict)

    def test_fresh_cache_skips_fetch(self, tmp_cache_dir):
        """Fresh cache should skip API call."""
        import gitbench.harness.capabilities as mod

        now = datetime.now(timezone.utc)
        cache_data = {
            "fetched_at": now.isoformat(),
            "reasoning_models": ["cached/model"],
        }
        _save_cache(cache_data)

        from unittest.mock import patch

        with patch("gitbench.harness.capabilities.fetch_model_capabilities") as mock_fetch:
            result = mod.resolve_capabilities()
            mock_fetch.assert_not_called()

        assert result["reasoning_models"] == {"cached/model"}

    def test_stale_cache_fetches_fresh(self, tmp_cache_dir):
        """Stale cache triggers a fresh fetch."""
        stale_time = datetime.now(timezone.utc) - timedelta(days=8)
        cache_data = {
            "fetched_at": stale_time.isoformat(),
            "reasoning_models": ["stale/model"],
        }
        _save_cache(cache_data)

        mock_response = {
            "data": [
                {
                    "id": "fresh/model",
                    "supported_parameters": ["reasoning"],
                },
            ]
        }
        from unittest.mock import patch

        with patch("gitbench.harness.capabilities.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
                mock_response
            ).encode()
            result = resolve_capabilities()

        assert result["reasoning_models"] == {"fresh/model"}

    def test_fetch_failure_with_stale_cache_uses_stale(self, tmp_cache_dir):
        """When fetch fails but stale cache exists, use the stale data."""
        stale_time = datetime.now(timezone.utc) - timedelta(days=8)
        cache_data = {
            "fetched_at": stale_time.isoformat(),
            "reasoning_models": ["stale/model"],
        }
        _save_cache(cache_data)

        from unittest.mock import patch

        with patch(
            "gitbench.harness.capabilities.fetch_model_capabilities",
            side_effect=RuntimeError("network error"),
        ):
            result = resolve_capabilities()

        assert result["reasoning_models"] == {"stale/model"}

    def test_fetch_failure_no_cache_raises(self, tmp_cache_dir):
        """No cache and fetch failure raises RuntimeError."""
        from unittest.mock import patch

        with patch(
            "gitbench.harness.capabilities.fetch_model_capabilities",
            side_effect=RuntimeError("network error"),
        ):
            with pytest.raises(RuntimeError):
                resolve_capabilities()


# ---------------------------------------------------------------------------
# validate_models
# ---------------------------------------------------------------------------

class TestValidateModels:
    """Tests for validate_models."""

    def _mock_resolve_capabilities(self, caps=None):
        """Set up a mocked resolve_capabilities that returns known data."""
        if caps is None:
            caps = {
                "reasoning_models": {"openai/gpt-4o", "anthropic/claude-opus-4.7"},
                "effort_matrix": {
                    "gpt-4o": {
                        "minimal": "minimal",
                        "low": "low",
                        "medium": "medium",
                        "high": "high",
                        "xhigh": "xhigh",
                    },
                    "claude-opus-4.7": {
                        "none": "none",
                        "minimal": "minimal",
                        "low": "low",
                        "medium": "medium",
                        "high": "high",
                        "xhigh": "xhigh",
                        "max": "max",
                    },
                },
                "fetched_at": "2026-01-01T00:00:00Z",
            }
        from unittest.mock import patch

        return patch(
            "gitbench.harness.capabilities.resolve_capabilities", return_value=caps
        )

    def test_empty_list_ok(self):
        """Empty model list passes."""
        with self._mock_resolve_capabilities():
            assert validate_models([]) == []

    def test_mock_models_bypass(self):
        """Mock models bypass validation."""
        with self._mock_resolve_capabilities():
            assert validate_models(["mock"]) == []
            assert validate_models(["mock#high"]) == []
            assert validate_models(["mock:max"]) == []

    def test_no_effort_suffix_passes(self):
        """Models without effort pass regardless of capabilities."""
        with self._mock_resolve_capabilities():
            assert validate_models(["openai/gpt-4o"]) == []
            assert validate_models(["some/new-model"]) == []

    def test_valid_level_passes(self):
        """Known model with valid level passes."""
        with self._mock_resolve_capabilities():
            assert validate_models(["openai/gpt-4o#high"]) == []

    def test_valid_colon_level_passes(self):
        """Colon-delimited effort works."""
        with self._mock_resolve_capabilities():
            assert validate_models(["openai/gpt-4o:high"]) == []
            assert validate_models(["anthropic/claude-opus-4.7:max"]) == []

    def test_invalid_level_reported(self):
        """Invalid level string returns error."""
        with self._mock_resolve_capabilities():
            errors = validate_models(["openai/gpt-4o#ultra"])
        assert len(errors) == 1
        assert "invalid reasoning level" in errors[0].lower()
        assert "ultra" in errors[0]

    def test_undocumented_level_warns_not_errors(self):
        """Undocumented level for matrix-known model warns but passes."""
        with self._mock_resolve_capabilities():
            errors = validate_models(["openai/gpt-4o#max"])
        assert errors == []

    def test_no_reasoning_support_warns(self):
        """Model not in reasoning_models set warns but passes."""
        with self._mock_resolve_capabilities():
            errors = validate_models(["some-other/model#high"])
        assert errors == []

    def test_multiple_errors_collected(self):
        """All invalid models are reported, not just first.

        ``openai/gpt-4o#max`` is no longer an error — the matrix only has
        verified mappings up to xhigh so max warns rather than rejects.
        ``some-other/model#high`` also warns (not in API reasoning set).
        """
        with self._mock_resolve_capabilities():
            errors = validate_models(
                ["openai/gpt-4o#ultra", "some-other/model#high", "openai/gpt-4o#max"]
            )
        assert len(errors) == 1  # only 'ultra' is invalid vocabulary

    def test_mixed_valid_and_invalid(self):
        """Valid models don't mask invalid ones."""
        with self._mock_resolve_capabilities():
            errors = validate_models(
                ["openai/gpt-4o#high", "unknown#high", "anthropic/claude-opus-4.7:max"]
            )
        assert errors == []

    def test_ollama_model_warns_not_errors(self):
        """Ollama models get warning, not error."""
        caps = {
            "reasoning_models": set(),
            "effort_matrix": {},
            "fetched_at": "2026-01-01T00:00:00Z",
        }
        with self._mock_resolve_capabilities(caps):
            errors = validate_models(
                ["llama3.1:8b#high"],
                profile_configs=[{"provider": "ollama"}],
            )
        assert errors == []

    def test_openrouter_model_undocumented_level_warns(self):
        """OpenRouter models with undocumented level warn but pass."""
        caps = {
            "reasoning_models": {"openai/gpt-4o"},
            "effort_matrix": {"gpt-4o": {"low": "low", "medium": "medium"}},
            "fetched_at": "2026-01-01T00:00:00Z",
        }
        with self._mock_resolve_capabilities(caps):
            errors = validate_models(
                ["openai/gpt-4o#high"],
                profile_configs=[{"provider": "openai"}],
            )
        assert errors == []

    def test_fetch_failure_returns_error(self):
        """When resolve_capabilities fails, an error is returned."""
        from unittest.mock import patch

        with patch(
            "gitbench.harness.capabilities.resolve_capabilities",
            side_effect=RuntimeError("network down"),
        ):
            errors = validate_models(["openai/gpt-4o#high"])
        assert len(errors) == 1
        assert "network down" in errors[0]

    def test_provider_prefix_stripped_for_matrix_lookup(self):
        """Models with provider/gpt-4o find matrix entry for gpt-4o."""
        caps = {
            "reasoning_models": {"openai/gpt-4o"},
            "effort_matrix": {
                "gpt-4o": {
                    "low": "low",
                    "medium": "medium",
                    "high": "high",
                    "xhigh": "xhigh",
                }
            },
            "fetched_at": "2026-01-01T00:00:00Z",
        }
        with self._mock_resolve_capabilities(caps):
            errors = validate_models(["openai/gpt-4o#high"])
        assert errors == []

    @pytest.mark.parametrize("model_id", ["deepseek-v4-flash", "deepseek-v4-pro"])
    @pytest.mark.parametrize("level", ["none", "minimal", "low", "medium"])
    def test_deepseek_v4_warns_undocumented_efforts(self, model_id, level):
        """Unverified DeepSeek V4 efforts warn but pass static validation."""
        caps = {
            "reasoning_models": {f"deepseek/{model_id}"},
            "effort_matrix": {
                model_id: {"high": "high", "xhigh": "xhigh"}
            },
            "fetched_at": "2026-01-01T00:00:00Z",
        }
        with self._mock_resolve_capabilities(caps):
            errors = validate_models([f"deepseek/{model_id}:{level}"])
        assert errors == []

    @pytest.mark.parametrize("model_id", ["deepseek-v4-flash", "deepseek-v4-pro"])
    @pytest.mark.parametrize("level", ["high", "xhigh"])
    def test_deepseek_v4_accepts_verified_efforts(self, model_id, level):
        """Verified DeepSeek V4 efforts pass static validation."""
        caps = {
            "reasoning_models": {f"deepseek/{model_id}"},
            "effort_matrix": {
                model_id: {"high": "high", "xhigh": "xhigh"}
            },
            "fetched_at": "2026-01-01T00:00:00Z",
        }
        with self._mock_resolve_capabilities(caps):
            assert validate_models([f"deepseek/{model_id}:{level}"]) == []

"""Tests for GitBench config module."""

import json
import os
from unittest.mock import patch

import pytest

from gitbench.config import (
    discover_judge_benchmarks,
    find_config,
    find_profile_for_model,
    load_config,
    load_project_env,
    load_result_safety_config,
    resolve_profile,
)


class TestFindConfig:
    """Tests for find_config function."""

    def test_returns_none_when_no_config(self, tmp_path, monkeypatch):
        """Test that None is returned when no config file exists."""
        monkeypatch.chdir(tmp_path)
        result = find_config()
        assert result is None

    def test_finds_gitbench_json(self, tmp_path, monkeypatch):
        """Test that gitbench.json in cwd is found."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "gitbench.json"
        config_file.write_text("{}")
        result = find_config()
        assert result == config_file

    def test_finds_dot_gitbench_json(self, tmp_path, monkeypatch):
        """Test that .gitbench.json in cwd is found."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / ".gitbench.json"
        config_file.write_text("{}")
        result = find_config()
        assert result == config_file


class TestLoadConfig:
    """Tests for load_config function."""

    def test_returns_empty_dict_when_no_config(self, tmp_path, monkeypatch):
        """Test that empty dict is returned when no config file exists."""
        monkeypatch.chdir(tmp_path)
        result = load_config()
        assert result == {}

    def test_loads_valid_config(self, tmp_path):
        """Test loading a valid config file."""
        config_file = tmp_path / "gitbench.json"
        config = {
            "models": {
                "test": {"model": "gpt-4o", "api_key_env": "TEST_KEY"}
            }
        }
        config_file.write_text(json.dumps(config))
        result = load_config(config_file)
        assert result == config

    def test_exits_on_invalid_json(self, tmp_path):
        """Test that invalid JSON raises SystemExit."""
        config_file = tmp_path / "gitbench.json"
        config_file.write_text("{invalid json}")
        with pytest.raises(SystemExit):
            load_config(config_file)

    def test_loads_dotenv_next_to_config_without_overriding_shell_env(
        self, tmp_path, monkeypatch
    ):
        """Project .env values are loaded, while existing shell env values win."""
        monkeypatch.delenv("DOTENV_ONLY_KEY", raising=False)
        monkeypatch.setenv("SHELL_WINS_KEY", "sk-from-shell")
        config_file = tmp_path / "gitbench.json"
        config_file.write_text("{}")
        (tmp_path / ".env").write_text(
            "DOTENV_ONLY_KEY=sk-from-dotenv\n"
            "SHELL_WINS_KEY=sk-from-dotenv\n"
        )

        load_config(config_file)

        assert os.environ["DOTENV_ONLY_KEY"] == "sk-from-dotenv"
        assert os.environ["SHELL_WINS_KEY"] == "sk-from-shell"

    def test_missing_dotenv_is_allowed(self, tmp_path, monkeypatch):
        """Missing .env files do not prevent config loading."""
        monkeypatch.delenv("MISSING_DOTENV_KEY", raising=False)
        config_file = tmp_path / "gitbench.json"
        config_file.write_text("{}")

        assert load_project_env(config_file) is False
        assert load_config(config_file) == {}


class TestResolveProfile:
    """Tests for resolve_profile function."""

    def test_raises_on_missing_profile(self):
        """Test that missing profile raises SystemExit."""
        config = {"models": {"existing": {"model": "gpt-4o"}}}
        with pytest.raises(SystemExit, match="not found"):
            resolve_profile(config, "nonexistent")

    def test_returns_profile_values(self):
        """Test resolving a profile with api_key_env set."""
        config = {
            "models": {
                "test": {
                    "model": "gpt-4o",
                    "base_url": "https://api.openai.com/v1",
                    "api_key_env": "TEST_API_KEY",
                }
            }
        }
        with patch.dict(os.environ, {"TEST_API_KEY": "sk-test123"}):
            result = resolve_profile(config, "test")
            assert result["models"] == ["gpt-4o"]
            assert result["base_url"] == "https://api.openai.com/v1"
            assert result["api_key"] == "sk-test123"
            assert result["_api_key_env"] == "TEST_API_KEY"

    def test_api_key_none_when_env_not_set(self):
        """Test that api_key is None when env var is not set."""
        config = {
            "models": {
                "test": {
                    "model": "gpt-4o",
                    "api_key_env": "NONEXISTENT_VAR_12345",
                }
            }
        }
        with patch.dict(os.environ, {}, clear=True):
            result = resolve_profile(config, "test")
            assert result["api_key"] is None
            assert result["_api_key_env"] == "NONEXISTENT_VAR_12345"

    def test_no_api_key_when_not_configured(self):
        """Test profile without api_key_env."""
        config = {
            "models": {
                "local": {
                    "model": "llama3.1",
                    "base_url": "http://localhost:11434/v1",
                }
            }
        }
        result = resolve_profile(config, "local")
        assert result["models"] == ["llama3.1"]
        assert "api_key" not in result
        assert "_api_key_env" not in result

    def test_direct_api_key_in_config_is_rejected(self):
        """Persisted api_key secrets are rejected."""
        config = {
            "models": {
                "cloud": {
                    "model": "gpt-4o",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-direct-key-123",
                }
            }
        }
        with pytest.raises(SystemExit, match="unsupported field 'api_key'"):
            resolve_profile(config, "cloud")

    def test_api_key_with_api_key_env_is_rejected(self):
        """api_key is invalid even when api_key_env is also present."""
        config = {
            "models": {
                "cloud": {
                    "model": "gpt-4o",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-direct-key",
                    "api_key_env": "MY_API_KEY",
                }
            }
        }
        with patch.dict(os.environ, {"MY_API_KEY": "sk-from-env"}):
            with pytest.raises(SystemExit, match="unsupported field 'api_key'"):
                resolve_profile(config, "cloud")

    def test_resolves_api_key_from_dotenv_loaded_by_config(self, tmp_path, monkeypatch):
        """Resolving a profile can use values loaded from .env."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config = {
            "models": {
                "cloud": {
                    "model": "gpt-4o",
                    "api_key_env": "OPENAI_API_KEY",
                }
            }
        }
        config_file = tmp_path / "gitbench.json"
        config_file.write_text(json.dumps(config))
        (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-from-dotenv\n")

        loaded = load_config(config_file)
        result = resolve_profile(loaded, "cloud")

        assert result["api_key"] == "sk-from-dotenv"
        assert result["_api_key_env"] == "OPENAI_API_KEY"

    def test_explicit_provider_preserved(self):
        """Test that explicit provider field is preserved."""
        config = {
            "models": {
                "local": {
                    "model": "gemma4:26b",
                    "base_url": "http://localhost:11434/v1",
                    "provider": "ollama",
                }
            }
        }
        result = resolve_profile(config, "local")
        assert result["provider"] == "ollama"

    def test_provider_inferred_as_ollama_for_localhost(self):
        """Test that provider defaults to 'ollama' when base_url contains localhost."""
        config = {
            "models": {
                "local": {
                    "model": "llama3.1:8b",
                    "base_url": "http://localhost:11434/v1",
                }
            }
        }
        result = resolve_profile(config, "local")
        assert result["provider"] == "ollama"

    def test_provider_inferred_as_ollama_for_127_0_0_1(self):
        """Test that provider defaults to 'ollama' for 127.0.0.1."""
        config = {
            "models": {
                "local": {
                    "model": "llama3.1:8b",
                    "base_url": "http://127.0.0.1:11434",
                }
            }
        }
        result = resolve_profile(config, "local")
        assert result["provider"] == "ollama"

    def test_provider_inferred_as_openai_for_remote_url(self):
        """Test that provider defaults to 'openai' for remote URLs."""
        config = {
            "models": {
                "cloud": {
                    "model": "gpt-4o",
                    "base_url": "https://api.openai.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                }
            }
        }
        result = resolve_profile(config, "cloud")
        assert result["provider"] == "openai"

    def test_provider_inferred_as_openai_when_no_base_url(self):
        """Test that provider defaults to 'openai' when no base_url is set."""
        config = {
            "models": {
                "default": {
                    "model": "gpt-4o-mini",
                    "api_key_env": "OPENAI_API_KEY",
                }
            }
        }
        result = resolve_profile(config, "default")
        assert result["provider"] == "openai"


class TestFindProfileForModel:
    """Tests for find_profile_for_model function."""

    def test_finds_matching_profile(self):
        """Test finding a profile by model name."""
        config = {
            "models": {
                "local-ollama": {
                    "model": "gemma4:26b",
                    "base_url": "http://localhost:11434/v1",
                    "provider": "ollama",
                },
                "cloud-openai": {
                    "model": "gpt-4o",
                    "base_url": "https://api.openai.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                },
            }
        }
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            result = find_profile_for_model(config, "gemma4:26b")
            assert result["models"] == ["gemma4:26b"]
            assert result["provider"] == "ollama"
            assert result["base_url"] == "http://localhost:11434/v1"

    def test_returns_empty_dict_when_no_match(self):
        """Test that empty dict is returned when model is not in any profile."""
        config = {
            "models": {
                "local": {
                    "model": "llama3.1:8b",
                    "base_url": "http://localhost:11434",
                }
            }
        }
        result = find_profile_for_model(config, "unknown-model")
        assert result == {}

    def test_returns_empty_dict_when_no_config(self):
        """Test that empty dict is returned when config has no models."""
        config = {}
        result = find_profile_for_model(config, "gemma4:26b")
        assert result == {}

    def test_returns_first_matching_profile(self):
        """Test that the first matching profile is returned."""
        config = {
            "models": {
                "profile-a": {
                    "model": "llama3.1:8b",
                    "base_url": "http://localhost:11434",
                    "provider": "ollama",
                },
                "profile-b": {
                    "model": "llama3.1:8b",
                    "base_url": "http://other-host:11434",
                    "provider": "ollama",
                },
            }
        }
        result = find_profile_for_model(config, "llama3.1:8b")
        assert result["base_url"] == "http://localhost:11434"

    def test_resolves_provider_for_matched_profile(self):
        """Test that the returned profile has provider resolved."""
        config = {
            "models": {
                "local": {
                    "model": "llama3.1:8b",
                    "base_url": "http://localhost:11434",
                    # No explicit provider — should be inferred
                }
            }
        }
        result = find_profile_for_model(config, "llama3.1:8b")
        assert result["provider"] == "ollama"


class TestLoadResultSafetyConfig:
    def test_absent_configuration_is_disabled(self):
        assert load_result_safety_config({"models": {}}) is None

    def test_valid_single_model_profile_is_resolved(self):
        config = {
            "models": {
                "safety": {
                    "model": "openai/safety-model",
                    "base_url": "https://openrouter.ai/api/v1",
                }
            },
            "result_safety": {"profile": "safety"},
        }

        result = load_result_safety_config(config)

        assert result is not None
        assert result["profile"] == "safety"
        assert result["model"] == "openai/safety-model"
        assert result["resolved_profile"]["models"] == ["openai/safety-model"]

    def test_missing_profile_name_is_rejected(self):
        with pytest.raises(SystemExit, match="non-empty 'profile'"):
            load_result_safety_config({"models": {}, "result_safety": {}})

    def test_missing_referenced_profile_is_rejected(self):
        config = {
            "models": {"other": {"model": "model"}},
            "result_safety": {"profile": "missing"},
        }
        with pytest.raises(SystemExit, match="Result safety profile 'missing' not found"):
            load_result_safety_config(config)

    @pytest.mark.parametrize("models, count", [([], 0), (["one", "two"], 2)])
    def test_profile_requires_exactly_one_model(self, models, count):
        config = {
            "models": {"safety": {"models": models}},
            "result_safety": {"profile": "safety"},
        }
        with pytest.raises(SystemExit, match=f"exactly one model; found {count}"):
            load_result_safety_config(config)


class TestMultipleModels:
    """Tests for multiple models per profile."""

    def test_models_list_normalized(self):
        """Test that 'models' list is preserved as-is."""
        config = {
            "models": {
                "openrouter": {
                    "models": ["anthropic/claude-3.5-sonnet", "google/gemini-2.5-flash"],
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key_env": "OPENROUTER_KEY",
                }
            }
        }
        with patch.dict(os.environ, {"OPENROUTER_KEY": "sk-test"}):
            result = resolve_profile(config, "openrouter")
            assert result["models"] == ["anthropic/claude-3.5-sonnet", "google/gemini-2.5-flash"]
            assert "model" not in result

    def test_single_model_string_normalized_to_list(self):
        """Test that single 'model' string is normalized to a list."""
        config = {
            "models": {
                "test": {
                    "model": "gpt-4o",
                    "base_url": "https://api.openai.com/v1",
                }
            }
        }
        result = resolve_profile(config, "test")
        assert result["models"] == ["gpt-4o"]
        assert "model" not in result

    def test_models_string_normalized_to_list(self):
        """Test that 'models' as a string is normalized to a list."""
        config = {
            "models": {
                "test": {
                    "models": "gpt-4o",
                    "base_url": "https://api.openai.com/v1",
                }
            }
        }
        result = resolve_profile(config, "test")
        assert result["models"] == ["gpt-4o"]

    def test_find_profile_with_models_list(self):
        """Test finding a profile that uses 'models' list."""
        config = {
            "models": {
                "openrouter": {
                    "models": ["anthropic/claude-3.5-sonnet", "google/gemini-2.5-flash"],
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key_env": "OPENROUTER_KEY",
                }
            }
        }
        with patch.dict(os.environ, {"OPENROUTER_KEY": "sk-test"}):
            result = find_profile_for_model(config, "google/gemini-2.5-flash")
            assert result["models"] == ["anthropic/claude-3.5-sonnet", "google/gemini-2.5-flash"]

    def test_find_profile_returns_empty_for_missing_model_in_list(self):
        """Test that find_profile returns empty when model not in any list."""
        config = {
            "models": {
                "openrouter": {
                    "models": ["anthropic/claude-3.5-sonnet", "google/gemini-2.5-flash"],
                    "base_url": "https://openrouter.ai/api/v1",
                }
            }
        }
        result = find_profile_for_model(config, "openai/gpt-4o")
        assert result == {}

    def test_empty_models_list(self):
        """Test profile with empty models list."""
        config = {
            "models": {
                "empty": {
                    "models": [],
                    "base_url": "https://api.example.com/v1",
                }
            }
        }
        result = resolve_profile(config, "empty")
        assert result["models"] == []

    def test_model_list_normalized(self):
        """Test that 'model' as a list is normalized to 'models' list."""
        config = {
            "models": {
                "openrouter": {
                    "model": ["openai/gpt-oss-20b", "openai/gpt-oss-120b"],
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key_env": "OPENROUTER_KEY",
                }
            }
        }
        with patch.dict(os.environ, {"OPENROUTER_KEY": "sk-test"}):
            result = resolve_profile(config, "openrouter")
            assert result["models"] == ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
            assert "model" not in result

    def test_find_profile_with_model_list(self):
        """Test finding a profile that uses 'model' as a list."""
        config = {
            "models": {
                "openrouter": {
                    "model": ["openai/gpt-oss-20b", "deepseek/deepseek-v4-flash"],
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key_env": "OPENROUTER_KEY",
                }
            }
        }
        with patch.dict(os.environ, {"OPENROUTER_KEY": "sk-test"}):
            result = find_profile_for_model(config, "deepseek/deepseek-v4-flash")
            assert result["models"] == ["openai/gpt-oss-20b", "deepseek/deepseek-v4-flash"]


class TestDiscoverJudgeBenchmarks:
    """Tests for discover_judge_benchmarks function."""

    def test_detects_benchmark_with_llm_judge_fixtures(self):
        """Benchmark with llm_judge fixtures is detected."""
        result = discover_judge_benchmarks(["commit_messages"])
        assert "commit_messages" in result

    def test_does_not_detect_benchmark_without_llm_judge(self):
        """Benchmark without llm_judge fixtures is not detected."""
        result = discover_judge_benchmarks(["cherry_pick"])
        assert "cherry_pick" not in result

    def test_unknown_benchmark_not_included(self):
        """Unknown/nonexistent benchmark is not included in results."""
        result = discover_judge_benchmarks(["nonexistent_benchmark"])
        assert "nonexistent_benchmark" not in result

    def test_mixed_benchmarks_correctly_filtered(self):
        """Only benchmarks with llm_judge fixtures are returned from a mixed list."""
        result = discover_judge_benchmarks([
            "commit_messages",
            "cherry_pick",
            "nonexistent_benchmark",
        ])
        assert result == {"commit_messages"}

    def test_empty_list_returns_empty_set(self):
        """Empty benchmark list returns empty set."""
        result = discover_judge_benchmarks([])
        assert result == set()


class TestCampaignDefaults:
    """Tests for campaign configuration defaults."""

    def test_load_campaign_defaults_empty(self):
        from gitbench.config import load_campaign_defaults

        assert load_campaign_defaults({}) == {}
        assert load_campaign_defaults({"models": {}}) == {}

    def test_load_campaign_defaults_values(self):
        from gitbench.config import load_campaign_defaults

        config = {
            "campaign": {
                "default_trials": 5,
                "require_campaign_id": True,
            }
        }
        defaults = load_campaign_defaults(config)
        assert defaults["default_trials"] == 5
        assert defaults["require_campaign_id"] is True

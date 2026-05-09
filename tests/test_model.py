"""Tests for GitBench model interface."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gitbench.harness.model import (
    MockModelClient,
    ModelInterface,
    ModelResponseError,
    OllamaAdapter,
    OpenAIAdapter,
    parse_model_name,
)
from gitbench.harness.types import ModelMessage


class TestModelInterface:
    """Tests for ModelInterface ABC."""

    def test_is_abstract(self):
        """Test that ModelInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ModelInterface()


class TestMockModelClient:
    """Tests for MockModelClient."""

    def test_creation(self):
        """Test creating a MockModelClient."""
        client = MockModelClient(response="Test response")
        assert client.response == "Test response"

    def test_default_response(self):
        """Test default response value."""
        client = MockModelClient()
        assert client.response == "Mock response"

    def test_generate_returns_configured_response(self):
        """Test that generate returns the configured response."""
        client = MockModelClient(response="Expected output")
        messages = [ModelMessage(role="user", content="Hello")]
        result = client.generate(messages)
        assert result == {"text": "Expected output", "usage": None}

    def test_generate_stores_messages(self):
        """Test that generate stores the messages for inspection."""
        client = MockModelClient(response="Output")
        messages = [
            ModelMessage(role="system", content="You are helpful"),
            ModelMessage(role="user", content="Hi"),
        ]
        client.generate(messages)
        assert client.last_messages == messages

    def test_generate_tracks_call_count(self):
        """Test that generate increments call count."""
        client = MockModelClient(response="Response")
        messages = [ModelMessage(role="user", content="Test")]
        assert client.call_count == 0
        client.generate(messages)
        assert client.call_count == 1
        client.generate(messages)
        assert client.call_count == 2

    def test_set_response(self):
        """Test updating the mock response."""
        client = MockModelClient(response="Original")
        messages = [ModelMessage(role="user", content="Test")]
        assert client.generate(messages)["text"] == "Original"

        client.set_response("Updated")
        assert client.generate(messages)["text"] == "Updated"

    def test_generate_accepts_kwargs(self):
        """Test that generate accepts additional kwargs without error."""
        client = MockModelClient(response="Output")
        messages = [ModelMessage(role="user", content="Test")]
        # Should not raise, kwargs are ignored
        result = client.generate(messages, temperature=0.5, max_tokens=100)
        assert result == {"text": "Output", "usage": None}

    def test_accepts_timeout_and_retry(self):
        """Test that MockModelClient accepts timeout and retry_count params."""
        client = MockModelClient(response="Test", timeout=10, retry_count=5)
        assert client.timeout == 10
        assert client.retry_count == 5
        assert client.response == "Test"


class TestOllamaAdapter:
    """Tests for OllamaAdapter."""

    def test_creation(self):
        """Test creating an OllamaAdapter."""
        adapter = OllamaAdapter(model="llama3.1:8b")
        assert adapter.model == "llama3.1:8b"
        assert adapter.base_url == "http://localhost:11434"

    def test_custom_base_url(self):
        """Test creating with a custom base URL."""
        adapter = OllamaAdapter(model="gemma4:26b", base_url="http://192.168.1.50:11434")
        assert adapter.base_url == "http://192.168.1.50:11434"

    def test_base_url_trailing_slash_stripped(self):
        """Test that trailing slash is stripped from base URL."""
        adapter = OllamaAdapter(model="llama3.1:8b", base_url="http://localhost:11434/")
        assert adapter.base_url == "http://localhost:11434"

    def test_default_timeout_and_retry(self):
        """Test default timeout and retry values."""
        adapter = OllamaAdapter(model="llama3.1:8b")
        assert adapter.timeout == 120
        assert adapter.retry_count == 3

    def test_custom_timeout_and_retry(self):
        """Test custom timeout and retry values."""
        adapter = OllamaAdapter(model="llama3.1:8b", timeout=60, retry_count=5)
        assert adapter.timeout == 60
        assert adapter.retry_count == 5

    @patch("urllib.request.urlopen")
    def test_generate_calls_ollama_api(self, mock_urlopen):
        """Test that generate calls the Ollama /api/chat endpoint."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "model": "llama3.1:8b",
            "message": {"role": "assistant", "content": "fix: resolve null pointer"},
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        adapter = OllamaAdapter(model="llama3.1:8b", timeout=30)
        messages = [ModelMessage(role="user", content="Generate a commit message")]
        result = adapter.generate(messages)

        assert result == {"text": "fix: resolve null pointer", "usage": None}
        mock_urlopen.assert_called_once()

        # Verify the request was made to the correct URL
        request = mock_urlopen.call_args[0][0]
        assert request.full_url == "http://localhost:11434/api/chat"

    @patch("urllib.request.urlopen")
    def test_generate_sends_correct_payload(self, mock_urlopen):
        """Test that generate sends the correct JSON payload."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"content": "output"},
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        adapter = OllamaAdapter(model="gemma4:26b")
        messages = [
            ModelMessage(role="system", content="You are helpful"),
            ModelMessage(role="user", content="Test"),
        ]
        adapter.generate(messages)

        request = mock_urlopen.call_args[0][0]
        body = json.loads(request.data.decode("utf-8"))
        assert body["model"] == "gemma4:26b"
        assert body["stream"] is False
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "system"

    @patch("urllib.request.urlopen")
    def test_empty_response_handling(self, mock_urlopen):
        """Test handling of empty response content."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"content": ""},
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        adapter = OllamaAdapter(model="llama3.1:8b")
        messages = [ModelMessage(role="user", content="Test")]
        result = adapter.generate(messages)
        assert result["text"] == ""
        assert result["usage"] is None

    @patch("urllib.request.urlopen")
    def test_timeout_raises_timeout_error(self, mock_urlopen):
        """Test that a slow response triggers TimeoutError."""
        import time

        def slow_response(*args, **kwargs):
            time.sleep(5)
            return MagicMock()

        mock_urlopen.side_effect = slow_response

        adapter = OllamaAdapter(model="llama3.1:8b", timeout=1, retry_count=1)
        messages = [ModelMessage(role="user", content="Test")]

        with pytest.raises(TimeoutError, match="timed out"):
            adapter.generate(messages)


class TestOpenAIAdapter:
    """Tests for OpenAIAdapter."""

    @pytest.fixture(autouse=True)
    def _require_openai(self):
        """Skip OpenAI tests when the package is not installed."""
        pytest.importorskip("openai", reason="openai not installed")

    def test_creation(self):
        """Test creating an OpenAIAdapter."""
        adapter = OpenAIAdapter(model="gpt-4o-mini")
        assert adapter.model == "gpt-4o-mini"

    def test_creation_with_custom_api_key(self):
        """Test creating with custom API key."""
        adapter = OpenAIAdapter(model="gpt-4", api_key="sk-test-key")
        assert adapter._api_key == "sk-test-key"

    def test_default_model(self):
        """Test that default model is set correctly."""
        adapter = OpenAIAdapter()
        assert adapter.model == "gpt-4o-mini"

    def test_timeout_and_retry_params(self):
        """Test that timeout and retry_count parameters are accepted."""
        adapter = OpenAIAdapter(timeout=5, retry_count=2)
        assert adapter.timeout == 5
        assert adapter.retry_count == 2

    def test_default_timeout_and_retry(self):
        """Test default timeout and retry values."""
        adapter = OpenAIAdapter()
        assert adapter.timeout == 30
        assert adapter.retry_count == 3

    @patch("openai.OpenAI")
    def test_generate_calls_openai_api(self, mock_openai_class):
        """Test that generate calls the OpenAI API correctly."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.error = None
        mock_response.choices[0].message.content = "Generated output"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        adapter = OpenAIAdapter(api_key="test-key")
        adapter._client = mock_client

        messages = [
            ModelMessage(role="system", content="You are helpful"),
            ModelMessage(role="user", content="Generate a commit message"),
        ]
        result = adapter.generate(messages)

        assert result["text"] == "Generated output"
        assert "usage" in result
        mock_client.chat.completions.create.assert_called_once()

        # Verify the call format
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4o-mini"
        assert len(call_kwargs.kwargs["messages"]) == 2

    @patch("openai.OpenAI")
    def test_generate_passes_extra_kwargs(self, mock_openai_class):
        """Test that generate passes extra kwargs to the API."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.error = None
        mock_response.choices[0].message.content = "Output"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        adapter = OpenAIAdapter(api_key="test-key")
        adapter._client = mock_client

        messages = [ModelMessage(role="user", content="Test")]
        adapter.generate(messages, temperature=0.7, max_tokens=50)

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["temperature"] == 0.7
        assert call_kwargs.kwargs["max_tokens"] == 50

    def test_client_lazy_loads_openai(self):
        """Test that the client property lazy-loads the OpenAI module."""
        adapter = OpenAIAdapter(api_key="test-key")

        # Client should be None until accessed
        assert adapter._client is None

        # Access the client property - should create the client
        client = adapter.client
        assert client is not None
        assert adapter._client is client  # Subsequent access returns same instance

    @patch("openai.OpenAI")
    def test_client_uses_adapter_timeout_and_disables_sdk_retries(self, mock_openai_class):
        """Test SDK timeout/retry policy is configured by the adapter."""
        adapter = OpenAIAdapter(api_key="test-key", timeout=45)

        _ = adapter.client

        mock_openai_class.assert_called_once_with(
            api_key="test-key",
            timeout=45,
            max_retries=0,
        )

    @patch("openai.OpenAI")
    def test_client_keeps_base_url_with_timeout_options(self, mock_openai_class):
        """Test custom base URL is preserved with SDK timeout configuration."""
        adapter = OpenAIAdapter(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
            timeout=120,
        )

        _ = adapter.client

        mock_openai_class.assert_called_once_with(
            api_key="test-key",
            timeout=120,
            max_retries=0,
            base_url="https://openrouter.ai/api/v1",
        )

    @patch("openai.OpenAI")
    def test_empty_response_handling(self, mock_openai_class):
        """Test handling of empty response content."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.error = None
        mock_response.choices[0].message.content = ""
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        adapter = OpenAIAdapter(api_key="test-key")
        adapter._client = mock_client

        messages = [ModelMessage(role="user", content="Test")]
        result = adapter.generate(messages)
        assert result["text"] == ""

    @patch("openai.OpenAI")
    def test_missing_choices_raises_clear_response_error(self, mock_openai_class):
        """Test malformed provider responses fail with a useful error."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = SimpleNamespace(
            choices=None
        )
        mock_openai_class.return_value = mock_client

        adapter = OpenAIAdapter(api_key="test-key", retry_count=1)
        adapter._client = mock_client

        messages = [ModelMessage(role="user", content="Test")]
        with pytest.raises(ModelResponseError, match="missing choices"):
            adapter.generate(messages)

    @patch("openai.OpenAI")
    def test_missing_choices_is_retryable(self, mock_openai_class):
        """Test transient malformed provider responses are retried."""
        mock_client = MagicMock()
        malformed_response = SimpleNamespace(choices=None)
        good_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="Recovered output")
                )
            ]
        )
        mock_client.chat.completions.create.side_effect = [
            malformed_response,
            good_response,
        ]
        mock_openai_class.return_value = mock_client

        adapter = OpenAIAdapter(api_key="test-key", retry_count=2)
        adapter._client = mock_client

        messages = [ModelMessage(role="user", content="Test")]
        result = adapter.generate(messages)

        assert result["text"] == "Recovered output"
        assert mock_client.chat.completions.create.call_count == 2

    @patch("openai.OpenAI")
    def test_provider_error_response_is_preserved(self, mock_openai_class):
        """Test provider error payloads are surfaced in adapter errors."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = SimpleNamespace(
            choices=None,
            error={"message": "upstream provider overloaded"},
        )
        mock_openai_class.return_value = mock_client

        adapter = OpenAIAdapter(api_key="test-key", retry_count=1)
        adapter._client = mock_client

        messages = [ModelMessage(role="user", content="Test")]
        with pytest.raises(ModelResponseError, match="upstream provider overloaded"):
            adapter.generate(messages)


class TestParseModelName:
    """Tests for parse_model_name utility."""

    def test_bare_name(self):
        """Bare model name returns itself with no reasoning level."""
        base, level = parse_model_name("gpt-4o")
        assert base == "gpt-4o"
        assert level is None

    def test_with_reasoning_level(self):
        """Model name with #level parses base and level."""
        base, level = parse_model_name("o3-mini#high")
        assert base == "o3-mini"
        assert level == "high"

    def test_multiple_hash_chars_uses_last(self):
        """Multiple # chars — only last delimits reasoning level."""
        base, level = parse_model_name("model#extra#low")
        assert base == "model#extra"
        assert level == "low"

    def test_empty_level(self):
        """Trailing # with no text yields empty string level."""
        base, level = parse_model_name("model#")
        assert base == "model"
        assert level == ""

    def test_no_hash(self):
        """No hash — returns name and None."""
        base, level = parse_model_name("llama3.1:8b")
        assert base == "llama3.1:8b"
        assert level is None


class TestOpenAIAdapterReasoning:
    """Tests for OpenAIAdapter reasoning level handling."""

    def test_parses_model_with_reasoning_level(self):
        """Model o3-mini#high stores base model and reasoning level."""
        adapter = OpenAIAdapter(model="o3-mini#high", api_key="test-key")
        assert adapter.model == "o3-mini"
        assert adapter.reasoning_level == "high"
        assert adapter._full_model == "o3-mini#high"

    def test_no_reasoning_level_is_none(self):
        """Model without # suffix has reasoning_level None."""
        adapter = OpenAIAdapter(model="gpt-4o", api_key="test-key")
        assert adapter.model == "gpt-4o"
        assert adapter.reasoning_level is None
        assert adapter._full_model == "gpt-4o"

    @patch("openai.OpenAI")
    def test_generate_forwards_reasoning_as_effort(self, mock_openai_class):
        """reasoning_level is forwarded as reasoning_effort."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.error = None
        mock_response.choices[0].message.content = "Output"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        adapter = OpenAIAdapter(model="o3-mini#high", api_key="test-key")
        adapter._client = mock_client

        messages = [ModelMessage(role="user", content="Hi")]
        adapter.generate(messages)

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["reasoning_effort"] == "high"
        assert call_kwargs.kwargs["model"] == "o3-mini"

    @patch("openai.OpenAI")
    def test_generate_without_reasoning_omits_effort(self, mock_openai_class):
        """No reasoning_level means no reasoning_effort is sent."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.error = None
        mock_response.choices[0].message.content = "Output"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        adapter = OpenAIAdapter(model="gpt-4o", api_key="test-key")
        adapter._client = mock_client

        messages = [ModelMessage(role="user", content="Hi")]
        adapter.generate(messages)

        call_kwargs = mock_client.chat.completions.create.call_args
        assert "reasoning_effort" not in call_kwargs.kwargs


class TestOllamaAdapterReasoning:
    """Tests for OllamaAdapter reasoning level handling."""

    def test_parses_model_with_reasoning_level(self):
        """Model with #level stores base model and reasoning level."""
        adapter = OllamaAdapter(model="llama3.1#medium")
        assert adapter.model == "llama3.1"
        assert adapter.reasoning_level == "medium"
        assert adapter._full_model == "llama3.1#medium"

    def test_no_reasoning_level_is_none(self):
        """Model without # suffix has reasoning_level None."""
        adapter = OllamaAdapter(model="llama3.1:8b")
        assert adapter.model == "llama3.1:8b"
        assert adapter.reasoning_level is None
        assert adapter._full_model == "llama3.1:8b"

    @patch("urllib.request.urlopen")
    def test_generate_logs_debug_when_reasoning_present(self, mock_urlopen):
        """Reasoning level triggers a debug log and the request uses base model."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"content": "output"},
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        adapter = OllamaAdapter(model="llama3.1#medium")
        messages = [ModelMessage(role="user", content="Test")]

        with patch("logging.Logger.debug") as mock_debug:
            result = adapter.generate(messages)

        assert result["text"] == "output"
        request = mock_urlopen.call_args[0][0]
        body = json.loads(request.data.decode("utf-8"))
        assert body["model"] == "llama3.1"
        assert "reasoning_level" not in body
        mock_debug.assert_called_once()
        assert "ignoring" in mock_debug.call_args[0][0].lower()


class TestMockModelClientReasoning:
    """Tests for MockModelClient reasoning level attribute."""

    def test_has_reasoning_level_attribute(self):
        """MockModelClient exposes reasoning_level for runner access."""
        client = MockModelClient()
        assert hasattr(client, "reasoning_level")
        assert client.reasoning_level is None

    def test_generate_works_with_reasoning_level(self):
        """generate() works fine even with reasoning_level set."""
        client = MockModelClient(response="Test")
        client.reasoning_level = "high"
        result = client.generate([ModelMessage(role="user", content="Hi")])
        assert result == {"text": "Test", "usage": None}
        assert client.call_count == 1

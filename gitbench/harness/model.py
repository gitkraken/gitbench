"""Model interface for GitBench."""

import json
import logging
import threading
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

from .types import ModelMessage

logger = logging.getLogger(__name__)


def parse_model_name(model: str) -> tuple[str, str | None]:
    """Split a model name into base name and optional reasoning level.

    Syntax: ``base_model`` or ``base_model#level``.
    If multiple ``#`` are present, only the last one delimits the level.

    Args:
        model: Full model name, optionally with ``#level`` suffix.

    Returns:
        A tuple of ``(base_model, reasoning_level)`` where
        ``reasoning_level`` is ``None`` when no ``#`` is present.
    """
    if "#" in model:
        idx = model.rfind("#")
        return model[:idx], model[idx + 1:]
    return model, None


class ModelResponseError(RuntimeError):
    """Raised when a provider response cannot be parsed as model text."""


def _format_provider_error(error_obj: Any) -> str:
    """Extract a useful message from provider-specific error payloads."""
    if isinstance(error_obj, dict):
        message = error_obj.get("message") or error_obj.get("error")
        if message:
            return str(message)
    message = getattr(error_obj, "message", None)
    if message:
        return str(message)
    return str(error_obj)


def _extract_openai_content(response: Any) -> str:
    """Extract assistant content from an OpenAI-compatible chat response."""
    provider_error = getattr(response, "error", None)
    if provider_error:
        raise ModelResponseError(
            f"OpenAI-compatible response contained provider error: "
            f"{_format_provider_error(provider_error)}"
        )

    choices = getattr(response, "choices", None)
    if not choices:
        raise ModelResponseError(
            "OpenAI-compatible response missing choices; no model output was returned"
        )

    first_choice = choices[0]
    message = getattr(first_choice, "message", None)
    if message is None:
        raise ModelResponseError(
            "OpenAI-compatible response choice missing message; no model output was returned"
        )

    return getattr(message, "content", None) or ""


class ModelInterface(ABC):
    """Abstract base class for model adapters."""

    @abstractmethod
    def generate(self, messages: list[ModelMessage], **kwargs: Any) -> dict:
        """Generate a response from the model.

        Args:
            messages: List of ModelMessage objects representing the conversation.
            **kwargs: Additional model-specific parameters.

        Returns:
            A dict with keys ``text`` (str) and ``usage`` (dict with
            ``input_tokens``, ``output_tokens``, ``total_tokens``
            keys, or ``None`` if unavailable).

        Raises:
            Exception: If the model call fails.
        """
        ...


class OpenAIAdapter(ModelInterface):
    """Adapter for OpenAI API compatible models."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None, timeout: int = 30, retry_count: int = 3, base_url: str | None = None):
        """Initialize the OpenAI adapter.

        Args:
            model: The model identifier (default: gpt-4o-mini). May include
                   ``#level`` suffix for reasoning effort (e.g. ``o3-mini#high``).
            api_key: Optional API key. If not provided, reads from OPENAI_API_KEY env var.
            timeout: Timeout in seconds for model generation (default: 30).
            retry_count: Number of retries on failure (default: 3).
            base_url: Optional API base URL for OpenAI-compatible providers (e.g. OpenRouter).
        """
        self._full_model = model
        base_model, parsed_level = parse_model_name(model)
        self.model = base_model
        self.reasoning_level = parsed_level
        self.timeout = timeout
        self.retry_count = retry_count
        self._api_key = api_key
        self._base_url = base_url
        self._client = None

    @property
    def client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            try:
                import openai
            except ImportError:
                raise ImportError(
                    "openai package not installed. Install with: pip install openai"
                )
            api_key = self._api_key or openai.api_key
            if not api_key:
                raise ValueError(
                    "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                    "or pass api_key parameter."
                )
            client_kwargs: dict[str, Any] = {
                "api_key": api_key,
                "timeout": self.timeout,
                "max_retries": 0,
            }
            if self._base_url:
                client_kwargs["base_url"] = self._base_url
            self._client = openai.OpenAI(**client_kwargs)
        return self._client

    def generate(self, messages: list[ModelMessage], **kwargs: Any) -> dict:
        """Generate a response using the OpenAI API with timeout and retry.

        Args:
            messages: List of ModelMessage objects.
            **kwargs: Additional parameters (temperature, max_tokens, etc.).

        Returns:
            A dict with ``text`` and ``usage`` keys.

        Raises:
            TimeoutError: If the API call exceeds the configured timeout.
            openai.APIError: If all retries are exhausted.
        """
        import openai

        model_messages = [msg.to_dict() for msg in messages]
        last_error: Exception | None = None

        if self.reasoning_level:
            kwargs["reasoning_effort"] = self.reasoning_level

        for attempt in range(1, self.retry_count + 1):
            try:
                result: list[dict] = []
                error: list[Exception] = []

                def call_api():
                    try:
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=model_messages,
                            **kwargs,
                        )
                        text = _extract_openai_content(response)
                        usage = None
                        try:
                            raw_usage = getattr(response, "usage", None)
                            if raw_usage is not None:
                                usage = {
                                    "input_tokens": getattr(raw_usage, "prompt_tokens", None),
                                    "output_tokens": getattr(raw_usage, "completion_tokens", None),
                                    "total_tokens": getattr(raw_usage, "total_tokens", None),
                                }
                        except Exception:
                            pass
                        result.append({"text": text, "usage": usage})
                    except Exception as e:
                        error.append(e)

                timer = threading.Timer(self.timeout, lambda: None)
                api_thread = threading.Thread(target=call_api, daemon=True)
                api_thread.start()
                timer.start()
                api_thread.join(timeout=self.timeout)
                timer.cancel()

                if api_thread.is_alive():
                    logger.error(
                        "Model call timed out after %ds (attempt %d/%d)",
                        self.timeout,
                        attempt,
                        self.retry_count,
                    )
                    raise TimeoutError(
                        f"Model call timed out after {self.timeout}s"
                    )

                if error:
                    raise error[0]

                if attempt > 1:
                    logger.info(
                        "Model call succeeded on attempt %d/%d",
                        attempt,
                        self.retry_count,
                    )
                return result[0]

            except (
                TimeoutError,
                openai.RateLimitError,
                openai.APITimeoutError,
                openai.APIConnectionError,
                openai.InternalServerError,
                ModelResponseError,
            ) as e:
                last_error = e
                if attempt < self.retry_count:
                    delay = min(2 ** (attempt - 1), 16)
                    logger.info(
                        "Retryable error on attempt %d/%d: %s — retrying in %ds",
                        attempt,
                        self.retry_count,
                        type(e).__name__,
                        delay,
                    )
                    threading.Event().wait(delay)
                else:
                    logger.error(
                        "All %d retries exhausted. Last error: %s",
                        self.retry_count,
                        e,
                    )
                    raise
            except Exception:
                raise

        raise last_error  # type: ignore[misc]


class OllamaAdapter(ModelInterface):
    """Adapter for local Ollama models using the Ollama REST API.

    Uses only stdlib (urllib) — no external dependencies required.
    Talks to Ollama's native /api/chat endpoint.
    """

    def __init__(self, model: str, base_url: str = "http://localhost:11434", timeout: int = 120, retry_count: int = 3):
        """Initialize the Ollama adapter.

        Args:
            model: Ollama model name (e.g. 'llama3.1:8b', 'gemma4:26b').
                   May include ``#level`` suffix (logged but ignored).
            base_url: Ollama server base URL (default: http://localhost:11434).
            timeout: Timeout in seconds for model generation (default: 120).
            retry_count: Number of retries on failure (default: 3).
        """
        self._full_model = model
        base_model, parsed_level = parse_model_name(model)
        self.model = base_model
        self.reasoning_level = parsed_level
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_count = retry_count

    def generate(self, messages: list[ModelMessage], **kwargs: Any) -> dict:
        """Generate a response using the Ollama API with timeout and retry.

        Args:
            messages: List of ModelMessage objects.
            **kwargs: Additional parameters (ignored — Ollama options go in the request body).

        Returns:
            A dict with ``text`` and ``usage`` keys.

        Raises:
            TimeoutError: If the API call exceeds the configured timeout.
            ConnectionError: If the Ollama server is unreachable.
            RuntimeError: If the API returns an error.
        """
        if self.reasoning_level:
            logger.debug(
                "Reasoning level '%s' is not supported by Ollama — ignoring",
                self.reasoning_level,
            )

        ollama_messages = [msg.to_dict() for msg in messages]
        request_body = json.dumps({
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
        }).encode("utf-8")

        url = f"{self.base_url}/api/chat"
        last_error: Exception | None = None

        for attempt in range(1, self.retry_count + 1):
            try:
                result: list[dict] = []
                error: list[Exception] = []

                def call_api():
                    try:
                        req = urllib.request.Request(
                            url,
                            data=request_body,
                            headers={"Content-Type": "application/json"},
                            method="POST",
                        )
                        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                            body = json.loads(resp.read().decode("utf-8"))
                            content = body.get("message", {}).get("content", "")
                            usage = None
                            try:
                                prompt_eval = body.get("prompt_eval_count")
                                eval_count = body.get("eval_count")
                                if eval_count is not None:
                                    output = eval_count
                                    input_t = prompt_eval
                                    total = (
                                        (prompt_eval + eval_count)
                                        if prompt_eval is not None
                                        else None
                                    )
                                else:
                                    output = None
                                    input_t = prompt_eval
                                    total = (
                                        prompt_eval
                                        if prompt_eval is not None
                                        else None
                                    )
                                if input_t is not None or output is not None:
                                    usage = {
                                        "input_tokens": input_t,
                                        "output_tokens": output,
                                        "total_tokens": total,
                                    }
                            except Exception:
                                pass
                            result.append({"text": content, "usage": usage})
                    except Exception as e:
                        error.append(e)

                api_thread = threading.Thread(target=call_api, daemon=True)
                api_thread.start()
                api_thread.join(timeout=self.timeout)

                if api_thread.is_alive():
                    logger.error(
                        "Ollama call timed out after %ds (attempt %d/%d)",
                        self.timeout,
                        attempt,
                        self.retry_count,
                    )
                    raise TimeoutError(
                        f"Ollama call timed out after {self.timeout}s"
                    )

                if error:
                    raise error[0]

                if attempt > 1:
                    logger.info(
                        "Ollama call succeeded on attempt %d/%d",
                        attempt,
                        self.retry_count,
                    )
                return result[0]

            except (TimeoutError, urllib.error.URLError, ConnectionError, OSError) as e:
                last_error = e
                if attempt < self.retry_count:
                    delay = min(2 ** (attempt - 1), 16)
                    logger.info(
                        "Retryable error on attempt %d/%d: %s — retrying in %ds",
                        attempt,
                        self.retry_count,
                        type(e).__name__,
                        delay,
                    )
                    threading.Event().wait(delay)
                else:
                    logger.error(
                        "All %d retries exhausted. Last error: %s",
                        self.retry_count,
                        e,
                    )
                    raise
            except Exception:
                raise

        raise last_error  # type: ignore[misc]


class MockModelClient(ModelInterface):
    """Mock model client for testing."""

    reasoning_level: str | None = None

    def __init__(self, response: str = "Mock response", timeout: int = 30, retry_count: int = 3):
        """Initialize with a fixed response.

        Args:
            response: The fixed string to return on every call.
            timeout: Timeout parameter (accepted but ignored for mock).
            retry_count: Retry count parameter (accepted but ignored for mock).
        """
        self.response = response
        self.timeout = timeout
        self.retry_count = retry_count
        self.call_count = 0
        self.last_messages = None

    def generate(self, messages: list[ModelMessage], **kwargs: Any) -> dict:
        """Return the configured mock response.

        Args:
            messages: List of ModelMessage objects (stored for inspection).
            **kwargs: Additional parameters (ignored).

        Returns:
            A dict with ``text`` and ``usage`` keys (``usage`` is always ``None``).
        """
        self.call_count += 1
        self.last_messages = messages
        return {"text": self.response, "usage": None}

    def set_response(self, response: str) -> None:
        """Update the mock response.

        Args:
            response: New response string to return.
        """
        self.response = response

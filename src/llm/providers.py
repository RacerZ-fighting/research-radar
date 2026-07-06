"""Concrete HTTP adapters for supported LLM providers."""

from __future__ import annotations

import json
import os
from typing import Any

import requests

from src.llm.base import LLMProvider, LLMProviderError, LLMResponse, LLMUsage, ModelTier, safe_int


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1/responses"
DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_OPENAI_MODELS = {
    ModelTier.FAST: "gpt-4o-mini",
    ModelTier.STANDARD: "gpt-5.2",
    ModelTier.PREMIUM: "gpt-5.4",
}
DEFAULT_ANTHROPIC_MODELS = {
    ModelTier.FAST: "claude-haiku-4-5-20251001",
    ModelTier.STANDARD: "claude-sonnet-4-6",
    ModelTier.PREMIUM: "claude-opus-4-6",
}
DEFAULT_GEMINI_MODELS = {
    ModelTier.FAST: "gemini-2.5-flash",
    ModelTier.STANDARD: "gemini-2.5-pro",
    ModelTier.PREMIUM: "gemini-3-pro-preview",
}


class OpenAIProvider(LLMProvider):
    """HTTP adapter for the OpenAI Responses API."""

    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        session: requests.Session | Any | None = None,
    ) -> None:
        """Initialize the provider with optional overrides for tests."""

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)
        self.session = session or requests.Session()
        self.input_as_list = _env_bool("OPENAI_INPUT_AS_LIST", default=False)
        self.stream = _env_bool("OPENAI_STREAM", default=False)
        self.store = _env_bool_or_none("OPENAI_STORE")
        self.omit_generation_params = _env_bool("OPENAI_OMIT_GENERATION_PARAMS", default=False)

    def default_model_map(self) -> dict[ModelTier, str]:
        """Return default OpenAI models for each tier."""

        return _resolve_model_map("OPENAI", DEFAULT_OPENAI_MODELS)

    def generate(
        self,
        *,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> LLMResponse:
        """Send one request to OpenAI and normalize the response payload."""

        self._require_api_key()
        payload = {
            "model": model,
            "input": [{"role": "user", "content": prompt}] if self.input_as_list else prompt,
        }
        if not self.omit_generation_params:
            payload["max_output_tokens"] = max_tokens
            payload["temperature"] = temperature
        if self.store is not None:
            payload["store"] = self.store
        if self.stream:
            payload["stream"] = True
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = self._post_json(headers=headers, payload=payload, timeout=timeout, model=model)
        text = str(data.get("output_text") or self._extract_openai_text(data))
        usage = self._parse_usage(data.get("usage"))
        return LLMResponse(text=text, model=str(data.get("model", model)), usage=usage)

    def _require_api_key(self) -> None:
        """Raise a provider error if the API key is missing."""

        if not self.api_key:
            raise LLMProviderError("Missing OPENAI_API_KEY", retryable=False)

    def _post_json(
        self,
        *,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
        model: str,
    ) -> dict[str, Any]:
        """POST JSON to OpenAI and return a parsed JSON object."""

        try:
            if self.stream:
                response = self.session.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                    stream=True,
                )
            else:
                response = self.session.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
        except requests.Timeout as exc:
            raise LLMProviderError("OpenAI request timed out", retryable=True) from exc
        except requests.RequestException as exc:
            raise LLMProviderError(f"OpenAI request failed: {exc}", retryable=True) from exc

        if self.stream and response.status_code == 200:
            return self._parse_stream_response(response, model=model)
        return _handle_response(response, provider_name=self.provider_name)

    def _parse_stream_response(self, response: requests.Response | Any, *, model: str) -> dict[str, Any]:
        """Parse a Responses API Server-Sent Events stream into a response-like payload."""

        deltas: list[str] = []
        done_text: str | None = None
        completed_payload: dict[str, Any] | None = None

        for raw_line in response.iter_lines(decode_unicode=False):
            if isinstance(raw_line, bytes):
                line = raw_line.decode("utf-8", errors="replace").strip()
            else:
                line = str(raw_line or "").strip()
            if not line.startswith("data:"):
                continue
            raw_data = line.removeprefix("data:").strip()
            if not raw_data or raw_data == "[DONE]":
                continue
            try:
                event = json.loads(raw_data)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type")
            if event_type == "response.output_text.delta":
                delta = event.get("delta")
                if delta:
                    deltas.append(str(delta))
            elif event_type == "response.output_text.done":
                text = event.get("text")
                if text:
                    done_text = str(text)
            elif event_type == "response.completed":
                response_payload = event.get("response")
                if isinstance(response_payload, dict):
                    completed_payload = response_payload

        output_text = "".join(deltas) or done_text or ""
        if not output_text:
            raise LLMProviderError("OpenAI stream response missing output text", retryable=False)

        return {
            "model": str((completed_payload or {}).get("model") or model),
            "output_text": output_text,
            "usage": (completed_payload or {}).get("usage"),
        }

    def _extract_openai_text(self, payload: dict[str, Any]) -> str:
        """Fallback parser for Responses API output blocks."""

        output = payload.get("output", [])
        if not isinstance(output, list):
            raise LLMProviderError("OpenAI response missing output text", retryable=False)

        texts: list[str] = []
        for item in output:
            for block in item.get("content", []):
                if block.get("type") == "output_text" and block.get("text"):
                    texts.append(str(block["text"]))
        if not texts:
            raise LLMProviderError("OpenAI response missing output text", retryable=False)
        return "".join(texts)

    def _parse_usage(self, usage_payload: Any) -> LLMUsage:
        """Normalize token usage fields from the OpenAI response."""

        if not isinstance(usage_payload, dict):
            return LLMUsage()
        input_tokens = safe_int(usage_payload.get("input_tokens"))
        output_tokens = safe_int(usage_payload.get("output_tokens"))
        total_tokens = safe_int(usage_payload.get("total_tokens"))
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        return LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )


class AnthropicProvider(LLMProvider):
    """HTTP adapter for the Anthropic Messages API."""

    provider_name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        session: requests.Session | Any | None = None,
    ) -> None:
        """Initialize the provider with optional overrides for tests."""

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url or os.getenv("ANTHROPIC_BASE_URL", DEFAULT_ANTHROPIC_BASE_URL)
        self.session = session or requests.Session()

    def default_model_map(self) -> dict[ModelTier, str]:
        """Return default Anthropic models for each tier."""

        return _resolve_model_map("ANTHROPIC", DEFAULT_ANTHROPIC_MODELS)

    def generate(
        self,
        *,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> LLMResponse:
        """Send one request to Anthropic and normalize the response payload."""

        self._require_api_key()
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        data = self._post_json(headers=headers, payload=payload, timeout=timeout)
        text = self._extract_anthropic_text(data)
        usage = self._parse_usage(data.get("usage"))
        return LLMResponse(text=text, model=str(data.get("model", model)), usage=usage)

    def _require_api_key(self) -> None:
        """Raise a provider error if the API key is missing."""

        if not self.api_key:
            raise LLMProviderError("Missing ANTHROPIC_API_KEY", retryable=False)

    def _post_json(self, *, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        """POST JSON to Anthropic and return a parsed JSON object."""

        try:
            response = self.session.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.Timeout as exc:
            raise LLMProviderError("Anthropic request timed out", retryable=True) from exc
        except requests.RequestException as exc:
            raise LLMProviderError(f"Anthropic request failed: {exc}", retryable=True) from exc

        return _handle_response(response, provider_name=self.provider_name)

    def _extract_anthropic_text(self, payload: dict[str, Any]) -> str:
        """Extract concatenated text blocks from an Anthropic response."""

        content = payload.get("content", [])
        if not isinstance(content, list):
            raise LLMProviderError("Anthropic response missing content blocks", retryable=False)

        texts = [str(block.get("text", "")) for block in content if block.get("type") == "text"]
        text = "".join(texts).strip()
        if not text:
            raise LLMProviderError("Anthropic response missing text content", retryable=False)
        return text

    def _parse_usage(self, usage_payload: Any) -> LLMUsage:
        """Normalize token usage fields from the Anthropic response."""

        if not isinstance(usage_payload, dict):
            return LLMUsage()
        input_tokens = safe_int(usage_payload.get("input_tokens"))
        output_tokens = safe_int(usage_payload.get("output_tokens"))
        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        return LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )


class GeminiProvider(LLMProvider):
    """HTTP adapter for the Gemini generateContent API."""

    provider_name = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        session: requests.Session | Any | None = None,
    ) -> None:
        """Initialize the provider with optional overrides for tests."""

        self.api_key = api_key or _resolve_api_key(
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "SSS_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
        )
        self.base_url = base_url or os.getenv("GEMINI_BASE_URL", DEFAULT_GEMINI_BASE_URL)
        self.session = session or requests.Session()

    def default_model_map(self) -> dict[ModelTier, str]:
        """Return default Gemini models for each tier."""

        return _resolve_model_map("GEMINI", DEFAULT_GEMINI_MODELS)

    def generate(
        self,
        *,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> LLMResponse:
        """Send one request to Gemini and normalize the response payload."""

        self._require_api_key()
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        headers = {
            "x-goog-api-key": self.api_key,
            "content-type": "application/json",
        }
        url = f"{self.base_url.rstrip('/')}/{model}:generateContent"
        data = self._post_json(url=url, headers=headers, payload=payload, timeout=timeout)
        text = self._extract_gemini_text(data)
        usage = self._parse_usage(data.get("usageMetadata"))
        return LLMResponse(text=text, model=model, usage=usage)

    def _require_api_key(self) -> None:
        """Raise a provider error if the API key is missing."""

        if not self.api_key:
            raise LLMProviderError("Missing GEMINI_API_KEY", retryable=False)

    def _post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        """POST JSON to Gemini and return a parsed JSON object."""

        try:
            response = self.session.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.Timeout as exc:
            raise LLMProviderError("Gemini request timed out", retryable=True) from exc
        except requests.RequestException as exc:
            raise LLMProviderError(f"Gemini request failed: {exc}", retryable=True) from exc

        return _handle_response(response, provider_name=self.provider_name)

    def _extract_gemini_text(self, payload: dict[str, Any]) -> str:
        """Extract concatenated text parts from the first Gemini candidate."""

        candidates = payload.get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            raise LLMProviderError("Gemini response missing candidates", retryable=False)

        content = candidates[0].get("content", {})
        if not isinstance(content, dict):
            raise LLMProviderError("Gemini response missing candidate content", retryable=False)

        parts = content.get("parts", [])
        if not isinstance(parts, list):
            raise LLMProviderError("Gemini response missing content parts", retryable=False)

        texts = [str(part.get("text", "")) for part in parts if isinstance(part, dict) and part.get("text")]
        text = "".join(texts).strip()
        if not text:
            raise LLMProviderError("Gemini response missing text content", retryable=False)
        return text

    def _parse_usage(self, usage_payload: Any) -> LLMUsage:
        """Normalize token usage fields from the Gemini response."""

        if not isinstance(usage_payload, dict):
            return LLMUsage()
        input_tokens = safe_int(usage_payload.get("promptTokenCount"))
        output_tokens = safe_int(usage_payload.get("candidatesTokenCount"))
        total_tokens = safe_int(usage_payload.get("totalTokenCount"))
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        return LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )


def _handle_response(response: Any, *, provider_name: str) -> dict[str, Any]:
    """Normalize one provider HTTP response or raise a retry-aware error."""

    status_code = int(getattr(response, "status_code", 0))
    text = getattr(response, "text", "")

    try:
        payload = response.json()
    except ValueError as exc:
        raise LLMProviderError(
            f"{provider_name} returned invalid JSON response: {text}",
            retryable=status_code >= 500,
        ) from exc

    if status_code in {429, 529}:
        raise LLMProviderError(f"{provider_name} rate limited the request", retryable=True)
    if status_code >= 500:
        raise LLMProviderError(
            f"{provider_name} server error ({status_code}): {_extract_error_message(payload, text)}",
            retryable=True,
        )
    if status_code >= 400:
        raise LLMProviderError(
            f"{provider_name} request failed ({status_code}): {_extract_error_message(payload, text)}",
            retryable=False,
        )
    if not isinstance(payload, dict):
        raise LLMProviderError(f"{provider_name} response must be a JSON object", retryable=False)
    return payload


def _extract_error_message(payload: Any, fallback: str) -> str:
    """Return a concise provider error message when available."""

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if isinstance(error, str):
            return error
        if payload.get("message"):
            return str(payload["message"])
    return fallback


def _resolve_model_map(prefix: str, defaults: dict[ModelTier, str]) -> dict[ModelTier, str]:
    """Resolve one provider's model map from env vars with fallback defaults."""

    return {
        ModelTier.FAST: os.getenv(f"{prefix}_MODEL_FAST", defaults[ModelTier.FAST]),
        ModelTier.STANDARD: os.getenv(f"{prefix}_MODEL_STANDARD", defaults[ModelTier.STANDARD]),
        ModelTier.PREMIUM: os.getenv(f"{prefix}_MODEL_PREMIUM", defaults[ModelTier.PREMIUM]),
    }


def _resolve_api_key(*env_vars: str) -> str | None:
    """Return the first non-empty API key from one list of env vars."""

    for env_var in env_vars:
        value = os.getenv(env_var)
        if value:
            return value
    return None


def _env_bool(name: str, *, default: bool) -> bool:
    """Parse a boolean environment variable."""

    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_bool_or_none(name: str) -> bool | None:
    """Parse an optional boolean environment variable."""

    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return None
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}

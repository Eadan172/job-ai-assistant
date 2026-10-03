"""Structured completions on top of the existing provider endpoints.

The old adapter stays in place for the popup routes. This gateway validates
the whole response with Pydantic. It does not search free text for a JSON object.
"""

from __future__ import annotations

from typing import Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_ENDPOINTS = {
    "deepseek": ("https://api.deepseek.com/v1/chat/completions", "deepseek-chat", "openai"),
    "qwen": (
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "qwen-turbo",
        "qwen",
    ),
    "glm": ("https://open.bigmodel.cn/api/paas/v4/chat/completions", "glm-4", "openai"),
}


class StructuredOutputError(ValueError):
    """The provider did not return the requested schema."""


class LLMGateway:
    def __init__(self, model_type: str = "deepseek", api_key: str = "", timeout: float = 30.0) -> None:
        self.model_type = model_type
        self.api_key = api_key
        self.timeout = timeout
        self.model_name = _ENDPOINTS.get(model_type, _ENDPOINTS["deepseek"])[1]

    def structured(self, schema: Type[T], *, system: str, user: str) -> T:
        return self.complete(schema, system=system, user=user)

    def complete(self, schema: Type[T], *, system: str, user: str) -> T:
        if not self.api_key:
            raise StructuredOutputError("API key is not configured")
        raw = self._complete_text(system, user)
        try:
            return schema.model_validate_json(unwrap_json_document(raw))
        except ValidationError as exc:
            raise StructuredOutputError("structured output did not match the schema") from exc

    def _complete_text(self, system: str, user: str) -> str:
        url, model, shape = _ENDPOINTS.get(self.model_type, _ENDPOINTS["deepseek"])
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        if shape == "qwen":
            payload: dict = {"model": model, "input": {"messages": messages}}
        else:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0,
                "response_format": {"type": "json_object"},
            }
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise TimeoutError("LLM provider timed out") from exc
        except httpx.HTTPError as exc:
            raise ConnectionError("LLM provider is unavailable") from exc
        if response.status_code >= 500:
            raise ConnectionError(f"LLM provider returned {response.status_code}")
        if response.status_code >= 400:
            raise StructuredOutputError(f"LLM provider rejected the request ({response.status_code})")
        data = response.json()
        if shape == "qwen":
            return str(data.get("output", {}).get("text", ""))
        choices = data.get("choices") or [{}]
        message = choices[0].get("message", {}) if choices else {}
        return str(message.get("content", ""))


def unwrap_json_document(text: str) -> str:
    raw = (text or "").strip()
    if not raw.startswith("```"):
        return raw
    lines = raw.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()

# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
from typing import Any

import requests

from acfpf.ai.diagnostics import (
    MAX_COMPLETION_TOKENS,
    MAX_PROVIDER_OUTPUT_CHARS,
    check_request_size,
    http_failure,
    transport_failure,
)
from acfpf.ai.provider import AIProviderError, AIProviderNotConfigured, ProviderRequest
from acfpf.ai.schema import AGENT_ACTION_SCHEMA


class OpenAICompatibleProvider:
    """Minimal provider for OpenAI-compatible Chat Completions APIs."""

    def __init__(
        self,
        *,
        name: str,
        api_key: str,
        model: str,
        api_url: str,
        timeout: float = 30.0,
        session: requests.Session | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        if not api_key.strip():
            raise AIProviderNotConfigured(f"No API key configured for provider {name}")
        self.name = name
        self.api_key = api_key.strip()
        self.model = model
        self.api_url = api_url
        self.timeout = timeout
        self.session = session or requests.Session()
        self.extra_headers = extra_headers or {}

    def complete_json(self, request: ProviderRequest) -> dict[str, Any]:
        check_request_size(request)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "response_format": self._response_format(request),
            "tool_choice": "none",
            "temperature": 0.1,
            "max_tokens": MAX_COMPLETION_TOKENS,
        }
        if self.name == "gemini" and self.model.startswith("gemini-3"):
            payload["reasoning_effort"] = "low"

        if self.name == "groq" and self.model.startswith("openai/gpt-oss-"):
            payload["reasoning_effort"] = "low"
            payload.pop("max_tokens")
            payload["max_completion_tokens"] = 2048

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }

        try:
            response = self.session.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
            choice = body["choices"][0]
            if choice.get("finish_reason") not in {None, "stop"}:
                raise AIProviderError(
                    f"{self.name} : réponse interrompue ou refusée, aucune analyse publiée.",
                    code="output_limit" if choice.get("finish_reason") == "length" else "refusal",
                )
            if choice["message"].get("refusal"):
                raise AIProviderError(
                    f"{self.name} : réponse refusée par le fournisseur.", code="refusal"
                )
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise AIProviderError(f"{self.name} returned a non-text JSON completion")
            if len(content) > MAX_PROVIDER_OUTPUT_CHARS:
                raise AIProviderError(
                    "La réponse du fournisseur dépasse la limite ACFPF.", code="output_limit"
                )
            result = json.loads(content)
            if not isinstance(result, dict):
                raise AIProviderError(f"{self.name} returned JSON that is not an object")
            return result
        except requests.HTTPError as exc:
            raise http_failure(self.name, exc.response, self.api_key) from None
        except requests.RequestException as exc:
            raise transport_failure(self.name, exc) from None
        except (AttributeError, KeyError, IndexError, TypeError, ValueError):
            raise AIProviderError(f"{self.name} : réponse JSON invalide ou inattendue.") from None

    def _response_format(self, request: ProviderRequest) -> dict[str, Any]:
        structured = self.name == "gemini" or (
            self.name == "groq" and self.model.startswith("openai/gpt-oss-")
        )
        if structured:
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": request.response_schema_name or "acfpf_agent_action",
                    "schema": request.response_schema or AGENT_ACTION_SCHEMA,
                    **({"strict": True} if self.name == "groq" else {}),
                },
            }
        return {"type": "json_object"}

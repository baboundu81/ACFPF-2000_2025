# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
from typing import Any

import requests

from acfpf.ai.provider import AIProviderError, AIProviderNotConfigured, ProviderRequest


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
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 900,
        }
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
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise AIProviderError(f"{self.name} returned a non-text JSON completion")
            result = json.loads(content)
            if not isinstance(result, dict):
                raise AIProviderError(f"{self.name} returned JSON that is not an object")
            return result
        except requests.RequestException as exc:
            raise AIProviderError(f"{self.name} API request failed") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError(f"{self.name} API returned an unexpected response") from exc

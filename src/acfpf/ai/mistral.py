# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
import os
from typing import Any

import requests

from acfpf.ai.provider import AIProviderError, AIProviderNotConfigured, ProviderRequest

API_URL = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "mistral-small-latest"


class MistralProvider:
    name = "mistral"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        if not api_key.strip():
            raise AIProviderNotConfigured("MISTRAL_API_KEY is not configured")
        self.api_key = api_key.strip()
        self.model = model
        self.timeout = timeout
        self.session = session or requests.Session()

    @classmethod
    def from_env(cls) -> "MistralProvider":
        api_key = os.getenv("MISTRAL_API_KEY", "")
        model = os.getenv("ACFPF_LLM_MODEL", DEFAULT_MODEL)
        return cls(api_key, model=model)

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
        }

        try:
            response = self.session.post(
                API_URL,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise AIProviderError("Mistral returned a non-text JSON completion")
            result = json.loads(content)
            if not isinstance(result, dict):
                raise AIProviderError("Mistral returned JSON that is not an object")
            return result
        except requests.RequestException as exc:
            raise AIProviderError("Mistral API request failed") from exc
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AIProviderError("Mistral API returned an unexpected response") from exc

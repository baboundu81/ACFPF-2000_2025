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


class AnthropicProvider:
    """Native Claude Messages API provider with guaranteed structured outputs."""

    name = "claude"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        api_url: str = "https://api.anthropic.com/v1/messages",
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        if not api_key.strip():
            raise AIProviderNotConfigured("No API key configured for provider claude")
        self.api_key = api_key.strip()
        self.model = model
        self.api_url = api_url
        self.timeout = timeout
        self.session = session or requests.Session()

    def complete_json(self, request: ProviderRequest) -> dict[str, Any]:
        check_request_size(request)
        payload = {
            "model": self.model,
            "max_tokens": MAX_COMPLETION_TOKENS,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.user_prompt}],
            "output_config": {
                "effort": "low",
                "format": {
                    "type": "json_schema",
                    "schema": request.response_schema or AGENT_ACTION_SCHEMA,
                },
            },
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
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
            if body.get("stop_reason") not in {None, "end_turn"}:
                raise AIProviderError(
                    "claude : réponse interrompue ou refusée.", code="output_limit"
                )
            blocks = body["content"]
            content = next(
                block["text"]
                for block in blocks
                if isinstance(block, dict) and block.get("type") == "text"
            )
            if not isinstance(content, str):
                raise AIProviderError("claude returned a non-text JSON completion")
            if len(content) > MAX_PROVIDER_OUTPUT_CHARS:
                raise AIProviderError("claude : réponse trop volumineuse.", code="output_limit")
            result = json.loads(content)
            if not isinstance(result, dict):
                raise AIProviderError("claude returned JSON that is not an object")
            return result
        except requests.HTTPError as exc:
            raise http_failure(self.name, exc.response, self.api_key) from None
        except requests.RequestException as exc:
            raise transport_failure(self.name, exc) from None
        except (AttributeError, KeyError, StopIteration, IndexError, TypeError, ValueError):
            raise AIProviderError("claude : réponse JSON invalide ou inattendue.") from None

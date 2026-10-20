# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
from typing import Any

import requests

from acfpf.ai.provider import AIProviderError, AIProviderNotConfigured, ProviderRequest
from acfpf.ai.schema import AGENT_ACTION_SCHEMA

MAX_PROVIDER_ERROR_MESSAGE_CHARS = 500


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
        payload = {
            "model": self.model,
            "max_tokens": 900,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.user_prompt}],
            "output_config": {
                "effort": "low",
                "format": {
                    "type": "json_schema",
                    "schema": AGENT_ACTION_SCHEMA,
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
            blocks = body["content"]
            content = next(
                block["text"]
                for block in blocks
                if isinstance(block, dict) and block.get("type") == "text"
            )
            if not isinstance(content, str):
                raise AIProviderError("claude returned a non-text JSON completion")
            result = json.loads(content)
            if not isinstance(result, dict):
                raise AIProviderError("claude returned JSON that is not an object")
            return result
        except requests.HTTPError as exc:
            raise AIProviderError(self._http_error_message(exc.response)) from exc
        except requests.RequestException as exc:
            raise AIProviderError(
                f"claude API request failed ({exc.__class__.__name__}: {exc})"
            ) from exc
        except (KeyError, StopIteration, TypeError, ValueError) as exc:
            raise AIProviderError("claude API returned an unexpected response") from exc

    def _http_error_message(self, response: requests.Response | None) -> str:
        if response is None:
            return "claude API request failed (HTTP error without response)"

        status = response.status_code
        labels = {
            400: "requête refusée",
            401: "clé API absente ou invalide",
            403: "accès refusé au modèle ou au projet",
            404: "modèle ou endpoint introuvable",
            413: "requête trop volumineuse",
            429: "limite de débit ou quota atteint",
            500: "erreur interne du fournisseur",
            529: "service fournisseur surchargé",
        }
        parts = [f"claude API request failed (HTTP {status}: {labels.get(status, 'erreur HTTP')})"]

        for header, label in (
            ("retry-after", "réessayer dans"),
            ("x-ratelimit-remaining-tokens", "tokens restants"),
            ("x-ratelimit-reset-tokens", "reset tokens"),
            ("x-ratelimit-remaining-requests", "requêtes restantes"),
            ("request-id", "request id"),
        ):
            value = response.headers.get(header)
            if value:
                suffix = " s" if header == "retry-after" else ""
                parts.append(f"{label}: {value}{suffix}")

        message = self._provider_error_message(response)
        if message:
            parts.append(f"détail fournisseur: {message}")
        return "; ".join(parts)

    @staticmethod
    def _provider_error_message(response: requests.Response) -> str | None:
        message: str | None = None
        try:
            payload = response.json()
            error = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(error, dict):
                raw_message = error.get("message")
                if isinstance(raw_message, str):
                    message = raw_message
        except (ValueError, TypeError):
            pass
        if not message:
            raw_text = getattr(response, "text", "")
            if isinstance(raw_text, str):
                message = raw_text.strip() or None
        if not message:
            return None
        return " ".join(message.split())[:MAX_PROVIDER_ERROR_MESSAGE_CHARS]

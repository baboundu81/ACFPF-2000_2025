# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
from typing import Any

import requests

from acfpf.ai.provider import AIProviderError, AIProviderNotConfigured, ProviderRequest

MAX_PROVIDER_ERROR_MESSAGE_CHARS = 500


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
            "tool_choice": "none",
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
        except requests.HTTPError as exc:
            response = exc.response
            raise AIProviderError(self._http_error_message(response)) from exc
        except requests.RequestException as exc:
            raise AIProviderError(
                f"{self.name} API request failed ({exc.__class__.__name__}: {exc})"
            ) from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError(f"{self.name} API returned an unexpected response") from exc

    def _http_error_message(self, response: requests.Response | None) -> str:
        if response is None:
            return f"{self.name} API request failed (HTTP error without response)"

        status = response.status_code
        labels = {
            400: "requête refusée",
            401: "clé API absente ou invalide",
            403: "accès refusé au modèle ou au projet",
            404: "modèle ou endpoint introuvable",
            413: "requête trop volumineuse",
            422: "requête non traitable",
            429: "limite de débit ou quota atteint",
            498: "capacité fournisseur temporairement saturée",
            500: "erreur interne du fournisseur",
            502: "passerelle fournisseur indisponible",
            503: "service fournisseur indisponible",
        }
        label = labels.get(status, "erreur HTTP")
        parts = [f"{self.name} API request failed (HTTP {status}: {label})"]

        retry_after = response.headers.get("retry-after")
        remaining_tokens = response.headers.get("x-ratelimit-remaining-tokens")
        reset_tokens = response.headers.get("x-ratelimit-reset-tokens")
        remaining_requests = response.headers.get("x-ratelimit-remaining-requests")
        request_id = response.headers.get("x-request-id") or response.headers.get("request-id")

        if retry_after:
            parts.append(f"réessayer dans {retry_after} s")
        if remaining_tokens:
            parts.append(f"tokens restants: {remaining_tokens}")
        if reset_tokens:
            parts.append(f"reset tokens: {reset_tokens}")
        if remaining_requests:
            parts.append(f"requêtes restantes: {remaining_requests}")
        if request_id:
            parts.append(f"request id: {request_id}")

        provider_message = self._provider_error_message(response)
        if provider_message:
            parts.append(f"détail fournisseur: {provider_message}")

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
            elif isinstance(error, str):
                message = error
        except (ValueError, TypeError):
            message = None

        if message is None:
            raw_text = getattr(response, "text", "")
            if isinstance(raw_text, str) and raw_text.strip():
                message = raw_text.strip()

        if not message:
            return None
        compact = " ".join(message.split())
        return compact[:MAX_PROVIDER_ERROR_MESSAGE_CHARS]

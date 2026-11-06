# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Provider boundaries: bounded inputs and diagnostics without raw provider payloads."""

from __future__ import annotations

import re

import requests

from acfpf.ai.provider import AIProviderError, ProviderRequest

MAX_PROVIDER_INPUT_CHARS = 128_000
MAX_PROVIDER_OUTPUT_CHARS = 32_000
MAX_COMPLETION_TOKENS = 4096


def check_request_size(request: ProviderRequest) -> None:
    if len(request.system_prompt) + len(request.user_prompt) > MAX_PROVIDER_INPUT_CHARS:
        raise AIProviderError(
            "Le contexte dépasse la limite de sécurité ACFPF. Réduisez le périmètre de la question.",
            code="context_limit",
        )


def http_failure(name: str, response: requests.Response | None, api_key: str) -> AIProviderError:
    # Never copy provider error.message/failed_generation: they may echo secrets,
    # the prompt, a candidate answer or private reasoning.
    status = response.status_code if response is not None else None
    codes = {
        401: "authentication",
        403: "authentication",
        413: "context_limit",
        429: "rate_limited",
        498: "unavailable",
        500: "unavailable",
        502: "unavailable",
        503: "unavailable",
        529: "unavailable",
    }
    labels = {
        400: "requête ou schéma refusé",
        401: "clé API absente ou invalide",
        403: "accès au modèle refusé",
        404: "modèle ou endpoint introuvable",
        413: "contexte trop volumineux",
        422: "requête non traitable",
        429: "limite de débit ou quota atteint",
    }
    code = codes.get(status, "request_rejected")
    label = labels.get(status, "fournisseur temporairement indisponible")
    message = f"{name} : HTTP {status} — {label}."
    retry_after = None
    if response is not None:
        value = response.headers.get("retry-after", "")
        if re.fullmatch(r"\d{1,6}(?:\.\d{1,3})?", value):
            retry_after = float(value)
            message += f" Réessayer dans {value} s."
        request_id = response.headers.get("x-request-id") or response.headers.get("request-id", "")
        if re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", request_id) and api_key not in request_id:
            message += f" Référence : {request_id}."
    return AIProviderError(message, code=code, http_status=status, retry_after=retry_after)


def transport_failure(name: str, error: requests.RequestException) -> AIProviderError:
    timeout = isinstance(error, requests.Timeout)
    return AIProviderError(
        f"{name} : délai de réponse dépassé."
        if timeout
        else f"{name} : connexion au fournisseur impossible.",
        code="timeout" if timeout else "unavailable",
    )

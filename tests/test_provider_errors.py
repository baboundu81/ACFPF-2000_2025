# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import requests
import pytest

from acfpf.ai.openai_compatible import OpenAICompatibleProvider
from acfpf.ai.provider import AIProviderError, ProviderRequest


class ErrorResponse:
    status_code = 429
    headers = {
        "retry-after": "7",
        "x-ratelimit-remaining-tokens": "0",
        "x-ratelimit-reset-tokens": "6.5s",
        "x-ratelimit-remaining-requests": "999",
        "x-request-id": "req-test-123",
    }
    text = '{"error":{"message":"Rate limit reached for model"}}'

    def raise_for_status(self) -> None:
        raise requests.HTTPError("429 Client Error", response=self)

    def json(self) -> dict:
        return {"error": {"message": "Rate limit reached for model"}}


class ErrorSession:
    def post(self, url, *, json, headers, timeout):
        del url, json, headers, timeout
        return ErrorResponse()


def test_provider_exposes_safe_rate_limit_diagnostics_without_api_key() -> None:
    provider = OpenAICompatibleProvider(
        name="groq",
        api_key="secret-must-never-appear",
        model="openai/gpt-oss-120b",
        api_url="https://api.groq.test/openai/v1/chat/completions",
        session=ErrorSession(),
    )

    with pytest.raises(AIProviderError) as exc_info:
        provider.complete_json(ProviderRequest("system", "user"))

    message = str(exc_info.value)
    assert "HTTP 429" in message
    assert "limite de débit ou quota atteint" in message
    assert "réessayer dans 7 s" in message
    assert "tokens restants: 0" in message
    assert "reset tokens: 6.5s" in message
    assert "req-test-123" in message
    assert "Rate limit reached for model" in message
    assert "secret-must-never-appear" not in message

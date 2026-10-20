# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import pytest
import requests

from acfpf.ai.openai_compatible import OpenAICompatibleProvider
from acfpf.ai.provider import AIProviderError, ProviderRequest


class ErrorResponse:
    def __init__(self) -> None:
        self.status_code = 429
        self.headers = {
            "retry-after": "7",
            "x-ratelimit-remaining-tokens": "0",
            "x-ratelimit-reset-tokens": "6.5s",
            "x-ratelimit-remaining-requests": "999",
            "x-request-id": "req-test-123",
        }
        self.text = '{"error":{"message":"Rate limit reached for model"}}'

    def raise_for_status(self) -> None:
        raise requests.HTTPError("429 Client Error", response=self)

    def json(self) -> dict:
        return {"error": {"message": "Rate limit reached for model"}}


class FailedGenerationResponse:
    def __init__(self) -> None:
        self.status_code = 400
        self.headers = {
            "x-ratelimit-remaining-tokens": "4335",
            "x-ratelimit-reset-tokens": "27.487s",
            "x-ratelimit-remaining-requests": "999",
            "x-request-id": "req-failed-generation",
        }
        self.text = ""

    def raise_for_status(self) -> None:
        raise requests.HTTPError("400 Client Error", response=self)

    def json(self) -> dict:
        return {
            "error": {
                "message": "Failed to validate JSON. Please adjust your prompt.",
                "failed_generation": {
                    "reason": "Generated content was not valid JSON",
                    "attempted_arguments": "{not valid json}",
                },
            }
        }


class ErrorSession:
    def __init__(self, response=None) -> None:
        self.response = response or ErrorResponse()

    def post(self, url, *, json, headers, timeout):
        del url, json, headers, timeout
        return self.response


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


def test_provider_exposes_failed_generation_reason_without_attempted_payload() -> None:
    provider = OpenAICompatibleProvider(
        name="groq",
        api_key="secret-must-never-appear",
        model="openai/gpt-oss-120b",
        api_url="https://api.groq.test/openai/v1/chat/completions",
        session=ErrorSession(FailedGenerationResponse()),
    )

    with pytest.raises(AIProviderError) as exc_info:
        provider.complete_json(ProviderRequest("system", "user"))

    message = str(exc_info.value)
    assert "HTTP 400" in message
    assert "Failed to validate JSON" in message
    assert "génération refusée: Generated content was not valid JSON" in message
    assert "{not valid json}" not in message
    assert "secret-must-never-appear" not in message

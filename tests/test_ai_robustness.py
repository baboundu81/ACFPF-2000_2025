# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

import pytest
import requests

from acfpf.ai.anthropic import AnthropicProvider
from acfpf.ai.diagnostics import MAX_PROVIDER_INPUT_CHARS, MAX_PROVIDER_OUTPUT_CHARS
from acfpf.ai.openai_compatible import OpenAICompatibleProvider
from acfpf.ai.provider import AIProviderError, ProviderRequest
from tests.test_provider_errors import ErrorResponse

SECRET = "provider-secret-never-exposed"


class Session:
    def __init__(self, result):
        self.result, self.calls = result, []

    def post(self, url, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class Response:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


def provider(name, result):
    session = Session(result)
    instance = (
        AnthropicProvider(api_key=SECRET, model="claude", session=session)
        if name == "claude"
        else OpenAICompatibleProvider(
            name=name,
            api_key=SECRET,
            model="openai/gpt-oss-120b" if name == "groq" else "model",
            api_url="https://provider.test/",
            session=session,
        )
    )
    return instance, session


@pytest.mark.parametrize("name", ["gemini", "groq", "claude", "mistral", "openai", "openrouter"])
@pytest.mark.parametrize(
    "error,code",
    [(requests.Timeout(SECRET), "timeout"), (requests.ConnectionError(SECRET), "unavailable")],
)
def test_transport_failure_has_safe_diagnostic_for_every_provider(name, error, code):
    instance, _ = provider(name, error)
    with pytest.raises(AIProviderError) as caught:
        instance.complete_json(ProviderRequest("system", "user"))
    assert caught.value.code == code
    assert SECRET not in str(caught.value)
    assert SECRET not in json.dumps(caught.value.as_dict())
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("name", ["gemini", "groq", "claude", "mistral", "openai", "openrouter"])
def test_oversized_context_is_refused_before_network_for_every_provider(name):
    instance, session = provider(name, Response({}))
    with pytest.raises(AIProviderError) as caught:
        instance.complete_json(ProviderRequest("system", "x" * MAX_PROVIDER_INPUT_CHARS))
    assert caught.value.code == "context_limit"
    assert session.calls == []


@pytest.mark.parametrize("name", ["groq", "claude"])
@pytest.mark.parametrize(
    "status,code",
    [
        (400, "request_rejected"),
        (401, "authentication"),
        (403, "authentication"),
        (413, "context_limit"),
        (429, "rate_limited"),
        (503, "unavailable"),
    ],
)
def test_raw_provider_payload_and_reasoning_are_never_exposed(name, status, code):
    class UnsafeResponse(ErrorResponse):
        def __init__(self):
            super().__init__()
            self.status_code = status
            self.headers["x-request-id"] = SECRET

        def json(self):
            return {"error": {"message": SECRET, "failed_generation": "private-reasoning-echo"}}

    instance, _ = provider(name, UnsafeResponse())
    with pytest.raises(AIProviderError) as caught:
        instance.complete_json(ProviderRequest("system", "user"))
    assert caught.value.code == code and caught.value.http_status == status
    assert SECRET not in str(caught.value) and "private-reasoning" not in str(caught.value)


@pytest.mark.parametrize("name", ["groq", "claude"])
@pytest.mark.parametrize(
    "content", ["not JSON", "[]", "null", "x" * (MAX_PROVIDER_OUTPUT_CHARS + 1)]
)
def test_malformed_or_excessive_completion_is_rejected(name, content):
    body = (
        {"content": [{"type": "text", "text": content}]}
        if name == "claude"
        else {"choices": [{"message": {"content": content}}]}
    )
    instance, _ = provider(name, Response(body))
    with pytest.raises(AIProviderError):
        instance.complete_json(ProviderRequest("system", "user"))


@pytest.mark.parametrize("name", ["groq", "claude"])
def test_even_valid_json_is_rejected_if_completion_was_truncated(name):
    body = (
        {"stop_reason": "max_tokens", "content": [{"type": "text", "text": '{"action":"answer"}'}]}
        if name == "claude"
        else {
            "choices": [{"finish_reason": "length", "message": {"content": '{"action":"answer"}'}}]
        }
    )
    instance, _ = provider(name, Response(body))
    with pytest.raises(AIProviderError) as caught:
        instance.complete_json(ProviderRequest("system", "user"))
    assert caught.value.code == "output_limit"


@pytest.mark.parametrize(
    "body", [None, [], {}, {"choices": []}, {"choices": [None]}, {"choices": [{"message": []}]}]
)
def test_invalid_envelope_is_a_safe_provider_error(body):
    instance, _ = provider("gemini", Response(body))
    with pytest.raises(AIProviderError):
        instance.complete_json(ProviderRequest("system", "user"))

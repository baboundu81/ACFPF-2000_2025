# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

from acfpf.ai.anthropic import AnthropicProvider
from acfpf.ai.provider import ProviderRequest
from acfpf.ai.registry import build_provider_from_env
from acfpf.ai.schema import AGENT_ACTION_SCHEMA


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.status_code = 200
        self.headers = {}
        self.text = ""

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.last_call = None

    def post(self, url, *, json, headers, timeout):
        self.last_call = {
            "url": url,
            "json": json,
            "headers": headers,
            "timeout": timeout,
        }
        return FakeResponse(self.payload)


def test_claude_native_provider_uses_structured_output() -> None:
    generated = {
        "action": "answer",
        "query": "",
        "source_ids": [],
        "reason": "",
        "url": "",
        "document_id": "",
        "unit": 0,
        "status": "answered",
        "answer": "Test",
        "citations": ["S1"],
        "limitations": [],
    }
    session = FakeSession(
        {"content": [{"type": "text", "text": json.dumps(generated)}]}
    )
    provider = AnthropicProvider(
        api_key="secret-test-key",
        model="claude-haiku-5-5",
        session=session,
    )

    result = provider.complete_json(ProviderRequest("system JSON", "user"))

    assert result == generated
    payload = session.last_call["json"]
    assert payload["model"] == "claude-haiku-5-5"
    assert payload["output_config"]["effort"] == "low"
    assert payload["output_config"]["format"]["type"] == "json_schema"
    assert payload["output_config"]["format"]["schema"] == AGENT_ACTION_SCHEMA
    assert session.last_call["headers"]["x-api-key"] == "secret-test-key"
    assert session.last_call["headers"]["anthropic-version"] == "2023-06-01"


def test_registry_selects_claude(monkeypatch) -> None:
    monkeypatch.setenv("ACFPF_LLM_PROVIDER", "claude")
    monkeypatch.setenv("ACFPF_LLM_API_KEY", "test-key")
    monkeypatch.delenv("ACFPF_LLM_MODEL", raising=False)

    provider = build_provider_from_env()

    assert isinstance(provider, AnthropicProvider)
    assert provider.name == "claude"
    assert provider.model == "claude-haiku-5-5"
    assert provider.api_url == "https://api.anthropic.com/v1/messages"


def test_registry_accepts_anthropic_legacy_key(monkeypatch) -> None:
    monkeypatch.setenv("ACFPF_LLM_PROVIDER", "claude")
    monkeypatch.delenv("ACFPF_LLM_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "legacy-key")

    provider = build_provider_from_env()

    assert isinstance(provider, AnthropicProvider)
    assert provider.api_key == "legacy-key"

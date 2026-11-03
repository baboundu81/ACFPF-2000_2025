# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

from acfpf.ai.openai_compatible import OpenAICompatibleProvider
from acfpf.ai.provider import ProviderRequest


CUSTOM_SCHEMA = {
    "type": "object",
    "properties": {"query": {"type": "string"}},
    "required": ["query"],
    "additionalProperties": False,
}


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.last_call = None

    def post(self, url, *, json, headers, timeout):
        self.last_call = {"url": url, "json": json, "headers": headers, "timeout": timeout}
        return FakeResponse(self.payload)


def test_gemini_uses_request_specific_json_schema() -> None:
    session = FakeSession(
        {"choices": [{"message": {"content": json.dumps({"query": "santé"})}}]}
    )
    provider = OpenAICompatibleProvider(
        name="gemini",
        api_key="test-key",
        model="gemini-3.8-flash",
        api_url="https://example.test/v1/chat/completions",
        session=session,
    )

    provider.complete_json(
        ProviderRequest(
            "system",
            "user",
            response_schema=CUSTOM_SCHEMA,
            response_schema_name="custom_plan",
        )
    )

    payload = session.last_call["json"]
    assert payload["response_format"]["json_schema"]["name"] == "custom_plan"
    assert payload["response_format"]["json_schema"]["schema"] == CUSTOM_SCHEMA

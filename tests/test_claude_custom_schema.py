# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

from acfpf.ai.anthropic import AnthropicProvider
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
        self.last_call = {"url": url, "json": json, "headers": headers, "timeout": timeout}
        return FakeResponse(self.payload)


def test_claude_uses_request_specific_json_schema() -> None:
    session = FakeSession(
        {"content": [{"type": "text", "text": json.dumps({"query": "santé"})}]}
    )
    provider = AnthropicProvider(
        api_key="test-key",
        model="claude-haiku-5-5",
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
    assert payload["output_config"]["format"]["schema"] == CUSTOM_SCHEMA

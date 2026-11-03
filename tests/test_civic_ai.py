# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

from acfpf.ai.civic import CIVIC_SYSTEM_PROMPT, CivicAnswerService
from acfpf.ai.provider import ProviderRequest
from acfpf.ai.service import AnswerService
from acfpf.data.eurostat import EurostatError


class FailingMacroService:
    def dashboard(self, *, refresh: bool = False):
        raise EurostatError("macro unavailable")


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self.requests: list[ProviderRequest] = []

    def complete_json(self, request: ProviderRequest) -> dict:
        self.requests.append(request)
        return {
            "action": "answer",
            "status": "insufficient",
            "answer": "Les preuves disponibles ne suffisent pas encore.",
            "citations": [],
            "limitations": ["Aucun document officiel n'a encore été lu."],
        }


def test_civic_agent_uses_public_action_prompt() -> None:
    provider = FakeProvider()
    civic = CivicAnswerService(AnswerService(provider, FailingMacroService()))

    answer = civic.ask("Que prévoit ce projet de loi ?")

    assert answer.status == "insufficient"
    assert provider.requests[0].system_prompt == CIVIC_SYSTEM_PROMPT
    assert "action publique" in provider.requests[0].system_prompt
    assert "amendement" in provider.requests[0].system_prompt


def test_civic_agent_can_continue_when_finance_data_is_unavailable() -> None:
    provider = FakeProvider()
    civic = CivicAnswerService(AnswerService(provider, FailingMacroService()))

    civic.ask("Explique ce texte.")

    state = json.loads(provider.requests[0].user_prompt)
    assert state["NUMERIC_CONTEXT"]["availability"] == "unavailable"
    assert state["EVIDENCE_AVAILABLE"] == {}

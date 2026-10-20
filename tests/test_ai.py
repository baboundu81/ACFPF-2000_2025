# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

import pytest

from acfpf.ai.mistral import MistralProvider
from acfpf.ai.provider import AIGroundingError, ProviderRequest
from acfpf.ai.service import AnswerService
from acfpf.macro import build_dashboard
from tests.test_eurostat import sample_dataset


class FakeMacroService:
    def dashboard(self, *, refresh: bool = False):
        assert isinstance(refresh, bool)
        return build_dashboard(sample_dataset())


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, response: dict) -> None:
        self.response = response
        self.last_request = None

    def complete_json(self, request: ProviderRequest) -> dict:
        self.last_request = request
        return self.response


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
        self.last_call = {
            "url": url,
            "json": json,
            "headers": headers,
            "timeout": timeout,
        }
        return FakeResponse(self.payload)


def test_answer_service_accepts_only_known_citations() -> None:
    provider = FakeProvider(
        {
            "status": "answered",
            "answer": "Les dépenses passent de 52,6 % à 57,3 % du PIB entre 2000 et 2025.",
            "citations": ["S1"],
            "limitations": ["Ce constat ne dit pas pourquoi les dépenses ont augmenté."],
        }
    )
    service = AnswerService(provider, FakeMacroService())

    answer = service.ask("Les dépenses publiques ont-elles augmenté depuis 2000 ?")

    assert answer.status == "answered"
    assert answer.citations[0].dataset_code == "gov_10a_main"
    assert answer.provider == "fake"
    assert "CONTEXTE_ACFPF" in provider.last_request.user_prompt
    assert "gov_10a_main" in provider.last_request.user_prompt


def test_answer_service_rejects_unknown_citation() -> None:
    provider = FakeProvider(
        {
            "status": "answered",
            "answer": "Réponse inventée.",
            "citations": ["S99"],
            "limitations": [],
        }
    )
    service = AnswerService(provider, FakeMacroService())

    with pytest.raises(AIGroundingError):
        service.ask("Question")


def test_answer_service_rejects_fact_answer_without_citation() -> None:
    provider = FakeProvider(
        {
            "status": "answered",
            "answer": "Réponse sans source.",
            "citations": [],
            "limitations": [],
        }
    )
    service = AnswerService(provider, FakeMacroService())

    with pytest.raises(AIGroundingError):
        service.ask("Question")


def test_answer_service_accepts_insufficient_answer_without_citation() -> None:
    provider = FakeProvider(
        {
            "status": "insufficient",
            "answer": "Les données ACFPF actuelles ne permettent pas de répondre sur l'éducation.",
            "citations": [],
            "limitations": ["Aucune série d'éducation n'est fournie au modèle."],
        }
    )
    service = AnswerService(provider, FakeMacroService())

    answer = service.ask("Le niveau scolaire a-t-il baissé ?")

    assert answer.status == "insufficient"
    assert answer.citations == ()


def test_mistral_provider_uses_json_mode_and_server_side_key() -> None:
    generated = {
        "status": "answered",
        "answer": "Test",
        "citations": ["S1"],
        "limitations": [],
    }
    session = FakeSession(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(generated),
                    }
                }
            ]
        }
    )
    provider = MistralProvider("secret-test-key", session=session)

    result = provider.complete_json(ProviderRequest("system JSON", "user"))

    assert result == generated
    assert session.last_call["json"]["response_format"] == {"type": "json_object"}
    assert session.last_call["json"]["model"] == "mistral-small-latest"
    assert session.last_call["headers"]["Authorization"] == "Bearer secret-test-key"

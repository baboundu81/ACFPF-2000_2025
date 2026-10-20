# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

import pytest

from acfpf.ai.openai_compatible import OpenAICompatibleProvider
from acfpf.ai.provider import AIGroundingError, AIProviderNotConfigured, ProviderRequest
from acfpf.ai.registry import build_provider_from_env
from acfpf.ai.service import AnswerService
from acfpf.cofog import build_cofog_analysis
from acfpf.data.cofog import parse_cofog_payload
from acfpf.document_corpus import CorpusSearch
from acfpf.evidence import EvidenceChunk, EvidenceRef
from acfpf.macro import build_dashboard
from tests.test_cofog import sample_cofog_payload
from tests.test_eurostat import sample_dataset


class FakeMacroService:
    def dashboard(self, *, refresh: bool = False):
        assert isinstance(refresh, bool)
        return build_dashboard(sample_dataset())


class FakeCofogService:
    def analysis(self, *, refresh: bool = False):
        assert isinstance(refresh, bool)
        return build_cofog_analysis(parse_cofog_payload(sample_cofog_payload()))


class FakeDocumentCorpus:
    def search(self, question: str, *, limit: int = 5, refresh: bool = False) -> CorpusSearch:
        assert question
        assert limit == 5
        evidence = EvidenceRef(
            id="finance-law",
            source_id="legifrance",
            stage="decision",
            kind="finance_law",
            title="Loi de finances de test",
            source_url="https://official.test/finance-law",
            document_id="LAW-TEST",
        )
        return CorpusSearch(
            chunks=(
                EvidenceChunk(
                    id="finance-law#0001",
                    evidence=evidence,
                    text="La loi autorise les crédits pour l'exercice considéré.",
                ),
            )
        )


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


def test_answer_service_adds_cofog_and_document_evidence() -> None:
    provider = FakeProvider(
        {
            "status": "answered",
            "answer": "Le poids de certaines fonctions a diminué ; une loi n'est pas une exécution.",
            "citations": ["S3", "S4"],
            "limitations": ["Les causes doivent être documentées séparément."],
        }
    )
    service = AnswerService(
        provider,
        FakeMacroService(),
        FakeCofogService(),
        FakeDocumentCorpus(),
    )

    answer = service.ask("Où la dépense a-t-elle baissé et quelles décisions ont été prises ?")

    assert [citation.dataset_code for citation in answer.citations] == [
        "gov_10a_exp",
        "LAW-TEST",
    ]
    prompt = provider.last_request.user_prompt
    assert "cofog_functional_spending" in prompt
    assert "retrieved_official_documents" in prompt
    assert "finance-law#0001" in prompt
    assert '"stage":"decision"' in prompt


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
            "answer": "Les données ACFPF actuelles ne permettent pas de répondre précisément.",
            "citations": [],
            "limitations": ["Le corpus est incomplet."],
        }
    )
    service = AnswerService(provider, FakeMacroService())

    answer = service.ask("Le niveau scolaire a-t-il baissé ?")

    assert answer.status == "insufficient"
    assert answer.citations == ()


def test_openai_compatible_provider_uses_json_mode_and_server_side_key() -> None:
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
    provider = OpenAICompatibleProvider(
        name="groq",
        api_key="secret-test-key",
        model="openai/gpt-oss-120b",
        api_url="https://api.groq.test/openai/v1/chat/completions",
        session=session,
    )

    result = provider.complete_json(ProviderRequest("system JSON", "user"))

    assert result == generated
    assert session.last_call["json"]["response_format"] == {"type": "json_object"}
    assert session.last_call["json"]["tool_choice"] == "none"
    assert session.last_call["json"]["model"] == "openai/gpt-oss-120b"
    assert session.last_call["headers"]["Authorization"] == "Bearer secret-test-key"


def test_registry_defaults_to_groq(monkeypatch) -> None:
    monkeypatch.delenv("ACFPF_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ACFPF_LLM_API_KEY", "test-key")
    monkeypatch.delenv("ACFPF_LLM_MODEL", raising=False)

    provider = build_provider_from_env()

    assert provider.name == "groq"
    assert provider.model == "openai/gpt-oss-120b"
    assert provider.api_url == "https://api.groq.com/openai/v1/chat/completions"


def test_registry_selects_gemini_and_custom_model(monkeypatch) -> None:
    monkeypatch.setenv("ACFPF_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("ACFPF_LLM_API_KEY", "test-key")
    monkeypatch.setenv("ACFPF_LLM_MODEL", "gemini-test-model")

    provider = build_provider_from_env()

    assert provider.name == "gemini"
    assert provider.model == "gemini-test-model"
    assert "generativelanguage.googleapis.com" in provider.api_url


def test_registry_accepts_legacy_provider_specific_key(monkeypatch) -> None:
    monkeypatch.setenv("ACFPF_LLM_PROVIDER", "mistral")
    monkeypatch.delenv("ACFPF_LLM_API_KEY", raising=False)
    monkeypatch.setenv("MISTRAL_API_KEY", "legacy-key")

    provider = build_provider_from_env()

    assert provider.name == "mistral"
    assert provider.api_key == "legacy-key"


def test_registry_rejects_unknown_provider(monkeypatch) -> None:
    monkeypatch.setenv("ACFPF_LLM_PROVIDER", "unknown")
    monkeypatch.setenv("ACFPF_LLM_API_KEY", "test-key")

    with pytest.raises(AIProviderNotConfigured):
        build_provider_from_env()

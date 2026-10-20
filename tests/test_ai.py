# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

import pytest

from acfpf.ai.openai_compatible import AGENT_ACTION_SCHEMA, OpenAICompatibleProvider
from acfpf.ai.provider import AIGroundingError, AIProviderNotConfigured, ProviderRequest
from acfpf.ai.registry import build_provider_from_env
from acfpf.ai.service import AnswerService
from acfpf.cofog import build_cofog_analysis
from acfpf.data.cofog import parse_cofog_payload
from acfpf.live_research import DocumentUnit, LiveDocument, SearchResult
from acfpf.macro import build_dashboard
from acfpf.source_registry import Source
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


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, *responses: dict) -> None:
        self.responses = list(responses)
        self.requests: list[ProviderRequest] = []

    def complete_json(self, request: ProviderRequest) -> dict:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("FakeProvider has no response left")
        return self.responses.pop(0)


class FakeLiveResearch:
    def __init__(self) -> None:
        self.sources = {
            "legifrance": Source(
                id="legifrance",
                name="Légifrance",
                base_url="https://www.legifrance.gouv.fr/",
                priority="primary",
                themes=("legislation",),
                evidence_stages=("decision",),
                allowed_domains=("legifrance.gouv.fr",),
            )
        }
        self.doc = LiveDocument(
            document_id="D1",
            source_id="legifrance",
            title="Loi de finances de test",
            url="https://www.legifrance.gouv.fr/test",
            retrieved_at="2026-10-20T12:00:00+00:00",
            sha256="abc123",
            content_type="text/html",
            units=(
                DocumentUnit(1, "segment 1", "La loi autorise les crédits pour l'exercice."),
                DocumentUnit(2, "segment 2", "Une disposition modifie les crédits d'une mission."),
            ),
        )

    def spawn(self):
        return self

    def source_catalog(self):
        return [
            {
                "id": "legifrance",
                "name": "Légifrance",
                "priority": "primary",
                "themes": ["legislation"],
                "evidence_stages": ["decision"],
                "allowed_domains": ["legifrance.gouv.fr"],
            }
        ]

    def search(self, query: str, *, source_ids: list[str]):
        assert query
        assert source_ids == ["legifrance"]
        return (
            SearchResult(
                source_id="legifrance",
                title="Loi de finances de test",
                url=self.doc.url,
            ),
        )

    def open(self, url: str):
        assert url == self.doc.url
        return self.doc

    def read(self, document_id: str, unit_index: int):
        assert document_id == "D1"
        return self.doc.units[unit_index - 1]

    def document(self, document_id: str):
        assert document_id == "D1"
        return self.doc


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


def test_answer_service_can_answer_from_numeric_context_only() -> None:
    provider = FakeProvider(
        {
            "action": "answer",
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
    assert answer.research == ()
    state = json.loads(provider.requests[0].user_prompt)
    assert "NUMERIC_CONTEXT" in state
    assert state["EVIDENCE_AVAILABLE"] == {}


def test_answer_service_runs_live_search_open_read_then_answers() -> None:
    provider = FakeProvider(
        {
            "action": "search",
            "query": "loi finances crédits mission",
            "source_ids": ["legifrance"],
            "reason": "Vérifier la décision juridique.",
        },
        {
            "action": "open",
            "url": "https://www.legifrance.gouv.fr/test",
            "reason": "Lire le texte officiel.",
        },
        {
            "action": "read",
            "document_id": "D1",
            "unit": 2,
            "reason": "Lire la suite du texte.",
        },
        {
            "action": "answer",
            "status": "answered",
            "answer": "Une variation est observée et un texte juridique modifie des crédits.",
            "citations": ["S3", "E1", "E2"],
            "limitations": ["Une décision ne prouve pas à elle seule l'exécution."],
        },
    )
    service = AnswerService(
        provider,
        FakeMacroService(),
        FakeCofogService(),
        FakeLiveResearch(),
    )

    answer = service.ask("Où la dépense a-t-elle baissé et quelles décisions ont été prises ?")

    assert [citation.id for citation in answer.citations] == ["S3", "E1", "E2"]
    assert answer.citations[1].source_id == "legifrance"
    assert answer.citations[1].sha256 == "abc123"
    assert [item["type"] for item in answer.research] == ["search", "open", "read"]
    final_state = json.loads(provider.requests[-1].user_prompt)
    assert "E1" in final_state["EVIDENCE_AVAILABLE"]
    assert "E2" in final_state["EVIDENCE_AVAILABLE"]
    assert "Une disposition modifie" in final_state["EVIDENCE_AVAILABLE"]["E2"]["text"]


def test_answer_service_rejects_citation_that_was_never_read() -> None:
    provider = FakeProvider(
        {
            "action": "answer",
            "status": "answered",
            "answer": "Réponse inventée.",
            "citations": ["E99"],
            "limitations": [],
        }
    )
    service = AnswerService(provider, FakeMacroService())

    with pytest.raises(AIGroundingError, match="n'ont pas été lues"):
        service.ask("Question")


def test_answer_service_rejects_fact_answer_without_citation() -> None:
    provider = FakeProvider(
        {
            "action": "answer",
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
            "action": "answer",
            "status": "insufficient",
            "answer": "Les preuves disponibles ne permettent pas de répondre précisément.",
            "citations": [],
            "limitations": ["Aucune preuve suffisante n'a été trouvée."],
        }
    )
    service = AnswerService(provider, FakeMacroService())

    answer = service.ask("Le niveau scolaire a-t-il baissé ?")

    assert answer.status == "insufficient"
    assert answer.citations == ()


def test_groq_gpt_oss_uses_structured_actions_and_server_side_key() -> None:
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
    response_format = session.last_call["json"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "acfpf_agent_action"
    assert response_format["json_schema"]["schema"] == AGENT_ACTION_SCHEMA
    assert session.last_call["json"]["tool_choice"] == "none"
    assert session.last_call["json"]["model"] == "openai/gpt-oss-120b"
    assert session.last_call["headers"]["Authorization"] == "Bearer secret-test-key"


def test_non_groq_provider_keeps_json_object_mode() -> None:
    generated = {"action": "answer"}
    session = FakeSession(
        {"choices": [{"message": {"content": json.dumps(generated)}}]}
    )
    provider = OpenAICompatibleProvider(
        name="openrouter",
        api_key="secret-test-key",
        model="openrouter/free",
        api_url="https://openrouter.test/api/v1/chat/completions",
        session=session,
    )

    provider.complete_json(ProviderRequest("system JSON", "user"))

    assert session.last_call["json"]["response_format"] == {"type": "json_object"}


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

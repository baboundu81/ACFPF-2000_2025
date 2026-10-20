# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

from acfpf.ai.service import AgentEvent, Citation, GroundedAnswer
from acfpf.cofog import build_cofog_analysis
from acfpf.data.cofog import parse_cofog_payload
from acfpf.data.eurostat import EurostatError
from acfpf.macro import build_dashboard
from acfpf.web import create_app
from tests.test_cofog import sample_cofog_payload
from tests.test_eurostat import sample_dataset


class FakeMacroService:
    def dashboard(self, *, refresh: bool = False):
        assert isinstance(refresh, bool)
        return build_dashboard(sample_dataset())


class FailingMacroService:
    def dashboard(self, *, refresh: bool = False):
        raise EurostatError("simulated source failure")


class FakeCofogService:
    def analysis(self, *, refresh: bool = False):
        assert isinstance(refresh, bool)
        return build_cofog_analysis(parse_cofog_payload(sample_cofog_payload()))


class FailingCofogService:
    def analysis(self, *, refresh: bool = False):
        raise EurostatError("simulated cofog failure")


class FakeAnswerService:
    @staticmethod
    def _answer() -> GroundedAnswer:
        return GroundedAnswer(
            status="answered",
            answer="Les dépenses ont augmenté de 4,7 points de PIB entre 2000 et 2025.",
            citations=(
                Citation(
                    id="S1",
                    dataset_code="gov_10a_main",
                    label="Government revenue, expenditure and main aggregates",
                    source_url="https://example.test/source",
                    source_id="eurostat",
                ),
            ),
            limitations=("Ce constat est descriptif.",),
            provider="fake",
            model="fake-model",
            research=(
                {
                    "type": "search",
                    "query": "dépenses publiques",
                    "source_ids": ["budget_gouv"],
                    "result_count": 2,
                    "reason": "Vérifier les documents officiels.",
                },
            ),
        )

    def ask(self, question: str) -> GroundedAnswer:
        assert question
        return self._answer()

    def iter_ask(self, question: str):
        assert question
        yield AgentEvent("started", {"message": "Préparation"})
        yield AgentEvent(
            "search",
            {
                "query": "dépenses publiques",
                "source_ids": ["budget_gouv"],
                "result_count": 2,
                "reason": "Vérifier les documents officiels.",
            },
        )
        yield AgentEvent("answer", {}, answer=self._answer())


def test_dashboard_page_renders_macro_cofog_and_live_research_experience() -> None:
    app = create_app(FakeMacroService(), cofog_service=FakeCofogService())
    client = app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Vingt-cinq ans de finances publiques" in html
    assert "57.3" in html
    assert "gov_10a_main" in html
    assert "gov_10dd_edpt1" in html
    assert "Enseignement" in html
    assert "Protection sociale" in html
    assert "Recherche live" in html
    assert "Une URL trouvée n'est citable qu'après lecture effective" in html
    assert 'id="research-progress"' in html
    assert 'id="functions"' in html


def test_macro_api_returns_same_analysis() -> None:
    app = create_app(FakeMacroService(), cofog_service=FakeCofogService())
    client = app.test_client()

    response = client.get("/api/macro")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["dataset_code"] == "gov_10a_main + gov_10dd_edpt1"
    assert payload["series"]["expenditure"]["values"][-1] == {
        "year": 2025,
        "value": 57.3,
    }
    assert len(payload["sources"]) == 2


def test_cofog_api_returns_functional_breakdown() -> None:
    app = create_app(FakeMacroService(), cofog_service=FakeCofogService())
    client = app.test_client()

    response = client.get("/api/cofog")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["dataset_code"] == "gov_10a_exp"
    assert len(payload["changes"]) == 10
    assert payload["increases"][0]["code"] == "GF10"


def test_evidence_api_exposes_live_allowlist_without_document_corpus() -> None:
    app = create_app(FakeMacroService(), cofog_service=FakeCofogService())
    client = app.test_client()

    response = client.get("/api/evidence")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["mode"] == "live_official_research"
    assert payload["persistent_document_corpus"] is False
    assert any(source["id"] == "legifrance" for source in payload["sources"])
    assert any("legifrance.gouv.fr" in source["allowed_domains"] for source in payload["sources"])
    assert "documents" not in payload


def test_ask_api_returns_grounded_answer() -> None:
    app = create_app(
        FakeMacroService(),
        FakeAnswerService(),
        cofog_service=FakeCofogService(),
    )
    client = app.test_client()

    response = client.post(
        "/api/ask",
        json={"question": "Les dépenses ont-elles augmenté depuis 2000 ?"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "answered"
    assert payload["citations"][0]["dataset_code"] == "gov_10a_main"
    assert payload["provider"] == "fake"


def test_stream_api_emits_progress_then_answer_as_ndjson() -> None:
    app = create_app(
        FakeMacroService(),
        FakeAnswerService(),
        cofog_service=FakeCofogService(),
    )
    client = app.test_client()

    response = client.post("/api/ask/stream", json={"question": "Où chercher ?"})
    lines = [json.loads(line) for line in response.get_data(as_text=True).splitlines()]

    assert response.status_code == 200
    assert response.mimetype == "application/x-ndjson"
    assert [item["type"] for item in lines] == ["started", "search", "answer"]
    assert lines[-1]["answer"]["status"] == "answered"


def test_sources_remain_available_when_macro_loading_fails() -> None:
    app = create_app(FailingMacroService(), cofog_service=FakeCofogService())
    client = app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 503
    assert 'id="sources"' in html
    assert "gov_10a_main" in html
    assert "gov_10dd_edpt1" in html


def test_dashboard_survives_cofog_failure() -> None:
    app = create_app(FakeMacroService(), cofog_service=FailingCofogService())
    client = app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Décomposition COFOG indisponible" in html
    assert "simulated cofog failure" in html


def test_error_api_includes_source_catalog() -> None:
    app = create_app(FailingMacroService(), cofog_service=FakeCofogService())
    client = app.test_client()

    response = client.get("/api/macro")
    payload = response.get_json()

    assert response.status_code == 503
    assert payload["error"] == "simulated source failure"
    assert [source["dataset_code"] for source in payload["sources"]] == [
        "gov_10a_main",
        "gov_10dd_edpt1",
    ]


def test_health_endpoint_reports_live_research_mode() -> None:
    app = create_app(FakeMacroService(), cofog_service=FakeCofogService())
    client = app.test_client()

    response = client.get("/healthz")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["ai"] in {"enabled", "disabled"}
    assert payload["research_mode"] == "live_official_sources"

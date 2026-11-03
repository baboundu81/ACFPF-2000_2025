# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

from acfpf.ai.service import AgentEvent, Citation, GroundedAnswer
from acfpf.cofog import build_cofog_analysis
from acfpf.data.cofog import parse_cofog_payload
from acfpf.data.eurostat import EurostatError
from acfpf.legislation import LegislationError, LegislativeDossier, LegislativeEvent
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


def sample_dossier() -> LegislativeDossier:
    return LegislativeDossier(
        id="DLR1",
        title="Projet de loi relatif au logement",
        legislature="17",
        procedure_code="PRJLOI",
        procedure_label="Projet de loi ordinaire",
        status="active",
        status_label="En cours",
        current_stage="Examen en commission",
        last_activity="2026-11-02",
        official_url="https://www.assemblee-nationale.fr/dyn/17/dossiers/logement",
        source_url="https://data.assemblee-nationale.fr/travaux-parlementaires/dossiers-legislatifs",
        events=(
            LegislativeEvent("2026-10-20", "Dépôt"),
            LegislativeEvent("2026-11-02", "Examen en commission"),
        ),
    )


class FakeLegislationService:
    def search(self, query="", *, status=None, limit=20, refresh=False):
        assert isinstance(refresh, bool)
        assert limit >= 1
        dossier = sample_dossier()
        if status == "promulgated":
            return ()
        if query and "santé" in query.lower():
            return ()
        return (dossier,)

    def get(self, dossier_id, *, refresh=False):
        assert isinstance(refresh, bool)
        return sample_dossier() if dossier_id == "DLR1" else None


class FailingLegislationService:
    def search(self, *args, **kwargs):
        raise LegislationError("simulated legislative source failure")

    def get(self, *args, **kwargs):
        raise LegislationError("simulated legislative source failure")


class FakeAnswerService:
    def __init__(self):
        self.last_question = None

    @staticmethod
    def _answer() -> GroundedAnswer:
        return GroundedAnswer(
            status="answered",
            answer="Réponse sourcée.",
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
            research=(),
        )

    def ask(self, question: str) -> GroundedAnswer:
        assert question
        self.last_question = question
        return self._answer()

    def iter_ask(self, question: str):
        assert question
        self.last_question = question
        yield AgentEvent("started", {"message": "Préparation"})
        yield AgentEvent("answer", {}, answer=self._answer())


def make_app(answer_service=None, legislation_service=None):
    return create_app(
        FakeMacroService(),
        answer_service,
        cofog_service=FakeCofogService(),
        legislation_service=legislation_service or FakeLegislationService(),
    )


def test_home_is_now_civic_legislation_search() -> None:
    client = make_app(FakeAnswerService()).test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Comprendre ce que décide réellement la puissance publique" in html
    assert "Projet de loi relatif au logement" in html
    assert "Textes & décisions" in html
    assert 'href="/finances"' in html


def test_natural_search_query_is_forwarded_to_legislation_service() -> None:
    client = make_app(FakeAnswerService()).test_client()

    response = client.get("/?q=Quels+textes+concernent+la+sant%C3%A9+%3F")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Aucun dossier correspondant" in html


def test_legislative_dossier_page_has_dedicated_chat() -> None:
    client = make_app(FakeAnswerService()).test_client()

    response = client.get("/textes/DLR1")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Projet de loi relatif au logement" in html
    assert "Chat dédié à ce texte" in html
    assert 'data-dossier-id="DLR1"' in html
    assert "Examen en commission" in html


def test_scoped_chat_adds_server_side_dossier_context() -> None:
    answer_service = FakeAnswerService()
    client = make_app(answer_service).test_client()

    response = client.post(
        "/api/ask",
        json={
            "question": "Qu'est-ce qui change ?",
            "dossier_id": "DLR1",
            "history": [{"role": "user", "content": "Résume-le-moi."}],
        },
    )

    assert response.status_code == 200
    assert answer_service.last_question is not None
    assert "Projet de loi relatif au logement" in answer_service.last_question
    assert "DLR1" in answer_service.last_question
    assert "Résume-le-moi" in answer_service.last_question
    assert "ne constitue pas une preuve" in answer_service.last_question


def test_legislation_api_returns_structured_results() -> None:
    client = make_app().test_client()

    response = client.get("/api/legislation?q=logement")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["results"][0]["id"] == "DLR1"
    assert payload["results"][0]["status"] == "active"


def test_finance_dashboard_remains_available_as_subtool() -> None:
    client = make_app(FakeAnswerService()).test_client()

    response = client.get("/finances")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Vingt-cinq ans de finances publiques" in html
    assert "57.3" in html
    assert "Enseignement" in html
    assert 'id="functions"' in html


def test_macro_api_returns_same_analysis() -> None:
    client = make_app().test_client()
    response = client.get("/api/macro")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["dataset_code"] == "gov_10a_main + gov_10dd_edpt1"
    assert payload["series"]["expenditure"]["values"][-1] == {"year": 2025, "value": 57.3}


def test_cofog_api_returns_functional_breakdown() -> None:
    client = make_app().test_client()
    response = client.get("/api/cofog")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["dataset_code"] == "gov_10a_exp"
    assert len(payload["changes"]) == 10


def test_evidence_api_exposes_live_allowlist_without_document_corpus() -> None:
    client = make_app().test_client()
    response = client.get("/api/evidence")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["mode"] == "live_official_research"
    assert payload["persistent_document_corpus"] is False
    assert any(source["id"] == "legifrance" for source in payload["sources"])


def test_stream_api_emits_progress_then_answer_as_ndjson() -> None:
    client = make_app(FakeAnswerService()).test_client()
    response = client.post("/api/ask/stream", json={"question": "Où chercher ?"})
    lines = [json.loads(line) for line in response.get_data(as_text=True).splitlines()]

    assert response.status_code == 200
    assert response.mimetype == "application/x-ndjson"
    assert [item["type"] for item in lines] == ["started", "answer"]


def test_legislation_source_failure_is_explicit() -> None:
    app = create_app(
        FakeMacroService(),
        cofog_service=FakeCofogService(),
        legislation_service=FailingLegislationService(),
    )
    response = app.test_client().get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 503
    assert "Impossible de charger les dossiers législatifs" in html
    assert "simulated legislative source failure" in html


def test_sources_remain_available_when_macro_loading_fails() -> None:
    app = create_app(
        FailingMacroService(),
        cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(),
    )
    response = app.test_client().get("/finances")
    html = response.get_data(as_text=True)

    assert response.status_code == 503
    assert 'id="sources"' in html
    assert "gov_10a_main" in html


def test_dashboard_survives_cofog_failure() -> None:
    app = create_app(
        FakeMacroService(),
        cofog_service=FailingCofogService(),
        legislation_service=FakeLegislationService(),
    )
    response = app.test_client().get("/finances")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Décomposition COFOG indisponible" in html


def test_health_endpoint_reports_primary_civic_experience() -> None:
    client = make_app().test_client()
    payload = client.get("/healthz").get_json()

    assert payload["status"] == "ok"
    assert payload["research_mode"] == "live_official_sources"
    assert payload["primary_experience"] == "civic_legislation"

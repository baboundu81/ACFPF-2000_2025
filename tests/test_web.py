# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

from acfpf.ai.service import AgentEvent, Citation, GroundedAnswer
from acfpf.cofog import build_cofog_analysis
from acfpf.data.cofog import parse_cofog_payload
from acfpf.data.eurostat import EurostatError
from acfpf.legislation import (
    LegislationError,
    LegislativeDossier,
    LegislativeEvent,
    LegislativeSourceRef,
)
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
        current_stage="Première lecture au Sénat",
        current_chamber="Sénat",
        last_activity="2026-11-02",
        initial_date="2026-10-20",
        official_url="https://www.assemblee-nationale.fr/dyn/17/dossiers/logement",
        source_url="https://data.assemblee-nationale.fr/travaux-parlementaires/dossiers-legislatifs",
        events=(
            LegislativeEvent(
                "2026-10-20",
                "Dépôt à l'Assemblée nationale",
                chamber="Assemblée nationale",
                source_id="assemblee_nationale_open_data",
            ),
            LegislativeEvent(
                "2026-11-02",
                "Première lecture au Sénat",
                chamber="Sénat",
                source_id="assemblee_nationale_open_data",
            ),
        ),
        sources=(
            LegislativeSourceRef(
                source_id="assemblee_nationale_open_data",
                label="Assemblée nationale",
                chamber="Assemblée nationale",
                official_url="https://www.assemblee-nationale.fr/dyn/17/dossiers/logement",
            ),
            LegislativeSourceRef(
                source_id="senat_open_data",
                label="Sénat",
                chamber="Sénat",
                official_url="https://www.senat.fr/dossier-legislatif/pjl25-913.html",
                state="Première lecture au Sénat",
            ),
        ),
        themes=("Logement et urbanisme",),
    )


class FakeLegislationService:
    def _all(self, *, refresh=False):
        assert isinstance(refresh, bool)
        return (sample_dossier(),)

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


class PartialLegislationService(FakeLegislationService):
    def warnings(self):
        return ("Sénat : source temporairement indisponible",)


class FailingLegislationService:
    def _all(self, *, refresh=False):
        raise LegislationError("simulated legislative source failure")

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
    assert "Séance / lecture" in html
    assert "Libellé source : Première lecture au Sénat" in html
    assert "Textes & décisions" in html
    assert "Assemblée nationale + Sénat" in html
    assert "Ordre des résultats : pertinence lexicale" in html
    assert 'href="/finances"' in html


def test_natural_search_query_is_forwarded_to_legislation_service() -> None:
    client = make_app(FakeAnswerService()).test_client()

    response = client.get("/?q=Quels+textes+concernent+la+sant%C3%A9+%3F")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Aucun dossier correspondant" in html


def test_home_combines_structured_legislative_filters() -> None:
    client = make_app().test_client()

    response = client.get(
        "/?status=all&chamber=S%C3%A9nat&stage=plenary&theme=Logement+et+urbanisme"
        "&text_type=Projet+de+loi&from_year=2026&to_year=2026"
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Projet de loi relatif au logement" in html
    assert 'option value="Sénat" selected' in html
    assert 'option value="plenary" selected' in html
    assert 'option value="Logement et urbanisme" selected' in html
    assert 'option value="Projet de loi" selected' in html
    assert 'value="2026"' in html


def test_home_rejects_inverted_legislative_period() -> None:
    client = make_app().test_client()

    response = client.get("/?status=all&from_year=2026&to_year=2025")
    html = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "année de début ne peut pas être postérieure" in html


def test_legislative_dossier_page_has_dedicated_chat_and_both_chambers() -> None:
    client = make_app(FakeAnswerService()).test_client()

    response = client.get("/textes/DLR1")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Projet de loi relatif au logement" in html
    assert "Chat dédié à ce texte" in html
    assert 'data-dossier-id="DLR1"' in html
    assert "Séance / lecture" in html
    assert "Libellé source de l'étape : Première lecture au Sénat" in html
    assert "Ouvrir le dossier Assemblée nationale" in html
    assert "Ouvrir le dossier Sénat" in html
    assert "Logement et urbanisme" in html
    assert "document HTML officiel individuellement" in html
    assert "ne garantit ni la structure des articles" in html
    assert 'js/versions.js' in html
    assert 'data-votes-dossier-id="DLR1"' in html
    assert 'js/votes.js' in html
    assert "Scrutins publics" in html
    assert "Rapports parlementaires" in html
    assert 'data-reports-dossier-id="DLR1"' in html
    assert "js/reports.js" in html
    assert "ni l&#39;adoption définitive" in html or "ni l\'adoption définitive" in html
    assert "Les positions nominatives sont accessibles" in html
    assert "annuaire historique de l\u0027Assemblée" in html
    assert "ne signifie" in html


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
    assert "Séance / lecture (plenary)" in answer_service.last_question
    assert "Première lecture au Sénat" in answer_service.last_question
    assert "assemblee-nationale.fr" in answer_service.last_question
    assert "senat.fr" in answer_service.last_question


def test_legislation_api_returns_structured_results_facets_and_filters() -> None:
    client = make_app().test_client()

    response = client.get(
        "/api/legislation?q=logement&status=all&chamber=S%C3%A9nat&stage=plenary"
        "&theme=Logement+et+urbanisme&text_type=Projet+de+loi&from_year=2026&to_year=2026"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["results"][0]["id"] == "DLR1"
    assert payload["results"][0]["status"] == "active"
    assert payload["results"][0]["stage"] == "plenary"
    assert payload["results"][0]["stage_label"] == "Séance / lecture"
    assert payload["results"][0]["current_stage"] == "Première lecture au Sénat"
    assert payload["results"][0]["current_chamber"] == "Sénat"
    assert payload["filters"] == {
        "chamber": "Sénat",
        "stage": "plenary",
        "theme": "Logement et urbanisme",
        "text_type": "Projet de loi",
        "from_year": 2026,
        "to_year": 2026,
    }
    assert payload["facets"] == {
        "chambers": ["Sénat"],
        "stages": [{"code": "plenary", "label": "Séance / lecture"}],
        "themes": ["Logement et urbanisme"],
        "text_types": ["Projet de loi"],
        "min_year": 2026,
        "max_year": 2026,
    }
    assert {source["name"] for source in payload["sources"]} == {
        "Assemblée nationale",
        "Sénat",
    }
    assert {source["source_id"] for source in payload["results"][0]["sources"]} == {
        "assemblee_nationale_open_data",
        "senat_open_data",
    }


def test_legislation_dossier_api_enriches_timeline_events_with_stage() -> None:
    client = make_app().test_client()

    response = client.get("/api/legislation/DLR1")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["stage"] == "plenary"
    assert payload["current_stage"] == "Première lecture au Sénat"
    assert payload["events"][0]["stage"] == "deposit"
    assert payload["events"][1]["stage"] == "plenary"


def test_legislation_api_rejects_invalid_year_filter() -> None:
    client = make_app().test_client()

    response = client.get("/api/legislation?from_year=pas-une-annee")
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["error"] == "invalid_filter"
    assert "année entière" in payload["message"]


def test_legislation_api_rejects_inverted_period() -> None:
    client = make_app().test_client()

    response = client.get("/api/legislation?from_year=2026&to_year=2025")
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["error"] == "invalid_filter"
    assert "année de début" in payload["message"]


def test_partial_legislation_source_is_visible_but_does_not_break_results() -> None:
    client = make_app(legislation_service=PartialLegislationService()).test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Projet de loi relatif au logement" in html
    assert "Vue partielle" in html
    assert "source temporairement indisponible" in html

    payload = client.get("/api/legislation").get_json()
    assert payload["warnings"] == ["Sénat : source temporairement indisponible"]


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
    assert "Impossible d'afficher les dossiers législatifs" in html
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

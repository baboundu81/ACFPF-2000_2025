# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from acfpf.ai.legislation_query import LegislativeQueryPlan
from acfpf.ai.provider import AIGroundingError
from acfpf.web import create_app
from tests.test_legislation_browse import sample_inventory
from tests.test_web import FakeAnswerService, FakeCofogService, FakeMacroService


class FakePlanner:
    def __init__(self, plan: LegislativeQueryPlan | None = None, error: Exception | None = None):
        self.plan_result = plan
        self.error = error
        self.calls = []

    def plan(self, query, facets):
        self.calls.append((query, facets))
        if self.error is not None:
            raise self.error
        assert self.plan_result is not None
        return self.plan_result


def make_assisted_app(planner):
    return create_app(
        FakeMacroService(),
        FakeAnswerService(),
        cofog_service=FakeCofogService(),
        legislation_service=sample_inventory(),
        legislation_query_planner=planner,
    )


def test_home_uses_planner_for_vague_query_and_explains_interpretation() -> None:
    planner = FakePlanner(
        LegislativeQueryPlan(
            query="",
            status="all",
            theme="Santé",
        )
    )
    client = make_assisted_app(planner).test_client()

    response = client.get("/?q=le+truc+sur+les+soins")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Projet de loi relatif à la santé" in html
    assert "Recherche interprétée" in html
    assert "Aucun mot-clé libre n'a été nécessaire" in html
    assert 'option value="Santé" selected' in html


def test_home_explicit_filter_overrides_planner_suggestion() -> None:
    planner = FakePlanner(
        LegislativeQueryPlan(
            query="",
            status="all",
            theme="Santé",
        )
    )
    client = make_assisted_app(planner).test_client()

    response = client.get(
        "/?q=montre+moi+ce+texte&status=all&theme=%C3%89ducation"
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Proposition de loi relative à l'école" in html
    assert "Projet de loi relatif à la santé" not in html
    assert 'option value="Éducation" selected' in html


def test_home_planner_failure_falls_back_without_5xx() -> None:
    planner = FakePlanner(error=AIGroundingError("réponse hors schéma"))
    client = make_assisted_app(planner).test_client()

    response = client.get(
        "/?q=Quels+textes+concernent+la+sant%C3%A9+%3F&status=all"
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Projet de loi relatif à la santé" in html
    assert "Interprétation assistée indisponible" in html
    assert "recherche déterministe" in html


def test_assist_zero_skips_planner_and_keeps_deterministic_results() -> None:
    planner = FakePlanner(LegislativeQueryPlan(query="logement", status="all"))
    client = make_assisted_app(planner).test_client()

    response = client.get(
        "/?q=Quels+textes+concernent+la+sant%C3%A9+%3F&status=all&assist=0"
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert planner.calls == []
    assert "Projet de loi relatif à la santé" in html
    assert 'option value="0" selected' in html


def test_legislation_api_exposes_assistance_metadata() -> None:
    planner = FakePlanner(
        LegislativeQueryPlan(
            query="santé",
            status="active",
            theme="Santé",
        )
    )
    client = make_assisted_app(planner).test_client()

    response = client.get("/api/legislation?q=le+truc+sur+les+soins")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["assistance"]["planner_used"] is True
    assert payload["assistance"]["original_query"] == "le truc sur les soins"
    assert payload["assistance"]["effective_query"] == "santé"
    assert payload["filters"]["theme"] == "Santé"
    assert [item["id"] for item in payload["results"]] == ["D1"]


def test_legislation_api_explicit_filter_overrides_planner() -> None:
    planner = FakePlanner(
        LegislativeQueryPlan(
            query="",
            status="all",
            theme="Santé",
        )
    )
    client = make_assisted_app(planner).test_client()

    response = client.get(
        "/api/legislation?q=un+texte&status=all&theme=%C3%89ducation"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["filters"]["theme"] == "Éducation"
    assert [item["id"] for item in payload["results"]] == ["D2"]

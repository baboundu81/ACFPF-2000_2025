# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

import pytest

from acfpf.ai.legislation_query import (
    LEGISLATIVE_QUERY_PLAN_SCHEMA,
    LegislativeQueryPlanner,
)
from acfpf.ai.provider import AIGroundingError, ProviderRequest
from acfpf.legislation_browse import LegislativeFacets
from acfpf.legislative_stages import LegislativeStage


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, response: dict) -> None:
        self.response = response
        self.request: ProviderRequest | None = None

    def complete_json(self, request: ProviderRequest) -> dict:
        self.request = request
        return self.response


def facets() -> LegislativeFacets:
    return LegislativeFacets(
        chambers=("Assemblée nationale", "Sénat"),
        stages=(
            LegislativeStage("committee", "Commission"),
            LegislativeStage("plenary", "Séance / lecture"),
        ),
        themes=("Santé", "Travail"),
        text_types=("Projet de loi", "Proposition de loi"),
        min_year=2024,
        max_year=2026,
    )


def valid_response(**overrides) -> dict:
    payload = {
        "query": "carence maladie",
        "status": "active",
        "chamber": "",
        "stage": "",
        "theme": "Travail",
        "text_type": "",
        "from_year": 0,
        "to_year": 0,
    }
    payload.update(overrides)
    return payload


def test_planner_returns_only_validated_retrieval_criteria() -> None:
    provider = FakeProvider(valid_response())
    planner = LegislativeQueryPlanner(provider)

    plan = planner.plan("le truc sur les jours de carence", facets())

    assert plan.query == "carence maladie"
    assert plan.status == "active"
    assert plan.theme == "Travail"
    assert plan.chamber is None
    assert provider.request is not None
    assert provider.request.response_schema == LEGISLATIVE_QUERY_PLAN_SCHEMA
    assert provider.request.response_schema_name == "acfpf_legislative_query_plan"

    state = json.loads(provider.request.user_prompt)
    assert state["USER_QUERY"] == "le truc sur les jours de carence"
    assert state["AVAILABLE_FILTERS"]["themes"] == ["Santé", "Travail"]
    serialized = json.dumps(state, ensure_ascii=False).lower()
    assert "dossier_id" not in serialized
    assert "official_url" not in serialized


def test_planner_schema_has_no_candidate_identity_or_url_fields() -> None:
    properties = set(LEGISLATIVE_QUERY_PLAN_SCHEMA["properties"])

    assert properties == {
        "query",
        "status",
        "chamber",
        "stage",
        "theme",
        "text_type",
        "from_year",
        "to_year",
    }
    assert not properties.intersection({"url", "id", "title", "candidates", "dossiers"})
    assert LEGISLATIVE_QUERY_PLAN_SCHEMA["additionalProperties"] is False


def test_planner_rejects_invented_facet_value() -> None:
    planner = LegislativeQueryPlanner(FakeProvider(valid_response(theme="Défense inventée")))

    with pytest.raises(AIGroundingError, match="inventé"):
        planner.plan("un texte vague", facets())


def test_planner_rejects_extra_candidate_field_even_if_provider_returns_it() -> None:
    response = valid_response()
    response["url"] = "https://example.test/invented"
    planner = LegislativeQueryPlanner(FakeProvider(response))

    with pytest.raises(AIGroundingError, match="champs de recherche non autorisés"):
        planner.plan("un texte vague", facets())


def test_planner_rejects_year_outside_loaded_inventory() -> None:
    planner = LegislativeQueryPlanner(FakeProvider(valid_response(from_year=2020)))

    with pytest.raises(AIGroundingError, match="année hors"):
        planner.plan("un vieux texte", facets())


def test_planner_rejects_inverted_period() -> None:
    planner = LegislativeQueryPlanner(FakeProvider(valid_response(from_year=2026, to_year=2025)))

    with pytest.raises(AIGroundingError, match="période inversée"):
        planner.plan("un texte entre deux dates", facets())

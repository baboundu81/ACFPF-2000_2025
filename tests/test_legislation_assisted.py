# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from acfpf.ai.legislation_query import LegislativeQueryPlan
from acfpf.ai.provider import AIGroundingError
from acfpf.legislation_assisted import assisted_browse_legislation
from tests.test_legislation_browse import sample_inventory


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


def test_assisted_search_turns_vague_phrase_into_deterministic_inventory_query() -> None:
    planner = FakePlanner(
        LegislativeQueryPlan(
            query="santé",
            status="active",
            theme="Santé",
        )
    )

    result = assisted_browse_legislation(
        sample_inventory(),
        "le truc dont on parle sur les soins",
        planner=planner,
    )

    assert result.planner_used is True
    assert result.original_query == "le truc dont on parle sur les soins"
    assert result.effective_query == "santé"
    assert result.effective_filters["theme"] == "Santé"
    assert [item.id for item in result.browse.results] == ["D1"]
    assert planner.calls[0][1].themes == ("Éducation", "Logement", "Santé")


def test_explicit_user_filter_overrides_planner_suggestion() -> None:
    planner = FakePlanner(
        LegislativeQueryPlan(
            query="",
            status="all",
            theme="Santé",
        )
    )

    result = assisted_browse_legislation(
        sample_inventory(),
        "montre moi un texte",
        planner=planner,
        status="all",
        theme="Éducation",
    )

    assert result.effective_filters["theme"] == "Éducation"
    assert [item.id for item in result.browse.results] == ["D2"]


def test_explicit_status_overrides_planner_status() -> None:
    planner = FakePlanner(
        LegislativeQueryPlan(
            query="logement",
            status="active",
        )
    )

    result = assisted_browse_legislation(
        sample_inventory(),
        "le texte sur le logement",
        planner=planner,
        status="promulgated",
    )

    assert result.effective_status == "promulgated"
    assert [item.id for item in result.browse.results] == ["D3"]


def test_missing_planner_keeps_existing_deterministic_search() -> None:
    result = assisted_browse_legislation(
        sample_inventory(),
        "Quels textes concernent la santé ?",
        planner=None,
        status="all",
    )

    assert result.planner_used is False
    assert result.interpreted_plan is None
    assert result.planner_warning is None
    assert [item.id for item in result.browse.results] == ["D1"]


def test_planner_failure_is_non_fatal_and_falls_back_to_original_query() -> None:
    planner = FakePlanner(error=AIGroundingError("réponse hors schéma"))

    result = assisted_browse_legislation(
        sample_inventory(),
        "Quels textes concernent la santé ?",
        planner=planner,
        status="all",
    )

    assert result.planner_used is False
    assert result.interpreted_plan is None
    assert result.effective_query == "Quels textes concernent la santé ?"
    assert "recherche déterministe" in (result.planner_warning or "")
    assert [item.id for item in result.browse.results] == ["D1"]


def test_assist_can_be_disabled_explicitly() -> None:
    planner = FakePlanner(LegislativeQueryPlan(query="logement", status="all"))

    result = assisted_browse_legislation(
        sample_inventory(),
        "santé",
        planner=planner,
        assist=False,
        status="all",
    )

    assert planner.calls == []
    assert result.planner_used is False
    assert [item.id for item in result.browse.results] == ["D1"]

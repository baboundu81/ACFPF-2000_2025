# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Promulgation dates and constitutional decisions are not normative legal text."""

from dataclasses import replace

from acfpf.legislation import LegislativeEvent
from acfpf.legislative_outcomes import official_outcomes
from acfpf.web import create_app
from tests.test_web import (
    FakeCofogService,
    FakeLegislationService,
    FakeMacroService,
    sample_dossier,
)


def test_only_senate_issued_explicit_events_count_as_verified_outcomes():
    dossier = replace(
        sample_dossier(), law_number="2026-1015",
        events=(
            LegislativeEvent(
                "2026-11-01", "Décision du Conseil constitutionnel : conforme",
                code="CONSTITUTIONAL_COUNCIL", source_id="senat_open_data",
            ),
            LegislativeEvent(
                "2026-11-02", "Promulgation — loi n° 2026-1015",
                code="PROMULGATION", source_id="senat_open_data",
            ),
            LegislativeEvent(
                "2026-11-02", "Promulgation — loi n° 2026-1015",
                code="PROMULGATION", source_id="senat_open_data",
            ),
            LegislativeEvent(
                "2026-11-03", "Promulgation supposée",
                code="PROMULGATION", source_id="unverified_source",
            ),
        ),
    )
    result = official_outcomes(dossier)
    assert result["promulgation_recorded"] is True
    assert result["law_number"] == "2026-1015"
    assert [item["kind"] for item in result["events"]] == [
        "constitutional_review", "promulgation",
    ]
    assert result["legifrance_text_verified"] is False
    assert result["constitutional_decision_text_verified"] is False
    assert result["events"][0]["source_url"].startswith("https://www.senat.fr/")


def test_no_promulgation_event_never_claims_a_promulgated_legal_text():
    result = official_outcomes(replace(sample_dossier(), law_number="2026-1015"))
    assert result["events"] == []
    assert result["law_number"] is None
    assert result["promulgation_recorded"] is False


def test_suspicious_law_number_not_exposed():
    dossier = replace(sample_dossier(), law_number="https://other.test/",
        events=(LegislativeEvent(
            "2026-11-02", "Promulgation", code="PROMULGATION",
            source_id="senat_open_data",
        ),),
    )
    assert official_outcomes(dossier)["law_number"] is None


def test_outcome_api_and_dossier_page_disclose_only_official_milestones():
    app = create_app(
        service=FakeMacroService(), cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(),
    )
    client = app.test_client()
    assert client.get("/api/legislation/UNKNOWN/outcomes").status_code == 404
    response = client.get("/api/legislation/DLR1/outcomes")
    assert response.status_code == 200
    assert response.get_json()["legifrance_text_verified"] is False
    html = client.get("/textes/DLR1").get_data(as_text=True)
    assert "Décisions et entrée en vigueur" in html
    assert "Aucun lien vers un texte de loi" in html

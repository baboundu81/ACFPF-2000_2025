# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Debate references never imply a particular transcript or speaker."""

from dataclasses import replace

from acfpf.legislation import LegislativeEvent
from acfpf.legislative_debates import debate_references
from acfpf.web import create_app
from tests.test_web import (
    FakeCofogService,
    FakeLegislationService,
    FakeMacroService,
    sample_dossier,
)


def test_exact_assembly_plenary_stages_only():
    dossier = sample_dossier()
    events = (
        LegislativeEvent(
            "2026-10-20", "Première lecture en séance",
            code="AN1-DEBATS", chamber="Assemblée nationale",
            source_id="assemblee_nationale_open_data",
        ),
        LegislativeEvent(
            "2026-10-20", "Première lecture en séance",
            code="AN1-DEBATS", chamber="Assemblée nationale",
            source_id="assemblee_nationale_open_data",
        ),
        LegislativeEvent(
            "2026-10-21", "Travaux de commission", code="AN1-COM",
            chamber="Assemblée nationale", source_id="assemblee_nationale_open_data",
        ),
        LegislativeEvent(
            "2026-10-22", "Lecture au Sénat", code="SN1-DEBATS",
            chamber="Sénat", source_id="assemblee_nationale_open_data",
        ),
        LegislativeEvent(
            "2026-10-23", "Première lecture en séance",
            code="AN1-DEBATS", chamber="Assemblée nationale",
            source_id="unverified_source",
        ),
    )
    result = debate_references(replace(dossier, events=events))
    assert result["count"] == 1
    first = result["references"][0]
    assert first["date"] == "2026-10-20"
    assert first["transcript_verified"] is False
    assert "Etape officielle" in first["linkage"]
    assert "aucun" in result["limitation"].lower()


def test_dossier_endpoint_does_not_fabricate_debates():
    app = create_app(
        service=FakeMacroService(), cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(),
    )
    client = app.test_client()
    assert client.get("/api/legislation/UNKNOWN/debates").status_code == 404
    response = client.get("/api/legislation/DLR1/debates")
    assert response.status_code == 200
    result = response.get_json()
    assert result["dossier_id"] == "DLR1"
    assert result["count"] == 0
    assert result["transcripts_available"] is False


def test_dossier_html_offers_official_search_portal_with_limits():
    app = create_app(
        service=FakeMacroService(), cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(),
    )
    html = app.test_client().get("/textes/DLR1").get_data(as_text=True)
    assert "Débats et séances" in html
    assert "Une étape de lecture n&#39;est pas un compte rendu" in html or "Une étape de lecture n'est pas un compte rendu" in html
    assert "comptes-rendus/seance" in html

# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Public-action coverage does not fabricate legal, financial or impact links."""

from dataclasses import replace

from acfpf.legislation import LegislativeEvent
from acfpf.public_action import STAGES, public_action_coverage
from acfpf.web import create_app
from tests.test_web import (
    FakeCofogService,
    FakeLegislationService,
    FakeMacroService,
    sample_dossier,
)


def test_public_action_stages_remain_explicitly_unverified_without_sources():
    dossier = sample_dossier()
    result = public_action_coverage(dossier)
    assert result["dossier_id"] == "DLR1"
    assert [item["code"] for item in result["stages"]] == [code for code, _ in STAGES]
    known = [item["code"] for item in result["stages"] if item["coverage"] == "metadata_only"]
    assert known == ["proposal", "parliamentary_process"]
    assert all(item["coverage"] == "unverified" for item in result["stages"][4:])
    assert not result["budget_links_verified"]
    assert not result["evaluation_links_verified"]
    assert not result["applicable_law_verified"]
    assert all(not item["normative_text_verified"] for item in result["evidence"])


def test_only_documented_senate_milestones_get_promulgation_or_review_status():
    dossier = replace(sample_dossier(), events=(
        LegislativeEvent(
            "2026-11-03", "Décision du Conseil constitutionnel",
            code="CONSTITUTIONAL_COUNCIL", source_id="senat_open_data",
        ),
        LegislativeEvent(
            "2026-11-05", "Promulgation",
            code="PROMULGATION", source_id="senat_open_data",
        ),
        LegislativeEvent(
            "2026-11-05", "Promulgation", code="PROMULGATION",
            source_id="senat_open_data",
        ),
        LegislativeEvent(
            "2026-11-06", "Promulgation non sourcée",
            code="PROMULGATION", source_id="untrusted_party",
        ),
    ))
    result = public_action_coverage(dossier)
    stages = {item["code"]: item for item in result["stages"]}
    assert stages["constitutional_review"]["evidence_count"] == 1
    assert stages["promulgation"]["evidence_count"] == 1
    assert stages["applicable_law"]["coverage"] == "unverified"
    assert stages["budget_authorization"]["coverage"] == "unverified"
    assert len(result["evidence"]) == 2  # deux événements Sénat vérifiés
    assert "untrusted_party" not in {item["source_id"] for item in result["evidence"]}


def test_unknown_source_does_not_make_public_action_coverage_look_complete():
    dossier = replace(
        sample_dossier(), source_id="untrusted_party", sources=(), initial_date="2026-01-01",
        events=(LegislativeEvent("2026-11-06", "Prétendue promulgation",
                                 code="PROMULGATION", source_id="untrusted_party"),),
    )
    result = public_action_coverage(dossier)
    assert result["evidence"] == []
    assert all(stage["coverage"] == "unverified" for stage in result["stages"])


def test_public_action_api_and_honest_dossier_display():
    app = create_app(
        service=FakeMacroService(), cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(),
    )
    client = app.test_client()
    assert client.get("/api/legislation/UNKNOWN/public-action").status_code == 404
    response = client.get("/api/legislation/DLR1/public-action")
    assert response.status_code == 200
    assert response.get_json()["budget_links_verified"] is False
    html = client.get("/textes/DLR1").get_data(as_text=True)
    assert "De la loi à l&#39;action publique" in html or "De la loi à l'action publique" in html
    assert "Aucune preuve structurée directement reliée" in html
    assert "Aucun lien loi" in html

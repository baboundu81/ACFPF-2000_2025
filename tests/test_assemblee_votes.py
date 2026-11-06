# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Regression tests: only exact official dossier references can link votes."""

import json
import zipfile
from io import BytesIO

from acfpf.data.assemblee_votes import Vote, parse_votes_archive
from acfpf.web import create_app
from tests.test_web import FakeCofogService, FakeLegislationService, FakeMacroService


def _archive(*scrutins):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for i, record in enumerate(scrutins):
            z.writestr(f"scrutin_{i}.json", json.dumps({"scrutin": record}))
    return buffer.getvalue()


def _scrutin(uid, ref, number):
    return {
        "uid": uid,
        "numero": number,
        "seanceRef": "RUANR5L17S2027IDS30918",
        "dateScrutin": "2026-10-15",
        "titre": "Vote de contrôle",
        "objet": {"dossierLegislatif": {"dossierRef": ref}},
        "sort": {"libelle": "Adopté"},
        "syntheseVote": {"decompte": {"pour": "12", "contre": "5", "abstentions": "1"}},
    }


def test_exact_reference_required_not_merely_text_occurrence():
    archive = _archive(
        _scrutin("VT1", "DLR123456", 1),
        _scrutin("VT2", "DLR999999", 2),
        {**_scrutin("VT3", "DLR999999", 3), "titre": "DLR123456 mentioned in title"},
    )
    votes = parse_votes_archive(archive, dossier_uid="DLR123456")
    assert len(votes) == 1
    assert votes[0].uid == "VT1"
    assert votes[0].pour == 12
    assert votes[0].seance_ref == "RUANR5L17S2027IDS30918"
    assert votes[0].as_dict()["seance_ref"] == votes[0].seance_ref
    assert votes[0].as_dict()["linked_by"] == "objet.dossierLegislatif.dossierRef"


def test_vote_api_does_not_invent_votes_for_unknown_dossier():
    app = create_app(
        service=FakeMacroService(),
        cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(),
        vote_loader=lambda **kwargs: (),
    )
    client = app.test_client()
    assert client.get("/api/legislation/UNKNOWN/votes").status_code == 404


def test_vote_api_paginates_and_reports_exact_linkage():
    app = create_app(
        service=FakeMacroService(),
        cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(),
        vote_loader=lambda **kwargs: tuple(
            Vote(uid=f"VT{i}", number=str(i), date="2026-10-15",
                 title="Scrutin public", result="Adopté", pour=12, contre=5,
                 abstentions=1, dossier_id="DLR1") for i in (1, 2)
        ),
    )
    response = app.test_client().get("/api/legislation/DLR1/votes?limit=1&offset=1")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 2
    assert len(payload["votes"]) == 1
    assert payload["votes"][0]["number"] == "2"
    assert "exact" in payload["linkage"]

# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json
import zipfile
from io import BytesIO

import pytest

from acfpf.legislative_versions import (
    TextVersionsError,
    TextVersionService,
    parse_assembly_text_versions,
)
from tests.test_legislation_detail import assembly_dossier, senate_only_dossier


def official_archive() -> bytes:
    dossier = {
        "dossierParlementaire": {
            "uid": "DLR5L17N54629",
            "actesLegislatifs": {
                "acteLegislatif": {
                    "codeActe": "AN1",
                    "libelleActe": {"libelleCourt": "1ère lecture"},
                    "actesLegislatifs": {
                        "acteLegislatif": [
                            {
                                "codeActe": "AN1-DEPOT",
                                "libelleActe": {"libelleCourt": "Dépôt initial"},
                                "dateActe": "2026-10-01T00:00:00.000+02:00",
                                "texteAssocie": "PRJLANR5L17B3210",
                            },
                            {
                                "codeActe": "AN1-COM",
                                "libelleActe": {"nomCanonique": "Texte de commission"},
                                "dateActe": "2026-10-20T00:00:00.000+02:00",
                                "texteAssocie": "TANR5L17B0042",
                            },
                        ]
                    },
                }
            },
        }
    }
    notice = {
        "document": {
            "uid": "PRJLANR5L17B3210",
            "titres": {"titrePrincipal": "Projet de loi de finances pour 2027"},
            "provenance": "Texte Déposé",
            "classification": {"type": {"code": "PRJL", "libelle": "Projet de loi"}},
            "cycleDeVie": {
                "chrono": {"datePublicationWeb": "2026-10-01T18:50:00.000+02:00"}
            },
        }
    }
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            "json/dossierParlementaire/DLR5L17N54629.json",
            json.dumps(dossier, ensure_ascii=False),
        )
        archive.writestr(
            "json/document/PRJLANR5L17B3210.json",
            json.dumps(notice, ensure_ascii=False),
        )
    return stream.getvalue()


def test_extracts_official_document_versions_without_fabricating_direct_url() -> None:
    collection = parse_assembly_text_versions(
        official_archive(),
        dossier_uid="DLR5L17N54629",
        dossier_url="https://www.assemblee-nationale.fr/dyn/17/dossiers/PLF_2027",
    )
    assert collection.available is True
    assert collection.dossier_id == "DLR5L17N54629"
    assert len(collection.versions) == 2
    initial, committee = collection.versions
    assert initial.uid == "PRJLANR5L17B3210"
    assert initial.title == "Projet de loi de finances pour 2027"
    assert initial.kind == "Projet de loi"
    assert initial.provenance == "Texte Déposé"
    assert initial.stage_label == "Dépôt initial"
    assert initial.stage_date == "2026-10-01"
    assert initial.publication_date == "2026-10-01"
    assert initial.as_dict()["full_text_available"] is False
    assert "official_url" not in initial.as_dict()
    assert committee.uid == "TANR5L17B0042"
    assert committee.notice_available is False


def test_refuses_malformed_dossier_uid() -> None:
    with pytest.raises(TextVersionsError, match="Invalid official dossier"):
        parse_assembly_text_versions(
            official_archive(),
            dossier_uid="../secrets",
            dossier_url="https://example.test",
        )


def test_refuses_identity_mismatch() -> None:
    with pytest.raises(TextVersionsError, match="not found"):
        parse_assembly_text_versions(
            official_archive(),
            dossier_uid="DLR5L17N99999",
            dossier_url="https://example.test",
        )


def test_service_uses_official_archive_and_rejects_senate_only(tmp_path) -> None:
    calls = []

    def loader(*, cache_path, refresh):
        calls.append(refresh)
        cache_path.write_bytes(official_archive())
        return ()

    service = TextVersionService(cache_path=tmp_path / "dossiers.zip", loader=loader)
    collection = service.for_dossier(assembly_dossier())
    assert calls == [False]
    assert len(collection.versions) == 2

    missing = service.for_dossier(senate_only_dossier())
    assert missing.available is False
    assert missing.versions == ()
    assert calls == [False]

# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import io
import json
import zipfile
from pathlib import Path

from acfpf.data.assemblee_legislation import parse_assembly_archive
from acfpf.legislation import LegislationService


def _payload(uid: str, title: str, *, final: bool = False):
    acts = [
        {
            "codeActe": "DEPOT",
            "libelleActe": "Dépôt à l'Assemblée nationale",
            "dateActe": "2026-10-01",
        },
        {
            "codeActe": "COM",
            "libelleActe": "Examen en commission",
            "dateActe": "2026-10-20",
        },
    ]
    if final:
        acts.append(
            {
                "codeActe": "PROM",
                "libelleActe": "Promulgation de la loi",
                "dateActe": "2026-10-30",
            }
        )
    return {
        "dossierParlementaire": {
            "uid": uid,
            "legislature": "17",
            "titreDossier": {"titre": title, "titreChemin": f"dossier_{uid.lower()}"},
            "procedureParlementaire": {
                "code": "PRJLOI",
                "libelle": "Projet de loi ordinaire",
            },
            "actesLegislatifs": {"acteLegislatif": acts},
        }
    }


def _archive(*payloads: dict) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for index, payload in enumerate(payloads):
            archive.writestr(f"dossier-{index}.json", json.dumps(payload, ensure_ascii=False))
    return output.getvalue()


def test_parse_assembly_archive_extracts_dossier_and_events() -> None:
    dossiers = parse_assembly_archive(_archive(_payload("DLR1", "Projet de loi sur le logement")))

    assert len(dossiers) == 1
    dossier = dossiers[0]
    assert dossier.uid == "DLR1"
    assert dossier.title == "Projet de loi sur le logement"
    assert dossier.last_activity == "2026-10-20"
    assert dossier.official_url.endswith("/dyn/17/dossiers/dossier_dlr1")


def test_search_understands_natural_active_query(tmp_path: Path) -> None:
    parsed = parse_assembly_archive(
        _archive(
            _payload("DLR1", "Projet de loi relatif au logement"),
            _payload("DLR2", "Projet de loi relatif à la santé"),
            _payload("DLR3", "Projet de loi relatif à l'éducation", final=True),
        )
    )

    def loader(**_kwargs):
        return parsed

    service = LegislationService(cache_path=tmp_path / "unused.zip", loader=loader)
    results = service.search("Quels textes de loi sont en cours sur le logement ?")

    assert [item.id for item in results] == ["DLR1"]
    assert results[0].status == "active"


def test_search_can_list_recent_active_texts_without_keyword(tmp_path: Path) -> None:
    parsed = parse_assembly_archive(
        _archive(
            _payload("DLR1", "Projet de loi A"),
            _payload("DLR2", "Projet de loi B", final=True),
        )
    )

    def loader(**_kwargs):
        return parsed

    service = LegislationService(cache_path=tmp_path / "unused.zip", loader=loader)
    results = service.search("Quels sont les textes en cours de vote ?")

    assert [item.id for item in results] == ["DLR1"]


def test_scope_context_is_orientation_not_evidence(tmp_path: Path) -> None:
    parsed = parse_assembly_archive(_archive(_payload("DLR1", "Projet de loi sur la santé")))

    def loader(**_kwargs):
        return parsed

    dossier = LegislationService(cache_path=tmp_path / "unused.zip", loader=loader).get("DLR1")
    assert dossier is not None
    scope = dossier.scope_context()
    assert scope["type"] == "legislative_dossier"
    assert scope["dossier_id"] == "DLR1"
    assert "assemblee_nationale_open_data" in scope["preferred_source_ids"]


def test_archive_accepts_nested_collection_and_path_url() -> None:
    payload = _payload("DLR9", "Projet de loi relatif au numérique")
    payload["dossierParlementaire"]["titreDossier"]["titreChemin"] = "/dyn/17/dossiers/numerique"
    nested = {"export": {"dossiers": [payload]}}

    dossiers = parse_assembly_archive(_archive(nested))

    assert [item.uid for item in dossiers] == ["DLR9"]
    assert dossiers[0].official_url == "https://www.assemblee-nationale.fr/dyn/17/dossiers/numerique"


def test_discussion_words_do_not_become_topic_keywords(tmp_path: Path) -> None:
    parsed = parse_assembly_archive(
        _archive(
            _payload("DLR1", "Projet de loi relatif au logement"),
            _payload("DLR2", "Projet de loi relatif à la santé"),
        )
    )

    def loader(**_kwargs):
        return parsed

    service = LegislationService(cache_path=tmp_path / "unused.zip", loader=loader)
    results = service.search("Quels textes sont actuellement en discussion sur la santé ?")

    assert [item.id for item in results] == ["DLR2"]

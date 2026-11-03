# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import io
import json
import zipfile
from pathlib import Path

from acfpf.data.assemblee_legislation import AssemblyLegislationError, parse_assembly_archive
from acfpf.data.senat_legislation import (
    SenateLegislationError,
    SenateLegislativeDossier,
    fetch_senate_csv,
    load_senate_dossiers,
    parse_senate_csv,
)
from acfpf.legislation import LegislationService

SENATE_HEADER = (
    "Titre;Type de dossier;Date initiale;URL du dossier;État du dossier;"
    "Décision du Conseil constitutionnel;Date de la décision du Conseil constitutionnel;"
    "Date de promulgation;Numéro de la loi;Thèmes\n"
)


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


def _senate_csv(*rows: str) -> bytes:
    return (SENATE_HEADER + "\n".join(rows) + "\n").encode("latin-1")


def _senate(
    title: str,
    *,
    uid: str = "senat:pjl25-913",
    state: str = "Première lecture au Sénat",
    law_number: str | None = None,
) -> SenateLegislativeDossier:
    return SenateLegislativeDossier(
        uid=uid,
        title=title,
        type_label="Projet de loi",
        initial_date="2026-10-01",
        official_url=f"https://www.senat.fr/dossier-legislatif/{uid.split(':', 1)[1]}.html",
        state=state,
        constitutional_result=None,
        constitutional_date=None,
        promulgation_date="2026-10-30" if "Promulgué" in state else None,
        law_number=law_number,
        themes=("Logement et urbanisme",),
        retrieved_at="2026-11-03T10:00:00+00:00",
    )


def test_parse_assembly_archive_extracts_dossier_and_events() -> None:
    dossiers = parse_assembly_archive(_archive(_payload("DLR1", "Projet de loi sur le logement")))

    assert len(dossiers) == 1
    dossier = dossiers[0]
    assert dossier.uid == "DLR1"
    assert dossier.title == "Projet de loi sur le logement"
    assert dossier.last_activity == "2026-10-20"
    assert dossier.official_url.endswith("/dyn/17/dossiers/dossier_dlr1")


def test_parse_senate_csv_reads_latin1_semicolon_export() -> None:
    blob = _senate_csv(
        '"Projet de loi relatif à la santé";Projet de loi;22/07/2026;'
        'https://www.senat.fr/dossier-legislatif/pjl25-913.html;Première lecture au Sénat;;;;;'
        '"Questions sociales et santé|Société"'
    )

    dossiers = parse_senate_csv(blob, retrieved_at="2026-11-03T10:00:00+00:00")

    assert len(dossiers) == 1
    dossier = dossiers[0]
    assert dossier.uid == "senat:pjl25-913"
    assert dossier.title == "Projet de loi relatif à la santé"
    assert dossier.initial_date == "2026-07-22"
    assert dossier.state == "Première lecture au Sénat"
    assert dossier.themes == ("Questions sociales et santé", "Société")
    assert dossier.retrieved_at == "2026-11-03T10:00:00+00:00"


def test_parse_senate_csv_reads_promulgation_metadata() -> None:
    blob = _senate_csv(
        '"Proposition de loi relative au sport";Proposition de loi;01/02/2026;'
        'https://www.senat.fr/dossier-legislatif/ppl25-100.html;Promulgué;Conforme;'
        '15/07/2026;07/08/2026;2026-777;Sports'
    )

    dossier = parse_senate_csv(blob)[0]

    assert dossier.promulgation_date == "2026-08-07"
    assert dossier.law_number == "2026-777"
    assert dossier.constitutional_date == "2026-07-15"
    assert dossier.constitutional_result == "Conforme"


class FakeSenateResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


class FakeSenateSession:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.last_url = None
        self.last_timeout = None

    def get(self, url, *, timeout):
        self.last_url = url
        self.last_timeout = timeout
        return FakeSenateResponse(self.content)


def test_fetch_senate_csv_uses_official_https_endpoint() -> None:
    content = _senate_csv(
        'Titre;Projet de loi;2026-01-01;https://www.senat.fr/dossier-legislatif/pjl25-1.html;'
        'Première lecture au Sénat;;;;;Budget'
    )
    session = FakeSenateSession(content)

    assert fetch_senate_csv(session=session, timeout=4.0) == content
    assert session.last_url == "https://data.senat.fr/data/dosleg/dossiers-legislatifs.csv"
    assert session.last_timeout == 4.0


def test_load_senate_dossiers_uses_fresh_cache(tmp_path: Path) -> None:
    content = _senate_csv(
        'Titre;Projet de loi;2026-01-01;https://www.senat.fr/dossier-legislatif/pjl25-1.html;'
        'Première lecture au Sénat;;;;;Budget'
    )
    cache = tmp_path / "senat.csv"
    cache.write_bytes(content)

    dossiers = load_senate_dossiers(cache_path=cache)

    assert isinstance(dossiers[0], SenateLegislativeDossier)
    assert dossiers[0].from_cache is True


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


def test_assembly_and_senate_same_title_merge_into_one_dossier(tmp_path: Path) -> None:
    assembly = parse_assembly_archive(
        _archive(_payload("DLR1", "Projet de loi relatif au logement"))
    )
    senate = (_senate("Projet de loi relatif au logement", state="Promulgué", law_number="2026-999"),)

    def assembly_loader(**_kwargs):
        return assembly

    def senate_loader(**_kwargs):
        return senate

    service = LegislationService(
        cache_path=tmp_path / "assembly.zip",
        senate_cache_path=tmp_path / "senat.csv",
        loader=assembly_loader,
        senate_loader=senate_loader,
    )
    results = service.search("logement", status="all")

    assert len(results) == 1
    dossier = results[0]
    assert dossier.id == "DLR1"
    assert dossier.status == "promulgated"
    assert dossier.law_number == "2026-999"
    assert {source.source_id for source in dossier.sources} == {
        "assemblee_nationale_open_data",
        "senat_open_data",
    }
    assert dossier.themes == ("Logement et urbanisme",)
    assert "senat_open_data" in dossier.scope_context()["preferred_source_ids"]


def test_senate_state_can_close_dossier_that_assembly_looks_active(tmp_path: Path) -> None:
    assembly = parse_assembly_archive(
        _archive(_payload("DLR1", "Proposition de loi relative au logement"))
    )
    senate = (_senate("Proposition de loi relative au logement", state="Non adopté"),)

    service = LegislationService(
        cache_path=tmp_path / "assembly.zip",
        senate_cache_path=tmp_path / "senat.csv",
        loader=lambda **_kwargs: assembly,
        senate_loader=lambda **_kwargs: senate,
    )

    assert service.search("logement", status="active") == ()
    closed = service.search("logement", status="closed_without_law")
    assert len(closed) == 1
    assert closed[0].status_label == "Clos sans promulgation"


def test_senate_only_dossier_is_searchable(tmp_path: Path) -> None:
    senate = (_senate("Projet de loi relatif aux ingérences étrangères"),)
    service = LegislationService(
        cache_path=tmp_path / "assembly.zip",
        senate_cache_path=tmp_path / "senat.csv",
        loader=lambda **_kwargs: (),
        senate_loader=lambda **_kwargs: senate,
    )

    results = service.search("ingérences", status="active")

    assert [item.id for item in results] == ["senat:pjl25-913"]
    assert results[0].current_chamber == "Sénat"


def test_one_legislative_source_can_fail_without_hiding_the_other(tmp_path: Path) -> None:
    assembly = parse_assembly_archive(_archive(_payload("DLR1", "Projet de loi A")))

    def failing_senate(**_kwargs):
        raise SenateLegislationError("simulated DOSLEG failure")

    service = LegislationService(
        cache_path=tmp_path / "assembly.zip",
        senate_cache_path=tmp_path / "senat.csv",
        loader=lambda **_kwargs: assembly,
        senate_loader=failing_senate,
    )

    assert [item.id for item in service.search(status="all")] == ["DLR1"]
    assert service.warnings() == ("Sénat : simulated DOSLEG failure",)


def test_senate_remains_available_if_assembly_fails(tmp_path: Path) -> None:
    def failing_assembly(**_kwargs):
        raise AssemblyLegislationError("simulated Assemblée failure")

    senate = (_senate("Projet de loi B"),)
    service = LegislationService(
        cache_path=tmp_path / "assembly.zip",
        senate_cache_path=tmp_path / "senat.csv",
        loader=failing_assembly,
        senate_loader=lambda **_kwargs: senate,
    )

    assert [item.id for item in service.search(status="all")] == ["senat:pjl25-913"]
    assert service.warnings() == ("Assemblée nationale : simulated Assemblée failure",)

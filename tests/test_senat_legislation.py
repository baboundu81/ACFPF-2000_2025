# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from pathlib import Path

import acfpf.data.senat_legislation as senat


HEADER = (
    "Titre;Type de dossier;Date initiale;URL du dossier;État du dossier;"
    "Décision du Conseil constitutionnel;Date de la décision du Conseil constitutionnel;"
    "Date de promulgation;Numéro de la loi;Thèmes\n"
)


def _csv(*rows: str) -> bytes:
    return (HEADER + "\n".join(rows) + "\n").encode("latin-1")


def test_parse_senate_csv_reads_latin1_semicolon_export() -> None:
    blob = _csv(
        '"Projet de loi relatif à la santé";Projet de loi;22/07/2026;'
        'https://www.senat.fr/dossier-legislatif/pjl25-913.html;Première lecture au Sénat;;;;;'
        '"Questions sociales et santé|Société"'
    )

    dossiers = senat.parse_senate_csv(blob, retrieved_at="2026-11-03T10:00:00+00:00")

    assert len(dossiers) == 1
    dossier = dossiers[0]
    assert dossier.uid == "senat:pjl25-913"
    assert dossier.title == "Projet de loi relatif à la santé"
    assert dossier.initial_date == "2026-07-22"
    assert dossier.state == "Première lecture au Sénat"
    assert dossier.themes == ("Questions sociales et santé", "Société")
    assert dossier.retrieved_at == "2026-11-03T10:00:00+00:00"


def test_parse_senate_csv_reads_promulgation_metadata() -> None:
    blob = _csv(
        '"Proposition de loi relative au sport";Proposition de loi;01/02/2026;'
        'https://www.senat.fr/dossier-legislatif/ppl25-100.html;Promulgué;Conforme;'
        '15/07/2026;07/08/2026;2026-777;Sports'
    )

    dossier = senat.parse_senate_csv(blob)[0]

    assert dossier.promulgation_date == "2026-08-07"
    assert dossier.law_number == "2026-777"
    assert dossier.constitutional_date == "2026-07-15"
    assert dossier.constitutional_result == "Conforme"


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.last_url = None
        self.last_timeout = None

    def get(self, url, *, timeout):
        self.last_url = url
        self.last_timeout = timeout
        return FakeResponse(self.content)


def test_fetch_senate_csv_uses_official_https_endpoint() -> None:
    content = _csv(
        'Titre;Projet de loi;2026-01-01;https://www.senat.fr/dossier-legislatif/pjl25-1.html;'
        'Première lecture au Sénat;;;;;Budget'
    )
    session = FakeSession(content)

    assert senat.fetch_senate_csv(session=session, timeout=4.0) == content
    assert session.last_url == "https://data.senat.fr/data/dosleg/dossiers-legislatifs.csv"
    assert session.last_timeout == 4.0


def test_load_senate_dossiers_uses_fresh_cache(tmp_path: Path) -> None:
    content = _csv(
        'Titre;Projet de loi;2026-01-01;https://www.senat.fr/dossier-legislatif/pjl25-1.html;'
        'Première lecture au Sénat;;;;;Budget'
    )
    cache = tmp_path / "senat.csv"
    cache.write_bytes(content)

    dossiers = senat.load_senate_dossiers(cache_path=cache)

    assert isinstance(dossiers[0], senat.SenateLegislativeDossier)
    assert dossiers[0].from_cache is True

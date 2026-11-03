# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import pytest

from acfpf.data.assemblee_amendments import (
    AssemblyAmendmentsError,
    amendment_csv_url,
    parse_assembly_amendments_csv,
)


def sample_csv() -> bytes:
    return (
        "Numéro de l'amendement;Instance;Désignation de l'article;Auteur;"
        "Sort de l'amendement;URL Amendement format XML\n"
        "I-42;Séance publique;Article 12;Mme Alice Martin;Adopté;"
        "https://www.assemblee-nationale.fr/dyn/opendata/AMANR5L17N000042.xml\n"
        "I-43;Commission des finances;Après l'article 12;M. Bob Dupont;Non soutenu;"
        "https://www.assemblee-nationale.fr/dyn/opendata/AMANR5L17N000043.xml\n"
    ).encode("utf-8")


def test_parse_amendments_csv_preserves_official_fields_and_builds_page_url() -> None:
    items = parse_assembly_amendments_csv(
        sample_csv(),
        legislature="17",
        dossier_id="54629",
        retrieved_at="2026-11-03T12:00:00+00:00",
    )

    assert len(items) == 2
    first = items[0]
    assert first.uid == "AMANR5L17N000042"
    assert first.number == "I-42"
    assert first.instance == "Séance publique"
    assert first.article == "Article 12"
    assert first.author == "Mme Alice Martin"
    assert first.fate == "Adopté"
    assert first.dossier_id == "54629"
    assert first.legislature == "17"
    assert first.official_url.endswith("/dyn/17/amendements/AMANR5L17N000042")
    assert first.xml_url.endswith("AMANR5L17N000042.xml")


def test_parse_amendments_csv_accepts_cp1252_and_normalized_headers() -> None:
    raw = (
        "Numero amendement;Instance;Article;Auteur;Sort;URL Amendement XML\n"
        "77;Commission;Article premier;Gouvernement;Rejeté;"
        "https://www.assemblee-nationale.fr/dyn/opendata/AMANR5L17N000077.xml\n"
    ).encode("cp1252")

    items = parse_assembly_amendments_csv(
        raw,
        legislature="17",
        dossier_id="12345",
    )

    assert [item.number for item in items] == ["77"]
    assert items[0].fate == "Rejeté"


def test_parse_amendments_csv_deduplicates_same_uid() -> None:
    blob = sample_csv() + (
        "I-42;Séance publique;Article 12;Mme Alice Martin;Adopté;"
        "https://www.assemblee-nationale.fr/dyn/opendata/AMANR5L17N000042.xml\n"
    ).encode("utf-8")

    items = parse_assembly_amendments_csv(blob, legislature="17", dossier_id="54629")

    assert [item.uid for item in items] == ["AMANR5L17N000042", "AMANR5L17N000043"]


def test_parse_amendments_csv_rejects_missing_required_url_column() -> None:
    raw = "Numéro de l'amendement;Auteur\n42;Mme Alice Martin\n".encode()

    with pytest.raises(AssemblyAmendmentsError, match="Required amendment CSV column"):
        parse_assembly_amendments_csv(raw, legislature="17", dossier_id="54629")


def test_amendment_csv_url_is_scoped_to_legislature_and_dossier() -> None:
    url = amendment_csv_url("17", "54629")

    assert "/repository/17/dossiers_legislatifs_opendata/54629/libre_office.csv" in url


def test_amendment_csv_url_rejects_non_numeric_identifiers() -> None:
    with pytest.raises(ValueError):
        amendment_csv_url("17", "DLR5L17N54629")

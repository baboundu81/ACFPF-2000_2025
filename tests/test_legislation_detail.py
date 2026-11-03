# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from pathlib import Path

from acfpf.data.assemblee_amendment_detail import AssemblyAmendmentDetail
from acfpf.data.assemblee_amendments import AssemblyAmendmentIndexItem
from acfpf.legislation import LegislativeDossier, LegislativeSourceRef
from acfpf.legislation_detail import (
    AmendmentService,
    assembly_numeric_dossier_id,
    normalize_amendment_fate,
)


def assembly_dossier() -> LegislativeDossier:
    return LegislativeDossier(
        id="DLR5L17N54629",
        title="Projet de loi de finances pour 2027",
        legislature="17",
        procedure_code="PRJLOI",
        procedure_label="Projet de loi",
        status="active",
        status_label="En cours",
        current_stage="Séance publique",
        last_activity="2026-11-03",
        official_url="https://www.assemblee-nationale.fr/dyn/17/dossiers/PLF_2027",
        source_url="https://data.assemblee-nationale.fr/",
        sources=(
            LegislativeSourceRef(
                source_id="assemblee_nationale_open_data",
                label="Assemblée nationale",
                chamber="Assemblée nationale",
                official_url="https://www.assemblee-nationale.fr/dyn/17/dossiers/PLF_2027",
            ),
        ),
    )


def senate_only_dossier() -> LegislativeDossier:
    return LegislativeDossier(
        id="ppl24-123",
        title="Proposition de loi de test",
        legislature="",
        procedure_code=None,
        procedure_label="Proposition de loi",
        status="active",
        status_label="En cours",
        current_stage="En commission",
        last_activity="2026-10-20",
        official_url="https://www.senat.fr/dossier-legislatif/ppl24-123.html",
        source_url="https://data.senat.fr/",
        source_id="senat_open_data",
        sources=(
            LegislativeSourceRef(
                source_id="senat_open_data",
                label="Sénat",
                chamber="Sénat",
                official_url="https://www.senat.fr/dossier-legislatif/ppl24-123.html",
            ),
        ),
    )


def amendment_item(fate: str = "Adopté") -> AssemblyAmendmentIndexItem:
    return AssemblyAmendmentIndexItem(
        uid="AMANR5L17N000042",
        number="I-42",
        instance="Séance publique",
        article="Article 12",
        author="Mme Alice Martin",
        fate=fate,
        xml_url="https://www.assemblee-nationale.fr/dyn/opendata/AMANR5L17N000042.xml",
        official_url="https://www.assemblee-nationale.fr/dyn/17/amendements/AMANR5L17N000042",
        legislature="17",
        dossier_id="54629",
        retrieved_at="2026-11-03T12:00:00+00:00",
    )


def amendment_detail() -> AssemblyAmendmentDetail:
    return AssemblyAmendmentDetail(
        uid="AMANR5L17N000042",
        dispositif="Remplacer 15 % par 12 %.",
        purpose="Limiter la hausse proposée.",
        sort_order="000042",
        source_url="https://www.assemblee-nationale.fr/dyn/opendata/AMANR5L17N000042.xml",
        retrieved_at="2026-11-03T14:00:00+00:00",
    )


def test_extracts_numeric_assembly_dossier_id_only_when_source_is_present() -> None:
    assert assembly_numeric_dossier_id(assembly_dossier()) == "54629"
    assert assembly_numeric_dossier_id(senate_only_dossier()) is None


def test_amendment_fate_normalization_preserves_distinct_non_adopted_outcomes() -> None:
    assert normalize_amendment_fate("Adopté")[0] == "adopted"
    assert normalize_amendment_fate("Rejeté")[0] == "rejected"
    assert normalize_amendment_fate("Retiré")[0] == "withdrawn"
    assert normalize_amendment_fate("Non soutenu")[0] == "not_supported"
    assert normalize_amendment_fate("Tombé")[0] == "fallen"
    assert normalize_amendment_fate("Irrecevable 40")[0] == "inadmissible"
    assert normalize_amendment_fate("Discuté")[0] == "discussed"
    assert normalize_amendment_fate(None)[0] == "pending"


def test_service_calls_loader_with_deterministic_numeric_id_and_cache_path(tmp_path: Path) -> None:
    calls = []

    def loader(**kwargs):
        calls.append(kwargs)
        return (amendment_item(),)

    service = AmendmentService(cache_dir=tmp_path, loader=loader)
    collection = service.for_dossier(assembly_dossier())

    assert calls[0]["legislature"] == "17"
    assert calls[0]["dossier_id"] == "54629"
    assert calls[0]["cache_path"] == tmp_path / "assembly-17-54629.csv"
    assert collection.available is True
    assert collection.amendments[0].fate == "adopted"
    assert collection.amendments[0].fate_raw == "Adopté"
    assert collection.amendments[0].article == "Article 12"
    assert collection.source_url.startswith("https://data.assemblee-nationale.fr/")


def test_service_returns_explicit_unavailable_collection_for_senate_only_dossier(tmp_path: Path) -> None:
    called = False

    def loader(**_kwargs):
        nonlocal called
        called = True
        return ()

    collection = AmendmentService(cache_dir=tmp_path, loader=loader).for_dossier(
        senate_only_dossier()
    )

    assert called is False
    assert collection.available is False
    assert collection.amendments == ()
    assert "Assemblée nationale" in (collection.reason or "")


def test_service_keeps_unknown_fate_instead_of_guessing(tmp_path: Path) -> None:
    def loader(**_kwargs):
        return (amendment_item("Mise en réserve"),)

    collection = AmendmentService(cache_dir=tmp_path, loader=loader).for_dossier(assembly_dossier())

    assert collection.amendments[0].fate == "unknown"
    assert collection.amendments[0].fate_raw == "Mise en réserve"


def test_detail_for_uses_url_from_official_index_and_merges_text(tmp_path: Path) -> None:
    detail_calls = []

    def loader(**_kwargs):
        return (amendment_item(),)

    def detail_loader(**kwargs):
        detail_calls.append(kwargs)
        return amendment_detail()

    service = AmendmentService(
        cache_dir=tmp_path,
        loader=loader,
        detail_loader=detail_loader,
    )
    detail = service.detail_for(assembly_dossier(), "AMANR5L17N000042")

    assert detail is not None
    assert detail.amendment.number == "I-42"
    assert detail.dispositif == "Remplacer 15 % par 12 %."
    assert detail.purpose == "Limiter la hausse proposée."
    assert detail_calls[0]["url"].endswith("AMANR5L17N000042.xml")
    assert detail_calls[0]["cache_path"] == tmp_path / "details" / "AMANR5L17N000042.xml"


def test_detail_for_unknown_amendment_does_not_call_detail_loader(tmp_path: Path) -> None:
    called = False

    def loader(**_kwargs):
        return (amendment_item(),)

    def detail_loader(**_kwargs):
        nonlocal called
        called = True
        return amendment_detail()

    service = AmendmentService(
        cache_dir=tmp_path,
        loader=loader,
        detail_loader=detail_loader,
    )

    assert service.detail_for(assembly_dossier(), "AMANR5L17N999999") is None
    assert called is False

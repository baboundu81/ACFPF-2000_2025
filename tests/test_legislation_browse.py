# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import pytest

from acfpf.legislation import LegislativeDossier, LegislativeSourceRef
from acfpf.legislation_browse import browse_legislation, canonical_text_type


class FakeInventoryService:
    def __init__(self, *dossiers: LegislativeDossier) -> None:
        self.dossiers = dossiers

    def _all(self, *, refresh: bool = False):
        assert isinstance(refresh, bool)
        return self.dossiers


def _dossier(
    dossier_id: str,
    title: str,
    *,
    chamber: str,
    stage_label: str,
    theme: str,
    procedure: str,
    year: int,
    status: str = "active",
) -> LegislativeDossier:
    source_id = "senat_open_data" if chamber == "Sénat" else "assemblee_nationale_open_data"
    return LegislativeDossier(
        id=dossier_id,
        title=title,
        legislature="17",
        procedure_code=None,
        procedure_label=procedure,
        status=status,
        status_label="En cours" if status == "active" else "Promulgué",
        current_stage=stage_label,
        current_chamber=chamber,
        last_activity=f"{year}-10-20",
        initial_date=f"{year}-02-01",
        official_url=f"https://example.test/{dossier_id}",
        source_url="https://example.test",
        source_id=source_id,
        themes=(theme,),
        sources=(
            LegislativeSourceRef(
                source_id=source_id,
                label=chamber,
                chamber=chamber,
                official_url=f"https://example.test/{dossier_id}",
            ),
        ),
    )


def sample_inventory() -> FakeInventoryService:
    return FakeInventoryService(
        _dossier(
            "D1",
            "Projet de loi relatif à la santé",
            chamber="Sénat",
            stage_label="Première lecture au Sénat",
            theme="Santé",
            procedure="Projet de loi ordinaire",
            year=2026,
        ),
        _dossier(
            "D2",
            "Proposition de loi relative à l'école",
            chamber="Assemblée nationale",
            stage_label="Examen en commission",
            theme="Éducation",
            procedure="Proposition de loi",
            year=2025,
        ),
        _dossier(
            "D3",
            "Projet de loi relatif au logement",
            chamber="Assemblée nationale",
            stage_label="Promulgation de la loi",
            theme="Logement",
            procedure="Projet de loi",
            year=2024,
            status="promulgated",
        ),
    )


def test_browse_builds_facets_from_complete_inventory() -> None:
    result = browse_legislation(sample_inventory(), status="all")

    assert result.facets.chambers == ("Assemblée nationale", "Sénat")
    assert [item.code for item in result.facets.stages] == ["committee", "promulgated", "plenary"]
    assert result.facets.themes == ("Éducation", "Logement", "Santé")
    assert result.facets.text_types == ("Projet de loi", "Proposition de loi")
    assert result.facets.min_year == 2024
    assert result.facets.max_year == 2026


def test_browse_combines_chamber_stage_theme_type_and_period_filters() -> None:
    result = browse_legislation(
        sample_inventory(),
        status="all",
        chamber="Sénat",
        stage="plenary",
        theme="Santé",
        text_type="Projet de loi",
        from_year=2026,
        to_year=2026,
    )

    assert [item.id for item in result.results] == ["D1"]


def test_browse_stage_filter_uses_stable_code_not_raw_label() -> None:
    result = browse_legislation(sample_inventory(), status="all", stage="committee")

    assert [item.id for item in result.results] == ["D2"]


def test_browse_keeps_natural_language_relevance_before_facets() -> None:
    result = browse_legislation(sample_inventory(), "Quels textes concernent la santé ?", status="all")

    assert [item.id for item in result.results] == ["D1"]


def test_browse_period_uses_start_year() -> None:
    result = browse_legislation(sample_inventory(), status="all", from_year=2025, to_year=2025)

    assert [item.id for item in result.results] == ["D2"]


def test_browse_rejects_inverted_period() -> None:
    with pytest.raises(ValueError, match="année de début"):
        browse_legislation(sample_inventory(), status="all", from_year=2026, to_year=2025)


def test_canonical_text_type_coarsens_assembly_procedure_label() -> None:
    dossier = sample_inventory().dossiers[0]

    assert canonical_text_type(dossier) == "Projet de loi"
